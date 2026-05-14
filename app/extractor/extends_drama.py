import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .kuaishou import KuaishouExtractor as _KuaishouExtractor
from .tiktok import TikTokExtractor as _TikTokExtractor
from .youtube import YouTubeExtractor as _YouTubeExtractor
from .youtube import YouTubeSortBy

current_dir = Path(__file__).parent


class YouTubeExtractor(_YouTubeExtractor):
    _EXTENDS_NAME = 'youtube'

    def get_drama_id(self, url: str):
        channel_url, username = self.get_channel_url_username(url)
        return channel_url, username

    def get_cover_url(self, info: Dict[str, Any]):
        return info.get("cover", "")

    def get_video_url_play(self, chapter: Dict[str, Any]):
        return chapter.get("sd", "")

    async def get_profile_info(
        self,
        url: str,
        limit: Optional[int] = None,
        sort_by: YouTubeSortBy.ChannelVideos = "newest",
        next_data: Optional[dict] = None,
        use_per_next_cursor: bool = False,
        content_type: YouTubeSortBy.VideoType = "videos"
    ):
        info_list = []
        async for data in self.get_channel_videos(
            url,
            content_type,
            limit,
            sort_by,
            use_per_next_cursor,
            next_data
        ):
            info_list.append(data)

        if not isinstance(info_list, list):
            self.logger.error(f"[!] ❌ No channel/videos info found")
            return None
        if len(info_list) == 0:
            self.logger.info("[!] ✅ Found 0 videos")
            return None

        channel_url, username = self.get_channel_url_username(url)
        info = {}
        for idx, data in enumerate(info_list):
            if idx == 0:
                info.update(data.get('user_info', {}))
                info['title'] = data.get('uploader', "Unknown")
                info['cover'] = data.get('thumbnail', "")
                break
        info['chapterList'] = info_list
        self._cache[username] = info
        return info

    async def download_all_episodes(
        self,
        info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        # progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False
    ):
        pass


class TikTokExtractor(_TikTokExtractor):
    _EXTENDS_NAME = 'tiktok'

    def get_drama_id(self, url: str):
        user_id = self.get_user_id(url)
        url = self._LINK_USERNAME % user_id
        return url, user_id

    def get_cover_url(self, info: Dict[str, Any]):
        return info.get("cover", "")

    def get_video_url_play(self, chapter: Dict[str, Any]):
        return chapter.get("sd", "")

    async def get_profile_info(
        self,
        url: str,
        limit: int | None = None,
        sort_by: str = "newest",
        cursor_continue: str = '',
        cursor_position: int = 0,
        use_per_next_cursor: bool = False
    ):
        info_list = await self.get_video_info_list_from_user(
            url,
            limit,
            sort_by,
            cursor_continue,
            cursor_position,
            use_per_next_cursor
        )
        if not isinstance(info_list, list):
            self.logger.error(f"[!] ❌ No profile/videos info found")
            return None
        if len(info_list) == 0:
            self.logger.info("[!] ✅ Found 0 videos")
            return None

        user_id = self.get_user_id(url)
        info = {}
        for idx, data in enumerate(info_list):
            if idx == 0:
                info.update(data.get('user_info', {}))
                info['title'] = data.get('uploader', "Unknown")
                info['cover'] = data.get('thumbnail', "")
                break
        info['chapterList'] = info_list
        self._cache[user_id] = info
        return info

    async def download_all_episodes(
        self,
        info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        # progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False
    ):
        pass


class KuaishouExtractor(_KuaishouExtractor):
    _EXTENDS_NAME = 'kuaishou'

    def get_drama_id(self, url: str):
        user_id = self.get_user_id(url)
        url = self._LINK_USER_WITH % user_id
        return url, user_id

    def get_cover_url(self, info: Dict[str, Any]):
        return info.get("cover", "")

    def get_video_url_play(self, chapter: Dict[str, Any]):
        return chapter.get("sd", "")

    def _set_cookie_testing(self):
        raw_cookies = None
        cookie_path = current_dir / "_data" / "cookies.json"
        if cookie_path.exists():
            with open(cookie_path, "r") as f:
                cookies = json.load(f)
                raw_cookies = cookies.get('kuaishou') or None

        if raw_cookies:
            self.set_cookies(raw_cookies)

    async def get_profile_info(
        self,
        url: str,
        limit: int | None = None,
        sort_by: str = "newest",
        cursor_continue: str = '',
        cursor_position: int = 0,
        use_per_next_cursor: bool = False
    ):
        self._set_cookie_testing()
        info_list = await self.get_video_info_list_from_user(
            url,
            limit,
            sort_by,
            cursor_continue,
            cursor_position,
            use_per_next_cursor
        )
        if not isinstance(info_list, list):
            self.logger.error(f"[!] ❌ No profile/videos info found")
            return None
        if len(info_list) == 0:
            self.logger.info("[!] ✅ Found 0 videos")
            return None

        user_id = self.get_user_id(url)
        info = {}
        for idx, data in enumerate(info_list):
            if idx == 0:
                info.update(data.get('user_info', {}))
                info['title'] = data.get('uploader', "Unknown")
                info['cover'] = data.get('thumbnail', "")
                break
        info['chapterList'] = info_list
        self._cache[user_id] = info
        return info

    async def download_all_episodes(
        self,
        info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        # progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False
    ):
        pass
