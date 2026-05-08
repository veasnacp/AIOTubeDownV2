from yt_dlp import YoutubeDL as TikTokDL
from .youtube_ import YouTubeSortBy as TikTokSortBy
from .util_extract import (
    Pool,
    _execute_request,
    all_promise,
    arr_chunk,
    async_request,
    datetime_timestamp,
    default_chrome_options,
    extract_info_video_list_localhost_async,
    generate_url_query,
    get_content_from_html_selector,
    headers,
    headers_mob,
    infoDict,
    res_async,
    use_cpu,
)
import asyncio
import json
import os
import random
import re
import time
from math import ceil
from urllib.parse import quote, unquote

# from math import ceil
from typing_extensions import Literal, TypeAlias, Union


# from playwright.async_api import BrowserContext, async_playwright
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
class webdriver:
    def Chrome(options=None):
        pass


def Options():
    pass


class By:
    ...


# from .util_extract import (
#     AsPlaylistOrProfile,
#     AudioQuality,
#     VideoDownloadType,
#     VideoQuality,
#     download_multi_videos_info_async,
#     osA,
# )

# import requests

# from chompjs import parse_js_object
# from TikTokApi import TikTokApi
DictKeyVideoInfoList: TypeAlias = Literal["video_info_list", "video_list"]

# __import_section__

ms_token = os.environ.get(
    "ms_token", None
)  # set your own ms_token, think it might need to have visited a profile

headers_keep_alive = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    # "User-Agent": headers_mob["User-Agent"],
}


def execute_script_promise_all(url_list, method="GET", return_type="text"):
    headers = headers_keep_alive

    return_type = "response.text()" if return_type == "text" else "response.json()"

    return f"""
    return Promise.all(
      {url_list}.map(url => {{
        return new Promise((resolve, reject) => {{
          fetch(url, {{ method: "{method}", headers: {headers} }})
              .then(response => {return_type})
              .then(data => resolve(data))
              .catch(error => reject(error.message));
        }});
      }})
    )
  """


class TikTokBaseIE:
    _HOST_DOMAIN = "https://www.tiktok.com"
    _BRAND_URL_WITH = "https://www.tiktok.com/@tiktok/%s"
    _USER_URL_WITH = "https://www.tiktok.com/@%s/video/%s"

    _API_USER_POST = "https://www.tiktok.com/api/post/item_list/"
    # https://www.tikwm.com/api/user/posts?unique_id=@krita_juju1810&count=2&cursor=0
    _API_TIKWM_USER = 'https://www.tikwm.com/api/user/posts?unique_id=@%s&count=%s&cursor=%s'
    _API_TIKWM_VIDEO = 'https://www.tikwm.com/api/?url=%s'

    # https://stackoverflow.com/questions/62767867/embed-video-from-tiktok

    # "https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/play/?video_id=v0f025gc0000cdf0cpbc77u9dod0h9hg&line=0&is_play_url=1&file_id=70279f0e78b149c9855b026c2da08a71&item_id=7160167493275847962&signaturev3=dmlkZW9faWQ7ZmlsZV9pZDtpdGVtX2lkLjViMDQyNzk1MDY5M2Y3NWZhNGY0ZDBlOGQxMzYxMzU4&shp=9e36835a&shcp=280c9438"
    # https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/aweme_id/7332111319681862914
    # https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/

    # _API_DOWNLOAD_VIDEO = "https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/play/?video_id=%s&line=0&is_play_url=1&source=PackSourceEnum_FEED&file_id=d563acde86bd4190a038e0c8369a9b62&item_id=7332111319681862914&signaturev3=dmlkZW9faWQ7ZmlsZV9pZDtpdGVtX2lkLmNkY2JmMzUwYTcwZDgzNjkzYWJmZTNhNDJkNTUzYzk2"
    # _API_DOWNLOAD_VIDEO_WATERMARK = "https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/play/?video_id=v10044g50000cn0e8gvog65nuv247hq0&line=0&watermark=1&logo_name=tiktok&source=FEED&file_id=c041f4489ddb4e59ae4a78e5b3854808&item_id=7332111319681862914&signaturev3=dmlkZW9faWQ7ZmlsZV9pZDtpdGVtX2lkLjc2YWRiNWEzYTNjOGUxNWQ1ZjUzOTExMjNmMzE4M2Fm"

    _TIKWM_PLAY = 'https://tikwm.com/video/media/play/%s.mp4'
    _TIKWM_HDPLAY = 'https://tikwm.com/video/media/hdplay/%s.mp4'
    _TIKWM_WMPLAY = 'https://tikwm.com/video/media/wmplay/%s.mp4'
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

    def get_url_vid(self, url_vid: str):
        url = url_vid.strip()
        if not url.startswith("http") and not "/video/" in url:
            video_id = re.sub(r'\D', '', url)
            url = self._USER_URL_WITH % ("tiktok", video_id)
        return url

    def get_user_id(self, url_uid: str):
        user_id = url_uid.split(
            "@")[1].split('?')[0].split('/')[0] if "@" in url_uid else url_uid.strip()
        return user_id

    def get_session_params(self, browser: webdriver.Chrome):
        """Set the session params for a TikTokPlaywrightSession"""
        session_evaluate: dict = browser.execute_script("""return ({
      "userAgent": navigator.userAgent,
      "language": navigator.language || navigator.userLanguage,
      "platform": navigator.platform,
      "timezone": Intl.DateTimeFormat().resolvedOptions().timeZone
    })""")

        # print(session_evaluate)

        user_agent = session_evaluate.get("userAgent", "")
        language = session_evaluate.get("language", "")
        platform = session_evaluate.get("platform", "")
        timezone = session_evaluate.get("timezone", "")

        device_id = str(random.randint(10**18, 10**19 - 1))  # Random device id
        history_len = str(random.randint(1, 10))  # Random history length
        screen_height = str(random.randint(600, 1080))  # Random screen height
        screen_width = str(random.randint(800, 1920))  # Random screen width

        session_params = {
            # "WebIdLastTime": "1696632738",
            "aid": "1988",
            "app_language": language,
            "app_name": "tiktok_web",
            "browser_language": language,
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": platform,
            "browser_version": user_agent,
            "channel": "tiktok_web",
            "cookie_enabled": "true",
            "device_id": device_id,
            "device_platform": "web_pc",
            "focus_state": "true",
            "from_page": "user",
            "history_len": history_len,
            "is_fullscreen": "false",
            "is_page_visible": "true",
            "language": language,
            "os": platform,
            "priority_region": "",
            "referer": "",
            "region": "US",  # TODO: TikTokAPI option
            "screen_height": screen_height,
            "screen_width": screen_width,
            "tz_name": timezone,
            "webcast_language": language,
        }
        session_params = {
            "aid": "1988",
            "app_language": language,
            "app_name": "tiktok_web",
            "browser_language": language,
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": platform,
            "browser_version": user_agent,
            "channel": "tiktok_web",
            "cookie_enabled": "true",
            "device_id": device_id,
            "device_platform": "web_pc",
            "focus_state": "true",
            "from_page": "user",
            "history_len": history_len,
            "is_fullscreen": "false",
            "is_page_visible": "true",
            "language": language,
            "os": platform,
            "priority_region": "",
            "referer": "",
            "region": "US",  # TODO: TikTokAPI option
            "screen_height": screen_height,
            "screen_width": screen_width,
            "tz_name": timezone,
            "webcast_language": language,
        }
        return session_params

    def dict_to_url_quote(self, info_dict: dict):
        update_info_dict = {"info_dict": {**info_dict}}
        url_dl = info_dict["hd"] + ("&download_with_info_dict=%s" %
                                    quote(json.dumps(update_info_dict)))
        return {**update_info_dict, "url_dl": url_dl}

    def _extract_node_yt_dlp(self, url: str, only_url_dl=False) -> dict[str, any]:
        yt_opts = {
            "quiet": True,
            # 'logger': MyLogger(),
            # 'progress_hooks': [my_hook],
        }
        info_dict = None
        try:
            with TikTokDL(yt_opts) as tdl:
                info_dict = tdl.extract_info(url, False)
        except ValueError as err:
            print("Error: ", err)

        if isinstance(info_dict, dict):
            video_info = info_dict.copy()
            info_dict["sd"] = video_info["url"]
            info_dict["hd"] = video_info["url"]
            info_dict["dl_with_watermark"] = video_info["formats"][0]["url"]
            info_dict["url"] = video_info["original_url"]
            info_dict = infoDict(info_dict)
            info_dict["info_dict"]["requested_download"] = [{
                "title": video_info["title"],
                "width": video_info["width"],
                "height": video_info["height"],
                "resolution": video_info["resolution"],
                "url": video_info["original_url"],
            }]
            info_dict = {
                **info_dict["info_dict"],
                "video_only": info_dict["video_only"],
                "audio_only": info_dict["audio_only"],
                "both": info_dict["both"],
            }

            if only_url_dl is True:
                return self.dict_to_url_quote(info_dict)

        return info_dict

    async def extract_node_yt_dlp(self, url: str, only_url_dl=False) -> dict[str, any]:
        await asyncio.sleep(0.0001)
        info_dict = self._extract_node_yt_dlp(url, only_url_dl)
        # print("[Info Dict]: ", info_dict)
        return info_dict

    def extract_node(self, node: dict, only_url_dl=False) -> dict[str, any]:
        video = node
        video_id = video.get("video_id") or video.get("id", "")
        music = node.get("music") if isinstance(
            node.get("music"), dict) else node.get("music_info", {})
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
        url = self._USER_URL_WITH % (user_id, video_id)

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

        # print("[TESTING]: ... ", "1")

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
            # "music": music["play_url"]["uri"] if music.get("play_url") is not None else music.get("play",""),
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
            "uploader_url": f"{self._HOST_DOMAIN}/@{user_id}",
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
            # "duration": int(float(video["duration"] / 1000)) if video.get("duration") is not None and video.get("duration") != 0 else music["duration"],
            "timestamp": timestamp,
            "release_timestamp": timestamp,
            "upload_date": datetime_timestamp(timestamp).__str__(),
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

        if only_url_dl is True:
            return self.dict_to_url_quote(info_dict)

        return info_dict


class TikTokRequest(TikTokBaseIE):
    def __init__(self) -> None:
        self.is_stopped = False

    def stop_extraction(self):
        self.is_stopped = True

    def on_callback_progress(self, video_info: dict):
        pass

    def callback_progress(self, video_info: dict):
        self.on_callback_progress(video_info)

    def webdriver(self, user_agent: str = None, headless=True):
        chrome_options = Options()
        user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        chrome_options.add_argument('--user-agent=%s' % user_agent)
        default_chrome_options(chrome_options)
        if headless:
            chrome_options.add_argument('--headless=new')

        browser = webdriver.Chrome(options=chrome_options)
        return browser, chrome_options

    async def all_promise(self, url_list, return_type="text", headers=headers):
        # data = await async_request(url_list, {"headers": headers}, True if return_type == "json" else False)
        data = await all_promise(url_list, return_type, headers)

        return data

    async def extract_video_list_from_other(self, url_list, only_url_dl=False):
        url_list = [self.get_url_vid(url) for url in url_list]

        def progress_callback(is_stopped):
            if self.is_stopped:
                return True
        data_list = await res_async(url_list, "text", self._HEADERS_VIDEO_HTML, progress_callback=progress_callback)
        # data_list = await self.all_promise(url_list)

        def _user_info_id(video_info):
            if only_url_dl is True:
                v_info = video_info.get("info_dict", {})
                user_id = v_info.get("uploader", "_")
                user_info = v_info.get("user_info", {})
            else:
                user_id = video_info.get("uploader", "_")
                user_info = video_info.get("user_info", {})
            return user_id, user_info

        video_info_list = []
        error_list = []
        test_list = []
        user_info_dict = {}
        for i, content in enumerate(data_list):
            if self.is_stopped:
                break
            try:
                # with open("./extractor/test/facebook_test_.json", "w") as f:
                #   f.write(json.dumps({"content": str(content)}, indent=2))
                data_content = get_content_from_html_selector(
                    str(content), "script", ['id=\"__UNIVERSAL_DATA_FOR_REHYDRATION__\"'])
                if len(data_content) > 0:
                    data = json.loads(data_content[0])
                    video_detail = data.get("__DEFAULT_SCOPE__", {}).get(
                        "webapp.video-detail")
                    node = video_detail.get("itemInfo", {}).get("itemStruct")
                    # if isinstance(node, dict):
                    #   with open("./extractor/test/facebook_test_user.json", "w") as f:
                    #     f.write(json.dumps(node, indent=2))
                    if isinstance(node, dict) and str(node.get("createTime")) and int(node.get("createTime")) != 0:
                        # print(url_list[i])
                        video_info = self.extract_node(node)
                        self.callback_progress(video_info)
                        if only_url_dl:
                            video_info = self.dict_to_url_quote(video_info)
                        user_id, user_info = _user_info_id(video_info)
                        if not (isinstance(user_info_dict.get(user_id), dict)):
                            user_info_dict[user_id] = user_info
                        video_info_list.append(video_info)
                    else:
                        print("Error => Create Time is 0 with URL: ",
                              url_list[i])
                        # video_info = self._extract_node_yt_dlp(url_list[i], only_url_dl)
                        # error_list.append(url_list[i])
                        # with open("./extractor/test/facebook_test_.json", "w") as f:
                        #     f.write(json.dumps(node, indent=2))
                else:
                    print("No Data: ", url_list[i])
                    # error_list.append(url_list[i])
                    # test_list.append({'url': url_list[i], "content": str(content)})
            except ValueError as err:
                print("Error: ", err)

        # print("user_info_dict: ", user_info_dict)
        # if len(error_list) > 0:
        #   data_list = await extract_info_video_list_localhost_async(error_list, only_url_dl)
        #   for data in data_list:
        #     if isinstance(data, dict) and not isinstance(data.get("status_code"), int):
        #       print("Data error is fixed")
        #       user_id, _u = _user_info_id(data)
        #       if isinstance(user_info_dict.get(user_id), dict):
        #           if only_url_dl is True:
        #             data["info_dict"]["user_info"] = user_info_dict.get(user_id)
        #           else:
        #             data["user_info"] = user_info_dict.get(user_id)
        #       video_info_list.append(data)

        return video_info_list

    def extract_video_list_from_other_run(self, url_list, only_url_dl=False):
        return asyncio.run(self.extract_video_list_from_other(url_list, only_url_dl))

    def extract_video_list_from_other_pool(self, video_url_list, only_url_dl=False):

        video_url_list_of_list = list(arr_chunk(video_url_list, 100))

        video_info_list_of_list = []
        for url_list in video_url_list_of_list:
            total_url = len(url_list)
            runtime = 2
            chunk_size = ceil(total_url / runtime)
            url_list_of_list = list(arr_chunk(url_list, chunk_size))
            only_url_dl_list = [only_url_dl for url in url_list_of_list]

            cpu = use_cpu(runtime)
            with Pool(cpu) as p:
                video_info_list_of_list_ = p.starmap(
                    self.extract_video_list_from_other_run, zip(*[url_list_of_list, only_url_dl_list]))
                p.close()
                p.join()
                video_info_list = sum(video_info_list_of_list_, [])
                video_info_list_of_list.append(video_info_list)

        return sum(video_info_list_of_list, [])

    def extract_video_info_list_mobile_api_sln_all(
        self, url_vid_list: list[str],
        with_url_dl=False
    ):

        url_list = [self.get_url_vid(url) for url in url_vid_list]
        browser, chrome_options = self.webdriver(
            user_agent=headers["User-Agent"], headless=True
        )
        goto_url = self._HOST_DOMAIN + "/search/user?q=tiktok"
        browser.get(goto_url)

        data_list = None
        loop_count = 0
        while True:
            print("================================")
            print("Loop Count ", loop_count)
            print("================================")
            if loop_count >= 6:
                break

            try:
                data_list = browser.execute_script(
                    execute_script_promise_all(url_list))
                if len(url_list) > 20:
                    time.sleep(5)

            except Exception as err:
                print("Error executing script: ", err)
                data_list = None
                loop_count += 1

            if isinstance(data_list, list):
                break
            else:
                continue

        browser.close()

        if data_list is None:
            return []

        def _user_info_id(video_info):
            if with_url_dl is True:
                v_info = video_info.get("info_dict", {})
                user_id = v_info.get("uploader", "_")
                user_info = v_info.get("user_info", {})
            else:
                user_id = video_info.get("uploader", "_")
                user_info = video_info.get("user_info", {})
            return user_id, user_info

        video_info_list = []
        error_list = []
        test_list = []
        user_info_dict = {}
        for i, content in enumerate(data_list):
            try:
                # with open("./extractor/test/facebook_test_.json", "w") as f:
                #   f.write(json.dumps({"content": str(content)}, indent=2))
                data_content = get_content_from_html_selector(
                    str(content), "script", ['id=\"__UNIVERSAL_DATA_FOR_REHYDRATION__\"'])
                if len(data_content) > 0:
                    data = json.loads(data_content[0])
                    with open("./extractor/test/facebook_test_.json", "w") as f:
                        f.write(json.dumps(data, indent=2))
                    video_detail = data.get("__DEFAULT_SCOPE__", {}).get(
                        "webapp.video-detail")
                    node = video_detail.get("itemInfo", {}).get("itemStruct")
                    # if isinstance(node, dict):
                    #   with open("./extractor/test/facebook_test_user.json", "w") as f:
                    #     f.write(json.dumps(node, indent=2))
                    if isinstance(node, dict) and str(node.get("createTime")) and int(node.get("createTime")) != 0:
                        # print(url_list[i])
                        video_info = self.extract_node(node, with_url_dl)
                        user_id, user_info = _user_info_id(video_info)
                        if not (isinstance(user_info_dict.get(user_id), dict)):
                            user_info_dict[user_id] = user_info
                        video_info_list.append(video_info)
                    else:
                        print("Error => Create Time is 0 with URL: ",
                              url_list[i])
                        # video_info = self._extract_node_yt_dlp(url_list[i], only_url_dl)
                        # error_list.append(url_list[i])
                        # with open("./extractor/test/facebook_test_.json", "w") as f:
                        #     f.write(json.dumps(node, indent=2))
                else:
                    print("No Data: ", url_list[i])
                    # error_list.append(url_list[i])
                    # test_list.append({'url': url_list[i], "content": str(content)})
            except ValueError as err:
                print("Error: ", err)

        return video_info_list


class TikTokExtractor(TikTokRequest):
    def __init__(self, server=None) -> None:
        super().__init__()
        self.cursor = 0
        self.server = server if isinstance(server, str) else "default"

    def extract_video_info(self, url_vid: str, only_url_dl=False):
        try:
            video_info = self._extract_node_yt_dlp(
                self.get_url_vid(url_vid), True)
            if only_url_dl is True:
                return video_info["url_dl"]
            return video_info
        except Exception as e:
            raise ValueError(e)

    async def extract_video_info_list(self, url_vid_list: list[str], only_url_dl=False):
        url_vid_list = [
            self.get_url_vid(url) for url in url_vid_list
        ]
        get_tasks = await extract_info_video_list_localhost_async(url_vid_list, True)
        print("GET TASKS: %s" % len(get_tasks))
        # tasks = [
        #   self.extract_node_yt_dlp(self.get_url_vid(url), True)
        #   for url in url_vid_list
        # ]
        # get_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        def get_video_info_list(get_tasks):
            video_info_list = []
            video_list = []
            error_video_list = []
            for video_info in get_tasks:
                if isinstance(video_info, dict):
                    is_error = isinstance(video_info.get(
                        "status_code"), int) and video_info.get("url")
                    if is_error:
                        url = unquote(video_info.get(
                            "url", "?url=").split("url=")[1].split("&")[0])
                        error_video_list.append(url)
                        video_info["url"] = url
                        # video_info_list.append(video_info)
                    elif not is_error and video_info.get("url_dl"):
                        video_list.append(video_info.get("url_dl"))
                        video_info_list.append(video_info)

            return video_info_list, video_list, error_video_list

        video_info_list_1, video_list_1, error_video_list = get_video_info_list(
            get_tasks)
        print(error_video_list, len(video_info_list_1))
        video_info_list_2, video_list_2 = [], []
        if len(error_video_list) > 0:
            get_tasks_2 = await self.extract_video_info_list_tikwm(error_video_list, True)
            video_info_list_2, video_list_2, error_video_list_2 = get_video_info_list(
                get_tasks_2)

        if only_url_dl is True:
            return sum([video_list_1, video_list_2], [])
        return sum([video_info_list_1, video_info_list_2], [])

    async def extract_video_info_list_tikwm(self, url_vid_list: list[str], only_url_dl=False) -> list[dict]:
        # api_vid = "https://www.tikwm.com/api/?url=%s"
        # api_vid = "https://www.tikwm.com/video/media/play/%s.mp4" % video_id
        api_url_list = [self._API_TIKWM_VIDEO %
                        self.get_url_vid(url_vid) for url_vid in url_vid_list]
        # print(api_url_list)
        options = {"headers": headers}
        video_info_list = []
        url_working_list = []
        url_not_working_list = []
        for url_list in list(arr_chunk(api_url_list, 50)):
            await asyncio.sleep(1)
            resp_list = await async_request(url_list, resp_option=options)
            for i, video_info in enumerate(resp_list):
                if isinstance(video_info, dict) and video_info.get("data") is not None:
                    info_dict = self.extract_node(video_info["data"], False)
                    url_working_list.append(info_dict.get("url"))
                    video_info_list.append(info_dict)
                else:
                    url_not_working_list.append(url_list[i])
        print({
            "working": len(url_working_list),
            "not_working": len(url_not_working_list),
        })

        if len(url_not_working_list) > 0:
            api_url_list = list(arr_chunk(url_not_working_list, 50))
            url_working_list = []
            url_not_working_list = []
            for url_list in api_url_list:
                await asyncio.sleep(1)
                resp_list = await async_request(url_list, resp_option=options)
                for i, video_info in enumerate(resp_list):
                    if isinstance(video_info, dict) and video_info.get("data") is not None:
                        info_dict = self.extract_node(
                            video_info["data"], False)
                        url_working_list.append(info_dict.get("url"))
                        video_info_list.append(info_dict)
                    else:
                        url_not_working_list.append(url_list[i])
            # video_info_list = [
            #   self.extract_node(video_info["data"], only_url_dl)
            #   for video_info in resp_list if isinstance(video_info,dict) and video_info.get("data") is not None
            # ]

            print({
                "working": len(url_working_list),
                "not_working": len(url_not_working_list),
            })
        if only_url_dl is True:
            return [self.dict_to_url_quote(info) for info in video_info_list]

        return video_info_list
        # return {
        #   "info_list": video_info_list,
        #   "working": url_working_list,
        #   "not_working": url_not_working_list,
        # }

    async def extract_info_profile(
        self,
        url_uid: str,
        limit: int = None,
        sort_by: TikTokSortBy.ChannelVideos = "newest",
        cursor_continue='',
        use_per_next_cursor=False,
        only_url_dl=False,
    ) -> list[Union[str, dict]]:
        global cursor, hasMore
        cursor = cursor_continue if cursor_continue and cursor_continue != '' else '0'
        cursor_position = int(0)
        hasMore = False

        use_per_next_cursor = sort_by and sort_by == "newest" and use_per_next_cursor

        await asyncio.sleep(0.1)
        user_id = self.get_user_id(url_uid)

        # user_api = "https://www.tikwm.com/api/user/info?unique_id=@{}".format(user_id)
        # user_info = requests.get(user_api).json()

        # total_video = user_info["data"]["stats"]["videoCount"]
        # run_time = ceil(total_video / 32)

        count = 0
        limit_copy = limit
        video_list = []
        video_info_list = []
        for i in range(300):
            if self.is_stopped:
                break
            url = self._API_TIKWM_USER % (
                user_id,
                limit if (isinstance(limit, int) and limit !=
                          0) and limit < 35 else 35,
                cursor
            )
            # print("[API USER TIKWM]: ", url)
            # response = requests.get(url=url).json()
            # data = response['data']
            add_headers = {
                **headers,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "max-age=0",
                "priority": "u=0, i",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
            }
            try:
                r = _execute_request(url, headers=add_headers)
                data = json.loads(bytes.decode(r.read()))["data"]
                hasMore = data['hasMore']
                current_cursor = cursor
                cursor = data["cursor"]
                # print("[DATA]: ", data)

                for info in data['videos']:
                    count += 1
                    video_info = self.extract_node(info)
                    video_info['cursor'] = current_cursor
                    video_info['next_cursor'] = '' if not hasMore else cursor
                    video_info['cursor_position'] = cursor_position
                    # info_dict = video_info.get("info_dict", {})
                    # print("[video_info]: ",info_dict.get("original_url"))
                    # print("[view_count]: ", info_dict.get("view_count"))
                    # print("[timestamp]: ", info_dict.get("timestamp"))
                    # video_info.update(**{
                    #   "view_count": info_dict.get("view_count"),
                    #   "timestamp": info_dict.get("timestamp")
                    # })
                    # video_link = info_dict.get("url")
                    video_link = video_info.get("original_url")
                    video_list.append(video_link)
                    video_info_list.append(video_info)
                    self.callback_progress(video_info)

                    # video_id = video_info['video_id']
                    # author = video_info["author"]
                    # video_url = self._USER_URL_WITH % (author["unique_id"], video_id)
                    # count += 1
                    # video_list.append(video_url)
                    # video_info_list.append(video_info)
                    # print(user_id, count)
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
                print("ERROR", err)
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
            # video_info_list.sort(key=lambda x : int(x[sort_key]), reverse=reverse)
            # video_list = [
            #   self._USER_URL_WITH % (video_info["author"]["unique_id"], video_info["video_id"])
            #   for video_info in video_info_list
            # ]
            video_info_list.sort(key=lambda x: int(
                x[sort_key]), reverse=reverse)
            video_info_list = video_info_list[0:limit]
            # video_list = [
            #   # self._LINK_VIDEO_WITH % video_info["id"]
            #   video_info["url_dl"]
            #   for video_info in video_info_list
            # ]
            # video_list = video_list[0:limit]

        # return video_info_list_or_video_list
        if only_url_dl is True:
            video_list = [self.dict_to_url_quote(info)[
                'url_dl'] for info in video_info_list if isinstance(info, dict) and info.get('hd')]
            return video_list

        return video_info_list

    # def extract_info_profile_pwr(self, url_uid:str):
    #   return asyncio.run(self.user_async(url_uid))

    async def extract_info_profile_pwr(
        self,
        url_uid: str,
        limit: int = None,
        sort_by: TikTokSortBy.ChannelVideos = "newest"
    ) -> dict[DictKeyVideoInfoList]:
        await asyncio.sleep(0.0001)
        user_id = self.get_user_id(url_uid)

        chrome_options = Options()
        # chrome_options.add_argument('--user-agent=Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36')
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        chrome_options.add_argument('--user-agent=%s' % user_agent)
        chrome_options.add_argument('--headless=new')

        browser = webdriver.Chrome(options=chrome_options)
        goto_url = self._HOST_DOMAIN + "/search/user?q=tiktok"
        browser.get(goto_url)

        params: dict = self.get_session_params(browser)
        add_params = {
            "count": 35,
            "coverFormat": "2",
            "cursor": 0,
            "secUid": user_id,
            # "secUid":"MS4wLjABAAAAc_SiW3pr5wSxNh9fL4EzwL8-18P5wyLU75H2o-czur6TaAAd2L8pdEni4tGQQ1hI",
        }

        params.update(**add_params)

        api_url = generate_url_query(self._API_USER_POST, params)
        print(api_url)

        async def evaluate(api_url):
            await asyncio.sleep(0.001)
            return browser.execute_script(
                f"""
          return fetch('{api_url}')
            .then(response => response.json())
            .then(data => data)
            .catch(error => error.message);
        """
            )
            # return browser.execute_script(
            #   f"""
            #     return new Promise((resolve, reject) => {{
            #         fetch('{api_url}', {{ method: 'GET', headers: {headers} }})
            #             .then(response => response.json())
            #             .then(data => resolve(data))
            #             .catch(error => reject(error.message));
            #     }});
            #   """
            # )
        data = browser.execute_script(
            f"""
          return fetch('{api_url}')
            .then(response => response.text())
            .then(data => data)
            .catch(error => error.message);
        """
        )
        print(type(data), data)

        browser.quit()
        return data

    #   params = {
    #   "https://www.tiktok.com/api/post/item_list/?aid":"1988",
    #   "app_language":"en",
    #   "app_name":"tiktok_web",
    #   "browser_language":"en-US",
    #   "browser_name":"Mozilla",
    #   "browser_online":"true",
    #   "browser_platform":"Win32",
    #   "browser_version":"5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    #   "channel":"tiktok_web",
    #   "cookie_enabled":"true",
    #   "count":"35",
    #   "coverFormat":"2",
    #   "cursor":"1684922628000",
    #   "device_id":"7286981996302599687",
    #   "device_platform":"web_pc",
    #   "focus_state":"false",
    #   "from_page":"user",
    #   "history_len":"2",
    #   "is_fullscreen":"false",
    #   "is_page_visible":"true",
    #   "language":"en",
    #   "os":"windows",
    #   "priority_region":"",
    #   "referer":"",
    #   "region":"KH",
    #   "screen_height":"1080",
    #   "screen_width":"1920",
    #   "secUid":"MS4wLjABAAAAc_SiW3pr5wSxNh9fL4EzwL8-18P5wyLU75H2o-czur6TaAAd2L8pdEni4tGQQ1hI",
    #   "tz_name":"Asia/Bangkok",
    #   "webcast_language":"en",
    # }

    # async def extract_info_profile_pwr(
    #   self,
    #   url_uid:str,
    #   limit:int=None,
    #   sort_by:TikTokSortBy.ChannelVideos="newest"
    # ) -> dict[DictKeyVideoInfoList]:
    #   user_id = self.get_user_id(url_uid)

    #   async with TikTokApi() as api:
    #     await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, sleep_after=1)
    #     # session = api.sessions
    #     # headers = session[0].headers
    #     user = api.user(user_id)
    #     tikwm = "https://www.tikwm.com%s"

    #     video_info_list =[]
    #     video_list =[]
    #     async for video in user.videos(limit, sort_by):
    #       video_data = video.as_dict
    #       author = video_data["author"]
    #       video_item = video_data["video"]
    #       music = video_data["music"]
    #       video_id = video_data["id"]
    #       stats:dict = video_data["stats"]

    #       video_info = {
    #         "video_id": video_id,
    #         "title": video_data["desc"],
    #         "cover": video_item["cover"],
    #         "origin_cover": video_item["originCover"],
    #         "duration": video_item["duration"],
    #         "play": tikwm % ("/video/media/play/%s.mp4" % video_id),
    #         "wmplay": tikwm % ("/video/media/hdplay/%s.mp4" % video_id),
    #         "music_info": {
    #           "id": music["id"],
    #           "title": music["title"],
    #           "play": tikwm % ("/video/music/%s.mp3" % video_id),
    #           "cover": music["coverLarge"],
    #           "author": music["authorName"],
    #           "original": music["original"],
    #           "duration": music["duration"],
    #           "album": music.get("album", "")
    #         },
    #         # **video_data["stats"],
    #         "create_time": video_data["createTime"],
    #         "author": {
    #           "id": author["id"],
    #           "unique_id": author["uniqueId"],
    #           "sec_uid": author["secUid"],
    #           "nickname": author["nickname"],
    #           "avatar": author["avatarLarger"],
    #         }
    #       }
    #       for key, val in stats.items():
    #         if stats.get(key) is not None and ("Count" in key or "count" in key):
    #           KEY = key.lower().replace("count", "_count")
    #           video_info[KEY] = val

    #       video_list.append(self._USER_URL_WITH % (author["uniqueId"], video_id))
    #       video_info_list.append(video_info)

    #     if sort_by and sort_by != "newest":
    #       limit = limit if isinstance(limit, int) and limit != 0 else len(video_info_list)
    #       if sort_by == "popular":
    #         sort_key = "play_count"
    #         reverse = True
    #       else:
    #         sort_key = "create_time"
    #         reverse = False
    #       video_info_list.sort(key=lambda x : int(x[sort_key]), reverse=reverse)
    #       video_list = [
    #         self._USER_URL_WITH % (video_info["author"]["unique_id"], video_info["video_id"])
    #         for video_info in video_info_list
    #       ]

    #       video_info_list = video_info_list[0:limit]
    #       video_list = video_list[0:limit]

    #   return {
    #     "video_info_list": video_info_list,
    #     "video_list": video_list
    #   }

    def extract_videos_from_multiple_user(
        self,
        url_username_list: list[str],
        limit: int = None,
        sort_by: TikTokSortBy.ChannelVideos = "newest",
        cursor_continue='',
        use_per_next_cursor=False,
        with_url_dl=False,
        only_url_dl=False
    ) -> list[str | dict]:
        async def extract_videos_from_multiple_user():
            async def extract_videos_from_user(url_username):
                await asyncio.sleep(0.0001)
                if self.server == "1" or self.server == "default":
                    video_list = await self.extract_info_profile(url_username, limit, sort_by, cursor_continue, use_per_next_cursor, only_url_dl)
                else:
                    try:
                        profile_video_info = await self.extract_info_profile_pwr(url_username, limit, sort_by)
                    except:
                        profile_video_info = await self.extract_info_profile_pwr(url_username, limit, sort_by)
                    if only_url_dl:
                        video_list = profile_video_info.get(
                            "video_list")  # type: list
                    else:
                        video_list = profile_video_info.get(
                            "video_info_list")  # type: list

                await asyncio.sleep(0.0001)
                # print("[[[Video list]]]: ", json.dumps(video_list), "\n")
                return video_list

            tasks = [extract_videos_from_user(url)
                     for url in url_username_list]
            get_tasks = await asyncio.gather(*tasks, return_exceptions=True)
            return [
                video_list for video_list in get_tasks if isinstance(video_list, list)
            ]

        video_list = asyncio.run(extract_videos_from_multiple_user())
        return sum(video_list, [])
        # return asyncio.run(extract_videos_from_multiple_user())
