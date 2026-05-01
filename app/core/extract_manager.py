import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Optional

from loguru import logger
from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from ..extractor.youtube import YouTubeExtractor
from ._worker import DefaultWorker, Slot


def fix_one_profile(video_links: list[str]):
    hostRedirectPattern = "vt.tiktok.com|v.douyin.com|v.kuaishou.com"

    video_list: list[str] = []
    is_profile = []

    for link in video_links:
        def match(pattern):
            return re.search(pattern, link)

        is_generic = "&download_with_info_dict=" in link

        if match(r'\.instagram\.com') and not is_generic:
            if not any(v == link.split("instagram.com/")[1].split('/')[0] for v in ["p", "reel", "reels"]):
                video_list.append(link)
                is_profile.append(True)

        elif match(r'\.tiktok\.com') and not is_generic:
            if "/video/" not in link:
                video_list.append(link)
                is_profile.append(True)

        elif match(r'\.youtube\.com') or match(r'\.youtu\.be'):
            if match(r"youtube\.com\/channel\/") or match(r"youtube\.com\/@"):
                video_list.append(link)
                is_profile.append(True)

        elif match(r'\.facebook\.com'):
            if not any(v in link for v in ["/videos/", "/watch?v=", "/watch/?v=", "/reel/", "?story_fbid=", "/posts/pfbid"]):
                video_list.append(link)
                is_profile.append(True)

        elif (match(r'\.kuaishou\.com/profile/') or match(r'\.kuaishou\.com/fw/user/')) and not is_generic:
            video_list.append(link)
            is_profile.append(True)

        elif (match(r'\.douyin\.com/user/') or match(r'\.douyin\.com/share/user/')) and not is_generic:
            video_list.append(link)
            is_profile.append(True)

    return video_list, len(is_profile) > 0


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
                        async for video_info in scout.get_channel_videos(url):
                            info_list.append(video_info)
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
        try:
            async def run():
                async with YouTubeExtractor() as scout:
                    scout.cancel = self.cancel

                    def on_callback_progress(d):
                        if d['status'] == 'progress':
                            self.signals.progress.emit(self.task_id, d)
                        elif d['status'] == 'finished':
                            self.signals.progress.emit(self.task_id, d)
                        elif d['status'] == 'error':
                            self.signals.error.emit(self.task_id, d)

                    scout.on_extracting = on_callback_progress
                    info_list = await scout.get_video_info_list(self.urls)
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

    def start_extraction(self, urls: list[str], extract_options: Optional[dict] = None):
        task_id = len(self.active_workers) + 1
        worker = ExtractWorker(task_id, urls, extract_options)
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
        for task_id in self.active_workers:
            self.active_workers[task_id].cancel()
            del self.active_workers[task_id]


extract_manager = ExtractManager()
