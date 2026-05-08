import asyncio
import json
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

from curl_cffi.requests import (
    AsyncSession,
    BrowserTypeLiteral,
    RequestsError,
    Response,
    Session,
)

# import logging
from loguru import logger

from ..config.constants import APP_NAME, DIRS

# logger = logging.getLogger(__name__)
current_dir = Path(__file__).parent


def search_dict(partial: Union[dict, list], search_key: str) -> Generator[dict, None, None]:
    stack = [partial]
    while stack:
        current_item = stack.pop(0)
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                if key == search_key:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current_item, list):
            for value in current_item:
                stack.append(value)


def get_json_from_html(html: str, key: str, num_chars: int = 2, stop: str = '"') -> str:
    pos_begin = html.find(key) + len(key) + num_chars
    pos_end = html.find(stop, pos_begin)
    return html[pos_begin:pos_end]


def get_content_from_html_selector(
    content: str,
    tag_name: Optional[str] = None,
    selectors: Optional[List[str]] = None,
) -> List[str]:
    tag_name = tag_name or "div"
    selector = ""
    if isinstance(selectors, list):
        selector = ".*?" + ".*?".join(selectors) + ".*?"
    html_pattern = "(?:<%s%s>)(.*?)(?:</%s>)" % (
        tag_name,
        selector,
        tag_name
    )

    return re.findall(html_pattern, content)


def dict_to_query_string(dict_obj: dict):
    return json.dumps(dict_obj, separators=(',', ':'))


def get_proxies(
    url: Optional[str] = None,
    session: Optional[Session] = None
) -> List[str]:
    session = session or Session(impersonate="chrome120")
    try:
        # 'https://proxylist.geonode.com/api/proxy-list?limit=30'
        # https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all
        response = session.get(
            url or "https://proxylist.geonode.com/api/proxy-list?limit=30",
        )
        if response.status_code == 200:
            return [f"{proxy['ip']}:{proxy['port']}" for proxy in response.json()['data']]
        else:
            print(
                f"[!] ❌ Failed to fetch proxies: Status code {response.status_code}")
            return []
    except Exception as e:
        print(f"[!] ❌ Error fetching proxies: {e}")

    return []


class AsyncBaseRequest:
    """
    Professional Base Request class for Scraper and API projects.
    Handles TLS Fingerprinting, Session Persistence, and Proxy Management.
    """

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        impersonate: BrowserTypeLiteral = "chrome120",
        timeout: int = 30,
        logger_name: str = __name__
    ):
        self.proxies = proxies
        self.impersonate = impersonate
        self.timeout = timeout
        # Persistent session allows for cookie-jar management across requests
        self.session = AsyncSession(impersonate=self.impersonate)
        self.session_sync = Session(impersonate=self.impersonate)

        self.base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        self.cancel = False
        self.logger_name = logger_name
        self.logger = logger.bind(name=self.logger_name)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        try:
            self.session_sync.close()
        except:
            pass
        await self.session.close()

    def _get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Selects a random proxy from the list if available."""
        if not self.proxies:
            return None
        proxy = random.choice(self.proxies)
        return {"http": proxy, "https": proxy}

    @staticmethod
    def parse_cookies(cookie_str: Union[str, Dict]) -> Dict[str, str]:
        """Helper to ensure cookies are always in dict format."""
        if isinstance(cookie_str, dict):
            return cookie_str
        if not cookie_str:
            return {}
        return {
            item.split('=', 1)[0].strip(): item.split('=', 1)[1].strip()
            for item in cookie_str.split(';') if '=' in item
        }

    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        data: Any = None,
        json_data: Optional[Dict] = None,
        cookies: Optional[Union[str, Dict]] = None,
        allow_redirects: bool = True,
        impersonate: BrowserTypeLiteral = None,
        retries: int = 2,
        **kwargs
    ) -> Union[Response, None]:
        """
        The core execution method with built-in retry logic.
        """
        if not url.lower().startswith("http"):
            raise ValueError(f"Invalid URL: {url}")

        if isinstance(cookies, (str, dict)):
            current_cookies = self.parse_cookies(cookies)
        else:
            current_cookies = None

        for attempt in range(retries + 1):
            if hasattr(self, "cancel") and self.cancel:
                break
            try:
                proxy = self._get_random_proxy()

                response = await self.session.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                    cookies=current_cookies,
                    proxy=proxy,
                    timeout=self.timeout,
                    allow_redirects=allow_redirects,
                    impersonate=impersonate or self.impersonate,
                    **kwargs
                )

                return response

            except (RequestsError, asyncio.TimeoutError) as e:
                if attempt == retries:
                    self.logger.error(
                        f"[!] Final attempt failed for {url}: {e}")
                    return {"error": str(e), "url": url}

                wait = (attempt + 1) * 2
                self.logger.warning(
                    f"[*] Request failed, retrying in {wait}s... ({attempt + 1}/{retries})")
                await asyncio.sleep(wait)

    def request_sync(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        data: Any = None,
        json_data: Optional[Dict] = None,
        cookies: Optional[Union[str, Dict]] = None,
        allow_redirects: bool = True,
        impersonate: BrowserTypeLiteral = None,
        retries: int = 2
    ) -> Union[Response, None]:
        """
        The core execution method with built-in retry logic.
        """
        if not url.lower().startswith("http"):
            raise ValueError(f"Invalid URL: {url}")

        if isinstance(cookies, (str, dict)):
            current_cookies = self.parse_cookies(cookies)
        else:
            current_cookies = None

        for attempt in range(retries + 1):
            try:
                proxy = self._get_random_proxy()

                response = self.session_sync.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                    cookies=current_cookies,
                    proxy=proxy,
                    timeout=self.timeout,
                    allow_redirects=allow_redirects,
                    impersonate=impersonate or self.impersonate
                )

                return response

            except (RequestsError, TimeoutError) as e:
                if attempt == retries:
                    self.logger.error(
                        f"[!] Final attempt failed for {url}: {e}")
                    return {"error": str(e), "url": url}

                wait = (attempt + 1) * 2
                self.logger.warning(
                    f"[*] Request failed, retrying in {wait}s... ({attempt + 1}/{retries})")
                time.sleep(wait)

    async def get(self, url: str, **kwargs):
        return await self.request(url, method="GET", **kwargs)

    async def post(self, url: str, **kwargs):
        return await self.request(url, method="POST", **kwargs)


class ExtractorBase(AsyncBaseRequest):
    _BASE_URL = ""
    _CLOUD_FOLDER = "parent/extractor"
    _skip_cached_info = False
    _cache = {}

    _IS_TESTING = True
    _TEST_URL = ""
    _TEST_VIDEO_ID = ""
    _TEST_DRAMA_ID = ""

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        impersonate: BrowserTypeLiteral = "safari170",
        timeout: int = 30
    ):
        super().__init__(proxies, impersonate, timeout)
        self.cancel_download = False
        self.active_downloader = None

    def stop_download(self):
        """ Stops the current download process """
        self.cancel_download = True
        if self.active_downloader:
            self.active_downloader.cancelled = True
            self.logger.info("Cancellation signal sent to downloader")

    def on_extracting(self, d: Any):
        pass

    def _on_extracting(self, d: Any):
        self.on_extracting(d)

    def stop_extraction(self):
        self.cancel = True

    def set_test_mode(self, is_testing: bool, test_url: str = "", test_video_id: str = "", test_drama_id: str = ""):
        self._IS_TESTING = is_testing
        # self._TEST_URL = test_url
        # self._TEST_VIDEO_ID = test_video_id
        # self._TEST_DRAMA_ID = test_drama_id

    def reset_cache(self, video_id: str = ""):
        if video_id:
            del self._cache[video_id]
        else:
            self._cache = {}

    def save_test_data(self, data: Any, suffix: str = ""):
        try:
            if self._IS_TESTING:
                folder = current_dir / '_data'
                folder.mkdir(exist_ok=True)
                with open(folder / f"__{self._CLOUD_FOLDER.split('/')[-1]}_data{suffix}.json", "w", encoding="utf-8", errors="strict") as out_f:
                    out_f.write(json.dumps(data, indent=2))
        except Exception as e:
            self.logger.error(
                f"[!] ❌ Failed to save data to Cloudinary or local file: {e}")

    def load_test_data(self, suffix: str = ""):
        try:
            if self._IS_TESTING:
                folder = current_dir / '_data'
                with open(folder / f"__{self._CLOUD_FOLDER.split('/')[-1]}_data{suffix}.json", "r", encoding="utf-8", errors="strict") as in_f:
                    return json.load(in_f)
        except Exception as e:
            self.logger.error(
                f"[!] ❌ Failed to load data from Cloudinary or local file: {e}")
            return None

    def save_error_text(self, text: str, ext: str = "txt", suffix: str = "_error"):
        try:
            if self._IS_TESTING:
                folder = current_dir / '_data'
                folder.mkdir(exist_ok=True)
                with open(folder / f"__{self._CLOUD_FOLDER.split('/')[-1]}{suffix}.{ext}", "w", encoding="utf-8", errors="strict") as out_f:
                    out_f.write(text)
        except Exception as e:
            self.logger.error(
                f"[!] ❌ Failed to save error text to Cloudinary or local file: {e}")

    def save_html_text(self, text: str, suffix: str = ""):
        self.save_error_text(text, ext="html", suffix=suffix)

    async def get_drama_info_from_cloudinary(self, video_id: str):
        try:
            result = self.cloud_manager.retrieve_data(
                public_id=f"{self._CLOUD_FOLDER}/{video_id}.json", as_json=True)
            return result
        except Exception as e:
            self.logger.debug(
                f"[!] ❌ Error fetching from Cloudinary for video ID {video_id}: {e}")
            return None

    async def check_cloud_cache(self, video_id: str):
        if not self._skip_cached_info:
            try:
                cached_info = await self.get_drama_info_from_cloudinary(video_id)
                if cached_info:
                    self.logger.info(f"Cache hit for video ID {video_id}")
                    if self._IS_TESTING:
                        self.save_test_data(cached_info)
                    return cached_info
                else:
                    self.logger.info(
                        f"No cache found for video ID {video_id}, fetching from source...")
            except Exception as e:
                self.logger.error(
                    f"[!] ❌ Error checking cache for video ID {video_id}: {e}")
                self.logger.info("Proceeding to fetch from source...")

    def set_output_dir(
        self, output_dir: Optional[str] = None, with_site_name: bool = False
    ):
        if output_dir:
            _output_dir = Path(output_dir)
        else:
            _output_dir = DIRS.user_downloads_path.joinpath(APP_NAME)
        if with_site_name:
            _output_dir = _output_dir.joinpath(
                self._CLOUD_FOLDER.split("/")[-1])
        return _output_dir

    def get_output_dir(self, output_dir: Optional[str] = None, with_site_name: bool = True):
        return self.set_output_dir(output_dir=output_dir, with_site_name=with_site_name)

    def get_video_url_play(self, chapter: dict, *args, **kwargs):
        return ""
