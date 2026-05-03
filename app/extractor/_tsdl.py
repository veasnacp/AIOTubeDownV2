import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from asyncio import Semaphore
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiofiles
from curl_cffi import requests
from tqdm.asyncio import tqdm as async_tqdm

from ._request import AsyncBaseRequest, BrowserTypeLiteral, Response


@dataclass
class ProgressData:
    """Progress data structure for callbacks"""
    current: int
    total: int
    description: str
    percentage: float
    timestamp: datetime = datetime.now()
    downloaded: int = 0
    failed: int = 0
    batch_num: int = 0
    total_batches: int = 0

    @property
    def remaining(self) -> int:
        """Get remaining items"""
        return self.total - self.current

    @property
    def speed(self) -> float:
        """Calculate speed"""
        total_completed = self.downloaded + self.failed
        if total_completed == 0:
            return 0.0
        return (self.downloaded / total_completed) * 100


class ProgressCallbackTqdm:
    """Wrapper for async_tqdm with custom progress callback support using ProgressData"""

    def __init__(
        self,
        total: int,
        desc: str = "",
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
        batch_num: int = 0,
        total_batches: int = 0
    ):
        """
        Args:
            total: Total number of tasks
            desc: Description of the progress
            progress_callback: Callback function with signature (ProgressData)
            batch_num: Current batch number (for batch processing)
            total_batches: Total number of batches
        """
        self.total = total
        self.desc = desc
        self.progress_callback = progress_callback
        self.current = 0
        self.downloaded = 0
        self.failed = 0
        self.batch_num = batch_num
        self.total_batches = total_batches
        self.start_time = datetime.now()

    async def __aenter__(self):
        self.pbar = async_tqdm(total=self.total, desc=self.desc)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Emit final progress update
        if self.progress_callback:
            final_data = ProgressData(
                current=self.current,
                total=self.total,
                description=f"{self.desc} - Complete",
                percentage=100.0 if self.current == self.total else (
                    self.current / self.total) * 100,
                timestamp=datetime.now(),
                downloaded=self.downloaded,
                failed=self.failed,
                batch_num=self.batch_num,
                total_batches=self.total_batches
            )
            self.progress_callback(final_data)

    def update(self, n: int = 1, success: bool = True):
        """Update progress by n steps

        Args:
            n: Number of steps to update
            success: Whether the update was successful (for tracking downloaded/failed)
        """
        self.current += n
        if success:
            self.downloaded += 1
        else:
            self.failed += 1

        self.pbar.update(n)

        # Call custom callback if provided
        if self.progress_callback:
            progress_data = ProgressData(
                current=self.current,
                total=self.total,
                description=self.desc,
                percentage=(self.current / self.total) *
                100 if self.total > 0 else 0,
                timestamp=datetime.now(),
                downloaded=self.downloaded,
                failed=self.failed,
                batch_num=self.batch_num,
                total_batches=self.total_batches
            )
            self.progress_callback(progress_data)

    def update_result(self, result: Any, is_success: bool = True):
        """Update progress with result tracking"""
        self.update(n=1, success=is_success)

    def set_description(self, desc: str):
        """Update the description"""
        self.desc = desc
        self.pbar.set_description(desc)
        if self.progress_callback:
            progress_data = ProgressData(
                current=self.current,
                total=self.total,
                description=desc,
                percentage=(self.current / self.total) *
                100 if self.total > 0 else 0,
                timestamp=datetime.now(),
                downloaded=self.downloaded,
                failed=self.failed,
                batch_num=self.batch_num,
                total_batches=self.total_batches
            )
            self.progress_callback(progress_data)


class DownloadContext:
    """Context manager for tracking download progress across multiple batches"""

    def __init__(
        self,
        total_segments: int,
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
        description: str = "Downloading segments"
    ):
        self.total_segments = total_segments
        self.progress_callback = progress_callback
        self.description = description
        self.completed = 0
        self.downloaded = 0
        self.failed = 0
        self.current_batch = 0
        self.total_batches = 0

    def set_total_batches(self, total_batches: int):
        """Set total number of batches"""
        self.total_batches = total_batches

    def update(self, success: bool = True, batch_num: int = 0):
        """Update overall progress"""
        self.completed += 1
        if success:
            self.downloaded += 1
        else:
            self.failed += 1

        if self.progress_callback:
            progress_data = ProgressData(
                current=self.completed,
                total=self.total_segments,
                description=self.description,
                percentage=(self.completed / self.total_segments) *
                100 if self.total_segments > 0 else 0,
                timestamp=datetime.now(),
                downloaded=self.downloaded,
                failed=self.failed,
                batch_num=batch_num,
                total_batches=self.total_batches
            )
            self.progress_callback(progress_data)

    def create_batch_progress(self, batch_total: int, batch_num: int, batch_desc: str = "") -> 'ProgressCallbackTqdm':
        """Create a ProgressCallbackTqdm instance for a batch"""
        return ProgressCallbackTqdm(
            total=batch_total,
            desc=batch_desc or f"Batch {batch_num}/{self.total_batches}",
            progress_callback=self.progress_callback,
            batch_num=batch_num,
            total_batches=self.total_batches
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Emit final progress update
        if self.progress_callback:
            final_data = ProgressData(
                current=self.completed,
                total=self.total_segments,
                description=f"{self.description} - Complete",
                percentage=100.0,
                timestamp=datetime.now(),
                downloaded=self.downloaded,
                failed=self.failed,
                batch_num=self.total_batches,
                total_batches=self.total_batches
            )
            self.progress_callback(final_data)


class AsyncTSVideoDownloader(AsyncBaseRequest):
    """Advanced TS video downloader with parallel downloads and merging capabilities"""

    def __init__(
        self,
        max_concurrent: int = 5,
        temp_dir_name: str = "temp_segments",
        proxies: Optional[List[str]] = None,
        impersonate: BrowserTypeLiteral = "safari170",
        timeout: int = 30
    ):
        super().__init__(proxies, impersonate, timeout)
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        self.custom_temp_segments_dir_name: Optional[str] = None
        with tempfile.TemporaryDirectory() as tmp_dirname:
            temp_path = Path(tmp_dirname).parent.joinpath(
                'aio_%s' % Path(tmp_dirname).name)
            self.set_temp_dir(str(temp_path), temp_dir_name)
        self.https_headers: Optional[dict] = None
        self.https_impersonate: BrowserTypeLiteral = "safari172_ios"
        self.overwrite = False
        self.chunk_size: Optional[int] = None  # 10485760
        self.cancelled = False

    def set_temp_dir(self, temp_dir: str, temp_dir_name: Optional[str] = None):
        self.temp_dir = Path(temp_dir)
        if temp_dir_name:
            self.temp_segments_dir = self.temp_dir.joinpath(temp_dir_name)
        else:
            self.temp_segments_dir = self.temp_dir

    def parse_m3u8(
        self,
        content: str,
        pattern: str | re.Pattern[str] | Callable[[str], List[str]],
    ):
        """Parse m3u8 playlist and extract TS segment URLs"""
        if callable(pattern):
            segment_urls = pattern(content)
        else:
            segment_urls = []
            for m in re.finditer(
                pattern,
                content,
            ):
                segment_urls.append(m.group(0))

        if not segment_urls:
            self.logger.info(f"❌ No streams found")
            return None

        return segment_urls

    async def download_segment_async(
        self, url: str, index: int, retries: int = 3,
        filename: Optional[str | Callable[[int], str]] = None,
        **req_kwargs
    ) -> Optional[Path]:
        """Download a single TS segment asynchronously with retry logic"""
        if filename:
            if callable(filename):
                filename = filename(index)
            file_path = self.temp_segments_dir / filename
        else:
            file_path = self.temp_segments_dir / f"segment_{index:04d}.ts"

        async with self.semaphore:  # Limit concurrent downloads
            for attempt in range(retries):
                try:
                    response = await self.request(
                        url,
                        headers=self.https_headers,
                        impersonate=self.https_impersonate,
                        retries=0,
                        **req_kwargs
                    )
                    if not response:
                        continue

                    if isinstance(response, Response) and response.status_code == 200:
                        # Write file asynchronously
                        if self.overwrite and file_path.exists() and file_path.is_file():
                            file_path.unlink()

                        # total_size = int(
                        #     response.headers.get('content-length', 0))
                        # chunk_size = self.chunk_size or 64 * 1024
                        # downloaded_size = 0

                        # self.logger.info(
                        #     f"📥 Downloading segment {index}: {total_size / (1024*1024):.2f} MB")

                        # check cancelled status from req_kwargs
                        if self.cancelled:
                            return None

                        if self.chunk_size:
                            async with aiofiles.open(file_path, 'wb') as f:
                                async for chunk in response.aiter_content(chunk_size=self.chunk_size):
                                    # check cancelled status from req_kwargs
                                    if self.cancelled:
                                        try:
                                            file_path.unlink()
                                        except:
                                            pass
                                        return None

                                    if chunk:
                                        await f.write(chunk)
                                        # downloaded_size += len(chunk)

                                        # # print("downloaded_size", downloaded_size,
                                        # #       "chunk_size * 100", chunk_size * 100)

                                        # # Log progress for large files
                                        # if total_size > 0 and downloaded_size % (chunk_size * 100) == 0:
                                        #     progress = (
                                        #         downloaded_size / total_size) * 100
                                        #     self.logger.info(
                                        #         f"Segment {index}: {progress:.1f}% ({downloaded_size}/{total_size} bytes)")
                        else:
                            async with aiofiles.open(file_path, 'wb') as f:
                                await f.write(response.content)
                        return file_path
                    else:
                        if not (hasattr(self, 'with_custom_response') and self.with_custom_response):
                            self.logger.error(
                                f"❌ Failed to download segment {index}: HTTP {response.status_code}")
                except Exception as e:
                    self.logger.error(
                        f"❌ Error downloading segment {index} (attempt {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        # Exponential backoff
                        await asyncio.sleep(2 ** attempt)

            return None

    async def download_segments_simple(
        self, segments: List[str],
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
        desc: str = "Downloading segments",
        filename: Optional[str | Callable[[int], str]] = None,
        filename_list: Optional[List[str]] = None,
        **req_kwargs
    ) -> List[Path]:
        """Ultra-simple sequential download (one at a time)

        This is the simplest version without any batching logic.

        Args:
            segments: List of segment URLs to download
            progress_callback: Callback function that receives ProgressData updates
            desc: Description for the download process

        Returns:
            Sorted list of downloaded file paths
        """
        downloaded_files = []
        total_segments = len(segments)

        async with DownloadContext(
            total_segments=total_segments,
            progress_callback=progress_callback,
            description=desc
        ) as ctx:
            ctx.set_total_batches(1)

            async with ProgressCallbackTqdm(
                total=total_segments,
                desc=desc,
                progress_callback=progress_callback,
                batch_num=1,
                total_batches=1
            ) as pbar:

                for idx, segment in enumerate(segments):
                    if self.cancelled:
                        self.logger.info(
                            "Download segments stopped")
                        break

                    if filename_list:
                        filename = filename_list[idx]
                    result = await self.download_segment_async(segment, idx, filename=filename, **req_kwargs)

                    if result:
                        downloaded_files.append(result)
                        pbar.update(n=1, success=True)
                        ctx.update(success=True, batch_num=1)
                    else:
                        pbar.update(n=1, success=False)
                        ctx.update(success=False, batch_num=1)

        return sorted(downloaded_files)

    # async def download_segments_batch(self, segments: List[str], batch_size: int = 20) -> List[Path]:
    #     """Download TS segments in batches with async/await"""
    #     downloaded_files = []

    #     # Process in batches to avoid overwhelming the system
    #     for i in range(0, len(segments), batch_size):
    #         batch = segments[i:i + batch_size]
    #         batch_indices = range(i, min(i + batch_size, len(segments)))

    #         # Create tasks for current batch
    #         tasks = [
    #             self.download_segment_async(url, idx)
    #             for url, idx in zip(batch, batch_indices)
    #         ]

    #         # Execute batch with progress tracking
    #         for coro in async_tqdm.as_completed(tasks, total=len(batch), desc=f"Batch {i//batch_size + 1}"):
    #             result = await coro
    #             if result:
    #                 downloaded_files.append(result)

    #     return sorted(downloaded_files)

    async def download_segments_batch(
        self, segments: List[str],
        batch_size: int = 20,
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
        desc: str = "Downloading segments",
        filename: Optional[str | Callable[[int], str]] = None,
        filename_list: Optional[List[str]] = None,
        **req_kwargs
    ) -> List[Path]:
        """Download segments in batches with enhanced progress tracking

        Args:
            segments: List of segment URLs to download
            batch_size: Number of segments to download in each batch
            progress_callback: Callback function that receives ProgressData updates
            desc: Description for the overall download process

        Returns:
            Sorted list of downloaded file paths
        """
        downloaded_files = []
        total_segments = len(segments)
        total_batches = (total_segments + batch_size - 1) // batch_size

        # Optional: Add batch lifecycle callbacks
        def on_batch_start(batch_num: int, batch_size: int):
            if progress_callback:
                progress_callback(ProgressData(
                    current=0,
                    total=total_segments,
                    description=f"Starting batch {batch_num}/{total_batches}",
                    percentage=((batch_num - 1) * batch_size /
                                total_segments) * 100,
                    timestamp=datetime.now(),
                    downloaded=len(downloaded_files),
                    failed=0,
                    batch_num=batch_num,
                    total_batches=total_batches
                ))

        async with DownloadContext(
            total_segments=total_segments,
            progress_callback=progress_callback,
            description=desc
        ) as ctx:
            ctx.set_total_batches(total_batches)

            for i in range(0, total_segments, batch_size):
                if self.cancelled:
                    self.logger.info("Download segments stopped")
                    break

                batch = segments[i:i + batch_size]
                batch_num = i // batch_size + 1

                # Notify batch start
                # on_batch_start(batch_num, len(batch))
                if filename_list:
                    filename = filename_list[i]

                # Create tasks for current batch
                tasks = [
                    self.download_segment_async(
                        url, idx, filename=filename, **req_kwargs)
                    for idx, url in enumerate(batch, start=i)
                ]

                # Use batch-specific progress tracking
                async with ctx.create_batch_progress(
                    batch_total=len(tasks),
                    batch_num=batch_num,
                    batch_desc=f"Batch {batch_num}/{total_batches}"
                ) as batch_pbar:

                    # Execute batch with async_tqdm for visual feedback
                    for coro in async_tqdm.as_completed(
                        tasks,
                        # total=len(batch),
                        # desc=f"Batch {batch_num}/{total_batches}",
                        disable=True,
                        # leave=False  # Remove batch progress bar when done
                    ):
                        result = await coro

                        if result:
                            downloaded_files.append(result)
                            batch_pbar.update(n=1, success=True)
                            ctx.update(success=True, batch_num=batch_num)
                        else:
                            batch_pbar.update(n=1, success=False)
                            ctx.update(success=False, batch_num=batch_num)

        return sorted(downloaded_files)

    async def download_all_parallel(
        self,
        segments: List[str],
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
        desc: str = "Downloading segments",
        filename: Optional[str | Callable[[int], str]] = None,
        filename_list: Optional[List[str]] = None,
        **req_kwargs
    ) -> List[Path]:
        """Download all segments concurrently with progress tracking

        Args:
            segments: List of segment URLs
            progress_callback: Callback for progress updates (receives ProgressData)
            desc: Description for progress bar
            batch_size: Optional batch size for processing (if None, process all at once)

        Returns:
            List of downloaded file paths
        """
        if not filename and filename_list:
            def _filename(i): return filename_list[i]
        else:
            _filename = filename  # type: ignore
        results = []
        tasks = [
            self.download_segment_async(
                url, idx, filename=_filename, **req_kwargs)
            for idx, url in enumerate(segments)
        ]

        async with ProgressCallbackTqdm(
            total=len(tasks),
            desc=desc,
            progress_callback=progress_callback
        ) as pbar:
            for coro in async_tqdm.as_completed(tasks, disable=True):
                result = await coro
                if result:
                    results.append(result)
                    pbar.update(n=1, success=True)
                else:
                    pbar.update(n=1, success=False)

        return sorted(results)

    async def merge_ts_files(self, ts_files: List[Path], output_file: str):
        """Merge TS files into a single video file using ffmpeg (async wrapper)"""
        if not ts_files:
            self.logger.error("No TS files to merge")
            return False

        # Create file list for ffmpeg
        file_list_path = self.temp_segments_dir / "file_list.txt"
        async with aiofiles.open(file_list_path, 'w') as f:
            for ts_file in ts_files:
                await f.write(f"file '{ts_file.absolute()}'\n")

        # check ffmpeg first
        if shutil.which('ffmpeg') is None:
            self.logger.error("FFmpeg not found. Please install FFmpeg first.")
            return {"error": "FFmpeg not found. Please install FFmpeg first."}

        probe_cmd = ['ffmpeg', '-i', str(ts_files[0]), '-f', 'null', '-']
        result = subprocess.run(probe_cmd, capture_output=True, text=True)

        # Then choose appropriate filter
        bsf_filter = ['-bsf:v', 'h264_mp4toannexb']
        if 'aac' in result.stderr.lower():
            bsf_filter += ['-bsf:a', 'aac_adtstoasc']

        # Run ffmpeg in executor to avoid blocking
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(file_list_path),
            '-c', 'copy',
            *bsf_filter,
            output_file,
            '-y'
        ]

        try:
            # Run in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                self.logger.info(f"Successfully merged to: {output_file}")
                return True
            else:
                self.logger.error(f"FFmpeg error: {stderr.decode()}")
                return {"error": stderr.decode()}

        except FileNotFoundError:
            self.logger.error("FFmpeg not found. Please install FFmpeg first.")
            return {"error": "FFmpeg not found. Please install FFmpeg first."}

    async def download_playlist(
        self,
        url_list: List[str],
        output_dir: str = ".",
        filename: Optional[str | Callable[[int], str]] = None,
        filename_list: Optional[List[str]] = None,
        overwrite: bool = True,
        use_parallel: bool = True,
        batch_mode: bool = False,
        batch_size: int = 10,
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
        **req_kwargs
    ):
        """Main async method to download and merge a complete video playlist"""

        try:
            self.overwrite = overwrite
            self.set_temp_dir(output_dir)
            if self.custom_temp_segments_dir_name:
                self.temp_segments_dir = self.temp_dir.joinpath(
                    self.custom_temp_segments_dir_name)

            self.temp_segments_dir.mkdir(parents=True, exist_ok=True)

            # Download segments using appropriate method
            if use_parallel:
                if batch_mode:
                    completed_files = await self.download_segments_batch(url_list, batch_size, progress_callback=progress_callback, filename=filename, filename_list=filename_list, **req_kwargs)
                else:
                    completed_files = await self.download_all_parallel(url_list, progress_callback=progress_callback, filename=filename, filename_list=filename_list, **req_kwargs)
            else:
                # Sequential download with progress
                completed_files = await self.download_segments_simple(url_list, progress_callback=progress_callback, filename=filename, filename_list=filename_list, **req_kwargs)

            if not completed_files:
                self.logger.error("No segments were downloaded successfully")
                return False

            total_url = len(url_list)
            if hasattr(self, 'with_custom_response') and self.with_custom_response:
                total_url = len(completed_files)

            self.logger.info(
                f"Successfully downloaded {len(completed_files)}/{total_url} urls")

            if self.cancelled:
                try:
                    for file in completed_files:
                        Path(file).unlink(missing_ok=True)
                except Exception as e:
                    self.logger.error(f"Error cleaning up temp files: {e}")
                return False

            return completed_files

        except Exception as e:
            self.logger.error(f"Error downloading playlist: {e}")
            return False

    async def download_playlist_m3u8(
        self,
        m3u8_url: str,
        pattern: str | re.Pattern[str] | Callable[[str], List[str]],
        m3u8_headers: dict | None = None,
        output_file: str = "output.mp4",
        overwrite: bool = True,
        use_parallel: bool = True,
        batch_mode: bool = False,
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
        custom_response: Optional[Response] = None
    ):
        """Main async method to download and merge a complete video playlist"""

        try:
            self.logger.debug(f'm3u8Url = {m3u8_url}')
            if custom_response:
                self.with_custom_response = True
            # Fetch the m3u8 playlist asynchronously
            response = custom_response or await self.request(
                m3u8_url,
                headers=m3u8_headers,
                impersonate=self.https_impersonate,
                retries=0
            )
            if not response:
                return False

            content = response.text
            if not content.strip().startswith('#EXT'):
                return False
            # Parse segments
            segments = self.parse_m3u8(content, pattern)
            if not segments:
                self.logger.error("No TS segments found in playlist")
                return False

            self.logger.info(f"✅ Found {len(segments)} TS segments")

            if self.custom_temp_segments_dir_name:
                self.temp_segments_dir = self.temp_dir.joinpath(
                    self.custom_temp_segments_dir_name)

            self.temp_segments_dir.mkdir(parents=True, exist_ok=True)
            # Download segments using appropriate method
            if use_parallel:
                if batch_mode:
                    ts_files = await self.download_segments_batch(segments, progress_callback=progress_callback)
                else:
                    ts_files = await self.download_all_parallel(segments, progress_callback=progress_callback)
            else:
                # Sequential download with progress
                ts_files = await self.download_segments_simple(segments, progress_callback=progress_callback)

            if not ts_files:
                self.logger.error("No segments were downloaded successfully")
                return False

            self.logger.info(
                f"Successfully downloaded {len(ts_files)}/{len(segments)} segments")

            if self.cancelled:
                await self.cleanup_temp_files()
                return False

            if overwrite and Path(output_file).exists() and Path(output_file).is_file():
                self.logger.info(f"🗑️ Override existing file: {output_file}")
                Path(output_file).unlink()

            output_dir = Path(output_file).parent
            if str(output_dir) != ".":
                output_dir.mkdir(parents=True, exist_ok=True)
            # Merge segments
            result = await self.merge_ts_files(ts_files, output_file)

            if isinstance(result, dict):
                return result

            # Cleanup
            await self.cleanup_temp_files()

            return result

        except Exception as e:
            self.logger.error(f"Error downloading playlist: {e}")
            return False

    async def cleanup_temp_files(self):
        """Remove temporary TS segment files asynchronously"""
        try:
            for file in self.temp_segments_dir.glob("segment_*.ts"):
                file.unlink()
            (self.temp_segments_dir / "file_list.txt").unlink(missing_ok=True)
            try:
                self.temp_segments_dir.rmdir()
                self.temp_dir.rmdir()
            except:
                self.logger.info(
                    f"Skip cleaning up {self.temp_segments_dir.name}")
        except Exception as e:
            self.logger.error(f"Error cleaning up temp files: {e}")


class AsyncEpisodeDownloader:
    """Download multiple episodes asynchronously"""

    def __init__(self, downloader: AsyncTSVideoDownloader):
        self.downloader = downloader
        self.logger = self.downloader.logger

    async def download_episodes(self, episode_urls: List[Tuple[str, str]], max_concurrent_episodes: int = 3):
        """
        Download multiple episodes concurrently

        Args:
            episode_urls: List of tuples (url, output_filename)
            max_concurrent_episodes: Maximum number of episodes to download simultaneously
        """
        semaphore = Semaphore(max_concurrent_episodes)

        async def download_with_semaphore(url: str, output_file: str, episode_num: int):
            async with semaphore:
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"Starting Episode {episode_num}")
                self.logger.info(f"{'='*50}")
                success = await self.downloader.download_playlist(url, output_file)
                if success:
                    self.logger.info(
                        f"Episode {episode_num} completed: {output_file}")
                else:
                    self.logger.error(f"Episode {episode_num} failed")
                return success

        # Create tasks for all episodes
        tasks = []
        for idx, (url, output_file) in enumerate(episode_urls, 1):
            tasks.append(download_with_semaphore(url, output_file, idx))

        # Execute all downloads concurrently
        results = await asyncio.gather(*tasks)
        return results

# Advanced: Streaming download with custom callback


class StreamingTSDownloader(AsyncTSVideoDownloader):
    """Extended version with streaming and progress callbacks"""

    async def download_segment_streaming(self, url: str, index: int,
                                         callback=None, retries: int = 3) -> Optional[Path]:
        """Download segment with streaming progress callback"""
        file_path = self.temp_segments_dir / f"segment_{index:04d}.ts"

        async with self.semaphore:
            for attempt in range(retries):
                try:
                    # Use stream=True for large files
                    response = await self.request(url, headers=self.https_headers, retries=0)
                    if not response:
                        continue
                    if response.status_code == 200:
                        total_size = int(
                            response.headers.get('content-length', 0))
                        downloaded = 0

                        async with aiofiles.open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunks():
                                if chunk:
                                    await f.write(chunk)
                                    downloaded += len(chunk)
                                    if callback and total_size:
                                        callback(
                                            index, downloaded, total_size)
                        return file_path
                    else:
                        self.logger.error(
                            f"Failed to download segment {index}: HTTP {response.status_code}")

                except Exception as e:
                    self.logger.error(
                        f"Error downloading segment {index} (attempt {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)

            return None

# Utility functions


async def extract_m3u8_from_page_async(url: str) -> Optional[str]:
    """Extract m3u8 playlist URL from HTML page asynchronously"""
    try:
        session = requests.Session()
        response = await session.get(url)

        patterns = [
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'video\.src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                return match.group(1)

        return None
    except Exception as e:
        print(f"Error extracting m3u8: {e}")
        return None


async def download_m3u8_with_retry_strategy(m3u8_url: str, output_file: str, max_attempts: int = 3):
    """Download with retry strategy for complete playlist"""
    downloader = AsyncTSVideoDownloader(max_concurrent=5)

    for attempt in range(max_attempts):
        print(f"\nDownload attempt {attempt + 1}/{max_attempts}")

        # Try with different concurrency settings on retry
        if attempt == 1:
            downloader.max_concurrent = 3  # Reduce concurrency on retry
        elif attempt == 2:
            downloader.max_concurrent = 1  # Sequential on last retry

        success = await downloader.download_playlist(m3u8_url, output_file, use_parallel=True)

        if success:
            print("Download completed successfully!")
            return True

        print(
            f"Attempt {attempt + 1} failed, retrying in {5 * (attempt + 1)} seconds...")
        await asyncio.sleep(5 * (attempt + 1))

    print("All download attempts failed")
    return False

# Main async execution


async def main():
    # Example 1: Basic async download
    downloader = AsyncTSVideoDownloader(max_concurrent=10)

    # Single episode
    m3u8_url = "https://example.com/path/to/playlist.m3u8"
    await downloader.download_playlist(m3u8_url, "video.mp4", use_parallel=True)

    # Example 2: Multiple episodes with different outputs
    episode_urls = [
        ("https://example.com/episode1.m3u8", "downloads/episode_01.mp4"),
        ("https://example.com/episode2.m3u8", "downloads/episode_02.mp4"),
        ("https://example.com/episode3.m3u8", "downloads/episode_03.mp4"),
    ]

    episode_downloader = AsyncEpisodeDownloader(downloader)
    await episode_downloader.download_episodes(episode_urls, max_concurrent_episodes=2)

    # Example 3: With retry strategy
    await download_m3u8_with_retry_strategy(m3u8_url, "robust_video.mp4", max_attempts=3)

    # Example 4: Extract m3u8 from webpage first
    page_url = "https://example.com/video-page"
    extracted_m3u8 = await extract_m3u8_from_page_async(page_url)
    if extracted_m3u8:
        await downloader.download_playlist(extracted_m3u8, "extracted_video.mp4")

# # Run with proper event loop handling
# if __name__ == "__main__":
#     # Windows requires specific event loop policy for asyncio
#     if os.name == 'nt':
#         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#     # Run the main function
#     asyncio.run(main())
