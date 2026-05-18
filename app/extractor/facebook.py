import asyncio
import base64
import functools
import hashlib
import itertools
import json
import operator
import random
import re
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote, urlparse

from curl_cffi.requests import BrowserTypeLiteral, Response
from yt_dlp.utils import extract_attributes, find_element, require, traverse_obj

try:
    from chompjs import parse_js_object
except:
    def parse_js_object(content):
        return 'none'

from ._request import (
    ExtractorBase,
    dict_to_query_string,
    generate_url_query,
    get_content_from_html_selector,
    get_json_from_html,
)

current_dir = Path(__file__).parent


class FacebookBaseIE(ExtractorBase):
    _BASE_URL = "https://www.facebook.com"
    _WEBPAGE_HOST = "https://web.facebook.com/%s"
    _LINK_USER_WITH = "https://web.facebook.com/%s/videos/%s"
    _LINK_USER_REEL_WITH = "https://web.facebook.com/%s/reels/%s"
    _LINK_VIDEO_WITH = "https://web.facebook.com/watch/?v=%s"

    _API_GRAPHQL = "https://web.facebook.com/api/graphql/"

    def get_video_id(self, url_vid: str) -> str:
        url_vid = url_vid.strip()
        parsed_url = urlparse(url_vid)
        path = parsed_url.path
        query = parsed_url.query
        if path.startswith("/watch") and "v=" in query:
            video_id = query.split("v=")[1].split("&")[0]
        elif "/videos/" in path and "/reel/" not in path:
            video_id = path.rstrip("/").split("/")[-1]
        else:
            video_id = re.findall('[0-9]+', url_vid)[0]

        return video_id

    def get_video_url(self, video_url: str) -> str:
        return self._LINK_VIDEO_WITH % self.get_video_id(video_url)

    def get_url_video_id(self, url_vid: str):
        video_id = self.get_video_id(url_vid)
        video_url = self._LINK_VIDEO_WITH % video_id

        return video_url, video_id

    def get_user_id(self, url_uid: str) -> str:
        if "profile.php?id=" in url_uid:
            user_id = url_uid.strip().split("?id=")[1].split("&")[0]
        else:
            url_uid = url_uid.strip().split("?")[0]
            if "facebook.com/" in url_uid:
                user_id = url_uid.split("facebook.com/")[1].split("/")[0]
            else:
                user_id = re.findall(
                    '[0-9]+', url_uid)[0] if url_uid.isdigit() else url_uid

        return user_id

    def datetime_timestamp(self, ts: int):
        return datetime.fromtimestamp(ts) if ts > 0 else "Unknown"

    def extract_node(self, node: dict):
        video_id = node.get("id", "")

        title = node.get("title", "")
        desc = node.get("description") or title

        thumbnail = node.get("thumbnail", "")

        url_dl = node.get("hd", "")
        sd = node.get("sd") or url_dl

        music = node.get("music", "")

        url = node.get("url", "")
        if video_id:
            url = self._LINK_VIDEO_WITH % video_id

        width = node.get("width", 0)
        height = node.get("height", 0)
        resolution = f"{width}x{height}"
        duration = node.get("duration", 0)
        timestamp = node.get("timestamp", 0)

        stats = {
            "view_count": node.get("view_count", 0),
            "like_count": node.get("like_count", 0),
            "comment_count": node.get("comment_count", 0),
            "share_count": node.get("share_count", 0),
        }

        uploader = node.get("uploader", "")
        uploader_id = node.get("uploader_id", "")
        uploader_url = node.get("uploader_url", "")

        title = title
        info_dict = {
            "id": video_id,
            "display_id": video_id,
            "title": title,
            "fulltitle": title,
            "description": desc,
            "thumbnail": thumbnail,
            "original_thumbnail": thumbnail,
            "sd": sd,
            "hd": url_dl,
            "music": music,
            "requested_download": [{
                "title": title,
                "width": width,
                "height": height,
                "resolution": resolution,
                "url": url
            }],
            "uploader": uploader,
            "uploader_id": uploader_id,
            "uploader_url": uploader_url,
            "url": url,
            "original_url": url,
            "webpage_url": url,
            "dash_manifest_url": node.get("dash_manifest_url", ""),
            "webpage_url_domain": "facebook.com",
            "extractor": "facebook",
            "extractor_key": "Facebook",
            "width": width,
            "height": height,
            "resolution": resolution,
            "duration": duration,
            # "duration": int(float(video["duration"] / 1000)) if video.get("duration") is not None and video.get("duration") != 0 else music["duration"],
            "timestamp": timestamp,
            "release_timestamp": timestamp,
            "upload_date": "",
            **stats,
            "subtitles": [],
            "audio_only": [],
            "video_only": [],
            "user_info": {
                **node.get("user_info", {})
            },
        }
        username = info_dict['user_info'].get('username')
        if isinstance(username, str) and 'https' in username and '%2F_u%2F' in username:
            match = re.search(r'%2F_u%2F([^&]+)', username)
            if match:
                username = match.group(1) or 'unknown'
                info_dict['user_info']['username'] = username
                if not uploader:
                    info_dict['uploader'] = username
                self.logger.debug(f'match: {username}')

        info_dict.update(**node)
        if info_dict["timestamp"] > 0:
            info_dict["upload_date"] = str(
                self.datetime_timestamp(info_dict["timestamp"]))

        return info_dict


class FacebookExtractor(FacebookBaseIE):
    def __init__(self, proxies: Optional[List[str]] = None, impersonate: BrowserTypeLiteral = "chrome120", timeout: int = 30):
        super().__init__(proxies, impersonate, timeout)
        self.concurrent_tasks = 10
        self.delay_jitter = False
        self.device_id = None

    def get_video_play(self, info: dict, quality: str = 'hd'):
        return None

    def get_video_info(self, content: str, next_cursor_data_list: list):
        splitText = '{\"label\":\"'
        # data_test = []

        user_info = {}
        video_info = {
            "user_info": user_info
        }
        for i, text in enumerate(content.split(splitText)):
            try:
                if i == 0:
                    info = json.loads(text)
                    data = info.get('data')
                    if isinstance(data, dict):
                        media = data.get("video", {}).get("story", {}).get(
                            "attachments", [{}])[0].get("media")
                        video_id = media["videoId"]
                        thumbnail = media["preferred_thumbnail"]["image"]["uri"]
                        width = media.get("width", 0)
                        height = media.get("height", 0)
                        sd = media.get("browser_native_sd_url", "")
                        hd = media.get("browser_native_hd_url") or sd

                        webpage_url = media.get(
                            "permalink_url") or media.get("url", "")
                        dash_manifest_url = media.get(
                            "dash_manifest_url", "")
                        duration = media.get("playable_duration_in_ms", 0)
                        duration = duration / 1000 if duration > 0 else duration
                        timestamp = media.get("publish_time", "")

                        if "/videos/" in webpage_url:
                            username = webpage_url.split(
                                "/videos/")[0].split(".com/")[1]

                            user_info["username"] = username
                            user_info["url"] = webpage_url.split(
                                "/video/")[0]

                        video_info.update(**{
                            "id": video_id,
                            "thumbnail": thumbnail,
                            "width": width,
                            "height": height,
                            "sd": sd,
                            "hd": hd,
                            "url": webpage_url,
                            "dash_manifest_url": dash_manifest_url,
                            "duration": duration,
                            "timestamp": timestamp,
                        })
                        video_info["user_info"].update(**user_info)

                elif i > 0:
                    info = json.loads(f"{splitText}{text}")
                    data = info.get('data')
                    # data.get("feedback") has comment_list_renderer
                    if isinstance(data, dict) and data.get("attachments") or data.get("creation_story"):
                        attachments = data.get("attachments")
                        creation_story = data.get("creation_story")

                        if isinstance(attachments, list) and len(attachments) > 0:
                            media = attachments[0].get("media", {})

                            try:
                                profile_url = media.get("creation_story", {}).get("comet_sections", {}).get(
                                    "actor_photo", {}).get("story", {}).get("actors", [{}])[0].get("profile_url", "")
                                user_info["url"] = profile_url
                                user_info["username"] = profile_url.split(
                                    ".com/")[1].split("/")[0]
                            except:
                                pass

                            owner = media.get("owner", {})
                            owner_as_page = owner.get("owner_as_page")
                            if user_info.get("username") is None:
                                username = owner.get("id", "")
                                user_info["username"] = username
                                user_info["url"] = f"{self._BASE_URL}/{username}"

                            if isinstance(owner_as_page, dict):
                                user_info.update(**{
                                    **owner,
                                    "avatar": owner_as_page.get("profile_pic_uri", ""),
                                    "page_id": owner_as_page.get("id")
                                })

                            video_info["user_info"].update(**user_info)

                        elif isinstance(creation_story, dict) and isinstance(data.get("feedback"), dict):
                            # with open("./extractor/test/facebook_test_user.json", "w") as f:
                            #   f.write(json.dumps(data, indent=2))
                            feedback = data.get("feedback")
                            like_count = feedback.get(
                                "reaction_count", {}).get("count", 0)
                            comment_count = feedback.get(
                                "total_comment_count", 0)
                            view_count_feedback = feedback.get(
                                "video_view_count_renderer", {}).get("feedback", {})
                            if view_count_feedback.get("video_view_count") is not None:
                                view_count = view_count_feedback.get(
                                    "video_view_count", 0)
                            elif view_count_feedback.get("video_insights") is not None:
                                try:
                                    view_count = view_count_feedback.get("video_insights", [{}])[
                                        0].get("totals", [{}])[0].get("raw_value", 0)
                                except:
                                    pass

                            description = (creation_story.get(
                                "message") or {}).get("text", "")
                            title = data.get("title", {}).get("text")
                            title = title if isinstance(
                                title, str) and title != "" else description
                            if title == "" and video_info.get("id") is not None:
                                title = "[%s] By %s" % (video_info.get(
                                    "id"), user_info.get("username", ""))

                            video_info.update(**{
                                "title": title,
                                "description": description,
                                "view_count": view_count,
                                "like_count": like_count,
                                "comment_count": comment_count,
                            })
            except Exception as err:
                self.logger.debug(f'An exception occurred: {err} {video_info}')

            # try:
            #   if i == 0:
            #     info = json.loads(text)
            #     data = info.get('data')
            #     data_test.append(data)
            #   else:
            #     info = json.loads(f"{splitText}{text}")
            #     data = info.get('data')
            #     data_test.append(data)
            # except:
            #   print('An exception occurred')

        if video_info.get("id") is not None:
            video_id = video_info['id']
            video_info = self.extract_node(video_info)
            user = video_info["user_info"]
            if len(next_cursor_data_list) > 0:
                try:
                    __next_cursor_data = list(
                        filter(lambda x: video_id in x, next_cursor_data_list))
                    next_cursor_data = json.loads(__next_cursor_data[0])
                    video_info.update(**next_cursor_data)
                except ValueError as err:
                    self.logger.debug(f'error: {err}')
                    pass
            video_info.update(**{
                "url": self._LINK_VIDEO_WITH % video_id,
                "uploader": user.get("username", ""),
                "uploader_id": user.get("id", ""),
                "uploader_url": user.get("url", ""),
            })

        return video_info

    async def _get_data_content_from_api_video(self, url: str) -> Optional[str]:
        resp = await self.request(url, method="POST")
        if not isinstance(resp, Response):
            return None
        if not resp.ok or resp.status_code != 200:
            return None

        return resp.text

    async def extract_video_list_from_graphql_no_chunks(
        self,
        url_list: list[str],
    ):
        def get_api_video_list(url):
            video_id = self.get_video_id(url)
            if "&next_data=" in url or "?next_data=" in url:
                try:
                    next_cursor_data = unquote(
                        url.split('next_data=')[1].split('&')[0])
                    next_cursor_data_list.append(next_cursor_data)
                except ValueError as err:
                    print(err)
                    pass
            # video_id = "2052994921749154"
            params = {
                "av": "0",
                "__aaid": "0",
                "__user": "0",
                "__a": "1",
                "__req": "y",
                "__hs": "19810.HYP:comet_loggedout_pkg.2.1..0.0",
                "dpr": "1",
                "__ccg": "GOOD",
                "__comet_req": "15",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "CometVideoHomeNewPermalinkHeroUnitQuery",
                "variables": dict_to_query_string({
                    "caller": "TAHOE",
                    "entityNumber": 5,
                    "feedbackSource": 41,
                    "feedLocation": "TAHOE",
                    "focusCommentID": "null",
                    "isCrawler": "false",
                    "isLoggedOut": "true",
                    "privacySelectorRenderLocation": "COMET_STREAM",
                    "renderLocation": "video_home",
                    "scale": 1,
                    "useDefaultActor": "false",
                    "videoID": video_id,
                    "videoIDStr": video_id,
                    "__relay_internal__pv__VideoPlayerRelayReplaceDashManifestWithPlaylistrelayprovider": "false",
                    "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": "false"
                }),
                "server_timestamps": "true",
                "doc_id": "7665516110125786"
            }
            api_video = generate_url_query(self._API_GRAPHQL, params)
            return api_video

        next_cursor_data_list = []
        api_url_list = [get_api_video_list(url) for url in url_list]

        semaphore = asyncio.Semaphore(self.concurrent_tasks)
        if len(url_list) > 15:
            self.delay_jitter = True

        tasks = []
        valid_url_list = []
        async with semaphore:
            for url in api_url_list:
                if self.cancel:
                    self.on_extracting({"status": "cancelled"})
                    break
                url = self.get_video_url(url)
                valid_url_list.append(url)
                tasks.append(self._get_data_content_from_api_video(url))
        content_list = await asyncio.gather(*tasks)

        video_info_list = []
        error_list = []
        for i, content in enumerate(content_list):
            url = valid_url_list[i]
            if self.cancel:
                break
            if not isinstance(content, str) or content == "":
                error_list.append(url)
                continue
            try:
                video_info = self.get_video_info(
                    content, next_cursor_data_list)

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

    async def get_video_info_list(self, url_list: List[str]) -> List[Dict[str, Any]]:
        return await self.extract_video_list_from_graphql_no_chunks(url_list)

    async def extract_user_videos_graphql(
        self, page_id: str, cursor: str, hasMore=False,
        limit: Optional[int] = None,
        sort_by: str = "newest",
        content_type: str = "reels",
        # cursor_continue='',
        cursor_position: int = 0,
        next_cursor=False,
        use_per_next_cursor=False,
    ):
        limit_copy = limit
        count = 0

        cursor_position = int(cursor_position) if isinstance(cursor_position, int) \
            else int(0)
        use_per_next_cursor = sort_by and sort_by == "newest" and use_per_next_cursor

        video_info_list = []
        video_list = []
        is_reel = content_type == "shorts" or content_type == "reels"
        for i in range(1000):
            if self.cancel:
                break

            if limit_copy and len(video_info_list) >= limit_copy:
                break

            if is_reel:
                id = page_id
                params = {
                    "av": "0",
                    "__user": "0",
                    "__a": "1",
                    "__req": "19",
                    "__hs": "19667.HYP:comet_loggedout_pkg.2.1..0.0",
                    "dpr": "1",
                    "__ccg": "GOOD",
                    "__rev": "1009706363",
                    "__s": "flisna:tkajno:wlh9rg",
                    "__hsi": "7298246105608153253",
                    "__dyn": "7xeUmxa13xu1syaxG4VuC2-m1FwAxu13wsoKbgS3q5UObwNwnof8boG0x8bo6u3y4o11U1lVE4W0om78bbwto2awgolzUO0-E4a3a4oaEd82lwv89k2C1Fwc60D8vwRwlE-U2exi4UaEW2a1VwwwJK2W5olwSU5nxmu3W0GpovUy0_o98bodEGdwda3e0Lo4q58jwTwNwLwFg661pwkoqwqo4eE7W",
                    "__csr": "n0EiOslfdnkdRZcFfB8qRmWJZeAFPKgB6BBjWZcyiBDVpWn9z7V8CBV6FGzqgjAHlzoOiFQUVeXQWAKE9rHBhopBxCmVptfBiXrxt5AKmFGyoyVFFJ2ahUVau8AV9GAyESVoCuFUSEyexl0PVXzAp1q58lyembz9XUhgO2WayouQ4bwbuu4U1w818o14t0k82iwefwcK0EWw2mE0rtw3482pwno6uEig0Dypm0bsw1Be0zzat2IM1kEaQ5o1v81d807PK1-w42U0djo5J0c0hy40jC15Bw8x1K5A2-7U5K3y2509G5VUrG221FwXa-09rwuE3eioC2Hul0go1cJ0m40i9049yo2ZDUdE27U5K9zkiq1lyFEG0uW5pU4W13N03_OBBArOa0QU3ilEJa4d1JwbvoSjja0K81RUNo2fa3pxC5U550bl05pxqE5Wa8A0CEhPwqo4y4A0E82M8K8m84Km3BwgU6GawGxaq11dCgcO0Bw4_xqu9wjUfosIJ0uodxXgGlwaIaA7NxwG0WEdo7lG2AweUkw0D8DQu0ugE7W0BE4i1AxK9xi7Uy0gm1PEEig2KwYDUcax91ngcm0TE0h5wm812QawVw8216KU17EIjpU9QeKEi1k2u0x4jwrEf8jAxnw8G1OxGt0WwXwNxe5u0pa0Fo9pZw-x208HOy86KEiCV9V910cKm5E2Kw4zxng6o8rhEpwgUlPwmA0J839wYwbeeQ2e",
                    "__comet_req": "15",
                    "lsd": "AVq-WJbAcrY",
                    "jazoest": "2935",
                    "__aaid": "0",
                    "__spin_r": "1009706363",
                    "__spin_b": "trunk",
                    "__spin_t": "1699255338",
                    "fb_api_caller_class": "RelayModern",
                    "fb_api_req_friendly_name": "ProfileCometAppCollectionReelsRendererPaginationQuery",
                    "variables": dict_to_query_string({
                        "UFI2CommentsProvider_commentsKey": "ProfileCometCollectionRootQuery",
                        "count": 10, "cursor": cursor,
                        "displayCommentsContextEnableComment": True, "displayCommentsContextIsAdPreview": False, "displayCommentsContextIsAggregatedShare": False, "displayCommentsContextIsStorySet": False,
                        "displayCommentsFeedbackContext": None,
                        "feedLocation": "COMET_MEDIA_VIEWER",
                        "feedbackSource": 65, "focusCommentID": None,
                        "renderLocation": None, "scale": 1,
                        "useDefaultActor": "true", "id": id
                    }),
                    "server_timestamps": "true",
                    "doc_id": "6791512760969319"
                }
            else:
                params = {
                    "av": "0",
                    "__user": "0",
                    "__a": "1",
                    "__req": "1f",
                    "__hs": "19632.HYP:comet_loggedout_pkg.2.1..0.0",
                    "dpr": "2",
                    "__ccg": "GOOD",
                    "fb_api_caller_class": "RelayModern",
                    "fb_api_req_friendly_name": "PagesCometChannelTabAllVideosCardImplPaginationQuery",
                    "variables": dict_to_query_string({
                        "alwaysIncludeAudioRooms": "true",
                        "count": 6,
                        "cursor": cursor,
                        "pageID": page_id,
                        "scale": 8,
                        "showReactions": "true",
                        "useDefaultActor": "false",
                        "id": page_id,
                    }),
                    "server_timestamps": "true",
                    "doc_id": "6557211744354341"
                }

            # var = """
            # {"UFI2CommentsProvider_commentsKey":"ProfileCometCollectionRootQuery","count":10,"cursor":"AQHRyNYa8a42V9z5zRSg0AkLO4GJTqFb1soy08SlsrS9HguRSXHRT9ZzLbQsFiB7ly2pApIcYdfPA5lhByZX7yxh5w","displayCommentsContextEnableComment":true,"displayCommentsContextIsAdPreview":false,"displayCommentsContextIsAggregatedShare":false,"displayCommentsContextIsStorySet":false,"displayCommentsFeedbackContext":null,"feedLocation":"COMET_MEDIA_VIEWER","feedbackSource":65,"focusCommentID":null,"renderLocation":null,"scale":1,"useDefaultActor":true,"id":"YXBwX2NvbGxlY3Rpb246MTAwMDY0ODM5NDk4MDcwOjE2ODY4NDg0MTc2ODM3NToyNjA="}
            # """

            api_user = generate_url_query(self._API_GRAPHQL, params)
            # print(api_user)
            headers = {
                # 'user-agent': random_user_agent(),
                # 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept': '*/*',
                'content-type': 'application/json',
                'accept-language': 'en-us,en;q=0.5',
                # 'sec-fetch-mode': 'navigate',
            }
            resp = await self.request(api_user, "POST", headers=headers)
            if not isinstance(resp, Response):
                self.logger.debug("Failed to get response from %s", api_user)
                continue

            if is_reel:
                _content = resp.text

                data = _content.split("{\"label\":\"")[0]
                data = json.loads(data).get("data")
                _data = _content.replace(
                    "{\"label\":\"", "__aioDLP__{\"label\":\"")

                def get_info(info):
                    data = json.loads(info)["data"]
                    stats = data["feedback"]
                    like_count = stats["unified_reactors"]["count"]
                    return {
                        "video_id": data["video"]["id"],
                        "url": data["url"],
                        "like_count": like_count,
                        "view_count": like_count,
                        "comment_count": stats["total_comment_count"],
                    }
                _data = [get_info(info) for info in _data.split(
                    "__aioDLP__") if "\"unified_reactors\"" in info]
            else:
                data = json.loads(resp.text).get("data")

            node = data["node"]
            all_videos = node["aggregated_fb_shorts"] if is_reel else node["all_videos"]
            edege_info_list = all_videos["edges"]
            page_info = all_videos["page_info"]
            current_cursor = cursor
            cursor = page_info["end_cursor"]
            hasMore = page_info["has_next_page"]

            # print("########################################")
            # print("# previous cursor %s" % current_cursor)
            # print("# next cursor %s" % cursor)
            # print("########################################")

            def next_data(url, video_id):
                next_cursor_data = ''
                if next_cursor:
                    _q = "&" if "?" in url else "?"
                    next_cursor_data = _q + ("next_data=%s" % quote(dict_to_query_string({
                        "videoId": video_id,
                        "pageId": page_id,
                        "cursor": current_cursor,
                        "next_cursor": page_info["end_cursor"],
                        "cursor_position": cursor_position,
                    })))
                return next_cursor_data
            # print(cursor, hasMore, count, limit)
            if is_reel:
                def edege_get_info(edege_info):
                    info = edege_info["profile_reel_node"]["node"]
                    video_id = info["short_form_video_context"]["video"]["id"]
                    return {"video_id": video_id, "timestamp": info["creation_time"]}

                edege_info_list = [edege_get_info(
                    info) for info in edege_info_list]
                _data.sort(key=operator.itemgetter("video_id"))
                edege_info_list.sort(key=operator.itemgetter("video_id"))
                # with open("./extractor/test/facebook_test_.json", "w") as f:
                #   f.write(json.dumps([_data, edege_info_list], indent=2))

            for i, edege_info in enumerate(edege_info_list):
                if self.cancel:
                    break
                if is_reel:
                    video_id = edege_info["video_id"]
                    if video_id == _data[i]["video_id"]:
                        _data[i]["timestamp"] = edege_info["timestamp"]
                        video_url = _data[i]["url"]
                        video_url = video_url + next_data(video_url, video_id)
                        video_list.append(video_url)
                        video_info_list.append(_data[i])
                        # print("[THE SAME]", video_id, _data[i]["video_id"])
                    count += 1
                else:
                    info = edege_info["node"]
                    video = info["channel_tab_thumbnail_renderer"]["video"]
                    video_id = video["id"]
                    video_url = self.get_video_url(video_id)
                    video_url = video_url + next_data(video_url, video_id)
                    view_count = video["play_count"]
                    publish_time = video["publish_time"]
                    count += 1

                    video_list.append(video_url)
                    video_info_list.append({
                        "view_count": view_count,
                        "create_time": publish_time,
                        "url": video_url
                    })

                if sort_by and sort_by != "newest":
                    limit_copy = None
                if not use_per_next_cursor and count == limit_copy:
                    hasMore = False
                    break

            if not isinstance(limit_copy, int) and use_per_next_cursor:
                break

            cursor_position += 1

        if sort_by and sort_by != "newest":
            limit = limit if isinstance(
                limit, int) and limit != 0 else len(video_info_list)
            if sort_by == "popular":
                sort_key = "view_count"
                reverse = True
            else:
                sort_key = "create_time"
                reverse = False
            video_info_list.sort(key=lambda x: int(
                x[sort_key]), reverse=reverse)
            video_info_list = video_info_list[0:limit]
            video_list = [
                video_info["url"]
                for video_info in video_info_list
            ]
            video_list = video_list[0:limit]

        return {
            "video_info_list": video_info_list,
            "video_list": video_list
        }

    async def get_video_info_list_from_user(
        self,
        url_uid: str,
        limit: int = None,
        sort_by="newest",
        cursor_continue='',
        cursor_position: int = 0,
        use_per_next_cursor=False,
        content_type: str = "reels",
    ):
        username_id = self.get_user_id(url_uid)

        page_id = None
        cursor = cursor_continue
        hasMore = False
        is_custom_cursor = True if cursor_continue and cursor_continue != "" else False

        is_reel = False
        if content_type == "shorts" or content_type == "reels":
            is_reel = True
        if "profile.php?id=" in url_uid or url_uid.split('?')[0].endswith('/reels') or url_uid.split('?')[0].endswith('/reels/'):
            is_reel = True
            content_type = "reels"

        try:
            if is_reel:
                url = self._LINK_USER_REEL_WITH % (username_id, "")
                if "profile.php?id=" in url_uid:
                    url = "https://web.facebook.com/profile.php?id=%s&%s" % (
                        username_id, "sk=reels_tab")
                    final_response = await self.request(url, retries=0)
                    if isinstance(final_response, Response):
                        url = final_response.url

                self.logger.debug("Goto URL Reel Tab: %s" % url)
                html = ''
                retries = 0
                while True:
                    if retries == 2:
                        time.sleep(0.2)

                    _resp = await self.request(url, retries=0)
                    if isinstance(_resp, Response) and _resp.status_code == 200:
                        html = _resp.text
                        if '"aggregated_fb_shorts":' in html:
                            break
                        else:
                            retries += 1

                        if retries >= 3:
                            break

                for content in html.split('"collection":'):
                    if '"aggregated_fb_shorts":' in content:
                        entries_obj = parse_js_object(content)
                        if isinstance(entries_obj, str) and entries_obj == 'none':
                            data = get_json_from_html(
                                '"collection":' + content, "collection", 2, '"},"__module_operation_ProfileCometPaginatedAppCollection_timelineAppCollection"') + '"}'

                            entries_obj = json.loads(data)
                        page_id = entries_obj["id"]
                        aggregated = entries_obj["aggregated_fb_shorts"]
                        cursor = aggregated["page_info"]["end_cursor"]
                        hasMore = aggregated["page_info"]["has_next_page"]

                        break

            else:
                url = self._LINK_USER_WITH % (username_id, "")
                self.logger.debug("Goto URL Video Tab: %s" % url)
                html = ''
                retries = 0
                while True:
                    if retries == 2:
                        time.sleep(0.2)
                    _resp = await self.request(url, retries=0)
                    if isinstance(_resp, Response) and _resp.status_code == 200:
                        html = _resp.text
                        if '"all_videos":' in html:
                            break
                        else:
                            retries += 1

                        if retries >= 3:
                            break

                for content in html.split('"all_videos":'):
                    if "channel_tab_thumbnail_renderer" in content:
                        entries_obj = parse_js_object(content)
                        if isinstance(entries_obj, str) and entries_obj == 'none':
                            data = get_json_from_html(
                                '"all_videos":' + content, "all_videos", 2, '}},"id"') + '}}'
                            entries_obj = json.loads(data)

                        edege_info_list = entries_obj["edges"]
                        if len(edege_info_list) > 0:
                            owner = edege_info_list[0]["node"]["channel_tab_thumbnail_renderer"]["video"]["owner"]

                        page_id = owner["owner_as_page"]["id"] if owner.get(
                            "owner_as_page") is not None else owner.get("delegate_page_id", None)
                        cursor = entries_obj["page_info"]["end_cursor"]
                        hasMore = entries_obj["page_info"]["has_next_page"]

                        break

            if is_custom_cursor:
                cursor = cursor_continue
                is_custom_cursor = False
            # print(page_id, cursor, hasMore)
            if page_id:
                video_info_list = await self.extract_user_videos_graphql(
                    page_id, cursor, hasMore, limit, sort_by, content_type, cursor_position, next_cursor=True, use_per_next_cursor=use_per_next_cursor
                )

                return video_info_list
        except ValueError as err:
            self.logger.error("ERROR: %s" % err)
            self._on_extracting(
                {"error": str(err), "url": url_uid, "status": "error"})

        return None

    async def test_get_video_info_list_from_user(self):
        self._skip_cached_info = True
        url = self._LINK_USER_REEL_WITH % 'rinsokreth.page'
        self.logger.debug(f"Video URL: {url}")

        info_list = await self.get_video_info_list_from_user(url, None, use_per_next_cursor=True)
        if info_list:
            previous_data = self.load_test_data('_user')
            if previous_data:
                info_list = previous_data + info_list
            self.logger.debug(f"Total videos: {len(info_list)} video")
            self.save_test_data(info_list, '_user')
        return info_list

    async def test_get_video_info_list(self):
        self._skip_cached_info = True
        url = self._LINK_VIDEO_WITH % "1288423651845715"
        url, _video_id = self.get_url_video_id(url)
        self.logger.debug(f"Video URL: {url}, {_video_id}")
        info_list = await self.get_video_info_list([url])

        if info_list:
            self.save_test_data(info_list)
        return info_list
