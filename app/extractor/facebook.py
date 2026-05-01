import asyncio
import json
import operator
import re
import time
from html import unescape
from math import ceil
from urllib.parse import quote, unquote, urlparse

from typing_extensions import Literal, Optional, TypeAlias, Union
from yt_dlp import YoutubeDL
from yt_dlp.utils.networking import random_user_agent
from yt_dlp.YoutubeDL import Request

from .util_extract import (
    PORT,
    _execute_request,
    all_promise,
    arr_chunk,
    datetime_timestamp,
    default_chrome_options,
    extract_info_video_list_local_ft_pool,
    extract_info_video_list_localhost_async,
    generate_url_query,
    get_json_from_html,
    osA,
    query_dict_encode,
    res_async,
)
from .youtube_ import YouTubeSortBy as FacebookSortBy

# import requests
try:
    from chompjs import parse_js_object
except:
    def parse_js_object(content):
        return 'none'
# from colorama import *
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

# from pystyle import *
# from rich.console import Console
# from rich.traceback import install
# from selectolax.lexbor import LexborHTMLParser as Parser

# import numpy as np


# from selenium.webdriver.chrome.service import Service


# from selenium.webdriver.common.by import By
# from webdriver_manager.chrome import ChromeDriverManager

# import_section

# install()
# console = Console()
# init()

AOS = osA.AOS

FacebookKeyVideoInfoList: TypeAlias = Literal["video_info_list",
                                              "user_info", "video_list"]

# __import_section__


def clean_html(content: str):
    html_pattern = r"(?:<div.*?class=\"some-class\".*?>)(.*?)(?:<\\/div>)"
    html_pattern = r"(?=src)src=\"(?P<src>[^\"]+)"  # get attribute value
    # get img src
    html_pattern = r'<img[^<>]+src=["\']([^"\'<>]+\.(?:gif|png|jpe?g))["\']'
    html_pattern = r"(?:<BaseURL>)(.*?)(?:<\\/BaseURL>)"

    return re.findall(html_pattern, content)


web_fb_downloader = [
    "https://en.savefrom.net",
    "https://www.fbvideodown.com",
]


facebookHeaders = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "dpr": "1",
    "priority": "u=0, i",
    "sec-ch-prefers-color-scheme": "light",
    # "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
    # "sec-ch-ua-full-version-list": "\"Not)A;Brand\";v=\"99.0.0.0\", \"Google Chrome\";v=\"127.0.6533.89\", \"Chromium\";v=\"127.0.6533.89\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": "\"\"",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-platform-version": "\"10.0.0\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    # "viewport-width": "608"
}


# facebookHeaders = {
#     "User-Agent": random_user_agent(),
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#     "Accept-Language": "en-us,en;q=0.5",
#     "Sec-Fetch-Mode": "navigate",
#     'Accept-Encoding': 'identity', # Disable compression
# }

class FaceBookBaseIE:
    _WEBPAGE_HOST = "https://web.facebook.com/%s"
    _LINK_USER_WITH = "https://web.facebook.com/%s/videos/%s"
    _LINK_USER_REEL_WITH = "https://web.facebook.com/%s/reels/%s"
    _LINK_VIDEO_WITH = "https://web.facebook.com/watch/?v=%s"

    _API_GRAPHQL = "https://web.facebook.com/api/graphql/"

    def get_video_id(self, url_vid: str) -> str:
        url_vid = url_vid.strip()
        if ".com/watch/?v=" in url_vid:
            video_id = url_vid.split("/watch/?v=")[1].split("&")[0]
        elif "/videos/" in url_vid:
            url = url_vid.split("?")[0]
            url = url[:-1] if url.endswith('/') else url
            video_id = url.split("/")[-1:][0]
        else:
            video_id = re.findall('[0-9]+', url_vid)[0]

        return video_id

    def get_url_vid(self, url_vid: str) -> str:
        return self._LINK_VIDEO_WITH % self.get_video_id(url_vid)

    def get_username_id(self, url_uid: str) -> str:
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

    def dict_to_url_quote(self, info_dict: dict):
        update_info_dict = {"info_dict": {**info_dict}}
        url_dl = info_dict["hd"] + ("&download_with_info_dict=%s" %
                                    quote(json.dumps(update_info_dict)))
        return {**update_info_dict, "url_dl": url_dl}

    def extract_node(self, node: dict, with_url_dl=False):
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
        print('=====================')
        if isinstance(username, str) and 'https' in username and '%2F_u%2F' in username:
            match = re.search(r'%2F_u%2F([^&]+)', username)
            if match:
                username = match.group(1) or 'unknown'
                info_dict['user_info']['username'] = username
                if not uploader:
                    info_dict['uploader'] = username
                print('match', username, info_dict)
        # for key, value in node.items():
        #   info_dict[key] = value
        info_dict.update(**node)
        if info_dict["timestamp"] > 0:
            info_dict["upload_date"] = datetime_timestamp(
                info_dict["timestamp"]).__str__()

        if with_url_dl is True:
            # update_info_dict = {"info_dict": {**info_dict}}
            # url_dl = url_dl + ("&download_with_info_dict=%s" % self.dict_to_url_quote(update_info_dict))
            # info_dict = json.loads(unquote(url_dl.split("info_dict=")[1]))
            return self.dict_to_url_quote(info_dict)

        return info_dict

    # def extract_node(self, node:dict, with_url_dl=False):

    #   info_dict = {
    #     "id": "",
    #     "display_id": "",
    #     "title": "",
    #     "fulltitle": "",
    #     "description": "",
    #     "thumbnail": "",
    #     "original_thumbnail": "",
    #     "sd": "",
    #     "hd": "",
    #     "music": "",
    #     "requested_download": [],
    #     "uploader": "",
    #     "uploader_id": "",
    #     "uploader_url": "",
    #     "url": "",
    #     "original_url": "",
    #     "webpage_url": "",
    #     "webpage_url_domain": "facebook.com",
    #     "extractor": "facebook",
    #     "extractor_key": "Facebook",
    #     "width": 0,
    #     "height": 0,
    #     "resolution": "0x0",
    #     "duration": 0,
    #     # "duration": int(float(video["duration"] / 1000)) if video.get("duration") is not None and video.get("duration") != 0 else music["duration"],
    #     "timestamp": 0,
    #     "release_timestamp": 0,
    #     "upload_date": "",
    #     "view_count": 0,
    #     "like_count": 0,
    #     "comment_count": 0,
    #     "share_count": 0,
    #     "subtitles": [],
    #     "audio_only": [],
    #     "video_only": [],
    #     "user_info": {},
    #   }
    #   # for key, value in node.items():
    #   #   info_dict[key] = value
    #   info_dict.update(**node)
    #   if info_dict["timestamp"] > 0:
    #     info_dict["upload_date"] = datetime_timestamp(info_dict["timestamp"]).__str__()

    #   if with_url_dl is True:
    #     # update_info_dict = {"info_dict": {**info_dict}}
    #     # url_dl = url_dl + ("&download_with_info_dict=%s" % self.dict_to_url_quote(update_info_dict))
    #     # info_dict = json.loads(unquote(url_dl.split("info_dict=")[1]))
    #     return self.dict_to_url_quote(info_dict)

    #   return info_dict


class FacebookRequest(FaceBookBaseIE):
    def __init__(self) -> None:
        super().__init__()
        self.is_stopped = False

    def stop_extraction(self):
        self.is_stopped = True

    def on_callback_progress(self, video_info: dict):
        pass

    def callback_progress(self, video_info: dict):
        self.on_callback_progress(video_info)

    async def extract_video_list_from_graphql_no_chunks(
        self,
        url_list: list[str],
        with_url_dl: bool = False,
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
                "variables": query_dict_encode({
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

        def getInfoDictFromContent(content: str):
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
                                    user_info["url"] = "https://www.facebook.com/%s" % username

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
                    print('An exception occurred', err, video_info)

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
                        print("error", err)
                        pass
                video_info.update(**{
                    "url": self._LINK_VIDEO_WITH % video_id,
                    "uploader": user.get("username", ""),
                    "uploader_id": user.get("id", ""),
                    "uploader_url": user.get("url", ""),
                })

            self.callback_progress(video_info)
            if with_url_dl == True:
                return self.dict_to_url_quote(video_info)

            return video_info

        next_cursor_data_list = []
        api_url_list = [get_api_video_list(url) for url in url_list]

        def progress_callback(is_stopped):
            return self.is_stopped

        content_list = await res_async(api_url_list, "text", method="POST", progress_callback=progress_callback)

        # content_list = []
        # with YoutubeDL() as ydl:
        #   for url in api_url_list:
        #     try:
        #       r = ydl.urlopen(Request(url, method="POST"))
        #       content_list.append(bytes.decode(r.read()))
        #     except ValueError as e:
        #       print("Error URL", url, e)

        # print(api_user)
        # r = _execute_request(api_url_list[0], "POST")
        # content = bytes.decode(r.read())

        # video_info = getInfoDictFromContent(content)

        video_info_list = []
        for content in content_list:
            if self.is_stopped:
                break
            video_info = getInfoDictFromContent(content)
            video_info_list.append(video_info)

        return video_info_list

    async def extract_video_list_from_graphql(
        self,
        url_list: list[str],
        with_url_dl: bool = False,
        chunks: int = None
    ):
        url_list_of_list = list(arr_chunk(url_list, int(chunks or 100)))
        if len(url_list_of_list) <= 1:
            return await self.extract_video_list_from_graphql_no_chunks(url_list, with_url_dl)

        video_info_list_of_list = [
            await self.extract_video_list_from_graphql_no_chunks(url_list, with_url_dl)
            for url_list in url_list_of_list
        ]
        return sum(video_info_list_of_list, [])


class FacebookExtractor(FacebookRequest):
    def __init__(self, server: str = None, sleep=3):
        super().__init__()
        self.server = server if isinstance(server, str) else "default"
        self.sleep = sleep
        self.user_videos_info = {}
        self.video_info_list = []
        self.video_list = []

    def sln_open_and_close(self, goto_url: str, user_agent: str = None):
        if True:
            return []
        chrome_options = Options()
        user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        chrome_options.add_argument('--user-agent=%s' % user_agent)
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument('--headless=new')
        # chrome_options.add_argument('headless')

        browser = webdriver.Chrome(options=chrome_options)
        browser.get(goto_url)
        browser.close()

    # def remove_duplicate(self, var_list:list|list[dict]):
    #   if isinstance(var_list[0], dict):
    #     return list(
    #       { frozenset(item.items()): item for item in var_list }.values()
    #     )
    #   else:
    #     return list(np.unique(var_list))

    def default_server(self):
        return self.server if isinstance(self.server, dict) else {
            "url": "https://en.savefrom.net",
            "selector": {
                "input": "input#sf_url",
                "click_action": ".r-box > button#sf_submit",
                "await_seletor": ".downloader-2 .result-box .link-box .def-btn-box a",
                "multi_link": ".downloader-2 .result-box.video .link-box .drop-down-box .list a.link",
                # "link_attr": "href"
            }
        }

    async def extract_info_video_list_sln(self, url_list: list[str], only_url_dl=False, use_in_driver=True, browser_driver=None):
        if True:
            return []
        await asyncio.sleep(0.0001)
        if use_in_driver is True:
            chrome_options = Options()
            # chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36')
            default_chrome_options(chrome_options)
            chrome_options.add_argument("--headless=new")

            browser = webdriver.Chrome(chrome_options)
        else:
            browser = browser_driver

        tasks = [
            self.pre_extract_info_video_sln(url, browser, only_url_dl)
            for url in url_list
        ]
        get_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        if use_in_driver is True:
            browser.quit()

        video_info_list = [
            video_info for video_info in get_tasks if isinstance(video_info, dict)
        ]
        return video_info_list

    async def extract_info_video_list_localhost(self, url_list: list[str], only_url_dl=False):
        data = await extract_info_video_list_localhost_async(url_list, only_url_dl)
        return data

    def extract_info_video_list_localhost_ft_pool(self, url_list: list[str], with_url_dl=False, custom_cpu: int = None):
        total_url = len(url_list)
        chunks = 50
        runtime = ceil(total_url / chunks)
        if isinstance(custom_cpu, int) and custom_cpu > 0:
            chunks = ceil(total_url / custom_cpu)
            runtime = custom_cpu
            video_info_list = extract_info_video_list_local_ft_pool(
                url_list, chunks, runtime, with_url_dl)
        if total_url >= 150:
            video_info_list = extract_info_video_list_local_ft_pool(
                url_list, chunks, runtime, with_url_dl)
        else:
            url_list_of_list = list(arr_chunk(url_list, 150))
            video_info_list_of_list = [
                extract_info_video_list_local_ft_pool(
                    url_list, chunks, runtime, with_url_dl)
                for url_list in url_list_of_list
            ]
            video_info_list = sum(video_info_list_of_list, [])

        # list(filter(lambda d: d.get("status_code") is None, video_info_list))
        return video_info_list

    def extract_info_video_list(self, url_list: list[str], only_url_dl=False, custom_cpu: int = None):
        if self.server == "local":
            video_info_list = self.extract_info_video_list_localhost_ft_pool(
                url_list, only_url_dl, custom_cpu)
        else:
            video_info_list = asyncio.run(
                self.extract_info_video_list_sln(url_list, only_url_dl))

        return video_info_list
    # async def extract_info_video_list_graphql(self, url_list:list[str]):

    #   params = {
    #     "av":"0",
    #     "__user":"0",
    #     "__a":"1",
    #     "__req":"5a",
    #     "__hs":"19633.HYP:comet_loggedout_pkg.2.1..0.0",
    #     "dpr":"1",
    #     "__ccg":"MODERATE",
    #     "fb_api_caller_class":"RelayModern",
    #     "fb_api_req_friendly_name":"CometVideoHomeNewPermalinkHeroUnitQuery",
    #     "variables": query_dict_encode({
    #       "UFI2CommentsProvider_commentsKey": "CometVideoHomeNewPermalinkHeroUnitQuery",
    #       "caller": "channel_view_from_page_timeline",
    #       "displayCommentsContextEnableComment": None,
    #       "displayCommentsContextIsAdPreview": None,
    #       "displayCommentsContextIsAggregatedShare": None,
    #       "displayCommentsContextIsStorySet": None,
    #       "displayCommentsFeedbackContext": None,
    #       "entityNumber": 5,
    #       "feedbackSource": 41,
    #       "feedLocation": "TAHOE",
    #       "focusCommentID": None,
    #       "isCrawler": "false",
    #       "isLoggedOut": "true",
    #       "privacySelectorRenderLocation": "COMET_STREAM",
    #       "renderLocation": "video_home",
    #       "scale": 1,
    #       "useDefaultActor": "false",
    #       "videoID": self.get_url_vid(url_list[0]), #"301195432554766"
    #       "videoIDStr": self.get_url_vid(url_list[0])
    #     }),
    #     "doc_id":"6499956053386921"
    #   }

    #   api_url = generate_url_query(self._API_GRAPHQL, params)
    #   print(api_url)
    #   r = _execute_request(api_url, "POST")
    #   content = bytes.decode(r.read())
    #   # data_list = []
    #   # for text in content.split("\n"):
    #   #   if not (
    #   #     "CometTahoeUpNextOverlayAndEndScreenWrapperConditionalLoader_video" in text or
    #   #     "VideoPlayerWithVideoCardsOverlay_video" in text or
    #   #     "InstreamVideoAdBreaksPlayer_video" in text or
    #   #     "CometTahoeSidePaneAttachmentRenderer_video" in text
    #   #   ):
    #   #     data = parse_js_object(text)
    #   #     data_list.append(data)

    #   with open("./extractor/test/facebook_test.json", "w") as f:
    #     f.write(content)

    def extract_user_videos_graphql(
        self, page_id: str, cursor: str, hasMore=False,
        limit: Optional[int] = None,
        sort_by: str = "newest",
        content_type: FacebookSortBy.VideoType = "videos",
        next_cursor=False,
        use_per_next_cursor=False,
    ):
        cursor_position = int(0)
        limit_copy = limit
        count = 0

        use_per_next_cursor = sort_by and sort_by == "newest" and use_per_next_cursor

        video_info_list = []
        video_list = []
        is_reel = content_type == "shorts"
        for i in range(1000):
            if self.is_stopped:
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
                    "variables": query_dict_encode({
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
                    "variables": query_dict_encode({
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
            r = _execute_request(api_user, "POST", headers=headers)
            if is_reel:
                _content = bytes.decode(r.read())

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
                data = json.loads(bytes.decode(r.read())).get("data")

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
                    next_cursor_data = _q + ("next_data=%s" % quote(query_dict_encode({
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
                    # with open("./extractor/test/facebook_test_.json", "w") as f:
                    #   f.write(json.dumps(info, indent=2))
                    video_id = info["short_form_video_context"]["video"]["id"]
                    return {"video_id": video_id, "timestamp": info["creation_time"]}

                edege_info_list = [edege_get_info(
                    info) for info in edege_info_list]
                _data.sort(key=operator.itemgetter("video_id"))
                edege_info_list.sort(key=operator.itemgetter("video_id"))
                # with open("./extractor/test/facebook_test_.json", "w") as f:
                #   f.write(json.dumps([_data, edege_info_list], indent=2))

            for i, edege_info in enumerate(edege_info_list):
                if self.is_stopped:
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
                    video_url = self.get_url_vid(video_id)
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

            if use_per_next_cursor:
                break

            cursor_position += 1
            if hasMore is False or count == limit_copy:
                break

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

        print('video_info_list', len(video_info_list))
        return {
            "video_info_list": video_info_list,
            "video_list": video_list
        }

    async def extract_user_videos_tab(
        self, url_uid_list: list[str],
        limit: int = None,
        sort_by: FacebookSortBy.ChannelVideos = "newest",
        content_type: FacebookSortBy.VideoType = "videos",
        with_url_dl=False,
        only_url_dl=False,
        only_original_url_from_profile=False,
        cursor_continue='',
        use_per_next_cursor=False,
        chunks: int = None
    ):
        async def pre_extract(url_uid: str, content_type, cursor_continue='',):
            global cursor, hasMore
            await asyncio.sleep(0.001)
            username_id = self.get_username_id(url_uid)

            page_id = None
            cursor = cursor_continue
            hasMore = False
            is_custom_cursor = True if cursor_continue and cursor_continue != "" else False

            is_reel = False
            if content_type == "shorts":
                is_reel = True
            if "profile.php?id=" in url_uid or url_uid.split('?')[0].endswith('/reels') or url_uid.split('?')[0].endswith('/reels/'):
                is_reel = True
                content_type = "shorts"

            try:
                if is_reel:
                    url = self._LINK_USER_REEL_WITH % (username_id, "")
                    if "profile.php?id=" in url_uid:
                        url = "https://web.facebook.com/profile.php?id=%s&%s" % (
                            username_id, "sk=reels_tab")
                        url = str(_execute_request(url).url)

                    print("Goto URL Reel Tab: %s" % url)
                    html = ''
                    retries = 0
                    while True:
                        if retries == 2:
                            time.sleep(0.2)

                        with YoutubeDL() as ydl:
                            r = ydl.urlopen(Request(url))

                        # r = _execute_request(url, headers=facebookHeaders)
                        html = bytes.decode(r.read())
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
                            # with open("./extractor/test/facebook_test_.json", "w") as f:
                                # with open(r"C:\Users\DELL\Desktop\Web Dev\Electron App\AIOTubeDown\electron\public\bin\video_info.txt", "w", encoding='utf-8') as f:
                                #   f.write(data)
                                entries_obj = json.loads(data)
                            page_id = entries_obj["id"]
                            aggregated = entries_obj["aggregated_fb_shorts"]
                            cursor = aggregated["page_info"]["end_cursor"]
                            hasMore = aggregated["page_info"]["has_next_page"]

                            break

                else:
                    url = self._LINK_USER_WITH % (username_id, "")
                    print("Goto URL Video Tab: %s" % url)
                    html = ''
                    retries = 0
                    while True:
                        if retries == 2:
                            time.sleep(0.2)
                        # r = _execute_request(url, headers=facebookHeaders)
                        with YoutubeDL() as ydl:
                            r = ydl.urlopen(url)
                        html = bytes.decode(r.read())
                        if '"all_videos":' in html:
                            break
                        else:
                            retries += 1

                        if retries >= 3:
                            break

                    for content in html.split('"all_videos":'):
                        if "channel_tab_thumbnail_renderer" in content:
                            entries_obj = parse_js_object(content)
                            # with open("./extractor/test/facebook_test_.json", "w") as f:
                            # with open(r"C:\Users\DELL\Desktop\Web Dev\Electron App\AIOTubeDown\electron\public\bin\video_info.txt", "w", encoding='utf-8') as f:
                            #   f.write(html)
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
                    video_info_list = self.extract_user_videos_graphql(
                        page_id, cursor, hasMore, limit, sort_by, content_type, next_cursor=True, use_per_next_cursor=use_per_next_cursor
                    )

                    return video_info_list
            except ValueError as err:
                print("ERROR", err)
                raise Exception(err, url_uid)

        # tasks = [pre_extract(url_uid, content_type, cursor_continue) for url_uid in url_uid_list]
        tasks = []
        for url_uid in url_uid_list:
            if self.is_stopped:
                break
            task = asyncio.create_task(pre_extract(
                url_uid, content_type, cursor_continue))
            tasks.append(task)

        get_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        video_list = [
            video_info["video_list"] for video_info in get_tasks
            if isinstance(video_info, dict)
        ]
        all_video_list = sum(video_list, [])

        if self.server != "graphql" and only_original_url_from_profile is True:
            return all_video_list
        # dl_video_list = all_video_list # Test only video links
        # print("[all_video_list]: ", all_video_list)
        if only_url_dl is True:
            with_url_dl = True

        if self.server == "default" or self.server == "graphql":
            video_info_list = await self.extract_video_list_from_graphql(all_video_list, with_url_dl, chunks)
        else:
            video_info_list = await self.extract_info_video_list_localhost(all_video_list, with_url_dl)

        if only_url_dl is True:
            dl_video_list = [
                video_info["url_dl"] for video_info in video_info_list
                if isinstance(video_info, dict) and video_info.get("url_dl")
            ]

            return dl_video_list
        else:
            video_info_list = [
                video_info for video_info in video_info_list
                if isinstance(video_info, dict)
            ]
            return video_info_list

    async def extract_user_videos_sln_graphql(
        self, url_uid_list: list[str],
        limit: int = None,
        sort_by: FacebookSortBy.ChannelVideos = "newest",
        content_type: FacebookSortBy.VideoType = "videos",
        only_url_dl=True,
        only_original_url_from_profile=False,
        chunks: int = None
    ):
        if True:
            return []
        chrome_options = Options()
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36')
        default_chrome_options(chrome_options)
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument("--headless=new")

        # service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(chrome_options)

        async def pre_extract(url_uid, content_type):
            global cursor, hasMore
            await asyncio.sleep(0.001)
            username_id = self.get_username_id(url_uid)

            page_id = None
            cursor = ""
            hasMore = False

            is_reel = False
            if content_type == "shorts":
                is_reel = True
            if "profile.php?id=" in url_uid or url_uid.split('?')[0].endswith('/reels') or url_uid.split('?')[0].endswith('/reels/'):
                is_reel = True
                content_type = "shorts"

            try:
                if is_reel:
                    url = self._LINK_USER_REEL_WITH % (username_id, "")
                    if "profile.php?id=" in url_uid:
                        url = "https://web.facebook.com/profile.php?id=%s&%s" % (
                            username_id, "sk=reels_tab")
                        url = str(_execute_request(url).url)

                    print("[Driver] Goto URL Reel Tab: %s" % url)
                    browser.get(url)
                    contents = browser.page_source
                    for content in contents.split('adp_ProfileCometTopAppSectionQueryRelayPreloader'):
                        if "TimelineAppSection" in content:
                            content = content.split("\"collection\"")[1]
                            entries_obj = parse_js_object(content)
                            if isinstance(entries_obj, str) and entries_obj == 'none':
                                entries_obj = {}
                            # with open("./extractor/test/facebook_test_.json", "w") as f:
                            # with open(r"C:\Users\DELL\Desktop\Web Dev\Electron App\AIOTubeDown\electron\public\bin\video_info.txt", "w") as f:
                            #   f.write(json.dumps(content, indent=2))
                            page_id = entries_obj["id"]
                            aggregated = entries_obj["aggregated_fb_shorts"]
                            cursor = aggregated["page_info"]["end_cursor"]
                            hasMore = aggregated["page_info"]["has_next_page"]

                            break
                else:
                    url = self._LINK_USER_WITH % (username_id, "")
                    print("Goto URL Video Tab: %s" % url)
                    browser.get(url)
                    contents = browser.page_source

                    # if contents:
                    #   return [contents]
                    for content in contents.split('"all_videos":'):
                        if "channel_tab_thumbnail_renderer" in content:
                            entries_obj = parse_js_object(content)
                            # with open("./extractor/test/facebook_test_.json", "w") as f:
                            # with open(r"C:\Users\DELL\Desktop\Web Dev\Electron App\AIOTubeDown\electron\public\bin\video_info.txt", "w", encoding='utf-8') as f:
                            #   f.write(contents)
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

                # print(page_id, cursor, hasMore)
                if page_id:
                    video_info_list = self.extract_user_videos_graphql(
                        page_id, cursor, hasMore, limit, sort_by, content_type
                    )

                    return video_info_list
            except ValueError as err:
                print("ERROR", err)
                raise Exception(err, url_uid)

        tasks = [pre_extract(url_uid, content_type)
                 for url_uid in url_uid_list]
        get_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        browser.close()
        video_list = [
            video_info["video_list"] for video_info in get_tasks
            if isinstance(video_info, dict)
        ]
        all_video_list = sum(video_list, [])

        if only_original_url_from_profile is True:
            return all_video_list
        # dl_video_list = all_video_list # Test only video links
        # print("[all_video_list]: ", len(all_video_list))

        if self.server == "default":
            video_info_list = await self.extract_video_list_from_graphql(all_video_list, True, chunks)
        else:
            video_info_list = await self.extract_info_video_list_localhost(all_video_list, True)

        try:
            browser.quit()
        except:
            pass
        if only_url_dl is True:
            dl_video_list = [
                video_info["url_dl"] for video_info in video_info_list
                if isinstance(video_info, dict) and video_info.get("url_dl")
            ]

            return dl_video_list
        else:
            video_info_list = [
                video_info for video_info in video_info_list
                if isinstance(video_info, dict)
            ]
            return video_info_list

    # async def extract_user_videos_pwr(
    #   self, url_uid:str,
    #   limit:int=None,
    #   sort_by:FacebookSortBy.ChannelVideos="newest",
    # ) -> dict[FacebookKeyVideoInfoList,list[dict|str]]:
    #   url = self._LINK_USER_WITH % (self.get_username_id(url_uid), "")
    #   # print(url)
    #   is_headless = isinstance(limit, int) and limit <= 9 and sort_by == "newest"
    #   async with async_playwright() as pw:
    #     browser = await pw.chromium.launch(
    #       headless=is_headless
    #     )
    #     context = await browser.new_context(viewport={"width":340, "height":600})
    #     page = await context.new_page()
    #     await page.goto(url)

    #     if is_headless is True:
    #       contents = await page.content()
    #       video_info_list = []
    #       video_list = []
    #       for content in contents.split('"all_videos"'):
    #         if "channel_tab_thumbnail_renderer" in content:
    #           entries_obj = parse_js_object(content)
    #           for video_info in entries_obj["edges"]:
    #             video = video_info["node"]["channel_tab_thumbnail_renderer"]["video"]
    #             video_url = self.get_url_vid(video["id"])
    #             view_count = video["play_count"]

    #             video_list.append(video_url)
    #             video_info_list.append({"view_count": view_count, "url": video_url})
    #           break

    #       return {
    #         "video_info_list": video_info_list[0:limit],
    #         "video_list": video_list[0:limit]
    #       }

    #     await page.click('[role="dialog"] [aria-label="Close"]')
    #     await page.query_selector_all('[role="main"] > :last-child a[href]')
    #     async def scroll_down(sleep=1):
    #       await page.evaluate("""() => {
    #           (function () {
    #             document.body.style.zoom = 0.3
    #             var intervalObj = null;
    #             var clickHandler = function () {
    #                 console.log("Clicked; stopping autoscroll");
    #                 clearInterval(intervalObj);
    #                 document.body.removeEventListener("click", clickHandler);
    #             }
    #             function scrollDown() {
    #                 var scrollHeight = document.body.scrollHeight,
    #                     scrollTop = document.body.scrollTop,
    #                     innerHeight = window.innerHeight,
    #                     difference = (scrollHeight - scrollTop) - innerHeight

    #                 if (difference > 0) {
    #                     window.scrollBy(0, difference);
    #                     console.log("scrolling down more");
    #                 } else {
    #                     console.log("reached bottom of page; stopping");
    #                     clearInterval(intervalObj);
    #                     document.body.removeEventListener("click", clickHandler);
    #                 }
    #             }

    #             document.body.addEventListener("click", clickHandler);

    #             intervalObj = setInterval(scrollDown, 5); }
    #           )();
    #         }
    #       """)
    #       await asyncio.sleep(sleep)

    #     async def get_video_info_list():
    #       return await page.evaluate(""" () => {
    #         var href_selector = '[role="main"] > :last-child > div > :last-child div > span > div > a[href]'
    #         var view_count_selector = '[role="main"] > :last-child > div > :last-child div > span > div:last-child > div > div:last-child div > span > div'
    #         var ele_href_list = document.querySelectorAll(href_selector)
    #         var ele_view_count = document.querySelectorAll(view_count_selector)

    #         let video_info_list = []
    #         ele_href_list.forEach((e,i) => {
    #           const video_url = e.getAttribute("href")
    #           const text = ele_view_count[i].textContent
    #           var viewCount = text ? Number(text.replace(/[^0-9.]/g,"")) : 0;
    #           if(text.includes("K")){
    #             viewCount = viewCount * 1000
    #           } else if(text.includes("M")){
    #             viewCount = viewCount * 1000000
    #           }
    #           video_info_list.push({
    #             view_count: viewCount, url: video_url
    #           })
    #         })
    #         return video_info_list
    #       }""")

    #     await scroll_down()
    #     hasMore = True
    #     count = 0
    #     limit_copy = limit
    #     video_info_list = []
    #     video_list = []
    #     for i in range(1000):
    #       video_info_1 = await get_video_info_list()
    #       await scroll_down()
    #       await scroll_down()
    #       video_info_2 = await get_video_info_list()
    #       hasMore = len(video_info_2) > len(video_info_1)
    #       for video_info in video_info_2:
    #         # if link not in self.video_list:
    #         count += 1
    #         if video_info["url"] not in video_list:
    #           video_list.append(video_info["url"])
    #           video_info_list = video_info_2

    #         if sort_by and sort_by != "newest":
    #           limit_copy = None
    #         if len(video_list) == limit_copy:
    #           hasMore = False
    #           break
    #       await asyncio.sleep(0.0001)
    #       # print(hasMore)
    #       if hasMore is False:
    #         await page.click('body')
    #         break

    #     video_info_list = self.remove_duplicate(video_info_list)
    #     video_list:list[str] = [self.get_url_vid(video_info["url"]) for video_info in video_info_list]
    #     if sort_by and sort_by != "newest":
    #       limit = limit if isinstance(limit, int) and limit != 0 else len(video_info_list)
    #       if sort_by == "popular":
    #         video_info_list.sort(key=lambda x : int(x["view_count"]), reverse=True)
    #         video_list = [
    #           self.get_url_vid(video_info["url"])
    #           for video_info in video_info_list
    #         ]
    #       else:
    #         video_info_list.reverse()
    #         video_list.reverse()

    #       video_info_list = video_info_list[0:limit]
    #       video_list = video_list[0:limit]
    #     else:
    #       video_info_list = video_info_list[0:limit]
    #       video_list = video_list[0:limit]

    #     # print(video_info_list)
    #     await context.close()
    #     await browser.close()
    #   return {
    #     "video_info_list": video_info_list,
    #     "video_list": video_list
    #   }

    def extract_videos_from_multiple_user(
        self, url_list: str,
        limit: int = None,
        sort_by: FacebookSortBy.ChannelVideos = "newest",
        content_type: FacebookSortBy.VideoType = "videos",
        with_url_dl=False,
        only_url_dl=False,
        only_original_url_from_profile=False,
        extractor='default',
        cursor_continue='',
        use_per_next_cursor=False,
        chunks: int = None
    ) -> list[str | dict]:

        if extractor == 'driver':
            video_list = asyncio.run(
                self.extract_user_videos_sln_graphql(
                    url_list, limit, sort_by, content_type, only_url_dl, only_original_url_from_profile, chunks)
            )
        else:
            video_list = asyncio.run(
                self.extract_user_videos_tab(url_list, limit, sort_by, content_type, only_url_dl,
                                             only_original_url_from_profile, cursor_continue, use_per_next_cursor, chunks)
            )
        # print(all_video_list)
        return video_list
