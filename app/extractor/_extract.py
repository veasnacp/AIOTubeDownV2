import asyncio
import re
from pathlib import Path
from typing import Any, Literal, TypeAlias
from urllib.parse import unquote, urlparse

# from .douyin import DouyinExtractor
# from .facebook import FacebookExtractor
# from .instagram import InstagramExtractor
# from .kuaishou import KuaishouExtractorMore, KuaishouExtractor
# from .tiktok import TikTokExtractor
from .youtube import YouTubeExtractor

# from .douyin import DouyinExtractor

FixExtractKeyProfileList: TypeAlias = Literal[
    "youtube_channel", "youtube_playlist",
    "facebook", "instagram",
    "tiktok"
]
AIODownloaderOptions = [
    "download_type", "resolution",
    "download_audio", "filename", "folderpath", "yt_opts",
    "add_download_options"
]
AIODownloaderType: TypeAlias = Literal[
    # "download",
    "download_type", "resolution",
    "download_audio",
    "filename",
    "folderpath",
    "yt_opts",
    "limit",
    "sort_by",
    "youtube_video_type",
    "facebook_extract_server",
    "tiktok_extract_server",
    "kuaishou_cookie",
    "youtube_string_next_data",
    "youtube_cursor_continue",
    "instagram_cursor_continue",
    "tiktok_cursor_continue",
    "facebook_extractor",
    "tiktok_extractor",
    "kuaishou_extractor",
    "is_on_web",
]


def isYouTube(url):
    parse = urlparse(url)
    return "youtube.com" in parse.netloc or "youtu.be" in parse.netloc


class AIODownloader:
    def __init__(
        self,
        download_options: dict[AIODownloaderType, Any] = None,
        # content_type:YouTubeSortBy.VideoType="videos",
        # tiktok_extract_server:str="1",
    ) -> None:

        self.download_options: dict[AIODownloaderType, Any] = {
            "is_on_web": False
        }
        if isinstance(download_options, dict):
            for key, val in download_options.items():
                if download_options.get(key) is not None:
                    self.download_options[key] = val

        self.is_stopped = False

    def download_config(self):
        pass
        # def dl_options(key:AIODownloaderType, default_val=None):
        #   return download_options[key] if download_options.get(key) is not None else default_val

        # self.download_options = {
        #   "download_type": dl_options("download_type"),
        #   "resolution": dl_options("resolution"),
        #   "download_audio": dl_options("download_audio"),
        #   "filename": dl_options("filename"),
        #   "folderpath": dl_options("folderpath"),
        #   "yt_opts": dl_options("yt_opts"),
        #   "limit": dl_options("limit"),
        #   "sort_by": dl_options("sort_by", "newest"),
        # }

    def callback_progress(self, ydl: YouTubeExtractor):
        def on_extracting(obj: Any):
            ydl.cancel = self.is_stopped
            self.on_extracting(obj)

        ydl.on_extracting = on_extracting

    def on_extracting(self, obj: Any):
        pass

    def get_videos_youtube_channel(self, url_list):
        ydl = YouTubeExtractor()
        self.callback_progress(ydl)
        ydl.string_next_data = self.download_options.get(
            "youtube_string_next_data") or self.download_options.get("youtube_cursor_continue", None)
        extract_options = {
            "content_type": self.download_options.get("youtube_video_type", "videos"),
            "use_per_next_cursor": self.download_options.get("use_per_next_cursor", False),
            "string_next_data": self.download_options.get("string_next_data", None),
            "extractor": self.download_options.get("youtube_extractor_video", "default"),
            "sleep": 1,
            "only_url_dl": self.download_options.get('only_url_dl', False) == True,
        }
        for key in ["limit", "sort_by", "only_original_url_from_profile"]:
            if self.download_options.get(key) is not None:
                extract_options[key] = self.download_options[key]

        video_list = ydl.extract_videos_from_multiple_channel(
            url_list, **extract_options
        )
        return video_list if video_list else []

    def get_videos_youtube_playlist(self, url_list):
        ydl = YouTubeExtractor()
        self.callback_progress(ydl)
        extract_options = {
            "sleep": 1,
            "only_url_dl": self.download_options.get('only_url_dl', False) == True,
        }
        for key in ["limit", "only_original_url_from_profile"]:
            if self.download_options.get(key) is not None:
                extract_options[key] = self.download_options[key]

        video_list = ydl.extract_videos_from_multiple_playlist(
            url_list, **extract_options
        )

        return video_list if video_list else []

    def get_videos_instagram_profile(self, url_list):
        idl = InstagramExtractor()
        self.callback_progress(idl)
        extract_options = {
            "cursor_continue": self.download_options.get("cursor_continue") or self.download_options.get("instagram_cursor_continue", None),
            "use_per_next_cursor": self.download_options.get("use_per_next_cursor", False),
            "only_url_dl": self.download_options.get('only_url_dl', False) == True,
        }
        for key in ["limit", "sort_by"]:
            if self.download_options.get(key) is not None:
                extract_options[key] = self.download_options[key]

        video_list = idl.extract_videos_from_multiple_user(
            url_list, **extract_options
        )

        return video_list if video_list else []

    def get_videos_tiktok_profile(self, url_list):
        server = self.download_options.get("tiktok_extract_server", "default")
        tdl = TikTokExtractor(server)
        self.callback_progress(tdl)
        extract_options = {
            "cursor_continue": self.download_options.get("cursor_continue") or self.download_options.get("tiktok_cursor_continue", ''),
            "use_per_next_cursor": self.download_options.get("use_per_next_cursor", False),
            "only_url_dl": self.download_options.get('only_url_dl', False) == True,
        }
        for key in ["limit", "sort_by"]:
            if self.download_options.get(key) is not None:
                extract_options[key] = self.download_options[key]

        video_list = tdl.extract_videos_from_multiple_user(
            url_list, **extract_options
        )

        return video_list if video_list else []

    def facebook_sever(self):
        server = self.download_options.get("facebook_extract_server", None)
        # server = server if isinstance(server, str) else None
        return server

    def get_videos_facebook_profile(self, url_list):
        server = self.facebook_sever()
        fdl = FacebookExtractor(server)
        self.callback_progress(fdl)
        extract_options = {
            "content_type": self.download_options.get("youtube_video_type", "videos"),
            "extractor": self.download_options.get("facebook_extractor", "default"),
            "chunks": self.download_options.get("facebook_extractor_chunks", None),
            "cursor_continue": self.download_options.get("cursor_continue") or self.download_options.get("facebook_cursor_continue", ""),
            "use_per_next_cursor": self.download_options.get("use_per_next_cursor", False),
            "only_url_dl": self.download_options.get('only_url_dl', False) == True,
        }
        for key in ["limit", "sort_by", "only_original_url_from_profile"]:
            if self.download_options.get(key) is not None:
                extract_options[key] = self.download_options[key]

        video_list = fdl.extract_videos_from_multiple_user(
            url_list, **extract_options
        )

        return video_list if video_list else []

    def get_videos_douyin_profile(self, url_list):
        ddl = DouyinExtractor()
        self.callback_progress(ddl)
        extract_options = {
            "is_headless": True,
            "only_url_dl": self.download_options.get('only_url_dl', False) == True,
        }
        for key in ["limit", "sort_by", "only_url_dl", "douyin_goto_url", "douyin_is_headless"]:
            if self.download_options.get(key) is not None:
                if "douyin_is_headless" in key:
                    extract_options["is_headless"] = self.download_options[key]
                else:
                    extract_options[key] = self.download_options[key]

        video_list = ddl.extract_videos_from_multiple_user(
            url_list, **extract_options
        )
        return video_list if video_list else []

    def get_videos_kuaishou_profile(self, url_list):
        server = self.download_options.get("kuaishou_server", "1")
        cookies = self.download_options.get("kuaishou_cookie", None)
        cookies = cookies if isinstance(
            cookies, str) and cookies != "" else None
        mobile_cookies = self.download_options.get(
            "kuaishou_mobile_cookie", None)
        user_share_url = self.download_options.get(
            "kuaishou_user_share_url", None)
        video_share_url = self.download_options.get(
            "kuaishou_video_share_url", None)
        cursor_continue = self.download_options.get(
            "cursor_continue") or self.download_options.get("kuaishou_cursor_continue", None)
        is_headless = self.download_options.get("kuaishou_is_headless", True)

        kdl = KuaishouExtractorMore(
            cookies, mobile_cookies, user_share_url, video_share_url, cursor_continue, is_headless)
        self.callback_progress(kdl)
        extract_options = {
            "only_url_dl": self.download_options.get('only_url_dl', False) == True,
        }
        for key in ["limit", "sort_by", "only_url_dl"]:
            if self.download_options.get(key) is not None:
                extract_options[key] = self.download_options[key]

        # video_list = kdl.extract_videos_from_multiple_user_cookie(
        #   url_list,**extract_options
        # )
        video_list = None
        cursor_continue = cursor_continue or ''
        use_per_next_cursor = self.download_options.get(
            "use_per_next_cursor", False)
        use_extract_url_dl = self.download_options.get(
            "kuaishou_use_extract_url_dl", None)
        extractor = self.download_options.get(
            "kuaishou_extractor_user", "default")
        extract_options["cursor_continue"] = cursor_continue
        extract_options["use_per_next_cursor"] = use_per_next_cursor
        extract_options["use_extract_url_dl"] = use_extract_url_dl
        extract_options["extractor"] = extractor

        if video_list is None:
            video_list = kdl.extract_videos_from_multiple_user(
                url_list, **extract_options
            )

        return video_list if video_list else []

    ###
    # Combine All Videos
    ###
    def fix_extract_url_profile_list(
        self,
        profile_url_list: list[str],
    ) -> dict[FixExtractKeyProfileList, list[str]]:
        yt_channel = []
        yt_playlist = []
        insta_profile = []
        tiktok_profile = []
        facebook_profile = []
        kuaishou_profile = []
        douyin_profile = []

        for url in profile_url_list:
            url = url.strip()
            if "youtube.com" in url or "youtu.be" in url:
                if "youtube.com/@" in url or "youtube.com/channel" in url:
                    yt_channel.append(url)
                elif "playlist?list=" in url or ("&list=" in url and "watch?v=" in url):
                    yt_playlist.append(url)
            if "instagram.com" in url:
                insta_profile.append(url)
            if "tiktok.com" in url:
                tiktok_profile.append(url)
            if "facebook.com" in url:
                facebook_profile.append(url)
            if "kuaishou.com" in url:
                kuaishou_profile.append(url)
            if "douyin.com" in url:
                douyin_profile.append(url)

        all_profile_url_list = {
            "youtube_channel": yt_channel,
            "youtube_playlist": yt_playlist,
            "instagram": insta_profile,
            "tiktok": tiktok_profile,
            "facebook": facebook_profile,
            "kuaishou": kuaishou_profile,
            "douyin": douyin_profile,
        }

        # for i, profile_list in enumerate(all_url_profile_list):
        #   if len(profile_list) > 0:
        #     pass
        return all_profile_url_list

    def get_all_videos_from_multiple_profile(self, profile_url_list) -> list[str]:
        all_profile_url_list = self.fix_extract_url_profile_list(
            profile_url_list)

        # all_profile_url_list["instagram"]
        all_video_list = []
        for key, video_list in all_profile_url_list.items():
            has_link = len(video_list) > 0
            if "youtube_channel" in key and has_link:
                youtube_video_list = self.get_videos_youtube_channel(
                    video_list)
                all_video_list.append(youtube_video_list)
            elif "youtube_playlist" in key and has_link:
                youtube_video_playlist = self.get_videos_youtube_playlist(
                    video_list)
                all_video_list.append(youtube_video_playlist)
            elif "instagram" in key and has_link:
                instagram_video_list = self.get_videos_instagram_profile(
                    video_list)
                all_video_list.append(instagram_video_list)
            elif "tiktok" in key and has_link:
                tiktok_video_list = self.get_videos_tiktok_profile(video_list)
                all_video_list.append(tiktok_video_list)
            elif "facebook" in key and has_link:
                facebook_video_list = self.get_videos_facebook_profile(
                    video_list)
                all_video_list.append(facebook_video_list)
            elif "kuaishou" in key and has_link:
                kuaishou_video_list = self.get_videos_kuaishou_profile(
                    video_list)
                all_video_list.append(kuaishou_video_list)
            elif "douyin" in key and has_link:
                douyin_video_list = self.get_videos_douyin_profile(video_list)
                all_video_list.append(douyin_video_list)

        # print(all_video_list)
        return sum(all_video_list, [])

    def download_multi_videos_info(
        self,
        url_vid_list: list[str],
        download=False,
        playlist_or_profile="",
        with_url_dl=True
    ):
        download_options = {
            "playlist_or_profile": playlist_or_profile,
            # window Downloads folder path as default, can be changed by user input or custom path
            "folderpath": (Path.home() / "Downloads").as_posix(),
        }
        key_opt = AIODownloaderOptions
        for key in key_opt:
            if self.download_options.get(key) is not None:
                if 'folderpath' in key:
                    download_options['folderpath'] = Path(
                        self.download_options[key]).as_posix()
                else:
                    download_options[key] = self.download_options[key]

        add_download_options = self.download_options["add_download_options"]
        use_logfile = add_download_options.get("use_logfile", True)
        custom_logfile = add_download_options.get("custom_logfile")
        # times_of_download = add_download_options.get("times_of_download")
        enable_generic_url = add_download_options.get(
            "enable_generic_url", True)

        # print(download_options)
        video_list = []
        generic_video_list = []
        youtube_video_list = []
        facebook_video_list = []
        instagram_video_list = []
        tiktok_video_list = []
        douyin_video_list = []
        kuaishou_video_list = []
        is_generic = False
        for url in url_vid_list:
            url_parse = urlparse(url)
            is_generic = "&download_with_info_dict=" in url_parse.query
            is_youtube = isYouTube(url)
            facebook_path = url.split("facebook.com")[
                1] if "facebook.com" in url_parse.netloc in url else ""
            is_facebook = "/videos/" in facebook_path or "/watch" in facebook_path or "/reel/" in facebook_path or (
                "?story_fbid=" in facebook_path or "/posts/pfbid" in facebook_path)
            is_instagram = "instagram.com" in url_parse.netloc and (
                "instagram.com/p/" in url or "instagram.com/reel/" in url or "instagram.com/reels/" in url)
            tiktok_path = url.split("tiktok.com")[
                1] if "tiktok.com" in url_parse.netloc else None
            if tiktok_path:
                tiktok_path = tiktok_path.split("?")[0]
                tiktok_path = tiktok_path[:-
                                          1] if tiktok_path.endswith("/") else tiktok_path
                split_tt_path = tiktok_path.replace("/@", "").split("/")
                is_tiktok = "/@" in tiktok_path and len(split_tt_path) > 1
            else:
                is_tiktok = False

            is_kuaishou = "kuaishou.com" in url_parse.netloc and url_parse.path.startswith(
                '/short-video')
            is_douyin = "douyin.com" in url_parse.netloc and url_parse.path.startswith(
                '/video')

            if is_youtube and not is_generic:
                youtube_video_list.append(url)
            if is_tiktok and not is_generic:
                tiktok_video_list.append(url)
            if is_instagram and not is_generic:
                instagram_video_list.append(url)
            if is_facebook and not is_generic:
                facebook_video_list.append(url)
            if is_douyin and not is_generic:
                douyin_video_list.append(url)
            if is_kuaishou and not is_generic:
                kuaishou_video_list.append(url)
            if is_generic:
                generic_video_list.append(url)
            elif not (is_youtube or is_facebook or is_douyin or is_kuaishou or is_instagram or is_tiktok):
                video_list.append(url)

        # print("generic_video_list", generic_video_list)

        generic_video_info_list = []
        youtube_video_info_list = []
        facebook_video_info_list = []
        instagram_video_info_list = []
        tiktok_video_info_list = []
        douyin_video_info_list = []
        kuaishou_video_info_list = []

        if len(youtube_video_list) > 0:
            ydl = YouTubeExtractor()
            self.callback_progress(ydl)
            extractor = self.download_options.get(
                "youtube_extractor_video", "default")
            custom_cpu = self.download_options.get(
                "youtube_extractor_custom_cpu", None)
            if extractor == "yt-dlp":
                youtube_video_info_list = ydl.extract_info_video_list_localhost_async_run(
                    youtube_video_list, with_url_dl)
            else:
                youtube_video_info_list = ydl.extract_video_info_list_from_mobile_run(
                    youtube_video_list, with_url_dl)

        if len(tiktok_video_list) > 0:
            tdl = TikTokExtractor()
            self.callback_progress(tdl)
            # tiktok_video_info_list = asyncio.run(
            #   tdl.extract_video_info_list(tiktok_video_list)
            # )
            tiktok_video_info_list = tdl.extract_video_list_from_other_run(
                tiktok_video_list, with_url_dl)
            # tiktok_video_info_list = tdl.extract_video_info_list_mobile_api_sln_all(tiktok_video_list, with_url_dl)

        if len(instagram_video_list) > 0:
            csrf_token = self.download_options.get('instagram_cookie', None)
            extractor = self.download_options.get(
                "instagram_extractor_video", "default")
            idl = InstagramExtractor(csrf_token)
            self.callback_progress(idl)
            if isinstance(extractor, str) and extractor == "default":
                if len(instagram_video_list) <= 100:
                    instagram_video_info_list = idl.extract_video_info_list_run(
                        instagram_video_list, with_url_dl)
                    if idl.require_login is True:
                        print("instagram require_login")
                        instagram_video_info_list = idl.extract_video_info_list_all_run(
                            instagram_video_list, with_url_dl)
                else:
                    instagram_video_info_list = idl.extract_video_info_list_all_run(
                        instagram_video_list, with_url_dl)
            else:
                instagram_video_info_list = idl.extract_video_info_list_sln(
                    instagram_video_list, with_url_dl)

            # print("instagram_video_info_list", instagram_video_info_list)
            # if len(instagram_video_info_list) <= 0:
            #   instagram_video_info_list = asyncio.run(
            #   idl.extract_video_info_list_sln(instagram_video_list, with_url_dl)
            # )

        if len(facebook_video_list) > 0:
            server = self.facebook_sever()
            custom_cpu = self.download_options.get(
                "facebook_extractor_custom_cpu", None)
            chunks = self.download_options.get(
                "facebook_extractor_chunks", None)
            fdl = FacebookExtractor(server)
            self.callback_progress(fdl)
            # facebook_video_info_list = fdl.extract_info_video_list(facebook_video_list, with_url_dl, custom_cpu)
            if fdl.server == "default":
                facebook_video_info_list = asyncio.run(
                    fdl.extract_video_list_from_graphql(facebook_video_list, with_url_dl, chunks))
            else:
                facebook_video_info_list = asyncio.run(
                    fdl.extract_info_video_list_localhost(facebook_video_list, with_url_dl))

        if len(douyin_video_list) > 0:
            ddl = DouyinExtractor()
            self.callback_progress(ddl)
            x_bogus = self.download_options.get("x_bogus", None)
            x_bogus_driver = self.download_options.get("x_bogus_driver", False)
            douyin_server = self.download_options.get(
                "douyin_server", "default")
            douyin_cookie = self.download_options.get("douyin_cookie", None)
            ddl.x_bogus = x_bogus
            ddl.x_bogus_driver = x_bogus_driver
            if isinstance(douyin_server, str) and douyin_server == "default":
                # ddl.extract_video_info_list_api_sln_all(douyin_video_list) # Test
                douyin_video_info_list = ddl.extract_video_list_from_other_run(
                    douyin_video_list, with_url_dl, douyin_cookie)
            else:
                douyin_video_info_list = ddl.extract_video_info_list_mobile_api_sln_all(
                    douyin_video_list, with_url_dl)
            # print(douyin_video_info_list)

        if len(kuaishou_video_list) > 0:
            cookies = self.download_options.get("kuaishou_cookie", None)
            mobile_cookies = self.download_options.get(
                "kuaishou_mobile_cookie", None)
            video_share_url = self.download_options.get(
                "kuaishou_video_share_url", None)
            extractor = self.download_options.get(
                "kuaishou_extractor_video", "default")
            custom_cpu = self.download_options.get(
                "kuaishou_extractor_custom_cpu", None)
            kdl = KuaishouExtractor(
                cookies, mobile_cookies, video_share_url=video_share_url)
            self.callback_progress(kdl)

            if extractor == "driver":
                kuaishou_video_info_list = []
                # kuaishou_video_info_list = kdl.extract_video_info_list(kuaishou_video_list, with_url_dl)
            else:
                kuaishou_video_info_list = kdl.extract_video_list_from_other_run(
                    kuaishou_video_list, with_url_dl)

        # print("generic_video_list", generic_video_list)
        if len(generic_video_list) > 0:
            generic_video_info_list = asyncio.run(download_multi_videos_info_async(
                generic_video_list, download, **download_options
            ))
            # print("generic_video_info_list", generic_video_info_list)

        video_info_list = []
        if len(video_list) > 0:
            video_info_list = asyncio.run(download_multi_videos_info_async(
                video_list, download, **download_options
            ))

        custom_generic_video_info_list = sum([
            youtube_video_info_list,
            tiktok_video_info_list,
            instagram_video_info_list,
            facebook_video_info_list,
            douyin_video_info_list,
            kuaishou_video_info_list,
        ], [])

        # print(custom_generic_video_info_list)
        # use_logfile = download_options.get("use_logfile", False) is True
        # custom_logfile = download_options.get("custom_logfile")
        # get_file_metadata = download_options.get("get_file_metadata", False)
        # if download is True and len(custom_generic_video_info_list) > 0 and self.download_options["is_on_web"] is True: #
        #     custom_generic_video_list = [
        #       video_info["url_dl"] for video_info in custom_generic_video_info_list
        #     ]
        #     custom_generic_video_info_list = asyncio.run(download_multi_videos_info_async(
        #       custom_generic_video_list, download, **download_options
        #     ))

        all_video_info_list = sum([
            video_info_list, generic_video_info_list, custom_generic_video_info_list
        ], [])

        def remove_url_dl(video_info):
            if isinstance(video_info.get("url_url"), str):
                del video_info["url_dl"]
            return video_info

        all_video_info_list = [
            remove_url_dl(video_info) for video_info in all_video_info_list if isinstance(video_info, dict)
        ]
        # print("all_video_info_list", all_video_info_list)
        return all_video_info_list
