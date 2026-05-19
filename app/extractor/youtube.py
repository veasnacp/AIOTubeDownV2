import asyncio
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from types import FunctionType
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    TypeAlias,
)
from urllib.parse import quote, unquote

from curl_cffi.requests import AsyncSession, Response, Session

# from pytubefix import extract
from yt_dlp.utils import format_bytes

from ._request import (
    BrowserTypeLiteral,
    ExtractorBase,
    dict_to_query_string,
    get_json_from_html,
    search_dict,
)
from ._tsdl import AsyncTSVideoDownloader, ProgressData
from ._utils import safe_filename
from .youtube_sig import extract_video_formats

current_dir = Path(__file__).parent
type_property_map = {
    "videos": "videoRenderer",
    "shorts": "richItemRenderer",
    "streams": "videoRenderer"
}


class YouTubeSortBy:
    ChannelVideos: TypeAlias = Literal["newest", "oldest", "popular"]
    VideoType: TypeAlias = Literal["videos", "shorts", "streams"]
    SearchVideo: TypeAlias = Literal["relevance",
                                     "upload_date", "view_count", "rating"]
    SearchVideoResult: TypeAlias = Literal["video",
                                           "channel", "playlist", "movie"]


class YouTubeBaseIE(ExtractorBase):
    _BASE_URL = "https://www.youtube.com"
    _LINK_CHANNEL = "https://www.youtube.com/channel/%s"
    _LINK_USERNAME = "https://www.youtube.com/@%s"
    _LINK_ID = "https://www.youtube.com/watch?v=%s"
    _MOBILE_LINK_ID = "https://m.youtube.com/watch?v=%s"
    _CLOUD_FOLDER = "videos/youtube"

    _TEST_VIDEO_ID = "dQw4w9WgXcQ"

    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }
    type_property_map = {
        "videos": "videoRenderer",
        "shorts": "richItemRenderer",
        "streams": "videoRenderer"
    }
    resolution = 720
    chunk_size = 1024 * 1024

    def get_video_id(self, video_url: str):
        url = video_url.strip()
        find_id = re.findall(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        video_id = ''
        if find_id:
            video_id = str(find_id[0])
        return video_id

    def get_video_url(self, video_url: str, is_mobile=False):
        watch_link = self._MOBILE_LINK_ID if is_mobile else self._LINK_ID
        url = watch_link % self.get_video_id(video_url)
        return url

    def get_channel_url_username(self, url_username_id: str):
        url = url_username_id.strip()
        username = ""
        if "/channel/" in url:
            username = url.split('/channel/')[1].split("?")[0].split("/")[0]
            channel_url = self._LINK_CHANNEL % username
        elif "@" in url:
            username = url.split('@')[1].split("?")[0].split("/")[0]
            channel_url = self._LINK_USERNAME % username
        else:
            channel_url = url
        return channel_url, username

    def get_channel_url(self, url: str):
        return self.get_channel_url_username(url)[1]

    def get_playlist_id(self, url_playlist_id: str):
        url = url_playlist_id.strip()
        if "playlist?list=" in url:
            playlist_id = url.split('playlist?list=')[1].split("&")[0]
        elif "&list=" in url and "watch?v=" in url:
            playlist_id = url.split("&list=")[1].split("&")[0]
        else:
            playlist_id = url
        return playlist_id

    def extract_node(self, node: dict, with_url_dl=False):
        video = node
        video_id = video.get("videoId")
        title = video["title"]
        description = video["shortDescription"]

        width = video.get("width", 0)
        height = video.get("height", 0)
        resolution = "%sx%s" % (width, height)
        upload_date = video.get("uploadDate", 0)
        timestamp = video.get("timestamp", 0)

        url = "https://www.youtube.com/watch?v=%s" % video_id
        duration = int(video.get("lengthSeconds", 0))

        thumbnail = "https://i.ytimg.com/vi_webp/%s/maxresdefault.webp" % video_id
        thumbnails = video.get("thumbnail", {}).get("thumbnails", [])

        keywords = video.get("keywords", [])
        channelId = video.get("channelId", "")
        channelName = video.get("author", "")

        stats = {
            "view_count": int(video.get("viewCount", 0)),
            "like_count": int(video.get("likeCount", 0)),
            "comment_count": int(video.get("commentCount", 0)),
            "share_count": int(video.get("shareCount", 0)),
        }
        isPrivate = video.get("isPrivate")
        isLiveContent = video.get("isLiveContent")

        user = {
            "id": channelId,
            "name": channelName,
            "username": channelId,
            "url": "https://www.youtube.com/channel/%s" % channelId,
            "channelUrl": "https://www.youtube.com/channel/%s" % channelId,
        }

        # user_keys = ["avatar_thumb","follower_count","total_favorited","sec_uid","unique_id_modify_time","cover_url"]
        update_user_info = {}
        # for key in user_keys:
        #   if user.get(key) is not None:
        #     if key == "avatar_thumb" and isinstance(user.get("avatar_thumb"), dict):
        #       update_user_info["avatar"] = user["avatar_thumb"].get("url_list", [""])[0]
        #     else:
        #       update_user_info[key] = user[key]

        info_dict = {
            "id": video_id,
            "display_id": video_id,
            "title": title,
            "fulltitle": title,
            "description": description,
            "thumbnail": thumbnail,
            "original_thumbnail": thumbnail,
            "thumbnails": thumbnails,
            "sd": "",
            "hd": "",
            "music": "",
            "requested_download": [{
                "title": title,
                "width": width,
                "height": height,
                "resolution": resolution,
                "url": url,
                # "video": unescape(video_hd),
            }],
            "keywords": keywords,
            "isPrivate": isPrivate,
            "isLiveContent": isLiveContent,
            "uploader": user.get("username") or channelId,
            "uploader_id": channelId,
            "uploader_url": user.get("url", "none"),
            "url": url,
            "original_url": url,
            "webpage_url": url,
            "webpage_url_domain": "youtube.com",
            "extractor": "youtube",
            "extractor_key": "YouTube",
            "width": width,
            "height": height,
            "resolution": resolution,
            "duration": duration,
            "timestamp": timestamp,
            "release_timestamp": timestamp,
            "upload_date": upload_date,
            **stats,
            "subtitles": [],
            "audio_only": [],
            "video_only": [],
            "both": [],
            "http_headers": {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': f'{self._BASE_URL}/',
                'Origin': self._BASE_URL,
            },
            "user_info": {
                **user,
                **update_user_info
            }
        }
        return info_dict

    def get_video_info(self, html: str, js: FunctionType = None):
        # with open("mobile_video_page.html", "w", encoding="utf-8") as f:
        #     f.write(html)
        user_info = {"id": "", "username": "",
                     "url": "", "avatar": "", "follower": ""}
        video_info = {
            'user_info': user_info,
        }
        visitor_data = None
        streaming_data = None
        html = str(html).replace("\\/", "/")
        if "var ytInitialData =" in html and "currentVideoEndpoint" in html:
            matches = re.search(
                r'(var\sytInitialData\s=\s)(.*?)(;<\/script>)', html)
            ytInitialData = [c for c in matches.groups(
            ) if 'currentVideoEndpoint' in c][0] if matches else None
            # if string_data:
            #     with open("mobile_ytInitialData.txt", "w", encoding="utf-8") as f:
            #         f.write(string_data)

            # ytInitialData = str(html).replace("\\/", "/")
            # content_decode = ytInitialData.encode('utf8').decode('unicode_escape')
            # content_decode = self.get_json_from_html(content_decode, "ytInitialData", 6, '"}}}};').strip() + '"}}}}'
            try:
                if "b\\x22responseContext\\x22:" in ytInitialData:
                    ytInitialData = ytInitialData.encode('utf8').decode(
                        'unicode_escape').lstrip("'").rstrip("'")
                # current_dir = Path(__file__).parent
                # # with open(current_dir.joinpath("mobile_ytInitialData.txt"), "w", encoding="utf-8") as f:
                # #     f.write(f"{ytInitialData}")
                content_dict = json.loads(ytInitialData)
                # video_info['ytInitialData'] = content_dict
                video_id = content_dict.get('currentVideoEndpoint', {}).get(
                    'watchEndpoint', {}).get('videoId')
                videoDescriptionInfoCard = next(search_dict(
                    content_dict, "videoDescriptionInfocardsSectionRenderer"))
                if 'runs' in videoDescriptionInfoCard.get("sectionSubtitle", {}):
                    subscribers = videoDescriptionInfoCard["sectionSubtitle"]["runs"][0]["text"].replace(
                        " subscribers", "")
                elif 'simpleText' in videoDescriptionInfoCard.get("sectionSubtitle", {}):
                    subscribers = videoDescriptionInfoCard["sectionSubtitle"]["simpleText"].replace(
                        " subscribers", "")

                avatar = videoDescriptionInfoCard["channelAvatar"]["thumbnails"][0]["url"]
                channelId = videoDescriptionInfoCard["channelEndpoint"]["browseEndpoint"].get(
                    "browseId")
                username = videoDescriptionInfoCard["channelEndpoint"]["browseEndpoint"].get(
                    "canonicalBaseUrl", "")
                username = username.replace(
                    "/@", "") if "@" in username else channelId

                # print(f"Extracted from ytInitialData - channelId: {channelId}, username: {username}, avatar: {avatar}, subscribers: {subscribers}")

                user_info.update(**{
                    "id": channelId,
                    "username": username,
                    "url": "https://www.youtube.com/%s" % (username if "@" in username else "channel/%s" % channelId),
                    "avatar": avatar,
                    "follower": str(subscribers).encode('latin1').decode('utf8')
                })
                visitor_data = content_dict.get('responseContext', {}).get(
                    'webResponseContextExtensionData', {}).get('ytConfigData', {}).get('visitorData')
                # print(f"Extracted visitorData: {visitor_data}")
            except Exception as err:
                self.logger.debug(f"Error ytInitialData: {err}")
                # continue

        if "var ytInitialPlayerResponse =" in html and "streamingData" in html:
            matches = re.search(
                r'(var\sytInitialPlayerResponse\s=\s{)(.*?)(;<\/script>)', html)
            # if matches:
            #     for i, c in enumerate(matches.groups()):
            #         c = c.strip()
            #         with open(f"mobile_ytInitialPlayerResponse_{i}.txt", "w", encoding="utf-8") as f:
            #             f.write("{" + c)
            ytInitialPlayerResponse = [
                "{" + c for c in matches.groups() if 'playerMicroformatRenderer' in c][0] if matches else None
            if ytInitialPlayerResponse:
                with open(current_dir.joinpath("_data", "__mobile_ytInitialPlayerResponse.txt"), "w", encoding="utf-8") as f:
                    f.write(ytInitialPlayerResponse)

            # ytInitialPlayerResponse = self.get_json_from_html(html, "ytInitialPlayerResponse", 6, '"}}}};').strip() + '"}}}}'
            # with open("mobile_ytInitialPlayerResponse.txt", "w", encoding="utf-8") as f:
            #         f.write(ytInitialPlayerResponse)
            try:
                if not ytInitialPlayerResponse.endswith("}}}}") and "}}}};var" in ytInitialPlayerResponse:
                    ytInitialPlayerResponse = ytInitialPlayerResponse.split("}}}};var")[
                        0] + "}}}}"
                ytResponseDict = json.loads(ytInitialPlayerResponse)
                video_details = ytResponseDict["videoDetails"]
                video_info = self.extract_node(video_details)
                # video_info['ytInitialPlayerResponse'] = ytResponseDict

                streaming_data = ytResponseDict.get("streamingData")

                microformat = ytResponseDict.get("microformat")
                if isinstance(microformat, dict) and isinstance(microformat.get("playerMicroformatRenderer"), dict):
                    vdo_details = microformat["playerMicroformatRenderer"]
                    try:
                        uploadDate = vdo_details.get(
                            "uploadDate") or vdo_details.get("publishDate")
                        timestamp = int(0)
                        if isinstance(uploadDate, str):
                            uploadDate = "-".join(uploadDate.split("-")
                                                  [0:3]).replace("T", " ")
                            timestamp = int(datetime.strptime(
                                uploadDate, '%Y-%m-%d %H:%M:%S').timestamp())

                        stats = {
                            "view_count": int(vdo_details.get("viewCount") or video_info.get("view_count", 0)),
                            "like_count": int(vdo_details.get("likeCount") or video_info.get("like_count", 0)),
                            "comment_count": int(vdo_details.get("commentCount") or video_info.get("comment_count", 0)),
                            "share_count": int(vdo_details.get("shareCount") or video_info.get("share_count", 0)),
                        }

                        video_info.update(**{
                            "thumbnail": vdo_details["thumbnail"]["thumbnails"][0]["url"],
                            "timestamp": timestamp,
                            "release_timestamp": timestamp,
                            "upload_date": uploadDate,
                            "uploader": user_info.get("username"),
                            "uploader_url": vdo_details["ownerProfileUrl"],
                            **stats
                        })
                        user_info.update(**{
                            "name": vdo_details["ownerChannelName"],
                            "url": vdo_details["ownerProfileUrl"],
                        })
                        video_info['user_info'].update(**user_info)
                    except Exception as err:
                        print("Error microformat ", err)
                        # continue

                try:
                    # print("visitor_data in extract_video_formats:", visitor_data)
                    # video_formats = extract_video_formats(
                    #     html, ytResponseDict, video_info, js, visitor_data, streaming_data)
                    video_formats = extract_video_formats(
                        html, ytResponseDict, video_info)
                    # print("ytInitialPlayerResponse error from this position - fix later")
                    vdo_downloads = video_formats.get("both", [])
                    audio_downloads = video_formats.get("audio_only")
                    if isinstance(vdo_downloads, list) and len(vdo_downloads) > 0:
                        vdo_downloads.sort(key=lambda x: x["height"])
                    len_vdo_downloads = len(vdo_downloads)
                    if len_vdo_downloads >= 2:
                        video_info["sd"] = vdo_downloads[len_vdo_downloads -
                                                         2].get("url", "")
                        video_info["hd"] = vdo_downloads[len_vdo_downloads -
                                                         1].get("url", "")
                    elif len_vdo_downloads > 0:
                        video_info["sd"] = vdo_downloads[0].get("url", "")
                        video_info["hd"] = vdo_downloads[0].get("url", "")

                    if len_vdo_downloads > 0:
                        req_download = vdo_downloads[len_vdo_downloads-1]
                        width = req_download.get("width", 0)
                        height = req_download.get("height", 0)
                        resolution = f"{width}x{height}"
                        video_info["width"] = width
                        video_info["height"] = height
                        video_info["resolution"] = resolution
                        video_info["requested_download"][0].update(**{
                            "width": width,
                            "height": height,
                            "resolution": resolution
                        })

                    if isinstance(audio_downloads, list) and len(audio_downloads) > 0:
                        video_info["music"] = audio_downloads[0].get("url", "")

                    video_info.update(**video_formats)
                    video_info["user_info"].update(**user_info)
                except ValueError as err:
                    self.logger.debug("error video format", err)

            except Exception as err:
                self.logger.debug("Error ytInitialPlayerResponse", err)
                # continue

        both = video_info.get('both', [])
        video_only = video_info.get('video_only', [])
        if isinstance(both, list) and len(both) > 0:
            video_info['both'] = sorted(both, key=lambda x: (
                x.get("height", 0)), reverse=True)
        if isinstance(video_only, list) and len(video_only) > 0:
            video_info['video_only'] = sorted(video_only, key=lambda x: (
                x.get("height", 0)), reverse=True)

        video_info['user_info'].update(**user_info)
        return video_info

    @staticmethod
    def _on_download_filename(index: int, title: str) -> str:
        suffix_name = f"_EP{index:02d}"
        _filename = safe_filename(
            title, max_length=255 - len(suffix_name)) + suffix_name + ".mp4"
        return _filename

    def get_selected_video_info(self, info: Dict[str, Any]):
        try:
            video_info = info['both'][0]
            video_url = video_info['url']
            for f in info['video_only']:
                width = f.get('width', 0)
                height = f.get('height', 0)
                resolution_compare = height if width >= height else width
                if f.get('ext') == 'mp4' and resolution_compare <= self.resolution:
                    self.logger.debug(f'resolution {resolution_compare}')
                    video_url = f['url']
                    video_info = f
                    break
        except Exception as err:
            self.logger.debug(f'Error getting selected video info: {err}')
            video_info = info.get('both', [])[0]
        return video_info

    def get_video_url_play(self, info: Dict[str, Any]):
        video_info = self.get_selected_video_info(info)
        return video_info.get('url', '')

    async def _download_all_videos(
        self,
        downloader: "AsyncTSVideoDownloader",
        info_list: List[Dict[str, Any]],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        with_channel_name: bool = False,
        overwrite: bool = True,
        batch_size: int = 10,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        downloader_settings_callback: Optional[Callable[[
            "AsyncTSVideoDownloader"], None]] = None,
        is_test=False
    ):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Sec-Fetch-Mode": "navigate",
            "Connection": "keep-alive",
            "Referer": f"{self._BASE_URL}/",
            "Origin": self._BASE_URL,
        }
        # downloader.custom_temp_segments_dir_name = _safe_title
        downloader.session = self.session
        # downloader.session.headers.clear()
        downloader.session.headers.update(headers)
        downloader.https_headers = headers
        downloader.https_impersonate = "chrome120"
        downloader.chunk_size = self.chunk_size * 10
        # User download folder
        _output_dir = self.set_output_dir(output_dir, with_site_name)

        if with_channel_name:
            user_info = info_list[0]['user_info']
            channel_name = user_info.get('username') or user_info.get(
                'name') or user_info.get('id', 'Unknown')
            _safe_channel_name = safe_filename(channel_name)
            _output_dir = _output_dir.joinpath(_safe_channel_name)

        if downloader_settings_callback and callable(downloader_settings_callback):
            downloader_settings_callback(downloader)

        url_list = []
        filename_list = []
        info_list = info_list[0:1] if is_test else info_list

        from yt_dlp import YoutubeDL
        _opts = {
            # 'write_thumbnail': self.download_with_thumbnail,
            'quiet': True,
            'overwrites': True,
            'http_chunk_size': 10485760,
            'no_part': True,
            'no_warnings': True,
        }
        for info in info_list:
            video_info = self.get_selected_video_info(info)
            self.logger.info(f"url: {video_info.get('url', '')}")
            url_list.append(video_info.get('url', ''))
            title = info['title']
            _filename = safe_filename(title) + ".mp4"
            filename_list.append(_filename)

        def _progress_callback(d: ProgressData):
            self.logger.info(
                f"downloaded: {format_bytes(d.downloaded)} | speed: {format_bytes(int(d.speed))}")

        for attempt in range(max_attempts):
            self.logger.info(
                f"\nDownload attempt {attempt + 1}/{max_attempts}")

            # Try with different concurrency settings on retry
            if attempt == 1:
                downloader.max_concurrent = 3  # Reduce concurrency on retry
            elif attempt == 2:
                downloader.max_concurrent = 1  # Sequential on last retry

            # result = []
            # for info in info_list:
            #     video_info = self.get_selected_video_info(info)
            #     url = video_info.get('url', '')
            #     self.logger.info(f"url: {url}")
            #     title = info['title']
            #     _filename = safe_filename(title) + ".mp4"
            #     ydl_opts = {
            #         **_opts,
            #         # 'progress_hooks': [progress_hook],
            #         'outtmpl': str(_output_dir.joinpath(_filename)),
            #         'http_chunk_size': self.chunk_size,
            #     }
            #     with YoutubeDL(ydl_opts) as ydl:
            #         _info = ydl.extract_info(url, download=True)
            #         if _info:
            #             result.append(_info)
            #         else:
            #             self.logger.error(f"❌ Error downloading video: {url}")

            result = await downloader.download_playlist(
                url_list,
                output_dir=str(_output_dir),
                filename_list=filename_list,
                overwrite=overwrite,
                use_parallel=True,
                batch_mode=True,
                batch_size=batch_size,
                progress_callback=_progress_callback,
                stream=True
            )

            if isinstance(result, list):
                self.logger.info("✅ Download completed successfully!")
                # self.save_test_data(result, '_list')
                return result
            else:
                self.logger.error(f"❌ Error downloading videos")

            self.logger.info(
                f"Attempt {attempt + 1} failed, retrying in {5 * (attempt + 1)} seconds...")
            await asyncio.sleep(5 * (attempt + 1))

        self.logger.info("All download attempts failed")
        return False


class YouTubeExtractor(YouTubeBaseIE):

    def __init__(self, proxies: Optional[List[str]] = None, impersonate: BrowserTypeLiteral = "chrome", timeout: int = 30):
        super().__init__(proxies, impersonate, timeout)

        self.concurrent_tasks = 10  # Limit concurrent tasks to avoid rate limiting
        self.delay_jitter = False  # Disable human-like delay by default

    @staticmethod
    def load_youtube_cookies(raw_cookie: str):
        """Parses a Netscape cookies.txt file into a dictionary."""
        cookies = {}
        for line in raw_cookie.splitlines():
            if not line.startswith('#') and line.strip():
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    # Name is at index 5, Value at index 6
                    cookies[parts[5]] = parts[6]
        return cookies

    # --- Core Request Methods ---

    async def get_initial_data(self, url: str):
        if self.delay_jitter:
            # Human-like delay (Jitter) to avoid pattern detection
            await asyncio.sleep(random.uniform(1.5, 4.0))
        # Every time we hit a new page, we can rotate the proxy
        self.session.cookies.set("CONSENT", "YES+cb", domain=".youtube.com")

        response = await self.request(
            url,
        )
        if isinstance(response, Response) and response.status_code == 200:
            return response.text
        return None

    async def get_initial_data_mobile(self, url: str, impersonate="chrome131_android"):
        if self.delay_jitter:
            # Human-like delay (Jitter) to avoid pattern detection
            await asyncio.sleep(random.uniform(1.5, 4.0))
        # Every time we hit a new page, we can rotate the proxy
        # proxy = self._get_proxy_dict()

        # raw_cookie = ''
        # self.cookies_mobile = self.load_youtube_cookies(raw_cookie)
        # self.cookies_mobile = None
        # cookies = self.parse_cookie_string(cookie)

        response = await self.request(
            url,
            # cookies=self.cookies_mobile,
            impersonate=impersonate
        )
        if isinstance(response, Response) and response.status_code == 200:
            return response.text
        return None

    async def get_ajax_data(
        self,
        api_endpoint: str,
        api_key: str,
        next_data: dict,
        client: dict
    ):

        payload = {
            "context": {"clickTracking": next_data["click_params"], "client": client},
            "continuation": next_data["token"],
        }

        response = await self.request(
            api_endpoint,
            method="POST",
            params={"key": api_key},
            json_data=payload,
        )

        if isinstance(response, Response) and response.status_code == 200:
            return response.json()
        return {}

    def get_next_data(self, data: dict, sort_by: Optional[str] = None) -> Optional[dict]:
        sort_by_map = {"newest": 0, "popular": 1, "oldest": 2}
        try:
            if sort_by and sort_by != "newest":
                chip_bar = next(search_dict(
                    data, "feedFilterChipBarRenderer"), None)
                contents = chip_bar["contents"]  # type: ignore
                endpoint = contents[sort_by_map[sort_by]
                                    ]["chipCloudChipRenderer"]["navigationEndpoint"]
            else:
                endpoint = next(search_dict(
                    data, "continuationEndpoint"), None)

            if not endpoint:
                return None

            return {
                "token": endpoint["continuationCommand"]["token"],
                "click_params": {"clickTrackingParams": endpoint["clickTrackingParams"]},
            }
        except:
            return None

    # --- High Level API Methods ---

    async def get_playlist(self, playlist_id: str, limit: Optional[int] = None, sleep: int = 1) -> AsyncGenerator[dict, None]:
        """Async Generator for Playlist items."""
        url = f"https://www.youtube.com/playlist?list={playlist_id}"
        api_endpoint = "https://www.youtube.com/youtubei/v1/browse"
        async for video in self.get_videos(url, api_endpoint, "playlistVideoRenderer", limit, sleep):
            yield video

    async def get_search(
        self, query: str, limit: Optional[int] = None, sleep: int = 1,
        sort_by: str = "relevance", results_type: str = "video"
    ) -> AsyncGenerator[dict, None]:
        """Async Generator for Search results."""
        sort_by_map = {"relevance": "A", "upload_date": "I",
                       "view_count": "M", "rating": "E"}
        res_type_map = {
            "video": ["B", "videoRenderer"],
            "channel": ["C", "channelRenderer"],
            "playlist": ["D", "playlistRenderer"],
            "movie": ["E", "videoRenderer"],
        }
        param = f"CA{sort_by_map[sort_by]}SAhA{res_type_map[results_type][0]}"
        url = f"https://www.youtube.com/results?search_query={query}&sp={param}"
        api_endpoint = "https://www.youtube.com/youtubei/v1/search"

        async for item in self.get_videos(url, api_endpoint, res_type_map[results_type][1], limit, sleep):
            yield item

    # --- Main Extractor Logic ---

    async def get_video(self, video_id: str):
        """Fetches detailed info for a single video ID."""
        url = self._LINK_ID % video_id
        html = await self.get_initial_data(url)

        if not html:
            return None

        client_json = json.loads(get_json_from_html(
            html, "INNERTUBE_CONTEXT", 2, '"}},') + '"}}')
        client = client_json["client"]

        # Temporary header update for this request
        self.session.headers.update({
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": client["clientVersion"]
        })

        data = json.loads(get_json_from_html(
            html, "var ytInitialData = ", 0, "};") + "}")
        return next(search_dict(data, "videoPrimaryInfoRenderer"), {})

    async def get_videos(
        self, url: str,
        api_endpoint: str,
        selector: YouTubeSortBy.VideoType,
        limit: Optional[int],
        sleep: int,
        sort_by: Optional[YouTubeSortBy.ChannelVideos] = None,
        next_data: Optional[dict] = None,
        cursor_position: int = 0,
        use_per_next_cursor: bool = False,
    ):

        is_first = False if isinstance(
            next_data, dict) and next_data.get('token') else True
        count = 0

        cursor_position = int(cursor_position) if isinstance(cursor_position, int) \
            else int(0)

        # html = await self.get_initial_data(url)
        html = self.load_text_data()

        if not html:
            return

        # self.save_html_text(html)
        # Extraction
        client = json.loads(get_json_from_html(
            html, "INNERTUBE_CONTEXT", 2, '"}},') + '"}}')["client"]
        api_key = get_json_from_html(html, "innertubeApiKey", 3)

        self.session.headers.update({
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": client["clientVersion"]
        })

        data = json.loads(get_json_from_html(
            html, "var ytInitialData = ", 0, "};") + "}")

        # Channel Metadata Extraction
        info_list = []
        user_info = None
        try:
            data_user = next(search_dict(data, "channelMetadataRenderer"))
            user_info = {
                "id": data_user.get("externalId"),
                "name": data_user.get("title"),
                "desc": data_user.get("description"),
                "url": data_user.get("vanityChannelUrl", data_user.get("channelUrl", "")),
                "avatar": data_user.get("avatar", {}).get("thumbnails", [{}])[0].get("url", ""),
                "rssUrl": data_user.get("rssUrl"),
            }
        except:
            pass

        while True:
            if self.cancel:
                break

            if limit and len(info_list) >= limit:
                break

            if is_first:
                next_data = self.get_next_data(data, sort_by)
                is_first = False
                if sort_by and sort_by != "newest":
                    continue
            else:
                data = await self.get_ajax_data(api_endpoint, api_key, next_data, client)
                next_data = self.get_next_data(data)

            if "contents" in data:
                try:
                    tabs = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
                    contents = None
                    for tab in tabs:
                        tabRenderer = tab["tabRenderer"]
                        if "selected" in tabRenderer and tabRenderer["selected"]:
                            contents = tabRenderer["content"]["richGridRenderer"]["contents"]
                            break
                    if isinstance(contents, list):
                        for content in contents:
                            lockupViewModel = next(
                                search_dict(content, "lockupViewModel"))
                            video_id = lockupViewModel.get("contentId")
                            if not video_id:
                                video_id = next(search_dict(
                                    lockupViewModel, 'reelWatchEndpoint'), {}).get('videoId')
                            thumbnails = next(search_dict(
                                lockupViewModel['contentImage'], "sources"))
                            title = next(search_dict(lockupViewModel['metadata'], "title"), {}).get(
                                "content", "")

                            _info = {
                                "id": video_id,
                                "title": title,
                                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                                "thumbnails": thumbnails,
                                "url": self._LINK_ID % video_id,
                            }
                            if isinstance(user_info, dict) and next_data:
                                _info.update({
                                    "uploader": user_info.get("name") if user_info else "",
                                    "uploader_id": user_info.get("id") if user_info else "",
                                    "extractor": "youtube",
                                    "user_info": user_info,
                                    "next_data": next_data,
                                    "cursor_position": cursor_position
                                    # "string_next_data": quote(dict_to_query_string(next_data))
                                })
                            info_list.append(_info)
                            self.on_extracting({
                                "status": "progress",
                                "data": _info
                            })

                except Exception as e:
                    self.logger.debug(f"Failed to extract video metadata: {e}")
            else:
                for result in search_dict(data, selector):
                    count += 1

                    # Logic for Video ID and Reel fallback
                    video_id = result.get('videoId')
                    self.logger.debug(f"video_id: {video_id}")
                    if not video_id:
                        video_id = next(search_dict(
                            result, 'reelWatchEndpoint'), {}).get('videoId')

                    if isinstance(user_info, dict) and next_data:
                        next_data.update({"videoId": video_id or ''})
                        result.update({
                            "videoId": video_id or '',
                            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                            "url": self._LINK_ID % (video_id or ''),
                            "extractor": "youtube",
                            "uploader": user_info.get("name") if user_info else "",
                            "uploader_id": user_info.get("id") if user_info else "",
                            "user_info": user_info,
                            "next_data": next_data,
                            "cursor_position": cursor_position
                            # "string_next_data": quote(dict_to_query_string(next_data))
                        })

                    self.on_extracting({
                        "status": "progress",
                        "data": result
                    })
                    info_list.append(result)

            if not isinstance(limit, int) and use_per_next_cursor:
                break
            if not next_data:
                break
            cursor_position += 1
            await asyncio.sleep(sleep)

        return info_list

    async def get_channel_videos(
        self,
        channel_url: str,
        content_type: YouTubeSortBy.VideoType = "videos",
        limit: Optional[int] = None,
        sort_by: YouTubeSortBy.ChannelVideos = "newest",
        next_data: Optional[dict] = None,
        cursor_position: int = 0,
        use_per_next_cursor: bool = False,
    ):
        url = f"{channel_url}/{content_type}"
        return await self.get_videos(
            url,
            "https://www.youtube.com/youtubei/v1/browse",
            content_type or 'videos',
            limit,
            1,
            sort_by,
            next_data,
            cursor_position,
            use_per_next_cursor,
        )

    async def get_video_info_list(
        self, url_list: list[str],
    ):
        # Use a Semaphore to control how many tasks run at once
        semaphore = asyncio.Semaphore(self.concurrent_tasks)
        if len(url_list) > 15:
            self.delay_jitter = True  # Enable delay jitter for large batches to avoid rate limiting

        tasks = []
        valid_url_list = []
        async with semaphore:
            for url in url_list:
                if self.cancel:
                    self.on_extracting({"status": "cancelled"})
                    break
                url = self.get_video_url(url, True)
                valid_url_list.append(url)
                tasks.append(self.get_initial_data(url))

        html_list = await asyncio.gather(*tasks)
        video_info_list = []
        for i, html in enumerate(html_list):
            try:
                if self.cancel:
                    self.on_extracting({"status": "cancelled"})
                    break
                self.save_html_text(html, "_m")
                # def fetch_js(js_url):
                #     try:
                #         resp = self.request_sync(js_url)
                #         if isinstance(resp, Response) and resp.status_code == 200:
                #             return resp.text
                #         return None
                #     except Exception as err:
                #         self.logger.error(
                #             f"[YouTube] Error fetching JS for video {valid_url_list[i]}: {err}")
                #         return None

                video_info = self.get_video_info(html)
                self._on_extracting({
                    "status": "progress",
                    "url": valid_url_list[i],
                    "data": video_info
                })
                video_info_list.append(video_info)
            except Exception as err:
                self.logger.error(
                    f"[YouTube] Error processing video info for URL {valid_url_list[i]}: {err}")
                self._on_extracting(
                    {"error": str(err), "url": valid_url_list[i], "status": "error"})
                continue

        return video_info_list

    async def download_all_videos(
        self,
        info_list: List[Dict[str, Any]],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        with_channel_name: bool = False,
        overwrite: bool = True,
        batch_size: int = 10,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False
    ):
        downloader = AsyncTSVideoDownloader(max_concurrent=5)
        return await self._download_all_videos(
            downloader,
            info_list,
            output_dir=output_dir,
            with_site_name=with_site_name,
            with_channel_name=with_channel_name,
            overwrite=overwrite,
            batch_size=batch_size,
            max_attempts=max_attempts,
            progress_callback=progress_callback,
            is_test=is_test
        )

    async def test_get_video_info_list_from_user(self):
        self._skip_cached_info = True
        url = self._LINK_USERNAME % '1MinuteMotivation'
        self.logger.debug(f"Video URL: {url}")

        info_list = await self.get_channel_videos(url, use_per_next_cursor=True)
        if info_list:
            # previous_data = self.load_test_data('_user')
            # if previous_data:
            #     info_list = previous_data + info_list
            self.logger.debug(f"Total videos: {len(info_list)} video")
            self.save_test_data(info_list, '_user')
        return info_list

    async def test_get_video_info_list(self):
        self._skip_cached_info = True
        url = self._LINK_ID % self._TEST_VIDEO_ID
        video_id = self.get_video_id(url)
        self.logger.debug(f"Video URL: {url}, {video_id}")
        # info_list = await self.get_video_info_list([url])
        info_list = self.load_test_data()
        if info_list:
            for info in info_list:
                selected_info = self.get_selected_video_info(info)
                info["selected_info"] = selected_info
            self.save_test_data(info_list)
        return info_list
