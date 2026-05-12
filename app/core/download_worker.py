import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from curl_cffi import requests
from loguru import logger
from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from yt_dlp import YoutubeDL
from yt_dlp.utils import determine_ext, encodeFilename, format_bytes

from ..utils.path import split_filepath

try:
    from pytubefix.sig_nsig.node_runner import NodeRunner
except ImportError:
    NodeRunner = None

from ..core.convert_worker import VideoConverter

# from ..extractor._extract import AsyncDouyinExtractor
from ..extractor.youtube import YouTubeExtractor


def populate_yt_dlp_formats(info_dict):
    formats = info_dict.get("formats", [])

    video_formats = []
    video_only_formats = []
    audio_formats = []

    # width, height = info_dict.get('width',0), info_dict.get('height',0)
    # filter_key =

    for f in formats:
        if not f.get('protocol', '').startswith('http'):
            continue
        filesize_str = ""
        if f.get('protocol', '').startswith('http'):
            for k, v in f.items():
                if not v:
                    f[k] = ''
                elif isinstance(v, float):
                    f[k] = str(v)
                elif k in ['filesize', 'filesize_approx'] and not filesize_str:
                    filesize_str = format_bytes(v or int(0))

            if f.get('video_ext') != 'none' and f.get('audio_ext') != 'none' and f.get('vcodec') != 'none' and f.get('acodec') != 'none':  # Video with audio
                video_formats.append({**f, 'filesize_str': filesize_str})
            elif f.get('audio_ext') == 'none' and f.get('vcodec') != 'none':  # Video only
                video_only_formats.append({**f, 'filesize_str': filesize_str})
            elif (f.get('video_ext') == 'none' and f.get('acodec') != 'none') or 'audio only' in f.get('resolution', ''):  # Audio only
                audio_formats.append({**f, 'filesize_str': filesize_str})

    # Sort by resolution, then format ID
    video_formats = sorted(video_formats, key=lambda x: (
        x.get("height", 0)), reverse=True)
    # Sort by resolution, then format ID
    video_only_formats = sorted(
        video_only_formats, key=lambda x: (x.get("height", 0)), reverse=True)
    audio_formats = sorted(audio_formats, key=lambda x: x.get("abr", 0),
                           reverse=True)  # Sort by bitrate

    return {
        "both": video_formats,
        "video_only": video_only_formats,
        "audio_only": audio_formats,
    }


class WorkerSignals(QObject):
    # task_id, downloaded, total, speed, eta
    progress = Signal(int, int, int, str, str)
    status_changed = Signal(int, str)  # task_id, status
    finished = Signal(int, str)  # task_id, filepath
    error = Signal(int, str)  # task_id, message
    filename_updated = Signal(int, str)  # task_id, real_filename


class DownloadWorker(QRunnable):
    def __init__(
        self,
        task_id,
        url,
        output_dir,
        filename,
        info: Optional[dict] = None,
        options: Optional[dict] = None
    ):
        super().__init__()
        self.task_id = task_id
        self.url = url
        self.info = info
        self.output_dir = output_dir
        self.filename = filename
        self.options = options or {}
        self.signals = WorkerSignals()
        self._is_paused = False
        self._is_cancelled = False
        self._is_video = "youtube.com" in str(
            url) or "youtu.be" in str(url) or "vimeo.com" in str(url)
        self._is_douyin = "douyin.com" in str(
            url) or "iesdouyin.com" in str(url)
        self.chunk_size = 10485760

    @Slot()
    def run(self):
        self.signals.status_changed.emit(self.task_id, "Downloading")

        if self.info:
            self.run_yt_dlp()
        elif self._is_douyin:
            self.run_douyin()
        else:
            self.run_yt_dlp()

    def run_douyin(self):
        self.signals.status_changed.emit(self.task_id, "Extracting...")
        try:
            async def get_info():
                async with AsyncDouyinExtractor() as extractor:
                    return await extractor.get_video_detail(self.url)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            info = loop.run_until_complete(get_info())
            loop.close()

            if info and ("hd" in info or "sd" in info):
                self.signals.status_changed.emit(
                    self.task_id, "Downloading...")
                # Use HD link from extractor
                direct_link = info.get("hd") or info.get("sd")
                self.filename = info.get("title", self.filename)
                self.signals.filename_updated.emit(self.task_id, self.filename)

                # Pass direct link to yt-dlp
                self.run_yt_dlp(override_url=direct_link,
                                filename=self.filename)
            else:
                error_msg = info.get(
                    "error", "No HD link found") if info else "Extraction failed"
                self.signals.error.emit(
                    self.task_id, f"Douyin Error: {error_msg}")
        except Exception as e:
            logger.error(f"Douyin Extraction failed: {e}")
            self.signals.error.emit(
                self.task_id, f"Douyin Extract Failed: {str(e)}")
        # if self._is_video:
        #     self.run_yt_dlp()
        # else:
        #     self.run_http()

    def run_http(self):
        full_path = os.path.join(self.output_dir, self.filename)
        try:
            start_time = time.time()
            downloaded = 0
            r = requests.get(self.url, stream=True, impersonate="chrome120")
            r.raise_for_status()
            total_length = int(r.headers.get('content-length', 0))

            with open(full_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if self._is_cancelled:
                        break
                    if self._is_paused:
                        while self._is_paused:
                            time.sleep(0.5)
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed_val = downloaded / elapsed if elapsed > 0 else 0
                        speed_str = self.format_speed(speed_val)
                        eta_val = (total_length - downloaded) / \
                            speed_val if speed_val > 0 else 1
                        eta_str = self.format_eta(eta_val)
                        self.signals.progress.emit(
                            self.task_id, downloaded, total_length, speed_str, eta_str)

            if self._is_cancelled:
                self.signals.status_changed.emit(self.task_id, "Cancelled")
                if os.path.exists(full_path):
                    os.remove(full_path)
            else:
                self.signals.finished.emit(self.task_id, full_path)
                self.signals.status_changed.emit(self.task_id, "Completed")
        except Exception as e:
            logger.error(f"HTTP Download failed: {e}")
            self.signals.error.emit(self.task_id, str(e))

    def run_youtube(self):
        try:
            async def get_info():
                async with YouTubeExtractor() as extractor:
                    return await extractor.get_video_info_list(self.url)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            info = loop.run_until_complete(get_info())
            loop.close()

            if info and ("hd" in info or "sd" in info):
                self.signals.status_changed.emit(
                    self.task_id, "Downloading...")
                # Use HD link from extractor
                direct_link = info.get("hd") or info.get("sd")
                self.filename = info.get("title", self.filename)
                self.signals.filename_updated.emit(self.task_id, self.filename)

                # Pass direct link to yt-dlp
                self.run_yt_dlp(override_url=direct_link,
                                filename=self.filename)
            else:
                error_msg = info.get(
                    "error", "No HD link found") if info else "Extraction failed"
                self.signals.error.emit(
                    self.task_id, f"YouTube Error: {error_msg}")
        except Exception as e:
            logger.error(f"YouTube Extraction failed: {e}")
            self.signals.error.emit(
                self.task_id, f"YouTube Extract Failed: {str(e)}")

    def run_yt_dlp(self, override_url=None, filename=None):
        target_url = override_url or self.url
        global has_ffmpeg
        # Determine format based on ffmpeg and user options
        has_ffmpeg = shutil.which("ffmpeg") is not None
        res = self.options.get("resolution", "720")

        # User requested specific high res (1080, 2k, 4k)
        # 2k is height 1440
        # 4k is height 2160
        if res == "4k":
            res = "2160"
        elif res == "2k":
            res = "1440"
        elif res == "1080":
            res = "1080"

        # Format string for yt-dlp
        # Prefer mp4 for easier merging and compatibility
        if has_ffmpeg:
            # Try to get mp4 specifically as requested
            fmt = f"bestvideo[height<={res}][ext=mp4][protocol^=http]+bestaudio[ext=m4a]/best[height<={res}]/best"
        else:
            fmt = f"best[height<={res}][ext=mp4]/best"

        if self.options.get("mp3", False):
            fmt = "bestaudio/best"

        if self.info:
            filename = self.info.get("title", filename)
            extractor_key = self.info.get('extractor_key')
            uploader = self.info.get('uploader')
            if self.options.get('with_site', False) and extractor_key:
                self.output_dir = os.path.join(
                    self.output_dir, f"{extractor_key}")
            if self.options.get('with_username', False) and uploader:
                self.output_dir = os.path.join(self.output_dir, f"{uploader}")

        if filename:
            outtmpl = os.path.join(self.output_dir, f'{filename}.%(ext)s')
        else:
            outtmpl = os.path.join(self.output_dir, f'%(title)s.%(ext)s')
        ydl_opts = {
            'format': fmt,
            'outtmpl': outtmpl,
            'progress_hooks': [self.yt_dl_hook_wrapper],
            'logger': logger,
            'noplaylist': True,
            'merge_output_format': 'mp4' if has_ffmpeg else None,
            'overwrites': True,
            'http_chunk_size': self.chunk_size,
        }
        try:
            if NodeRunner:
                # --js-runtimes node:/path/to/node
                runner = NodeRunner('')
                node_path = runner._node_path()
                if Path(node_path).exists():
                    ydl_opts['javascript_runtimes'] = [node_path]

        except Exception as e:
            logger.error(f"NodeRunner not found: {e}")

        only_download_audio = self.options.get("mp3", False)
        has_audio_url = False
        if only_download_audio and has_ffmpeg:
            has_audio_url = self.info and self.info.get('music')
            if not has_audio_url:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

        try:
            with YoutubeDL(ydl_opts) as ydl:
                if self.info:
                    _info, is_both, video_url, audio_url = self.select_format_for_yt_dlp(
                        int(res))
                    logger.debug(
                        f"_info: {_info.get('url')}, is_both: {is_both}, video_url: {video_url}, audio_url: {audio_url}")
                    video_url = video_url or self.info['url']
                    if only_download_audio:
                        if has_audio_url and audio_url:
                            info = ydl.extract_info(audio_url, download=True)
                        else:
                            info = ydl.extract_info(video_url, download=True)

                        final_path = ydl.prepare_filename(info)
                    else:
                        info = ydl.extract_info(
                            video_url, download=True)
                        if not is_both and audio_url:
                            video_path_for_merge = ydl.prepare_filename(info)
                            final_path = self.merge_video_and_audio(
                                ydl_opts, video_path_for_merge, audio_url)
                        else:
                            final_path = ydl.prepare_filename(info)
                else:
                    info = ydl.extract_info(target_url, download=True)
                    final_path = ydl.prepare_filename(info)

                # If merging or converting, extension might change
                if self.options.get("mp3", False) and shutil.which("ffmpeg"):
                    final_path = final_path.rsplit('.', 1)[0] + ".mp3"
                # elif shutil.which("ffmpeg"):
                    # yt-dlp might merge to mp4 even if requested but prepare_filename might say .webm
                    # Actually ydl.prepare_filename usually reflects the merged extension if download=True succeeded
                    # pass

                self.filename = os.path.basename(final_path)
                self.signals.filename_updated.emit(self.task_id, self.filename)

                if not self._is_cancelled:
                    self.signals.finished.emit(self.task_id, final_path)
                    self.signals.status_changed.emit(self.task_id, "Completed")
        except Exception as e:
            if not self._is_cancelled:
                logger.error(f"Download failed: {e}")
                self.signals.error.emit(self.task_id, str(e))

    def yt_dl_hook_wrapper(self, d):
        try:
            self.yt_dlp_hook(d)
        except Exception as e:
            # This is how we stop yt-dlp when cancelled
            if "Cancelled" in str(e):
                raise
            logger.error(f"Hook error: {e}")

    def yt_dlp_hook(self, d):
        global total, downloaded, speed_str, eta_str
        if self._is_cancelled:
            raise Exception("Cancelled by user")

        total = 0
        downloaded = 0
        speed_str = ""
        eta_str = ""

        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

            speed_str = self.format_speed(speed)
            eta_str = self.format_eta(eta)

            self.signals.progress.emit(
                self.task_id, downloaded, total, speed_str, eta_str)
        elif d['status'] == 'finished':
            if has_ffmpeg:
                self.signals.status_changed.emit(self.task_id, "Merging...")
                time.sleep(0.5)

            # self.signals.progress.emit(self.task_id, total, total, speed_str, eta_str)
            self.signals.status_changed.emit(self.task_id, "Completed")

    def get_audio_url(self, info: dict, with_audio_info=False) -> str | dict | None:
        music_url = None
        audio_info = None
        try:
            music = info.get('music')
            if 'formats' in info:
                for f in info['formats']:
                    if f.get('acodec') != 'none' and (f.get('ext') == 'm4a' or f.get('ext') == 'mp3'):
                        audio_info = f
                        audio = audio_info.get('url', '')
                        music_url = audio
                        break  # Stop searching once found a suitable format
            elif 'audio_only' in info and isinstance(info['audio_only'], list):
                for f in info['audio_only']:
                    if f.get('ext', '') in ['mp3', 'm4a'] and f.get('url'):
                        music_url = f['url']
                        audio_info = f
                        break  # Stop searching once found a suitable format
            elif isinstance(music, str) and music:
                music_url = info['music']
        except:
            pass

        if with_audio_info:
            if not audio_info:
                ext = determine_ext(music_url, 'mp3')
                audio_info = {
                    "url": music_url,
                    'ext': ext,
                    'audio_ext': ext,
                }

            audio_info['filesize'] = audio_info.get('filesize_num', 0)
            if not 'downloader_options' in audio_info and music_url:
                audio_info['downloader_options'] = {
                    "http_chunk_size":  self.chunk_size}

            audio_info['format_id'] = f'192'
            return audio_info

        return music_url

    def get_video_url_from_formats(self, resolution, with_video_info=False):
        info = self.info.copy() if self.info else {}
        if not 'video_only' in info and 'formats' in info:
            populate_formats = populate_yt_dlp_formats(info)
            info.update(populate_formats)
        else:
            both = info.get('both', [])
            video_only = info.get('video_only', [])
            both = sorted(both, key=lambda x: (
                x.get("height", 0)), reverse=True)
            video_only = sorted(video_only, key=lambda x: (
                x.get("height", 0)), reverse=True)
            info.update({
                "both": both,
                "video_only": video_only,
                "audio_only": info.get('audio_only', []),
            })

            if len(info.get('both', [])) <= 0:
                url = info.get('hd') or info.get(
                    'sd') or info.get('original_url') or info.get('webpage_url', '')
                ext = determine_ext(url, 'mp4')
                filesize = info.get('filesize_num', 0)
                if 'requested_download' in info and info['requested_download']:
                    f = info['requested_download'][0]
                    f.update({
                        'url': url,
                        'ext': ext,
                        'video_ext': ext,
                        'filesize': filesize
                    })
                    info['both'] = [f]
                else:
                    info['both'] = [{
                        "width": info.get('width', 0),
                        "height": info.get('height', 0),
                        "resolution": info.get('resolution', 'unknown'),
                        "url": url,
                        'ext': ext,
                        'video_ext': ext,
                        'filesize': filesize
                    }]

        self.info = info
        video_url = None
        video_info = {}
        for f in info['video_only']:
            width = f.get('width', 0)
            height = f.get('height', 0)
            resolution_compare = height if width >= height else width
            if f.get('ext') == 'mp4' and resolution_compare <= resolution:
                logger.debug('resolution', resolution_compare)
                video_url = f.get('url')
                video_info = f
                break

        if not video_url:
            for f in info['both']:
                width = f.get('width', 0)
                height = f.get('height', 0)
                resolution_compare = height if width >= height else width
                if len(info['both']) == 1:
                    logger.debug('resolution both 1', resolution_compare)
                    video_url = f.get('url')
                    video_info = f
                    video_info['is_both'] = True
                    break

                if resolution_compare <= resolution:
                    logger.debug('resolution both 2', resolution_compare)
                    video_url = f.get('url')
                    video_info = f
                    video_info['is_both'] = True
                    break

        if with_video_info:
            video_info['filesize'] = video_info.get('filesize_num', 0)
            if not 'downloader_options' in video_info:
                video_info.update({
                    "downloader_options": {"http_chunk_size":  self.chunk_size}
                })

            video_info['format_id'] = f'{resolution}'
            return video_info

        return video_url

    def select_format_for_yt_dlp(self, resolution):
        video_info = self.get_video_url_from_formats(resolution, True)

        info = self.info.copy() if self.info else {}

        if 'requested_download' in info:
            del info['requested_download']
        if 'requested_formats' in info:
            del info['requested_formats']

        if 'upload_date' in info:
            info['upload_date'] = str(info['upload_date']).split(' ')[
                0].replace('-', '')

        requested_formats = [video_info]
        is_both = video_info.get('is_both')
        audio_info = {}
        if not is_both:
            audio_info = self.get_audio_url(info, True)
            requested_formats += [audio_info]

        info.update({'requested_formats': requested_formats})

        if video_info and audio_info:
            info['format_id'] = f"{video_info.get('format_id')}+{audio_info.get('format_id')}"

        return info, is_both, video_info.get('url'), audio_info.get('url')

    def merge_video_and_audio(self, ydl_opts: dict, video_path_for_merge: str, audio_for_merge: str):
        self._audio_file = None

        def progress_hook(d):
            if self._is_cancelled:
                raise Exception("Download stopped")

            if d['status'] == 'finished':
                self._audio_file = d.get('filename')

        opts = ydl_opts.copy()
        opts.update({
            'progress_hooks': [progress_hook],
            'outtmpl': f'{self.output_dir}/{self.filename}.%(ext)s'
        })
        try:
            with YoutubeDL(opts) as ydl:
                _info = ydl.extract_info(audio_for_merge)
                self._audio_file = ydl.prepare_filename(_info)

                if not self._audio_file:
                    self._is_cancelled = True
                    raise Exception("Audio file not found")

                ffmpeg_path = shutil.which('ffmpeg')
                if not ffmpeg_path:
                    self._is_cancelled = True
                    raise Exception("FFmpeg has been not found")

                video_file_exists = os.path.exists(
                    video_path_for_merge)
                audio_file_exists = os.path.exists(self._audio_file)
                if not (video_file_exists and audio_file_exists):
                    self._is_cancelled = True
                    raise Exception("Video or audio file not found")

                converter = VideoConverter()
                if self.info and 'duration' in self.info and self.info.get('duration', 0) > 0:
                    converter.duration = self.info['duration']

                converter.info = self.info if self.info else {}

                final_path = video_path_for_merge
                root, basename, filename, ext = split_filepath(
                    video_path_for_merge)
                video_path_for_merge = str(Path(video_path_for_merge).rename(
                    Path(root) / f"{filename[:-4]}_pre.{ext}"))

                def progress(d):
                    if d['status'] == 'finished' and os.path.exists(final_path):
                        # self.complete_callback(self.output_dir)
                        pass
                    elif d['status'] == 'error':
                        raise Exception('Covert Error')

                converter.on_callback_progress = progress
                converter.merge_video_audio(
                    video_path_for_merge, self._audio_file, final_path)
                return final_path
        except Exception as e:
            raise e

    def format_speed(self, speed):
        if not speed:
            return "0 B/s"
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} TB/s"

    def format_eta(self, seconds):
        if not seconds:
            return "0s"
        mins, secs = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        return f"{hours}h {mins}m {secs}s" if hours > 0 else (f"{mins}m {secs}s" if mins > 0 else f"{secs}s")

    def pause(self): self._is_paused = True
    def resume(self): self._is_paused = False
    def cancel(self): self._is_cancelled = True
