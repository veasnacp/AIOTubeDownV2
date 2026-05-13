import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from urllib.parse import urlparse

from curl_cffi.requests import AsyncSession, BrowserTypeLiteral, RequestsError, Response

from ._request import ExtractorBase

current_dir = Path(__file__).parent


class KuaishouBaseIE(ExtractorBase):
    _BASE_URL = "https://www.kuaishou.com"
    _CLOUD_FOLDER = "video/kuaishou"
    _API_QRAPHQL = "https://www.kuaishou.com/graphql"

    _LIVE_API_M_QRAPHQL = "https://live.kuaishou.com/m_graphql"
    _LIVE_API_USER_ID_WITH = "https://live.kuaishou.com/live_api/baseuser/userinfo/byid?principalId=%s"
    # _LIVE_API_VIDEO_WITH = "https://live.kuaishou.com/live_api/profile/feedbyid?photoId=3xywnx98nq9idw9&principalId=yy1885666"

    _LINK_VIDEO_WITH = "https://www.kuaishou.com/short-video/%s"
    _LINK_VIDEO_WITH_USER_ID = "https://www.kuaishou.com/short-video/%s?user_id=%s"
    _LINK_USER_WITH = "https://www.kuaishou.com/profile/%s"

    _MOBILE_API_VIDEO = "https://v.m.chenzhongtech.com/rest/wd/ugH5App/recommend/photos?__NS_sig3=564602313f371060630b0809334d9d4cfe230474171715151a1b1802"

    _MOBILE_API_USER_PROFILE = "https://c.kuaishou.com/rest/wd/feed/profile"
    _MOBILE_API_USER_INFO = "https://c.kuaishou.com/rest/wd/user/profile"

    default_headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
    }

    def get_video_id(self, url_vid: str):
        url = url_vid.strip()
        if "/short-video/" in url:
            video_id = url.split(
                "/short-video/")[1].split("?")[0].split("/")[0]
        else:
            video_id = url

        return video_id

    def fix_video_url(self, url_vid: str):
        return self._LINK_VIDEO_WITH % self.get_video_id(url_vid)

    def get_video_id_and_user_id(self, url_vid_user_id: str):
        url = url_vid_user_id.strip()
        if "user_id=" in url or "authorId=" in url:
            split_user_id = "user_id=" if "user_id=" in url else "authorId="
            user_id = url.split(split_user_id)[1].split("&")[0]
        else:
            user_id = ""

        if "/short-video/" in url:
            video_id = url.split(
                "/short-video/")[1].split("?")[0].split("/")[0]
        else:
            video_id = url

        return video_id, user_id

    def get_user_id(self, url_uid: str):
        url = url_uid.strip()
        if "/profile/" in url:
            user_id = url.split("/profile/")[1].split("?")[0].split("/")[0]
        else:
            user_id = urlparse(url).path.replace('/', '')

        return user_id

    def datetime_timestamp(self, ts: int):
        return datetime.fromtimestamp(ts) if ts > 0 else "Unknown"

    def _extract_node_logic(self, html: str, node: dict):
        """Your integrated yt-dlp inspired extraction logic."""
        if isinstance(node.get('defaultClient'), dict):
            info_dict_raw = node["defaultClient"]
            video_id = node.get("video_id")
            if not video_id:
                matches = re.search(
                    r'(\"\$VisionVideoDetailPhoto:)(.*?)(.manifest\",\")', html)
                video_id = matches.group(2) if matches else ''

            user_id = node.get("user_id")
            if not user_id:
                matches = re.search(
                    r'(\"VisionVideoDetailAuthor:)(.*?)(\",\")', html)
                user_id = matches.group(2) if matches else ''

            video_details = info_dict_raw.get(
                "VisionVideoDetailPhoto:%s" % video_id, {})
            user = info_dict_raw.get(
                "VisionVideoDetailAuthor:%s" % user_id, {})
        else:
            video_details = node.get('photo', {})
            video_id = video_details.get('id', '')
            user = node.get('author', {})
            user_id = user.get("id", "")

        # Handle view count '万' (10k) conversion
        viewCount = video_details.get("viewCount", 0)
        if isinstance(viewCount, str) and any(x in viewCount for x in ["\u4e07", "万"]):
            viewCount = float(viewCount.replace(
                "\u4e07", "").replace("万", "")) * 10000

        stats = {
            "view_count": int(viewCount),
            "like_count": video_details.get("realLikeCount", 0),
            "comment_count": video_details.get("commentCount", 0),
            "share_count": video_details.get("shareCount", 0),
        }

        title = video_details.get("caption", f"{video_id} by ")
        cover = video_details.get("coverUrl", "")
        url_dl = video_details.get("photoUrl", "")
        url_dl_sd = video_details.get("photoH265Url", url_dl)
        timestamp = int(float(video_details.get("timestamp") / 1000)
                        ) if video_details.get("timestamp") else 0
        url = f"https://www.kuaishou.com/short-video/{video_id}?user_id={user_id}"

        # Resolution & Manifest Parsing
        width = height = 0
        resolution = f"{width}x{height}"
        manifestH265 = video_details.get("manifestH265")
        if isinstance(manifestH265, dict):
            try:
                m_data = manifestH265.get('json') or manifestH265
                rep = m_data["adaptationSet"][0]["representation"][0]
                width, height = rep["width"], rep["height"]
                resolution = f"{width}x{height}"
            except:
                pass

        # Music Extraction
        soundTrack = video_details.get("soundTrack")
        music = ""
        if isinstance(soundTrack, dict):
            try:
                audioUrls = soundTrack.get("audioUrls", [])
                music = audioUrls[1]["url"] if len(
                    audioUrls) > 1 else audioUrls[0]["url"]
            except:
                pass

        user_info = {
            "id": user_id,
            "name": user.get("name", ""),
            "username": user_id,
            "avatar": user.get("headerUrl", "")
        }

        # Final yt-dlp style info_dict
        return {
            "id": video_id,
            "display_id": video_id,
            "title": title,
            "fulltitle": title,
            "description": title,
            "thumbnail": cover,
            "sd": url_dl_sd,
            "hd": url_dl,
            "music": music,
            "requested_download": [{
                "title": title, "width": width, "height": height,
                "resolution": resolution, "url": url,
            }],
            "uploader": user_id,
            "uploader_id": user_id,
            "uploader_url": f"https://www.kuaishou.com/profile/{user_id}",
            "url": url,
            "extractor": "kuaishou",
            "width": width, "height": height, "resolution": resolution,
            "duration": int(float(video_details.get("duration") / 1000)) if video_details.get("duration") else 0,
            "timestamp": timestamp,
            "upload_date": str(self.datetime_timestamp(timestamp)),
            **stats,
            "user_info": user_info
        }

    def extract_node_logic(self, html: str, node: dict) -> Dict:
        """
        Refined version of your yt-dlp logic to handle both Detail Page and Profile Feed.
        """
        # 1. Determine Data Source (Detail Page vs. Feed Item)
        if "defaultClient" in node:
            # Single Video Page Structure
            client = node["defaultClient"]
            video_id = node.get("video_id") or ""
            user_id = node.get("user_id") or ""
            video_details = client.get(
                f"VisionVideoDetailPhoto:{video_id}", {})
            user = {}
            if not user_id:
                for _key, value in client.items():
                    if _key.startswith("VisionVideoDetailAuthor:") and isinstance(value, dict):
                        user = value
                        user_id = user.get("id", "")
                        break
            else:
                user = client.get(f"VisionVideoDetailAuthor:{user_id}", {})
        else:
            # Feed List Structure (Direct from GraphQL)
            video_details = node.get('photo', {})
            video_id = video_details.get('id', '')
            user = video_details.get('author', {})
            user_id = user.get('id', '')

        # 2. Stats & View Count
        vc = video_details.get("viewCount", 0)
        if isinstance(vc, str) and ("万" in vc or "\u4e07" in vc):
            vc = float(vc.replace("万", "").replace("\u4e07", "")) * 10000

        # 3. Core Info Dict Construction
        title = video_details.get("caption", video_id)
        ts = int(float(video_details.get("timestamp") / 1000)
                 ) if video_details.get("timestamp") else 0

        info_dict = {
            "id": video_id,
            "title": title,
            "thumbnail": video_details.get("coverUrl", ""),
            "sd": video_details.get("photoH265Url", ""),
            "hd": video_details.get("photoUrl", ""),
            "duration": int(float(video_details.get("duration") / 1000)) if video_details.get("duration") else 0,
            "view_count": int(vc),
            "like_count": video_details.get("realLikeCount", 0),
            "comment_count": video_details.get("commentCount", 0),
            "share_count": video_details.get("shareCount", 0),
            "timestamp": ts,
            "upload_date": datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts > 0 else "N/A",
            "uploader": user.get("name", ""),
            "uploader_id": user_id,
            "uploader_url": f"https://www.kuaishou.com/profile/{user_id}",
            "avatar": user.get("headerUrl", ""),
            "url": f"https://www.kuaishou.com/short-video/{video_id}?user_id={user_id}"
        }

        return info_dict

    def extract_live_node(self, item: Dict, user_id: str) -> Dict:
        """Converts Live API item to your standard info_dict."""
        # Live API uses different keys (e.g., 'photoId' instead of 'id')
        video_id = item.get("photoId")
        title = item.get("caption", "")

        # Mapping to your desired structure
        return {
            "id": video_id,
            "title": title,
            "thumbnail": item.get("coverUrl"),
            # Usually the Live API provides high quality directly
            "sd": item.get("photoUrl"),
            "hd": item.get("photoUrl"),
            "view_count": item.get("viewCount", 0),
            "like_count": item.get("likeCount", 0),
            "comment_count": item.get("commentCount", 0),
            "duration": item.get("duration", 0),
            "timestamp": int(item.get("timestamp", 0) / 1000),
            "uploader_id": user_id,
            "url": f"https://www.kuaishou.com/short-video/{video_id}?user_id={user_id}",
            "extractor": "kuaishou_live"
        }


class KuaishouExtractor(KuaishouBaseIE):
    USER_PAYLOAD = {
        "operationName": "visionProfilePhotoList",
        "variables": {
            "userId": "3x36h86rp4kvnzs",
            "pcursor": "",
            "page": "profile"
        },
        "query": "fragment photoContent on PhotoEntity {\n  __typename\n  id\n  duration\n  caption\n  originCaption\n  likeCount\n  viewCount\n  commentCount\n  realLikeCount\n  coverUrl\n  photoUrl\n  photoH265Url\n  manifest\n  manifestH265\n  videoResource\n  coverUrls {\n    url\n    __typename\n  }\n  timestamp\n  expTag\n  animatedCoverUrl\n  distance\n  videoRatio\n  liked\n  stereoType\n  profileUserTopPhoto\n  musicBlocked\n  riskTagContent\n  riskTagUrl\n}\n\nfragment recoPhotoFragment on recoPhotoEntity {\n  __typename\n  id\n  duration\n  caption\n  originCaption\n  likeCount\n  viewCount\n  commentCount\n  realLikeCount\n  coverUrl\n  photoUrl\n  photoH265Url\n  manifest\n  manifestH265\n  videoResource\n  coverUrls {\n    url\n    __typename\n  }\n  timestamp\n  expTag\n  animatedCoverUrl\n  distance\n  videoRatio\n  liked\n  stereoType\n  profileUserTopPhoto\n  musicBlocked\n  riskTagContent\n  riskTagUrl\n}\n\nfragment feedContent on Feed {\n  type\n  author {\n    id\n    name\n    headerUrl\n    following\n    headerUrls {\n      url\n      __typename\n    }\n    __typename\n  }\n  photo {\n    ...photoContent\n    ...recoPhotoFragment\n    __typename\n  }\n  canAddComment\n  llsid\n  status\n  currentPcursor\n  tags {\n    type\n    name\n    __typename\n  }\n  __typename\n}\n\nquery visionProfilePhotoList($pcursor: String, $userId: String, $page: String, $webPageArea: String) {\n  visionProfilePhotoList(pcursor: $pcursor, userId: $userId, page: $page, webPageArea: $webPageArea) {\n    result\n    llsid\n    webPageArea\n    feeds {\n      ...feedContent\n      __typename\n    }\n    hostName\n    pcursor\n    __typename\n  }\n}\n"
    }

    def __init__(self, proxies: Optional[List[str]] = None, impersonate: BrowserTypeLiteral = "chrome120", timeout: int = 30):
        super().__init__(proxies, impersonate, timeout)

        self.concurrent_tasks = 10  # Limit concurrent tasks to avoid rate limiting
        self.delay_jitter = False  # Disable human-like delay by default

        self.cookies: Optional[Union[str, Dict[str, str]]] = None

        # self.base_headers = {
        #     "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        #     "accept-language": "en-US,en;q=0.9,km;q=0.8",
        #     "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        #     "sec-ch-ua-platform": '"Windows"',
        #     "upgrade-insecure-requests": "1",
        #     "priority": "u=0, i",
        # }
        self.base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9,km;q=0.8",
            # "Cache-Control": "no-cache",
            # "Pragma": "no-cache",
            # "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            # "sec-ch-ua-mobile": "?0",
            # "sec-ch-ua-platform": '"Windows"',
            # "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            # "sec-fetch-site": "none",
            # "sec-fetch-user": "?1",
            # "upgrade-insecure-requests": "1",
        }
        self.base_profile_headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            # "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            # "cookie": "",
            "Referer": "https://www.kuaishou.com/profile/3x36h86rp4kvnzs",
            "Referrer-Policy": "unsafe-url"
        }

        self.nav_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,km;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        }

    def _get_proxy(self):
        return self._get_random_proxy()

    def set_cookies(self, cookies: Union[str, Dict[str, str]]):
        self.cookies = cookies

    async def login_stealth(self):
        """Pre-heats the session by visiting the home page to get base cookies."""
        print("[*] Pre-heating session (Shadow Protocol)...")
        await self.session.get("https://www.kuaishou.com/", headers=self.nav_headers, proxy=self._get_proxy())
        await asyncio.sleep(1)  # Wait for JS-like timing

    def on_report_callback(self, video_info: dict):
        pass

    def report_callback(self, video_info: dict):
        self.on_report_callback(video_info)

    def get_video_info(self, html: str, video_id: str, user_id: str | None = ""):
        """Internal handler to find JSON and run your extract_node_logic."""
        pattern = r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});'
        match = re.search(pattern, html)
        if match:
            try:
                node = json.loads(match.group(1))
                node['video_id'] = video_id
                node['user_id'] = user_id
                return self.extract_node_logic(html, node)
            except json.JSONDecodeError:
                return {"error": "Failed to parse JSON from __APOLLO_STATE__."}

        return {"error": "HTML loaded but window.__APOLLO_STATE__ was missing."}

    async def get_redirect_url(self, short_url: str, cookies: Optional[str] = None):
        """
        Follows a short URL and returns the final destination and headers.
        Useful for converting v.kuaishou.com/xxxx links.
        """
        cookie_dict = self.parse_cookies(cookies) if cookies else {}

        try:
            # We set allow_redirects=False to catch the first jump
            resp = await self.session.get(
                short_url,
                headers=self.base_headers,
                cookies=cookie_dict,
                proxy=self._get_proxy(),
                allow_redirects=True,
                timeout=10
            )

            redirect_url = resp.headers.get("Location") or resp.url
            status = resp.status_code
            print(resp)

            print(f"[+] Status: {status} | Destination: {redirect_url}")

            # save html
            with open("redirect_test.html", "w", encoding="utf-8") as f:
                f.write(resp.text)

            return {
                "status": status,
                "redirect_url": redirect_url,
                "headers": dict(resp.headers),
                "cookies_returned": dict(resp.cookies)
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_initial_data(
        self,
        video_id: str,
        user_id: str | None = None,
        cookie_input: str | Dict[str, str] | None = None,
        retries: int = 3,
        backoff: float = 2.0
    ):
        """
        Fetches the page with retry logic.
        :param cookie_input: Can be a raw string or a dict.
        :param retries: Number of attempts before giving up.
        :param backoff: Initial wait time between retries (multiplies each time).
        """
        if self.delay_jitter:
            # Human-like delay (Jitter) to avoid pattern detection
            await asyncio.sleep(random.uniform(1.5, 4.0))

        param_user_id = f"?user_id={user_id}" if user_id else ""
        url = self._LINK_VIDEO_WITH % f"{video_id}{param_user_id}"

        # Normalize cookies
        cookies = self.parse_cookies(cookie_input) if isinstance(
            cookie_input, str) else cookie_input

        self.session.cookies.update(cookies)

        self.base_headers["Referer"] = url
        if cookies:
            self.base_headers["Cookie"] = "; ".join(
                [f"{k}={v}" for k, v in cookies.items()])

        for attempt in range(retries):
            try:
                self.logger.info(
                    f"[*] [Attempt {attempt+1}/{retries}] Fetching Kuaishou...")

                resp = await self.request(
                    url,
                    headers=self.base_headers,
                    cookies=cookies,
                    impersonate=self.impersonate,
                    retries=0
                )
                if not resp or not isinstance(resp, Response):
                    self.logger.error(f"[!] No response from {url}")
                    continue

                if resp.status_code == 200:
                    # Successful fetch, proceed to extraction
                    return (video_id, user_id, resp.text)

                elif resp.status_code in [403, 429]:
                    self.logger.error(
                        f"[!] Rate limited or Blocked (Status {resp.status_code}).")
                else:
                    self.logger.error(f"[!] Server Error: {resp.status_code}")

            except (RequestsError, asyncio.TimeoutError) as e:
                self.logger.error(f"[!] Connection Error: {e}")

            # If we reached here, the attempt failed. Wait before retrying.
            if attempt < retries - 1:
                wait_time = backoff * (attempt + 1) + random.uniform(0.5, 1.5)
                self.logger.debug(
                    f"[*] Sleeping for {wait_time:.2f}s before retry...")
                await asyncio.sleep(wait_time)

        return {"error": "All retry attempts failed."}

    async def get_video_info_list(
        self, url_list: list[str],
        retries: int = 3,
        backoff: float = 2.0
    ):
        if self.cookies:
            cookie_input = self.cookies
        else:
            res = await self.request(self._LINK_USER_WITH % "3x36kuaishou")
            if isinstance(res, Response) and res.status_code == 200:
                cookie_input = res.cookies.get_dict()
                self.logger.debug(f"[*] Auto Cookies: {cookie_input}")

        # Use a Semaphore to control how many tasks run at once
        semaphore = asyncio.Semaphore(self.concurrent_tasks)
        if len(url_list) > 15:
            self.delay_jitter = True  # Enable jitter for large batches to avoid detection

        tasks = []
        valid_url_list = []
        async with semaphore:
            for url in url_list:
                if self.cancel:
                    self.on_extracting({"status": "cancelled"})
                    break

                video_id, user_id = self.get_video_id_and_user_id(url)
                valid_url_list.append(url)
                tasks.append(
                    self.get_initial_data(
                        video_id, user_id, cookie_input, retries, backoff)
                )

        task_list = await asyncio.gather(*tasks)
        video_info_list = []
        for i, task in enumerate(task_list):
            url = valid_url_list[i]
            if not isinstance(task, tuple):
                task = task['error'] if isinstance(task, dict) and 'error' in task \
                    else "Unknown error during fetch."
                self._on_extracting(
                    {"error": task, "url": url, "status": "error"})
                continue
            try:
                video_id, user_id, html = task
                video_info = self.get_video_info(html, video_id, user_id)
                video_info_list.append(video_info)
                self._on_extracting({
                    "status": "progress",
                    "url": url,
                    "data": video_info
                })
            except Exception as err:
                self._on_extracting(
                    {"error": str(err), "url": url, "status": "error"})

        return video_info_list

    async def get_public_profile_videos(
        self,
        user_id: str,
        cookie_input: str,
        limit: int = 12,
        retries: int = 3
    ) -> AsyncGenerator[Dict, None]:
        """
        Two-step fetch:
        1. Resolve principalId via byid API.
        2. Fetch video list via profile/public API.
        """
        # Signature is optional but recommended if your IP is restricted
        signature = "HUDR_sFnX-DtsB0FXsbDPT3TMP-sk0is9B7dAtQleg__VsxK3cJBScjfyoZuJDKCd0dFhpVOXKHFtTrFSOUNZnJTTlJFc98xCkEx5ZgnSHUamh8T1mQj2KahjLnk5k4h7AzVSQOFDJx_cz7yJPw1Sk0LdBXDB7EldiNpP-bUlhQif$HE_4b54cda9ab2b0796159d0111fc0060656b0100000001df98acba15db70e132dfdcdd9d019b563eda7b563ee800"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,km;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "Referer": f"https://live.kuaishou.com/profile/{user_id}",
        }

        cookies = self.parse_cookies(cookie_input)

        # --- STEP 1: Resolve User Info ---
        # info_url = "https://live.kuaishou.com/live_api/baseuser/userinfo/byid"
        # info_params = {"caver": "2", "principalId": user_id}

        # try:
        #     resp = await self.session.get(
        #         info_url,
        #         params=info_params,
        #         headers=headers,
        #         cookies=cookies,
        #         proxy=self._get_proxy(),
        #         timeout=15,
        #     )

        #     if resp.status_code != 200:
        #         yield {"error": f"Profile info fetch failed: {resp.status_code}"}
        #         return  # Stop generator

        #     data = resp.json().get("data", {})
        #     user_info = data.get("userInfo", {})
        #     principal_id = user_info.get("id", "HBDXMA369")
        #     print("data", data)
        #     print(
        #         f"[*] Resolved ID: {principal_id} | Name: {user_info.get('name')}")

        # except Exception as e:
        #     yield {"error": f"Info resolution exception: {str(e)}"}
        #     return

        principal_id = user_id
        # --- STEP 2: Fetch Video List with Pagination ---
        print(f"[*] Starting Video Scan for {principal_id}...")
        base_url = "https://live.kuaishou.com/live_api/profile/public"
        headers['Referer'] = f"https://live.kuaishou.com/profile/{principal_id}"

        pcursor = ""
        has_more = True
        count = 0

        while has_more and count < limit:
            params = {
                # "__NS_hxfalcon": signature,  # Included to prevent 403
                "caver": "2",
                "count": "12",
                "hasMore": str(has_more).lower(),
                "pcursor": pcursor,
                "principalId": principal_id,
                "privacy": "public"
            }

            for attempt in range(retries):
                try:
                    resp = await self.session.get(
                        base_url,
                        params=params,
                        headers=headers,
                        cookies=cookies,
                        proxy=self._get_proxy(),
                        timeout=15,
                        allow_redirects=False
                    )

                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        self.save_test_data(data, suffix="_public_profile")
                        list_data = data.get("list", [])

                        for item in list_data:
                            # Yield standard info_dict
                            yield self.extract_live_node(item, principal_id)
                            count += 1
                            if count >= limit:
                                return  # Successfully finished

                        pcursor = data.get("pcursor", "")
                        has_more = data.get("hasMore", False)
                        break  # Exit retry loop on success

                    elif resp.status_code == 403:
                        yield {"error": "403 Forbidden - Check Cookies/Signature"}
                        return

                except Exception as e:
                    print(f"[!] Attempt {attempt+1} failed: {e}")
                    if attempt == retries - 1:
                        yield {"error": f"Max retries reached: {str(e)}"}
                        return
                    await asyncio.sleep(2 * (attempt + 1))

            if not pcursor or pcursor == "no_more":
                break

            await asyncio.sleep(random.uniform(1.0, 2.5))

    async def get_live_profile_videos(
        self,
        url_uid: str,
        limit: int = None,
        sort_by="newest",
    ):
        await asyncio.sleep(0.00005)


async def run_multitasking_scout():
    raw_cookies = "did=web_db214ac2bfa3481494d80da73924f80c"
    async with KuaishouExtractor() as scout:
        print("[*] Launching simultaneous scan...")
        scout.set_test_mode(True)
        scout.set_cookies(raw_cookies)

        async def do_videos():
            print("[Videos] Fetching details for a specific video...")
            result = await scout.get_video_info_list(
                [
                    scout._LINK_VIDEO_WITH % "3xspaqvq478ugtw?user_id=3x36h86rp4kvnzs",
                    scout._LINK_VIDEO_WITH % "3x25by2mwk82ute",
                ],
                retries=3
            )
            scout.logger.info(f"[Videos] Fetched {len(result)} videos.")
            scout.save_test_data(result)

        async def do_live_scan():
            print("[Live] Starting live profile scan...")
            live_results = []
            async for video in scout.get_public_profile_videos("HBDXMA369", raw_cookies, limit=4):
                live_results.append(video)

            scout.save_test_data(live_results, suffix="_profile")

        async def do_live_profile_videos_scan():
            print("[Live] Starting live profile scan...")

            url_uid = 'https://www.kuaishou.com/profile/3xee4ritq5k6t2k'
            result = await scout.get_live_profile_videos(url_uid, )

        await asyncio.gather(do_videos())
