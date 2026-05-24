import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Optional, TypeAlias, Union
from urllib.parse import urlparse

from loguru import logger
from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from ..extractor.douyin import DouyinExtractor

# from ..extractor.instagram import InstagramExtractor
from ..extractor.facebook import FacebookExtractor
from ..extractor.kuaishou import KuaishouExtractor
from ..extractor.tiktok import TikTokExtractor
from ..extractor.youtube import YouTubeExtractor
from ._worker import DefaultWorker, Slot

TYPE_EXTRACTOR: TypeAlias = Union[
    'YouTubeExtractor', 'TikTokExtractor',
    'FacebookExtractor',
    # 'InstagramExtractor',
    'KuaishouExtractor', 'DouyinExtractor'
]

BASE_DOMAIN = {
    "instagram": "instagram.com",
    "tiktok": "tiktok.com",
    "tiktok_redirect": "vt.tiktok.com",
    "youtube": "youtube.com",
    "youtube_short": "youtu.be",
    "facebook": "facebook.com",
    "kuaishou": "kuaishou.com",
    "kuaishou_redirect": "v.kuaishou.com",
    "douyin": "douyin.com",
    "douyin_redirect": "v.douyin.com"
}

BASE_EXTRACTORS = {
    # "instagram": InstagramExtractor,
    "tiktok": TikTokExtractor,
    "youtube": YouTubeExtractor,
    "facebook": FacebookExtractor,
    "kuaishou": KuaishouExtractor,
    "douyin": DouyinExtractor,
}


def extract_url_list(url_list: list[str]):
    # hostRedirectPattern = "vt.tiktok.com|v.douyin.com|v.kuaishou.com"

    other_list: list[str] = []
    generic_list: list[str] = []

    tiktok_video_list: list[str] = []
    tiktok_profile_list: list[str] = []
    youtube_video_list: list[str] = []
    youtube_profile_list: list[str] = []
    facebook_video_list: list[str] = []
    facebook_profile_list: list[str] = []
    douyin_video_list: list[str] = []
    douyin_profile_list: list[str] = []
    kuaishou_video_list: list[str] = []
    kuaishou_profile_list: list[str] = []
    instagram_video_list: list[str] = []
    instagram_profile_list: list[str] = []

    for link in url_list:
        _parsed_url = urlparse(link)
        _path = _parsed_url.path
        _query = _parsed_url.query
        _netloc = _parsed_url.netloc
        is_generic = "&download_with_info_dict=" in _query

        if is_generic:
            generic_list.append(link)
            continue

        if not any(value in _netloc for value in BASE_DOMAIN.values()):
            other_list.append(link)
            continue

        if BASE_DOMAIN["instagram"] in _netloc:
            if re.search(r"/(p|reel|reels)/", _path):
                instagram_video_list.append(link)
                continue

            instagram_profile_list.append(link)
            continue

        if BASE_DOMAIN["tiktok"] in _netloc or BASE_DOMAIN["tiktok_redirect"] in _netloc:
            if re.search(r"/video/", _path) or BASE_DOMAIN["tiktok_redirect"] in _netloc:
                tiktok_video_list.append(link)
                continue

            tiktok_profile_list.append(link)
            continue

        if BASE_DOMAIN["youtube"] in _netloc or BASE_DOMAIN["youtube_short"] in _netloc:
            if re.search(r"/watch|/shorts", _path) or BASE_DOMAIN["youtube_short"] in _netloc:
                youtube_video_list.append(link)
                continue

            youtube_profile_list.append(link)
            continue

        if BASE_DOMAIN["facebook"] in _netloc:
            if re.search(r"/videos/|/watch/\?v=|/watch\?v=|/reel/|\?story_fbid=|/posts/pfbid", link):
                facebook_video_list.append(link)
                continue

            facebook_profile_list.append(link)
            continue

        if BASE_DOMAIN["kuaishou"] in _netloc or BASE_DOMAIN["kuaishou_redirect"] in _netloc:
            if re.search(r"/short-video/", _path) or BASE_DOMAIN["kuaishou_redirect"] in _netloc:
                kuaishou_video_list.append(link)
                continue

            kuaishou_profile_list.append(link)
            continue

        if BASE_DOMAIN["douyin"] in _netloc or BASE_DOMAIN["douyin_redirect"] in _netloc:
            if re.search(r"/video/", _path) or BASE_DOMAIN["douyin_redirect"] in _netloc:
                douyin_video_list.append(link)
                continue

            douyin_profile_list.append(link)
            continue

    return {
        "tiktok_video_list": tiktok_video_list,
        "tiktok_profile_list": tiktok_profile_list,
        "youtube_video_list": youtube_video_list,
        "youtube_profile_list": youtube_profile_list,
        "facebook_video_list": facebook_video_list,
        "facebook_profile_list": facebook_profile_list,
        "kuaishou_video_list": kuaishou_video_list,
        "kuaishou_profile_list": kuaishou_profile_list,
        "douyin_video_list": douyin_video_list,
        "douyin_profile_list": douyin_profile_list,
        "instagram_video_list": instagram_video_list,
        "instagram_profile_list": instagram_profile_list,
        "other_list": other_list,
        "generic_list": generic_list
    }


class ExtractWorker(DefaultWorker):
    def __init__(
        self,
        task_id: int,
        urls: list[str],
        extract_options: Optional[dict] = None
    ):
        super().__init__(task_id)
        self.task_id = task_id
        self.urls = urls
        self.with_url_dl = False
        self.is_profile = False

        self.extract_options = {}
        self.update_extract_options(extract_options)

        self.limit = 2
        self.use_per_next_cursor = False
        self.extract_video_type = "videos"

        self.on_stop_worker = self.on_stop_extraction

    def on_stop_extraction(self):
        pass

    def update_extract_options(self, extract_options: Optional[dict] = None):
        if isinstance(extract_options, dict):
            self.extract_options.update(extract_options)

    @Slot()
    def run(self):
        self.update_extract_options({
            'limit': self.limit,
            'use_per_next_cursor': self.use_per_next_cursor,
            'youtube_video_type': self.extract_video_type,
        })
        if self.is_profile:
            self.extract_videos_from_profile()
        else:
            self.extract_video_info_list()

    def extract_videos_from_profile(self):
        try:
            async def run():
                async with YouTubeExtractor() as scout:
                    scout.cancel = self.cancel

                    def on_callback_progress(d):
                        self.signals.progress.emit(self.task_id, d)

                    scout.on_extracting = on_callback_progress
                    info_list = []
                    for url in self.urls:
                        video_info_list = await scout.get_channel_videos(url)
                        if not video_info_list:
                            continue
                        info_list.extend(video_info_list)
                    self.signals.finished.emit(self.task_id, {
                        'status': 'finished',
                        'data': info_list
                    })

            asyncio.run(run())
        except Exception as e:
            self.signals.progress.emit(self.task_id, {
                'status': 'error',
                'error': str(e)
            })

    def extract_video_info_list(self):
        extract_dict = extract_url_list(self.urls)

        for key, value in extract_dict.items():
            if key.split("_")[0] in BASE_EXTRACTORS and len(value) > 0:
                extractor_class = BASE_EXTRACTORS[key.split("_")[
                    0]]
                self.run_extractor(extractor_class, url_list=value)

    def run_extractor(self, extractor_class: TYPE_EXTRACTOR, url_list: list[str]):
        try:
            async def run():
                async with extractor_class() as scout:
                    scout.cancel = self.cancel

                    extractor_name = None
                    try:
                        cookies = self.extract_options.get("cookies") or {}
                        extractor_name = scout._CLOUD_FOLDER.split("/")[-1]
                        raw_cookie = cookies.get(extractor_name)
                        if hasattr(scout, "set_cookies") and raw_cookie:
                            scout.set_cookies(raw_cookie)
                    except Exception as e:
                        scout.logger.debug(f"Set cookies error: {e}")

                    def on_callback_progress(d):
                        if d['status'] == 'progress':
                            self.signals.progress.emit(self.task_id, d)
                        elif d['status'] == 'finished':
                            self.signals.progress.emit(self.task_id, d)
                        elif d['status'] == 'error':
                            self.signals.error.emit(self.task_id, d)

                    scout.on_extracting = on_callback_progress
                    if extractor_name:
                        self.signals.progress.emit(self.task_id, {
                            'status': 'start',
                            'extractor': f"{extractor_name}".upper(),
                        })
                    if hasattr(scout, "get_video_info_list_yt_dlp"):
                        info_list = await scout.get_video_info_list_yt_dlp(url_list)
                    else:
                        info_list = await scout.get_video_info_list(url_list)
                    self.signals.finished.emit(self.task_id, {
                        'status': 'finished',
                        'data': info_list
                    })
            asyncio.run(run())
        except Exception as e:
            self.signals.error.emit(self.task_id, {
                'status': 'error',
                'error': str(e)
            })


class ExtractManager(QObject):
    # Signals to update the UI
    task_progress = Signal(int, dict)  # task_id, {status: str, info_list: []}
    task_status = Signal(int, str)  # task_id, status
    # task_id, {info_list: [], url_list: [], is_profile: bool}
    task_finished = Signal(int, dict)
    task_error = Signal(int, dict)  # task_id, error_msg

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3)
        self.active_workers = {}  # task_id -> DownloadWorker
        self.last_data_update = {}  # task_id -> last_timestamp
        self.options = {}

    def start_extraction(self, urls: list[str]):
        task_id = len(self.active_workers) + 1
        worker = ExtractWorker(task_id, urls, self.options)
        worker.signals.progress.connect(self.task_progress.emit)
        worker.signals.finished.connect(self.task_finished.emit)
        worker.signals.error.connect(self.task_error.emit)
        self.active_workers[task_id] = worker
        self.thread_pool.start(worker)
        return task_id

    def stop_extraction(self, task_id: int):
        if task_id in self.active_workers:
            self.active_workers[task_id].cancel()
            del self.active_workers[task_id]

    def stop_all_extraction(self):
        for task_id in list(self.active_workers.keys()):
            self.stop_extraction(task_id)


extract_manager = ExtractManager()
