import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..extractor._utils import arr_chunk
from .facebook import FacebookExtractor as _FacebookExtractor
from .kuaishou import KuaishouExtractor as _KuaishouExtractor
from .tiktok import TikTokExtractor as _TikTokExtractor
from .youtube import YouTubeExtractor as _YouTubeExtractor
from .youtube import YouTubeSortBy

# from .douyin import DouyinExtractor as _DouyinExtractor

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

    def get_chapter_url(self, chapter: Dict[str, Any]):
        return chapter.get("url", "")

    def get_next_options(self, chapter_list: List[Dict] | None = None, more="next"):
        options = {
            "limit": None,
            "sort_by": "newest",
            "next_data": None,
            "cursor_position": 0,
            "use_per_next_cursor": False if more == "all" else True,
            "content_type": "videos",
        }
        if not chapter_list:
            return options

        last_chapter = chapter_list[-1]
        next_data = last_chapter.get("next_data")
        cursor_position = last_chapter.get("cursor_position")
        cursor_position = cursor_position + 1 if cursor_position else 0
        options["next_data"] = next_data
        options["cursor_position"] = cursor_position

        return options

    async def get_profile_info(
        self,
        url: str,
        limit: Optional[int] = None,
        sort_by: YouTubeSortBy.ChannelVideos = "newest",
        next_data: Optional[dict] = None,
        cursor_position: int = 0,
        use_per_next_cursor: bool = False,
        content_type: YouTubeSortBy.VideoType = "videos"
    ):
        info_list = await self.get_channel_videos(
            url,
            content_type,
            limit,
            sort_by,
            next_data,
            cursor_position,
            use_per_next_cursor,
        )

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

    async def update_all_episodes(self, info, chunk_size=10):
        chapter_list = info['chapterList']
        url_list = [
            chapter_info['url'] for chapter_info in chapter_list
            if not chapter_info.get('sd') and not chapter_info.get('hd')
        ]

        if len(url_list) <= 0:
            return info

        return await self.update_episodes_selected(url_list, info)

    async def update_episodes_selected(self, url_list: list[str], info: Dict[str, Any]):
        user_id = info['id']
        chapter_list = info['chapterList']

        def merge_info(video_info):
            if video_info.get("id"):
                for chapter_info in chapter_list:
                    if chapter_info['id'] == video_info['id']:
                        chapter_info.update(video_info)
                        break

        video_info_list = await self.get_video_info_list(url_list, merge_info)
        if video_info_list and len(video_info_list) > 0:
            msg = ""
            if len(video_info_list) == 1:
                msg = f" from ID: {video_info_list[0].get('id')}"
            self.logger.info(
                f"[!] ✅ Updated {len(video_info_list)} videos{msg}")

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


class FacebookExtractor(_FacebookExtractor):
    _EXTENDS_NAME = 'facebook'

    def get_drama_id(self, url: str):
        user_id = self.get_user_id(url)
        url = self._LINK_USER_REEL_WITH % (user_id, '')
        return url, user_id

    def get_cover_url(self, info: Dict[str, Any]):
        return info.get("cover", "")

    def get_video_url_play(self, chapter: Dict[str, Any]):
        return chapter.get("sd", "")

    def get_chapter_url(self, chapter: Dict[str, Any]):
        return chapter.get("url", "")

    def get_next_options(self, chapter_list: List[Dict] | None = None, more="next"):
        options = {
            "limit": None,
            "sort_by": "newest",
            "cursor_continue": "",
            "cursor_position": 0,
            "use_per_next_cursor": False if more == "all" else True,
            "content_type": "reels",
            "page_id": None,
        }
        if not chapter_list:
            return options

        last_chapter = chapter_list[-1]
        cursor_continue = last_chapter.get("next_cursor") or ""
        cursor_position = last_chapter.get("cursor_position")
        cursor_position = cursor_position + 1 if cursor_position else 0
        page_id = last_chapter.get("page_id")
        options["cursor_continue"] = cursor_continue
        options["cursor_position"] = cursor_position
        options["page_id"] = page_id

        return options

    async def get_profile_info(
        self,
        url: str,
        limit: int | None = None,
        sort_by: str = "newest",
        cursor_continue: str = '',
        cursor_position: int = 0,
        use_per_next_cursor: bool = False,
        content_type: str = "reels",
        page_id: str | None = None
    ):
        info_list = await self.get_video_info_list_from_user(
            url,
            limit,
            sort_by,
            cursor_continue,
            cursor_position,
            use_per_next_cursor,
            content_type,
            page_id
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

    def get_chapter_url(self, chapter: Dict[str, Any]):
        return chapter.get("url", "")

    def get_next_options(self, chapter_list: List[Dict] | None = None, more="next"):
        options = {
            "limit": None,
            "sort_by": "newest",
            "cursor_continue": "",
            "cursor_position": 0,
            "use_per_next_cursor": False if more == "all" else True,
        }
        if not chapter_list:
            return options

        last_chapter = chapter_list[-1]
        cursor_continue = last_chapter.get("next_cursor") or ""
        cursor_position = last_chapter.get("cursor_position")
        cursor_position = cursor_position + 1 if cursor_position else 0
        options["cursor_continue"] = cursor_continue
        options["cursor_position"] = cursor_position

        return options

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

    def get_chapter_url(self, chapter: Dict[str, Any]):
        return chapter.get("url", "")

    def _set_cookie_testing(self):
        raw_cookies = None
        cookie_path = current_dir / "_data" / "cookies.json"
        if cookie_path.exists():
            with open(cookie_path, "r") as f:
                cookies = json.load(f)
                raw_cookies = cookies.get('kuaishou') or None

        if raw_cookies:
            self.set_cookies(raw_cookies)

    def get_next_options(self, chapter_list: List[Dict] | None = None, more="next"):
        options = {
            "limit": None,
            "sort_by": "newest",
            "cursor_continue": "",
            "cursor_position": 0,
            "use_per_next_cursor": False if more == "all" else True,
        }
        if not chapter_list:
            return options

        last_chapter = chapter_list[-1]
        cursor_continue = last_chapter.get("next_cursor") or ""
        cursor_position = last_chapter.get("cursor_position")
        cursor_position = cursor_position + 1 if cursor_position else 0
        options["cursor_continue"] = cursor_continue
        options["cursor_position"] = cursor_position

        return options

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
