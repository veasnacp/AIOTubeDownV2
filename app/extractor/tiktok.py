import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from curl_cffi.requests import BrowserTypeLiteral, Response

from ._request import ExtractorBase, get_content_from_html_selector

current_dir = Path(__file__).parent


class TikTokBaseIE(ExtractorBase):
    _BASE_URL = "https://www.tiktok.com"
    _LINK_USERNAME = "https://www.tiktok.com/@%s"
    _LINK_ID_USERNAME = "https://www.tiktok.com/@%s/video/%s"
    _LINK_ID = "https://www.tiktok.com/@tiktok/video/%s"
    _CLOUD_FOLDER = "videos/tiktok"

    _TEST_VIDEO_ID = "7597026176611175687"

    _API_USER_POST = "https://www.tiktok.com/api/post/item_list/"
    # https://www.tikwm.com/api/user/posts?unique_id=@krita_juju1810&count=2&cursor=0
    _API_TIKWM_USER = 'https://www.tikwm.com/api/user/posts?unique_id=@%s&count=%s&cursor=%s'
    _API_TIKWM_VIDEO = 'https://www.tikwm.com/api/?url=%s'

    # https://stackoverflow.com/questions/62767867/embed-video-from-tiktok

    _BASE_URL_TIKWM = 'https://tikwm.com'
    _TIKWM_PLAY = '%s/video/media/play/%s.mp4' % (_BASE_URL_TIKWM, '%s')
    _TIKWM_HDPLAY = '%s/video/media/hdplay/%s.mp4' % (_BASE_URL_TIKWM, '%s')
    _TIKWM_WMPLAY = '%s/video/media/wmplay/%s.mp4' % (_BASE_URL_TIKWM, '%s')
    # https://www.tikwm.com/api/user/posts?unique_id=@chang.bannc&count=35&cursor=0

    _HEADERS_VIDEO_HTML = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=0, i",
        # "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "cookie": "",
    }

    # USE LATER
    _API_VIDEO_EMBED = "https://www.tiktok.com/player/api/v1/items?item_ids=%s&language=en-US&aid=1459"
    _HEADERS_VIDEO_EMBED = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "agw-js-conv": "str",
        "priority": "u=1, i",
        # "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": "",
        "Referer": "https://www.tiktok.com/embed/v3/7390218309783784712",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

    def __init__(self, proxies: Optional[List[str]] = None, impersonate: BrowserTypeLiteral = "safari172_ios", timeout: int = 30):
        super().__init__(proxies, impersonate, timeout)

    def get_url_video_id(self, url_vid: str):
        url = url_vid.strip()
        video_id = None
        if not url.startswith("http") and not "/video/" in url:
            video_id = re.sub(r'\D', '', url)
            url = self._LINK_ID % video_id

        return url, video_id

    def get_user_id(self, url_uid: str):
        user_id = url_uid.split(
            "@")[1].split('?')[0].split('/')[0] if "@" in url_uid else url_uid.strip()
        return user_id

    def datetime_timestamp(self, ts: int):
        return datetime.fromtimestamp(ts) if ts > 0 else "Unknown"

    def extract_node(self, node: dict) -> dict[str, Any]:
        video = node
        video_id = video.get("video_id") or video.get("id", "")
        music = node['music'] if isinstance(
            node.get("music"), dict) else node.get("music_info") or {}
        _video = video.get("video")
        _stats = video.get("stats", {}) if isinstance(
            video.get("stats"), dict) else video
        stats = {
            "view_count": _stats.get("playCount") or _stats.get("play_count", 0),
            "like_count": _stats.get("diggCount") or _stats.get("digg_count", 0),
            "comment_count": _stats.get("commentCount") or _stats.get("comment_count", 0),
            "share_count": _stats.get("shareCount") or _stats.get("share_count", 0)
        }

        # url_dl_watermark = video["play_addr"]["url_list"][0]
        # url_dl = url_dl_watermark.replace("playwm", "play")
        if isinstance(_video, dict):
            # url_dl = self._TIKWM_PLAY % video_id
            # url_dl_watermark = self._TIKWM_WMPLAY % video_id
            url_dl = '/video/media/play/%s.mp4' % video_id
            url_dl_watermark = '/video/media/wmplay/%s.mp4' % video_id
            width = _video.get("width", 0)
            height = _video.get("height", 0)
            resolution = "%sx%s" % (width, height)
            tt_chain_token = {
                "playAddr": _video.get("playAddr"),
                "downloadAddr": _video.get("downloadAddr"),
            }
        else:
            playwm = video["playwm"] if video.get(
                "playwm") else video.get("wmplay", "")
            play_addr = video["play_addr"] if video.get(
                "play_addr") else video.get("play", "")
            url_dl = play_addr
            url_dl_watermark = playwm

            width = video.get("width", 0)
            height = video.get("height", 0)
            resolution = "%sx%s" % (width, height)
            tt_chain_token = {}

        timestamp = int(video.get("create_time") or video.get("createTime", 0))

        user = node.get("author", {})
        if user.get("unique_id"):
            user_id = user["unique_id"]
        elif user.get("uniqueId"):
            user_id = user["uniqueId"]
        else:
            user_id = user.get("id", "")
        url = self._LINK_ID_USERNAME % (user_id, video_id)

        user_keys = ["id", "nickname", "avatar", "avatarLarger",
                     "avatarMedium", "avatarThumb", "signature", "secUid"]
        # user_keys = ["avatar_thumb","follower_count","total_favorited","sec_uid","unique_id_modify_time","cover_url"]
        user_info = {
            "username": user_id
        }
        for key in user_keys:
            if user.get(key) is not None:
                if key == "avatarThumb":
                    user_info["avatar"] = user["avatarThumb"]
                else:
                    user_info[key] = user[key]
        title = node["title"] if node.get(
            "title") is not None else node.get("desc", "")
        title = title if title != "" else "Video by %s [%s]" % (
            user_id, video_id)

        if isinstance(_video, dict):
            cover = _video.get("cover", "")
            origin_cover = _video.get("originCover", cover)
        else:
            cover = video["cover_original_scale"] if video.get(
                "cover_original_scale") is not None else video.get("cover", "")
            origin_cover = video["origin_cover"] if video.get(
                "origin_cover") is not None else cover

        info_dict = {
            "id": video_id,
            "display_id": video_id,
            "title": title,
            "fulltitle": title,
            "description": title,
            "thumbnail": cover,
            "original_thumbnail": origin_cover,
            "sd": url_dl,
            "hd": url_dl,
            "dl_with_watermark": url_dl_watermark,
            **tt_chain_token,
            "music": music.get("play") or music.get("playUrl", ""),
            "music_info": music,
            "requested_download": [{
                "title": title,
                "width": width,
                "height": height,
                "resolution": resolution,
                "url": url,
                # "video": unescape(video_hd),
            }],
            "uploader": user_id or user_info.get("id") or user.get("nickname", ""),
            "uploader_id": user_info.get("id", ""),
            "uploader_url": self._LINK_USERNAME % user_id,
            "url": url,
            "original_url": url,
            "webpage_url": url,
            "webpage_url_domain": "tiktok.com",
            "extractor": "tiktok",
            "extractor_key": "TikTok",
            "width": width,
            "height": height,
            "resolution": resolution,
            "duration": _video.get("duration", 0) if isinstance(_video, dict) else video.get("duration", 0),
            "timestamp": timestamp,
            "release_timestamp": timestamp,
            "upload_date": str(self.datetime_timestamp(timestamp)),
            **stats,
            "subtitles": [],
            "audio_only": [],
            "video_only": [],
            "both": [],
            "user_info": {
                "name": user.get("nickname", ""),
                **user_info
            }
        }
        return info_dict

    def get_video_info(self, content: str, url: str):
        data_content = get_content_from_html_selector(
            str(content), "script", ['id=\"__UNIVERSAL_DATA_FOR_REHYDRATION__\"'])

        if len(data_content) > 0:
            data = json.loads(data_content[0])
            video_detail = data.get("__DEFAULT_SCOPE__", {}).get(
                "webapp.video-detail")
            node = video_detail.get("itemInfo", {}).get("itemStruct")

            if isinstance(node, dict) and str(node.get("createTime"))\
                    and int(node.get("createTime") or 0) != 0:
                video_info = self.extract_node(node)
                user_id = video_info.get("uploader", "_")
                user_info = video_info.get("user_info", {})
                return video_info, user_id, user_info
            else:
                self.logger.debug("Error => Create Time is 0 with URL: ", url)
                return None
        else:
            self.logger.debug("No Data: ", url)
            return None


class TikTokExtractor(TikTokBaseIE):

    async def _get_html_content(self, url):
        response = await self.request(
            url, headers=self._HEADERS_VIDEO_HTML,
            impersonate=self.impersonate
        )
        if not isinstance(response, Response):
            return None
        self.save_html_text(response.text, "")
        return response.text

    async def get_video_info_list(self, url_list: List[str]) -> List[Dict[str, Any]]:
        url_list = [self.get_url_video_id(url)[0] for url in url_list]

        tasks = []
        for url in url_list:
            tasks.append(self._get_html_content(url))
        content_list = await asyncio.gather(*tasks)

        video_info_list = []
        error_list = []
        user_info_dict = {}
        for i, content in enumerate(content_list):
            url = url_list[i]
            if self.cancel:
                break
            if not isinstance(content, str) or content == "":
                error_list.append(url)
                continue
            try:
                res = self.get_video_info(content, url)
                if res is None:
                    error_list.append(url)
                    continue
                video_info, user_id, user_info = res
                # if not (isinstance(user_info_dict.get(user_id), dict)):
                #     user_info_dict[user_id] = user_info
                self._on_extracting({
                    "status": "progress",
                    "url": url,
                    "data": video_info
                })
                video_info_list.append(video_info)

            except ValueError as err:
                self.logger.debug(err)
                self._on_extracting(
                    {"error": str(err), "url": url, "status": "error"})

        return video_info_list

    async def test_get_video_info_list(self):
        self._skip_cached_info = True
        url = self._LINK_ID % self._TEST_VIDEO_ID
        url, _video_id = self.get_url_video_id(url)
        self.logger.debug(f"Video URL: {url}, {_video_id}")
        info_list = await self.get_video_info_list([url])
        # info_list = self.load_test_data()
        # from yt_dlp import YoutubeDL

        # yt_dl_options = {
        #     'outtmpl': f'{self.get_output_dir()}/test/%(title)s.%(ext)s'
        # }
        # with YoutubeDL(yt_dl_options) as ydl:
        #     info = ydl.extract_info(url, download=False)
        #     info_list = [info]
        if info_list:
            self.save_test_data(info_list)
        return info_list
