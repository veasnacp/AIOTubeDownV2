import asyncio
import base64
import functools
import hashlib
import itertools
import json
import random
import re
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from curl_cffi.requests import BrowserTypeLiteral, Response
from yt_dlp.utils import extract_attributes, find_element, require, traverse_obj

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
    _API_CREATOR_ITEM_LIST = 'https://www.tiktok.com/api/creator/item_list/'
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

    _LINK_USER_EMBED = "https://www.tiktok.com/embed/@%s"
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

    def __init__(self, proxies: Optional[List[str]] = None, impersonate: BrowserTypeLiteral = "chrome120", timeout: int = 30):
        super().__init__(proxies, impersonate, timeout)
        self.concurrent_tasks = 10
        self.delay_jitter = False
        self.device_id = None

    @functools.cached_property
    def _KNOWN_DEVICE_ID(self):
        return self.device_id or None

    @functools.cached_property
    def _DEVICE_ID(self):
        return self._KNOWN_DEVICE_ID or str(random.randint(7250000000000000000, 7325099899999994577))

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

    def get_video_play(self, info: dict, quality: str = 'hd'):
        if quality == 'hd':
            if info['hd'].startswith('http'):
                return info['hd'].replace("faid=1988", "faid=1180")
            else:
                return self._TIKWM_HDPLAY % info['id']
        elif quality == 'sd':
            if info['sd'].startswith('http'):
                return info['sd'].replace("faid=1988", "faid=1180")
            else:
                return self._TIKWM_PLAY % info['id']
        elif quality == 'wm':
            if info['dl_with_watermark'].startswith('http'):
                return info['dl_with_watermark'].replace("faid=1988", "faid=1180")
            else:
                return self._TIKWM_WMPLAY % info['id']

        return info['hd']

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

        video_only = []
        audio_only = []
        both = []
        has_720p = False
        if isinstance(_video, dict) and "bitrateInfo" in _video:
            _bitrate_info = _video["bitrateInfo"]
            if isinstance(_bitrate_info, list):
                for item in _bitrate_info:
                    _play_addr = item.get("PlayAddr")
                    if not isinstance(_play_addr, dict):
                        continue
                    _url_list = _play_addr.get("UrlList")
                    if not isinstance(_url_list, list):
                        continue
                    _url = _url_list[-1]
                    if _url and "faid=1988" in _url and "signaturev3=" in _url:
                        _url = _url.replace("faid=1988", "faid=1180")
                        _width = int(_play_addr.get("Width", 0))
                        _height = int(_play_addr.get("Height", 0))
                        _vcodec = item.get("CodecType", "unknown")
                        _ext = item.get("Format", "mp4")
                        _video_info = {
                            "filesize": int(_play_addr.get("DataSize", 0)),
                            "tbr": int(item.get("Bitrate", 0)),
                            "fps": int(item.get("BitrateFPS", 0)),
                            "vcodec": _vcodec,
                            "acodec": "acc",
                            "ext": _ext,
                            "width": _width,
                            "height": _height,
                            "resolution": "%sx%s" % (_width, _height),
                            "url": _url,
                            "url_list": _url_list,
                        }
                        if "hvc1" in _vcodec and _ext != "mp4":
                            video_only.append(_video_info)
                        else:
                            both.append(_video_info)
                        if _width == 720:
                            has_720p = True
                            url_dl = _url
                            url_dl_watermark = _url
                            width = _width
                            height = _height
                            resolution = _video_info["resolution"]
                            tt_chain_token = {}

            if len(both) > 0:
                both.sort(key=lambda x: x["width"], reverse=True)
                if not has_720p:
                    url_dl = both[0]["url"]
                    url_dl_watermark = both[0]["url"]
                    width = both[0]["width"]
                    height = both[0]["height"]
                    resolution = both[0]["resolution"]
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
            "video_only": video_only,
            "both": both,
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

    def _build_web_query(self, sec_uid: str, cursor: str, count: int = 15):
        return {
            'aid': '1988',
            'app_language': 'en',
            'app_name': 'tiktok_web',
            'browser_language': 'en-US',
            'browser_name': 'Mozilla',
            'browser_online': 'true',
            'browser_platform': 'Win32',
            'browser_version': '5.0 (Windows)',
            'channel': 'tiktok_web',
            'cookie_enabled': 'true',
            'count': str(count),
            'cursor': cursor,
            'device_id': self._DEVICE_ID,
            'device_platform': 'web_pc',
            'focus_state': 'true',
            'from_page': 'user',
            'history_len': '2',
            'is_fullscreen': 'false',
            'is_page_visible': 'true',
            'language': 'en',
            'os': 'windows',
            'priority_region': '',
            'referer': '',
            'region': 'US',
            'screen_height': '1080',
            'screen_width': '1920',
            'secUid': sec_uid,
            'type': '1',  # pagination type: 0 == oldest-to-newest, 1 == newest-to-oldest
            'tz_name': 'UTC',
            'verifyFp': f'verify_{"".join(random.choices(string.hexdigits, k=7))}',
            'webcast_language': 'en',
        }


class TikTokExtractor(TikTokBaseIE):
    def _solve_challenge_and_set_cookies(self, webpage: str):
        challenge_data = traverse_obj(webpage, (
            {find_element(id='cs', html=True)}, {extract_attributes}, 'class',
            filter, {lambda x: f'{x}==='}, {base64.b64decode}, {json.loads}
        ))

        if not challenge_data:
            if 'Please wait...' in webpage:
                raise ValueError('Unable to extract challenge data')
            raise ValueError('Unexpected response from webpage request')

        self.logger.info(
            'Solving JS challenge using native Python implementation')

        expected_digest = traverse_obj(challenge_data, (
            'v', 'c', {str}, {base64.b64decode},
            {require('challenge expected digest')}))

        base_hash = traverse_obj(challenge_data, (
            'v', 'a', {str}, {base64.b64decode},
            {hashlib.sha256}, {require('challenge base hash')}))

        for i in range(1_000_001):
            number = str(i).encode()
            test_hash = base_hash.copy()
            test_hash.update(number)
            if test_hash.digest() == expected_digest:
                challenge_data['d'] = base64.b64encode(number).decode()
                break
        else:
            raise ValueError('Unable to solve JS challenge')

        wci_cookie_value = base64.b64encode(
            json.dumps(challenge_data, separators=(',', ':')).encode()).decode()

        # At time of writing, the wci cookie name was `_wafchallengeid`
        wci_cookie_name = traverse_obj(webpage, (
            {find_element(id='wci', html=True)}, {extract_attributes},
            'class', {require('challenge cookie name')}))

        # At time of writing, the **optional** rci cookie name was `waforiginalreid`
        rci_cookie_name = traverse_obj(webpage, (
            {find_element(id='rci', html=True)}, {extract_attributes}, 'class'))
        rci_cookie_value = traverse_obj(webpage, (
            {find_element(id='rs', html=True)}, {extract_attributes}, 'class'))

        # Actual JS sets Max-Age=1 for the cookies, but we'll manually clear them later instead
        expire_time = int(time.time()) + 120
        self.session.cookies.set(
            name=wci_cookie_name,
            value=wci_cookie_value,
            domain='.tiktok.com',
        )
        self.session.cookies.update({
            'name': wci_cookie_name,
            'value': wci_cookie_value,
            'domain': '.tiktok.com',
            'expires': str(expire_time)
        })
        if rci_cookie_name and rci_cookie_value:
            self.session.cookies.update({
                'name': rci_cookie_name,
                'value': rci_cookie_value,
                'domain': '.tiktok.com',
                'expires': str(expire_time)
            })

        return wci_cookie_name, rci_cookie_name

    async def _get_html_content(self, url):
        if self.delay_jitter:
            # Human-like delay (Jitter) to avoid pattern detection
            await asyncio.sleep(random.uniform(1.5, 4.0))

        async def get_webpage():
            response = await self.request(
                url, headers=self._HEADERS_VIDEO_HTML,
                retries=0
            )
            if not isinstance(response, Response):
                return None
            self.save_html_text(response.text, "")
            return response.text

        web_page = await get_webpage()
        if not web_page:
            return None

        cookies = self.session.cookies.get_dict()
        self.logger.debug(f"Cookies: {cookies}")
        if 'tt_chain_token' not in cookies:
            try:
                cookie_names = self._solve_challenge_and_set_cookies(web_page)
            except Exception as e:
                self.logger.debug(e)
                return web_page

            web_page = await get_webpage()
            if not web_page:
                return None

            for cookie_name in filter(None, cookie_names):
                self.session.cookies.jar.clear(
                    domain='.tiktok.com', path='/', name=cookie_name)

        return web_page

    async def get_video_info_from_embed(self, video_id: str):
        url = self._API_VIDEO_EMBED % video_id
        response = await self.request(
            url,
            retries=0
        )
        if not isinstance(response, Response):
            return None

        try:
            data = response.json()
            return data
        except ValueError as e:
            self.logger.debug(e)
            return None

    async def get_video_info_list(self, url_list: List[str]) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(self.concurrent_tasks)
        if len(url_list) > 15:
            self.delay_jitter = True

        tasks = []
        valid_url_list = []
        async with semaphore:
            for url in url_list:
                if self.cancel:
                    self.on_extracting({"status": "cancelled"})
                    break
                url, _ = self.get_url_video_id(url)
                valid_url_list.append(url)
                tasks.append(self._get_html_content(url))
        content_list = await asyncio.gather(*tasks)

        video_info_list = []
        error_list = []
        user_info_dict = {}
        for i, content in enumerate(content_list):
            url = valid_url_list[i]
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

    async def extract_info_profile_tikwm(
        self,
        url_uid: str,
        limit: int = None,
        sort_by="newest",
        cursor_continue='',
        use_per_next_cursor=False
    ):
        global cursor, hasMore
        cursor = cursor_continue if cursor_continue and cursor_continue != '' else '0'
        cursor_position = int(0)
        hasMore = False

        use_per_next_cursor = sort_by and sort_by == "newest" and use_per_next_cursor

        user_id = self.get_user_id(url_uid)

        count = 0
        limit_copy = limit
        video_list = []
        video_info_list = []
        for i in range(300):
            if self.cancel:
                break
            url = self._API_TIKWM_USER % (
                user_id,
                limit if (isinstance(limit, int) and limit !=
                          0) and limit < 35 else 35,
                cursor
            )

            try:
                r = await self.request(url, retries=0)
                if not isinstance(r, Response):
                    continue
                self.save_html_text(r.text, "_user_tikwm")
                data = json.loads(r.text)["data"]
                hasMore = data['hasMore']
                current_cursor = cursor
                cursor = data["cursor"]

                for info in data['videos']:
                    count += 1
                    video_info = self.extract_node(info)
                    video_info['cursor'] = current_cursor
                    video_info['next_cursor'] = '' if not hasMore else cursor
                    video_info['cursor_position'] = cursor_position

                    video_link = video_info.get("original_url")
                    video_list.append(video_link)
                    video_info_list.append(video_info)
                    self.on_extracting({
                        "status": "progress",
                        "url": url,
                        "data": video_info
                    })

                    if sort_by and sort_by != "newest":
                        limit_copy = None
                    if not use_per_next_cursor and count == limit_copy:
                        hasMore = False
                        break

                if use_per_next_cursor:
                    break
                cursor_position += 1
                if hasMore is False or count == limit_copy:
                    break
            except ValueError as err:
                self.logger.debug(err)
                raise Exception(err, url_uid)

        if len(video_info_list) <= 0:
            return

        if sort_by and sort_by != "newest":
            limit = limit if isinstance(
                limit, int) and limit != 0 else len(video_info_list)
            if sort_by == "popular":
                sort_key = "view_count"
                reverse = True
            else:
                sort_key = "timestamp"
                reverse = False

            video_info_list.sort(key=lambda x: int(
                x[sort_key]), reverse=reverse)
            video_info_list = video_info_list[0:limit]

        return video_info_list

    async def _extract_sec_uid_from_embed(self, user_name):
        resp = await self.request(self._LINK_USER_EMBED % user_name, retries=0)
        if not isinstance(resp, Response):
            return None
        if resp.status_code != 200:
            return None

        html = resp.text

        data_content = get_content_from_html_selector(
            html, 'script', ['id=\"__FRONTITY_CONNECT_STATE__\"'])
        if not data_content or not (f"/embed/@{user_name}" in data_content[0]):
            return None

        try:
            data = json.loads(data_content[0])
            video_list = data['source']['data'][f"/embed/@{user_name}"]['videoList']
            for video in video_list:
                video_id = video.get('id')
                if not video_id:
                    return None

                data_info = await self.get_video_info_from_embed(video_id)
                if not data_info or not isinstance(data_info, dict):
                    return None

                sec_uid = data_info['items'][0]['author_info']['secret_id']
                return sec_uid
        except Exception as err:
            self.logger.debug(f"_extract_sec_uid_from_embed error: {err}")
            return None

    async def get_video_info_list_from_user(
        self,
        url_uid: str,
        limit: int = None,
        sort_by="newest",
        cursor_continue='',
        cursor_position: int = 0,
        use_per_next_cursor=False
    ):
        global cursor, has_more
        cursor = cursor_continue if cursor_continue and cursor_continue != '' \
            else str(int(time.time() * 1E3))
        cursor_position = int(cursor_position) if isinstance(cursor_position, int) \
            else int(0)
        has_more = False

        use_per_next_cursor = sort_by and sort_by == "newest" and use_per_next_cursor

        user_id = self.get_user_id(url_uid)

        sec_uid = await self._extract_sec_uid_from_embed(user_id)
        if not sec_uid:
            return None

        count = 0
        limit_copy = limit
        video_list = []
        video_info_list = []
        for page in itertools.count(1):
            if self.cancel:
                break

            if limit_copy and len(video_info_list) >= limit_copy:
                break

            url = self._API_CREATOR_ITEM_LIST
            params = self._build_web_query(sec_uid, cursor)
            self.logger.debug(f"[cursor]: {cursor}")
            try:
                r = None
                for _ in range(0, 2):
                    r = await self.request(url, params=params, retries=0)
                    if not isinstance(r, Response):
                        continue
                    self.logger.debug("[status]: %s" % r.status_code)
                    if r.status_code == 429:
                        self.logger.debug("[ratelimit]: %s" % cursor)
                        await asyncio.sleep(10)
                        continue
                    else:
                        break

                if not isinstance(r, Response):
                    continue

                if r.status_code == 429 or 'itemList' not in r.text:
                    await asyncio.sleep(5)
                    continue

                self.save_html_text(r.text, "_user")
                data = json.loads(r.text)
                has_more = data['hasMorePrevious']
                prev_cursor = cursor
                if has_more:
                    last_data = data['itemList'][-1]
                    next_cursor = str(int(last_data.get('createTime') * 1E3))
                else:
                    next_cursor = ''

                self.logger.debug(f"[next_cursor]: {next_cursor}")

                for info in data['itemList']:
                    count += 1
                    video_info = self.extract_node(info)
                    video_info['cursor'] = prev_cursor
                    video_info['next_cursor'] = next_cursor if has_more else ''
                    video_info['cursor_position'] = cursor_position

                    video_link = video_info.get("original_url")
                    video_list.append(video_link)
                    video_info_list.append(video_info)
                    self.on_extracting({
                        "status": "progress",
                        "url": url,
                        "data": video_info
                    })

                    # if sort_by and sort_by != "newest":
                    #     limit_copy = None
                    # if not use_per_next_cursor and count == limit_copy:
                    #     has_more = False
                    #     break

                if not isinstance(limit_copy, int) and use_per_next_cursor:
                    break

                cursor = next_cursor
                cursor_position += 1
            except ValueError as err:
                self.logger.debug(f"extract_info_profile error: {err}")
                raise Exception(err, url_uid)

        if len(video_info_list) <= 0:
            return None

        if sort_by and sort_by != "newest":
            limit = limit if isinstance(
                limit, int) and limit != 0 else len(video_info_list)
            if sort_by == "popular":
                sort_key = "view_count"
                reverse = True
            else:
                sort_key = "timestamp"
                reverse = False

            video_info_list.sort(key=lambda x: int(
                x[sort_key]), reverse=reverse)
            video_info_list = video_info_list[0:limit]

        return video_info_list

    async def test_get_video_info_list_from_user(self):
        self._skip_cached_info = True
        url = self._LINK_USERNAME % 'uddomp'
        self.logger.debug(f"Video URL: {url}")

        info_list = await self.get_video_info_list_from_user(url, None, cursor_continue='1711793427000', cursor_position=9, use_per_next_cursor=False)
        if info_list:
            previous_data = self.load_test_data('_user')
            if previous_data:
                info_list = previous_data + info_list
            self.logger.debug(f"Total videos: {len(info_list)} video")
            self.save_test_data(info_list, '_user')
        return info_list

    async def test_get_video_info_list(self):
        self._skip_cached_info = True
        url = self._LINK_ID % self._TEST_VIDEO_ID
        url, _video_id = self.get_url_video_id(url)
        self.logger.debug(f"Video URL: {url}, {_video_id}")
        info_list = await self.get_video_info_list([url])

        if info_list:
            self.save_test_data(info_list)
        return info_list
