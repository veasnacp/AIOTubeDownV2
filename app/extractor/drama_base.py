import asyncio
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from curl_cffi.requests import Response

from ._cloud import CloudinaryDataManager
from ._request import ExtractorBase
from ._tsdl import AsyncTSVideoDownloader, ProgressData
from ._utils import safe_filename

current_dir = Path(__file__).parent

cloud_manager = CloudinaryDataManager(
    cloud_name="dvxh2vz5z",
    api_key="293416415366882",
    api_secret="8hnzstbS2sGIGRsE7jp_moN35ew"
)


class DramaExtractorBase(ExtractorBase):
    cloud_manager = cloud_manager

    async def _download_all_episodes(
        self,
        downloader: "AsyncTSVideoDownloader",
        info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        overwrite: bool = True,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        downloader_settings_callback: Optional[Callable[[
            "AsyncTSVideoDownloader"], None]] = None,
        is_test=False
    ):
        headers = {
            'Accept': '*/*',
            'Connection': 'keep-alive',
            "Referer": f"{self._BASE_URL}/",
            "Origin": self._BASE_URL,
        }
        # downloader.custom_temp_segments_dir_name = _safe_title
        downloader.session = self.session
        downloader.session.headers.update(headers)
        downloader.https_headers = headers
        downloader.https_impersonate = "chrome120"
        self.active_downloader = downloader
        downloader.cancelled = self.cancel_download
        # User download folder
        _output_dir = self.set_output_dir(output_dir, with_site_name)

        title = info['bookName']
        _safe_title = safe_filename(title)
        _output_dir = _output_dir.joinpath(_safe_title)

        if downloader_settings_callback and callable(downloader_settings_callback):
            downloader_settings_callback(downloader)

        url_list = []
        filename_list = []
        chapter_list = info['chapterList'][0:1] if is_test else info['chapterList']

        for chapter in chapter_list:
            if self.cancel_download:
                self.logger.info("Download process stopped by user")
                break

            url_list.append(self.get_video_url_play(chapter, "720p"))
            episode_index = int(chapter['indexStr'])
            suffix_name = f"_EP{episode_index:02d}"
            _filename = safe_filename(
                title, max_length=255 - len(suffix_name)) + suffix_name + ".mp4"
            filename_list.append(_filename)

        for attempt in range(max_attempts):
            self.logger.info(
                f"\nDownload attempt {attempt + 1}/{max_attempts}")

            if self.cancel_download:
                self.logger.info("Download process stopped")
                break

            # Try with different concurrency settings on retry
            if attempt == 1:
                downloader.max_concurrent = 3  # Reduce concurrency on retry
            elif attempt == 2:
                downloader.max_concurrent = 1  # Sequential on last retry

            result = await downloader.download_playlist(
                url_list,
                output_dir=str(_output_dir),
                filename_list=filename_list,
                overwrite=overwrite,
                progress_callback=progress_callback
            )

            if isinstance(result, list):
                self.logger.info("✅ Download completed successfully!")
                return result
            else:
                self.logger.error(f"❌ Error downloading playlist")

            self.logger.info(
                f"Attempt {attempt + 1} failed, retrying in {5 * (attempt + 1)} seconds...")
            await asyncio.sleep(5 * (attempt + 1))

        self.logger.info("All download attempts failed")
        return False

    async def download_m3u8(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        pattern: str | re.Pattern | Callable[[str], List[str]],
        output_file: str = "",
        temp_segments_dir_name: Optional[str] = None,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        downloader_settings_callback: Optional[Callable[[
            "AsyncTSVideoDownloader"], None]] = None,
        custom_response: Optional[Response] = None,
    ):
        headers = {
            'Accept': '*/*',
            'Connection': 'keep-alive',
            "Referer": f"{self._BASE_URL}/",
            "Origin": self._BASE_URL,
        }
        if hasattr(self, '_CUSTOM_BASE_URL') and self._CUSTOM_BASE_URL:
            headers["Referer"] = f"{self._CUSTOM_BASE_URL}/"
            headers["Origin"] = self._CUSTOM_BASE_URL

        self.logger.debug(f"Headers: {headers}")
        if temp_segments_dir_name:
            downloader.custom_temp_segments_dir_name = temp_segments_dir_name
        downloader.session = self.session
        downloader.session.headers.update(headers)
        downloader.https_headers = headers
        downloader.https_impersonate = "chrome131_android"
        if downloader_settings_callback and callable(downloader_settings_callback):
            downloader_settings_callback(downloader)

        for attempt in range(max_attempts):
            if downloader.cancelled:
                break
            self.logger.info(
                f"\nDownload attempt {attempt + 1}/{max_attempts}")

            # Try with different concurrency settings on retry
            if attempt == 1:
                downloader.max_concurrent = 3  # Reduce concurrency on retry
            elif attempt == 2:
                downloader.max_concurrent = 1  # Sequential on last retry

            result = await downloader.download_playlist_m3u8(
                m3u8_url,
                pattern=pattern,
                m3u8_headers=headers,
                output_file=output_file,
                use_parallel=True,
                batch_mode=True,
                progress_callback=progress_callback,
                custom_response=custom_response,
            )

            if isinstance(result, bool) and result:
                self.logger.info("✅ Download completed successfully!")
                return True
            elif isinstance(result, dict) and "error" in result:
                # this is ffmpeg error then skip retry
                self.logger.error(
                    f"❌ Error downloading playlist: {result['error']}")
                return False

            self.logger.info(
                f"Attempt {attempt + 1} failed, retrying in {5 * (attempt + 1)} seconds...")
            await asyncio.sleep(5 * (attempt + 1))

        self.logger.info("All download attempts failed")
        return False

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        temp_segments_dir_name: str,
        output_file: str,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
    ):
        return False

    async def _download_all_episodes_from_m3u8(
        self,
        downloader: "AsyncTSVideoDownloader",
        info: Dict[str, Any],
        keys_chaper_info: Dict[str, str | None | Callable] = {
            "video_url": "video_url",
            "temp_segments_dir_name": "chapter_id",
            "episode_number": "serial_number",
            "custom_temp_segments_dir_name": None
        },
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False
    ):
        # downloader = AsyncTSVideoDownloader(max_concurrent=5)
        self.active_downloader = downloader
        self.cancel_download = False
        downloader.cancelled = self.cancel_download
        _output_dir = self.set_output_dir(output_dir, with_site_name)
        # test 2 episodes
        chapters = info['chapterList'][0:1] if is_test else info['chapterList']
        title = info.get('title') or info.get('book_title') or info['book_id']
        success_data = []
        error_data = []
        _keys_chaper_info = keys_chaper_info.copy()
        for chapter in chapters:
            if self.cancel_download:
                self.logger.info("Download process stopped by user")
                break

            for key, value in keys_chaper_info.items():
                if key != "custom_temp_segments_dir_name" and callable(value):
                    chapter[key] = value(chapter)
                    _keys_chaper_info[key] = key

            chapter_id = chapter[_keys_chaper_info["temp_segments_dir_name"]]
            temp_segments_dir_name = chapter_id
            custom_temp_segments_dir_name = _keys_chaper_info.get(
                "custom_temp_segments_dir_name")
            if bool(custom_temp_segments_dir_name):
                if callable(custom_temp_segments_dir_name):
                    temp_segments_dir_name = custom_temp_segments_dir_name(
                        chapter)
                else:
                    temp_segments_dir_name = chapter[custom_temp_segments_dir_name]

            episode_index = int(chapter[_keys_chaper_info["episode_number"]])
            m3u8_url = chapter.get(_keys_chaper_info["video_url"])

            if episode_index == 0 or not m3u8_url:
                continue
            suffix_name = f"_EP{episode_index:02d}"
            filename = safe_filename(
                title, max_length=255 - len(suffix_name)) + suffix_name + ".mp4"
            title_folder = safe_filename(title)
            output_file = _output_dir.joinpath(title_folder, filename)
            success = await self.download_m3u8_url(
                downloader,
                m3u8_url,
                chapter,
                temp_segments_dir_name,
                str(output_file),
                max_attempts,
                progress_callback
                # progress_callback=lambda data: self.logger.info(
                #     f"{data.description}: {data.current}/{data.total} "
                #     f"({data.percentage:.1f}%)"),
            )

            chapter["status"] = "success" if success else "error"
            chapter["output_file"] = str(output_file)
            chapter["temp_segments_dir_name"] = temp_segments_dir_name
            if success:
                success_data.append(chapter)
            else:
                error_data.append(chapter)
                self.logger.error(
                    f"❌ Failed to download episode: {chapter_id}")
        return {
            "success": success_data,
            "failed": error_data
        }
