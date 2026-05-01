import asyncio
import json
import random
import re
import time
from datetime import datetime
from math import ceil
from typing_extensions import Any, Dict, List, Optional
from urllib.parse import quote, unquote, urlparse

from curl_cffi.requests import AsyncSession, Session


headers_mob = {
    'User-Agent': "Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Mobile Safari/537.36 Edg/87.0.664.66"
}


class DouyinBaseIE:
    """
    Douyin Base Class for extracting video information and downloading videos from douyin.com
    """
    request_session: Session = Session(impersonate="chrome120")
    _HOST_DOMAIN = "https://www.douyin.com/"
    _LINK_USER_WITH = "https://www.douyin.com/user/%s"
    _LINK_VIDEO_WITH = "https://www.douyin.com/video/%s"
    _LINK_VIDEO_MOBILE_WITH = "https://m.douyin.com/share/video/%s"

    _API_DOWNLOAD_VIDEO = "https://aweme.snssdk.com/aweme/v1/play/?aid=6383&video_id=%s"
    _API_DOWNLOAD_VIDEO_WATERMARK = "https://aweme.snssdk.com/aweme/v1/playwm/?aid=6383&video_id=%s"
    _API_VIDEO_INFO_WITH_ID = "https://www.douyin.com/aweme/v1/web/aweme/detail/?aid=6383&aweme_id=%s"
    _API_VIDEO_V1 = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
    _API_USER_POST_V1 = "https://www.douyin.com/aweme/v1/web/aweme/post/"

    _MOBILE_API_VIDEO_INFO_WITH_ID = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?reflow_source=reflow_page&item_ids=%s"
    _M_API_VIDEO_INFO_WITH_ID = "https://m.douyin.com/web/api/v2/aweme/iteminfo/?reflow_source=reflow_page&item_ids=%s"

    _MOBILE_API_USER_POST_V2 = "https://www.iesdouyin.com/web/api/v2/aweme/post/"
    _MOBILE_API_USER_INFO_V2 = "https://www.iesdouyin.com/web/api/v2/user/info/?reflow_source=reflow_page&sec_uid=MS4wLjABAAAA386t1T1jRuO-twAHWyqnwyZUyJ5S97eXG-Bq4pMW6TxOjJwes9Ee75lHbnJ6mjD9&a_bogus=YJBYhOheMsR1YDv43wkz9eJmf4g0YW-lgZEzB1AgPUq0"

    _USER_QUERY_PARAMS = {
        "aid": "6383",
        "sec_user_id": "MS4wLjABAAAAyQ85Dd8tKor7qsIsthnUIvAXqduT_fjRIRti8HwVhkZVYv3X527hXQ_SuPZMWkzs",
        "max_cursor": 0,
        "locate_item_id": "7254900116232867132",
        "locate_query": "false",
        "show_live_replay_strategy": 1,
        "need_time_list": 1,
        "time_list_query": 0,
        "whale_cut_token": "",
        "cut_version": "1",
        "count": 35,
        "publish_video_strategy_type": "2"
    }

    _VIDEO_QUERY_PARAMS = {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "aweme_id": "7346529921793051941"
    }

    douyinHeaders = {
        'connection': 'keep-alive',
        'content-encoding': 'br',
        'content-security-policy': 'upgrade-insecure-requests;report-to default;frame-ancestors self',
        'content-security-policy-report-only': "connect-src 'self' blob: data: ws: wss: bytedance: snssdk1128: android-webview-video-poster: *.zijieapi.com *.ibytedapm.com *.bytetos.com *.bytednsdoc.com *.zijieimg.com *.zjurl.cn *.pstatp.com *.bytecdn.cn *.bytecdn.com *.isnssdk.com *.365yg.com *.ipstatp.com *.amemv.com *.ibytedtos.com *.ixigua.com *.ixiguavideo.com *.hypstarcdn.com *.tiktokcdn.com *.topbuzzcdn.com *.muscdn.com *.huoshanzhibo.com *.huoshanxiaoshipin.cn *.huoshanxiaoshipin.net *.huoshanvideo.cn *.huoshanvideo.net *.ieshuodong.cn *.ieshuodong.net *.byteoversea.com *.byted.org *.bytedance.net *.bytescm.com *.bytedance.com *.toutiaocloud.com *.snssdk.com *.toutiao.com *.huoshan.com *.douyin.com *.douyincdn.com *.jinritemai.com *.chengzijianzhan.com *.baike.com *.ribaoapi.com *.bytexservice.com *.pglstatp-toutiao.com *.oceanengine.com *.dyvideotape.com *.alicdn.com *.iesdouyin.com *.m.douyin.com *.byteimg.com *.zjcdn.com *.bytednsdoc.com *.douyinpic.com *.douyinstatic.com *.bdxiguaimg.com *.bdxiguastatic.com *.bytegoofy.com *.unpkg.com *.unpkg.byted-static.com *.draftstatic.com *.bytetcc.com *.yhgfb-cn-static.com http://127.0.0.1:* https://127.0.0.1:* http://localhost:* https://localhost:* *.huoshanstatic.com *.idouyinvod.com:* *.douyinvod.com:* *.volcsiriusbd.com:* *.volcsirius.com:*  *.tt.x.bsgslb.cn:* *.dy.zzcdnx.com:*  *.qc.bsccdn.net:* *.smtcdns.com:* *.ugslb.com:* *.livehwc3.cn:* *.smtcdns.net:* *.bytefcdnrd.com:* *.ksyungslb.com:* *.ksyungslb2.com:* *.ourdvsss.com:* *.tbcache.com:* *.jomodns.com:* *.douyincdn.com:* *.ixigua.com:* *.bdxigualive.com:* *.pstatp.com:* *.douyinliving.com:* *.picovr.com:* *.huoshanlive.com:* *.ihuoshanlive.com:* *.volccdn.com:* *.bestv.com.cn:* *.bytefcdn.com:* *.qnqcdn.net:*  *.jomoxc.com *.jomoxd.com *.a.bdycdn.cn *.hiecheimaetu.com:* *.ppio.cloud:* *.weilayun.com:* *.saxysec.com:* *.saxyit.com:* *.saxydc.com:* *.sjxysec.com:* *.sjxydc.com:* *.vegslb.com:*;script-src 'strict-dynamic' 'nonce-dSGrX5Ad8KrH-a0PXOJNg' 'unsafe-eval' 'unsafe-inline' *.bytescm.com *.bytecdn.com *.ibytedapm.com *.bytetos.com *.unpkg.com *.zijieapi.com;upgrade-insecure-requests;report-to default;frame-ancestors self",
    }

    def generate_url_query(self, url: str, params: dict[str, str]):
        query = '&'.join(f'{key}={value}' for key, value in params.items())
        return f"{url}?{query}"

    def get_sec_uid(self, url_uid: str):
        url = url_uid.strip()
        if "v.douyin.com" in url:
            r = self.request_session.get(url)
            url = r.headers.get("Location") or r.url
            sec_uid = str(url).split("/user/")[1].split("?")[0]
        elif "/user/" in url:
            sec_uid = url.split("/user/")[1].split("?")[0].split('/')[0]
        else:
            sec_uid = url
        return sec_uid

    def get_video_id(self, url_vid: str):
        url = url_vid.strip()
        if "v.douyin.com" in url:
            r = self.request_session.get(url)
            url = r.headers.get("Location") or r.url
            video_id = str(url).split("/video/")[1].split("?")[0]
        elif "?modal_id=" in url:
            video_id = url.split("?modal_id=")[1].split("&")[0]
        elif "/video/" in url:
            video_id = url.split("/video/")[1].split("?")[0].split('/')[0]
        else:
            video_id = url
        return re.sub(r"\D", "", video_id)

    def fix_video_url(self, url: str, is_mobile=False):
        video_id = self.get_video_id(url)
        if is_mobile:
            return self._LINK_VIDEO_MOBILE_WITH % video_id
        return self._LINK_VIDEO_WITH % video_id

    def extract_node(self, node: dict) -> dict[str, any]:
        is_default_api = isinstance(node.get("video"), dict)
        video: dict = node["video"] if is_default_api else node
        music: dict = node["music_info"] if isinstance(
            node.get("music_info"), dict) else node.get("music", {})

        stats = node["statistics"] if isinstance(
            node.get("statistics"), dict) else {}

        def getCount(key):
            return stats[key] if stats.get(key) else node.get(key, 0)

        stats.update(**({
            "view_count": getCount("play_count"),
            "like_count": getCount("digg_count"),
            "comment_count": getCount("comment_count"),
            "share_count": getCount("share_count"),
        }))

        video_id = node.get("aweme_id") or node.get("id", "none")
        tikwm_url_dl = {}
        if is_default_api:
            play_addr = video["play_addr"]
            video_dl_id = play_addr["uri"]
            url_dl = self._API_DOWNLOAD_VIDEO % video_dl_id
            url_dl_watermark = self._API_DOWNLOAD_VIDEO_WATERMARK % video_dl_id
        else:
            url_dl = video.get("play")
            url_dl_watermark = video.get("wmplay")
            tikwm_url_dl = {
                # "tikwm": {
                #   "hd": self._TIKWM_PLAY % video_id,
                #   "4k": self._TIKWM_HDPLAY % video_id,
                #   "wm": self._TIKWM_WMPLAY % video_id,
                #   "music": self._TIKWM_MUSIC % video_id,
                # }
            }

        width = video.get("width", 0)
        height = video.get("height", 0)
        resolution = "%sx%s" % (width, height)
        timestamp = node["create_time"]

        url = self._LINK_VIDEO_WITH % video_id
        user = node["author"]
        user_id = user["unique_id"] if user.get(
            "unique_id") else user.get("uid", "")

        user_keys = ["avatar_thumb", "follower_count", "total_favorited",
                     "sec_uid", "unique_id_modify_time", "cover_url"]
        update_user_info = {}
        for key in user_keys:
            if user.get(key) is not None:
                if key == "avatar_thumb" and isinstance(user.get("avatar_thumb"), dict):
                    update_user_info["avatar"] = user["avatar_thumb"].get("url_list", [""])[
                        0]
                else:
                    update_user_info[key] = user[key]

        title = node["title"] if node.get(
            "title") is not None else node.get("desc", "")
        title = title if title != "" else "Video by %s [%s]" % (
            user_id, video_id)
        cover = video["cover_original_scale"] if video.get(
            "cover_original_scale") is not None else video["cover"]
        origin_cover = video["origin_cover"] if video.get(
            "origin_cover") is not None else video["cover"]

        if is_default_api:
            duration = int(float(video["duration"] / 1000)) if video.get(
                "duration") is not None and video.get("duration") != 0 else music.get("duration", 0)
        else:
            duration = video.get("duration", 0)

        info_dict = {
            "id": video_id,
            "display_id": video_id,
            "title": title,
            "fulltitle": title,
            "description": title,
            "thumbnail": cover["url_list"][0] if is_default_api and isinstance(cover, dict) else cover,
            "original_thumbnail": origin_cover["url_list"][0] if is_default_api and isinstance(cover, dict) else origin_cover,
            "sd": "%s&ratio=720p&line=0" % url_dl,
            "hd": "%s&ratio=1080p&line=0" % url_dl,
            **tikwm_url_dl,
            "dl_with_watermark": url_dl_watermark,
            "music": music["play_url"]["uri"] if music.get("play_url") is not None else music.get("play", ""),
            "requested_download": [{
                "title": title,
                "width": width,
                "height": height,
                "resolution": resolution,
                "url": url,
                # "video": unescape(video_hd),
            }],
            "uploader": user.get("nickname") or user_id,
            "uploader_id": user_id,
            "sec_id": user.get("sec_uid", ""),
            "uploader_url": self._LINK_USER_WITH % user.get("sec_uid", "none"),
            "url": url,
            "original_url": url,
            "webpage_url": url,
            "webpage_url_domain": "douyin.com",
            "extractor": "douyin",
            "extractor_key": "Douyin",
            "width": width,
            "height": height,
            "resolution": resolution,
            "duration": duration,
            "timestamp": timestamp,
            "release_timestamp": timestamp,
            "upload_date": datetime.fromtimestamp(timestamp).__str__(),
            **stats,
            "subtitles": [],
            "audio_only": [],
            "video_only": [],
            "both": [],
            "user_info": {
                "id": user.get("sec_uid", "none"),
                "name": user.get("nickname", ""),
                "username": user_id,
                **update_user_info
            }
        }

        return info_dict


class DouyinRequest(DouyinBaseIE):
    def __init__(self):
        super().__init__()
        self.is_stopped = False

    def stop_extraction(self):
        self.is_stopped = True

    def on_callback_progress(self, video_info: dict):
        pass

    def callback_progress(self, video_info: dict):
        self.on_callback_progress(video_info)


class AsyncDouyinExtractor(DouyinRequest):
    def __init__(self, proxies: Optional[List[str]] = None):
        self.proxies = proxies
        # Douyin strictly checks TLS fingerprints; chrome120 is essential
        self.session = AsyncSession(impersonate="chrome")
        self.headers = {
            "Accept": "*/*", **headers_mob, **self.douyinHeaders
        }

    async def __aenter__(self): return self
    async def __aexit__(self, *args): await self.session.close()

    def _get_proxy(self):
        if not self.proxies:
            return None
        return {"http": random.choice(self.proxies), "https": random.choice(self.proxies)}

    @staticmethod
    def parse_cookie_string(cookie_str: str) -> Dict[str, str]:
        if not cookie_str:
            return {}
        return {item.split('=', 1)[0].strip(): item.split('=', 1)[1].strip()
                for item in cookie_str.split(';') if '=' in item}

    async def get_video_detail(self, url: str, cookie_input: Optional[str] = None):
        """
        Fetches Douyin HTML and extracts window._ROUTER_DATA
        """
        cookies = self.parse_cookie_string(
            cookie_input) if cookie_input else None

        url = self.fix_video_url(url, True)
        print(f"[*] Extracting Douyin: {url}")

        video_not_found = False
        try:
            response = await self.session.get(
                url,
                proxy=self._get_proxy(),
                headers=self.headers,
                cookies=cookies,
                # timeout=15
            )

            print(f"[*] Received response: {response.status_code} for {url}")

            content = response.text
            with open("./douyin_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            if 'window._ROUTER_DATA' in content:
                if 'img_bitrate' in content:
                    matches = re.search(r'(window\._ROUTER_DATA = )(.*?)(<\/script>)', content)
                    string_data = [c for c in matches.groups() if 'img_bitrate' in c][0] if matches else None
                    # print(type(string_data), matches)
                    if string_data:
                        dict_data = json.loads(string_data)
                        data = next(search_dict(dict_data, "item_list"), None)
                        if isinstance(data, list):
                            videoInfo = data[0]
                            # with open("./extractor/test/facebook_test_.json", "w") as f:
                            #   f.write(json.dumps(videoInfo, indent=2))
                            info_dict = self.extract_node(videoInfo)
                            self.callback_progress(info_dict)
                        if with_url_dl is True:
                            info_dict = self.dict_to_url_quote(info_dict)
                else:
                    print("Error => Video has not been Found with URL: ", url)
                    video_not_found = True
            else:
                print("Error => No _ROUTER_DATA with URL: ", url)

            if 'window._ROUTER_DATA' in content:
                # Optimized regex to capture the JSON object specifically
                matches = re.search(
                    r'window\._ROUTER_DATA\s*=\s*(.*?)</script>', content, re.S)
                print(f"[*] Extracted _ROUTER_DATA: {matches.group(1)[:100]}...") if matches else print(
                    "[*] _ROUTER_DATA not found in the page.")
                if matches:
                    try:
                        string_data = matches.group(1).strip()
                        dict_data = json.loads(string_data)
                        return self.extract_douyin_logic(dict_data)
                    except json.JSONDecodeError as e:
                        return {"error": f"JSON Decode Failed: {e}"}

            return {"error": "Could not find _ROUTER_DATA. Possible CAPTCHA or blocked IP."}

        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    def extract_douyin_logic(self, data: Dict) -> Dict:
        """
        Navigates the complex _ROUTER_DATA tree to find video info.
        """
        info = self.extract_node(data)
        # with open("douyin_extracted_info.json", "w", encoding="utf-8") as f:
        #     json.dump(info, f, indent=2, ensure_ascii=False)
        return info

# --- Execution ---


# async def test_douyin():
#     target = "https://www.douyin.com/video/7294586291344264458"
#     async with AsyncDouyinExtractor() as extractor:
#         result = await extractor.get_video_detail(target)
#         if 'error' in result:
#             print(f"Error: {result['error']}")
#         else:
#             with open("douyin_video_info.json", "w", encoding="utf-8") as f:
#                 json.dump(result, f, indent=2, ensure_ascii=False)

# if __name__ == "__main__":
#     asyncio.run(test_douyin())
