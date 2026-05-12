import asyncio
import base64
import binascii
import json
import math
import re
import uuid
from asyncio import Semaphore
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import quote, unquote, urlparse

import aiofiles
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto.Util.Padding import pad, unpad
from curl_cffi.requests import Response

from ._cloud import CloudinaryDataManager
from ._request import ExtractorBase, get_proxies
from ._tsdl import AsyncTSVideoDownloader, ProgressData
from ._utils import arr_chunk, safe_filename

# from playwright.async_api import async_playwright


current_dir = Path(__file__).parent

cloud_manager = CloudinaryDataManager(
    cloud_name="dvxh2vz5z",
    api_key="293416415366882",
    api_secret="8hnzstbS2sGIGRsE7jp_moN35ew"
)


class DramaExtractorBase(ExtractorBase):
    cloud_manager = cloud_manager

    async def _download_all_episodes(
        self,
        downloader: "AsyncTSVideoDownloader",
        info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        overwrite: bool = True,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        downloader_settings_callback: Optional[Callable[[
            "AsyncTSVideoDownloader"], None]] = None,
        is_test=False
    ):
        headers = {
            'Accept': '*/*',
            'Connection': 'keep-alive',
            "Referer": f"{self._BASE_URL}/",
            "Origin": self._BASE_URL,
        }
        # downloader.custom_temp_segments_dir_name = _safe_title
        downloader.session = self.session
        downloader.session.headers.update(headers)
        downloader.https_headers = headers
        downloader.https_impersonate = "chrome120"
        self.active_downloader = downloader
        downloader.cancelled = self.cancel_download
        # User download folder
        _output_dir = self.set_output_dir(output_dir, with_site_name)

        title = info['bookName']
        _safe_title = safe_filename(title)
        _output_dir = _output_dir.joinpath(_safe_title)

        if downloader_settings_callback and callable(downloader_settings_callback):
            downloader_settings_callback(downloader)

        url_list = []
        filename_list = []
        chapter_list = info['chapterList'][0:1] if is_test else info['chapterList']

        for chapter in chapter_list:
            if self.cancel_download:
                self.logger.info("Download process stopped by user")
                break

            url_list.append(self.get_video_url_play(chapter, "720p"))
            episode_index = int(chapter['indexStr'])
            suffix_name = f"_EP{episode_index:02d}"
            _filename = safe_filename(
                title, max_length=255 - len(suffix_name)) + suffix_name + ".mp4"
            filename_list.append(_filename)

        for attempt in range(max_attempts):
            self.logger.info(
                f"\nDownload attempt {attempt + 1}/{max_attempts}")

            if self.cancel_download:
                self.logger.info("Download process stopped")
                break

            # Try with different concurrency settings on retry
            if attempt == 1:
                downloader.max_concurrent = 3  # Reduce concurrency on retry
            elif attempt == 2:
                downloader.max_concurrent = 1  # Sequential on last retry

            result = await downloader.download_playlist(
                url_list,
                output_dir=str(_output_dir),
                filename_list=filename_list,
                overwrite=overwrite,
                progress_callback=progress_callback
            )

            if isinstance(result, list):
                self.logger.info("✅ Download completed successfully!")
                return result
            else:
                self.logger.error(f"❌ Error downloading playlist")

            self.logger.info(
                f"Attempt {attempt + 1} failed, retrying in {5 * (attempt + 1)} seconds...")
            await asyncio.sleep(5 * (attempt + 1))

        self.logger.info("All download attempts failed")
        return False

    async def download_m3u8(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        pattern: str | re.Pattern | Callable[[str], List[str]],
        output_file: str = "",
        temp_segments_dir_name: Optional[str] = None,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        downloader_settings_callback: Optional[Callable[[
            "AsyncTSVideoDownloader"], None]] = None,
        custom_response: Optional[Response] = None,
    ):
        headers = {
            'Accept': '*/*',
            'Connection': 'keep-alive',
            "Referer": f"{self._BASE_URL}/",
            "Origin": self._BASE_URL,
        }
        if hasattr(self, '_CUSTOM_BASE_URL') and self._CUSTOM_BASE_URL:
            headers["Referer"] = f"{self._CUSTOM_BASE_URL}/"
            headers["Origin"] = self._CUSTOM_BASE_URL

        self.logger.debug(f"Headers: {headers}")
        if temp_segments_dir_name:
            downloader.custom_temp_segments_dir_name = temp_segments_dir_name
        downloader.session = self.session
        downloader.session.headers.update(headers)
        downloader.https_headers = headers
        downloader.https_impersonate = "chrome131_android"
        if downloader_settings_callback and callable(downloader_settings_callback):
            downloader_settings_callback(downloader)

        for attempt in range(max_attempts):
            if downloader.cancelled:
                break
            self.logger.info(
                f"\nDownload attempt {attempt + 1}/{max_attempts}")

            # Try with different concurrency settings on retry
            if attempt == 1:
                downloader.max_concurrent = 3  # Reduce concurrency on retry
            elif attempt == 2:
                downloader.max_concurrent = 1  # Sequential on last retry

            result = await downloader.download_playlist_m3u8(
                m3u8_url,
                pattern=pattern,
                m3u8_headers=headers,
                output_file=output_file,
                use_parallel=True,
                batch_mode=True,
                progress_callback=progress_callback,
                custom_response=custom_response,
            )

            if isinstance(result, bool) and result:
                self.logger.info("✅ Download completed successfully!")
                return True
            elif isinstance(result, dict) and "error" in result:
                # this is ffmpeg error then skip retry
                self.logger.error(
                    f"❌ Error downloading playlist: {result['error']}")
                return False

            self.logger.info(
                f"Attempt {attempt + 1} failed, retrying in {5 * (attempt + 1)} seconds...")
            await asyncio.sleep(5 * (attempt + 1))

        self.logger.info("All download attempts failed")
        return False

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        temp_segments_dir_name: str,
        output_file: str,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
    ):
        return False

    async def _download_all_episodes_from_m3u8(
        self,
        downloader: "AsyncTSVideoDownloader",
        info: Dict[str, Any],
        keys_chaper_info: Dict[str, str | None | Callable] = {
            "video_url": "video_url",
            "temp_segments_dir_name": "chapter_id",
            "episode_number": "serial_number",
            "custom_temp_segments_dir_name": None
        },
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False
    ):
        # downloader = AsyncTSVideoDownloader(max_concurrent=5)
        self.active_downloader = downloader
        self.cancel_download = False
        downloader.cancelled = self.cancel_download
        _output_dir = self.set_output_dir(output_dir, with_site_name)
        # test 2 episodes
        chapters = info['chapterList'][0:1] if is_test else info['chapterList']
        title = info.get('title') or info.get('book_title') or info['book_id']
        success_data = []
        error_data = []
        _keys_chaper_info = keys_chaper_info.copy()
        for chapter in chapters:
            if self.cancel_download:
                self.logger.info("Download process stopped by user")
                break

            for key, value in keys_chaper_info.items():
                if key != "custom_temp_segments_dir_name" and callable(value):
                    chapter[key] = value(chapter)
                    _keys_chaper_info[key] = key

            chapter_id = chapter[_keys_chaper_info["temp_segments_dir_name"]]
            temp_segments_dir_name = chapter_id
            custom_temp_segments_dir_name = _keys_chaper_info.get(
                "custom_temp_segments_dir_name")
            if bool(custom_temp_segments_dir_name):
                if callable(custom_temp_segments_dir_name):
                    temp_segments_dir_name = custom_temp_segments_dir_name(
                        chapter)
                else:
                    temp_segments_dir_name = chapter[custom_temp_segments_dir_name]

            episode_index = int(chapter[_keys_chaper_info["episode_number"]])
            m3u8_url = chapter.get(_keys_chaper_info["video_url"])

            if episode_index == 0 or not m3u8_url:
                continue
            suffix_name = f"_EP{episode_index:02d}"
            filename = safe_filename(
                title, max_length=255 - len(suffix_name)) + suffix_name + ".mp4"
            title_folder = safe_filename(title)
            output_file = _output_dir.joinpath(title_folder, filename)
            success = await self.download_m3u8_url(
                downloader,
                m3u8_url,
                chapter,
                temp_segments_dir_name,
                str(output_file),
                max_attempts,
                progress_callback
                # progress_callback=lambda data: self.logger.info(
                #     f"{data.description}: {data.current}/{data.total} "
                #     f"({data.percentage:.1f}%)"),
            )

            chapter["status"] = "success" if success else "error"
            chapter["output_file"] = str(output_file)
            chapter["temp_segments_dir_name"] = temp_segments_dir_name
            if success:
                success_data.append(chapter)
            else:
                error_data.append(chapter)
                self.logger.error(
                    f"❌ Failed to download episode: {chapter_id}")
        return {
            "success": success_data,
            "failed": error_data
        }


class DramaBoxExtractor(DramaExtractorBase):
    _BASE_URL = "https://www.dramaboxdb.com"
    _LINK_ID = "https://www.dramaboxdb.com/movie/%s"
    _LINK_EP = "https://www.dramaboxdb.com/ep/%s"
    _PROXY_VIDEO_URL = "https://nahhhngapainlohhh.dramabos.asia/proxy?url=%s"
    _BUILD_ID = "dramaboxdb_prod_20260423"
    _LINK_GET_BUILD_ID = f"{_BASE_URL}/downloadapp"
    _CLOUD_FOLDER = "drama/dramabox"
    _resolution = "720p"

    def _get_build_id(self):
        response = self.session_sync.get(self._LINK_GET_BUILD_ID)
        if not isinstance(response, Response):
            return None
        try:
            html = response.text
            nd_match = re.search(
                r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if nd_match:
                data_obj = json.loads(nd_match.group(1))
                props = data_obj.get('props', {})
                build_id = props.get('buildId') or data_obj.get('buildId')
                if build_id:
                    self._BUILD_ID = build_id
                    self.logger.debug(f"Updated buildId: {build_id}")
                    return build_id
        except Exception as e:
            self.logger.error(f"[!] ❌ Error fetching buildId: {e}")
        return None

    def get_drama_id_slug_title(self, url: str):
        url_path = urlparse(url).path.rstrip('/')
        if "/movie/" in url_path:
            video_id = '/'.join(url_path.split("/movie/")[-1].split('/')[:2])
            url = self._LINK_ID % video_id
        elif "/ep/" in url_path:
            video_id = url_path.split(
                "/ep/")[-1].split('/')[0].replace('_', '/', 1)
            url = self._LINK_EP % video_id
        else:
            video_id = ''
            url = self._LINK_ID % video_id
        return url, video_id

    def get_video_ts(self, cover: str, ep: int, resolution: str = "720p"):
        pre_ts = cover.split('.mp4.')[0].replace(
            'thwztvideo', 'hwzthls', 1).split('/')
        id = pre_ts[-1]
        m3u8_path = f'm3u8/{id}.{resolution}-{ep:05d}.ts'
        pre_ts.pop()
        pre_ts.append(m3u8_path)
        ts = '/'.join(pre_ts)
        return ts

    def get_video_resolution(self, cover: str):
        pre_mp4 = cover.split('.mp4.')[0]
        return {
            "1080p": self._PROXY_VIDEO_URL % quote(pre_mp4 + '.1080p.nav2.mp4'),
            "720p": self._PROXY_VIDEO_URL % quote(pre_mp4 + '.720p.narrowv3.mp4'),
            "540p": self._PROXY_VIDEO_URL % quote(pre_mp4 + '.540p.narrowv2.mp4'),
            "360p": self._PROXY_VIDEO_URL % quote(pre_mp4 + '.360p.mp4'),
            "144p": self._PROXY_VIDEO_URL % quote(pre_mp4 + '.144p.mp4'),
        }

    def get_cover_url(self, info: dict) -> str:
        return info.get('cover', '')

    def get_video_url_play(self, chapter: dict, resolution: str = "720p"):
        if bool(chapter.get('m3u8Url')):
            return chapter['m3u8Url']
        return self.get_video_resolution(chapter['cover'])[resolution]

    async def get_drama_info(self, url: str):
        url, drama_id_with_title_slug = self.get_drama_id_slug_title(url)
        drama_id = drama_id_with_title_slug.split('/')[0]

        json_url = f"{self._BASE_URL}/_next/data/{self._BUILD_ID}/en/movie/{drama_id_with_title_slug}.json"
        if self._IS_TESTING:
            self.logger.debug(f"[!] 🔍 Fetching video info from: {json_url}")
        response = await self.request(
            json_url,
            impersonate=self.impersonate
        )
        if not response or not isinstance(response, Response) and "error" in response:
            if not response:
                self.logger.error(
                    f"[!] ❌ Error fetching video info: No response received for {url}")
            else:
                self.logger.error(
                    f"[!] ❌ Error fetching video info: {response['error']}")
            return None
        if response.status_code == 200:
            raw_data = response.text
            try:
                data = json.loads(raw_data)
                page_props = data['pageProps']
                chapter_list = page_props.get('chapterList', [])
                page_props['bookInfo']['chapterList'] = chapter_list
                info = page_props['bookInfo']
                info['title'] = info.get('bookName')

                if len(chapter_list) > 0:
                    self.logger.info(
                        f"[!] ✅ Found {len(chapter_list)} episodes")

                self._cache[drama_id] = info
                return info

            except Exception as e:
                self.logger.error(f"[!] ❌ Error processing video info: {e}")

            return None
        else:
            self.logger.error(
                f"[!] ❌ Error: Status code {response.status_code}")
            self.save_error_text(response.text)

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        chapter_id: str,
        output_file: str = "",
        max_attempts: int = 2,
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
    ):
        temp_segments_dir_name = chapter_id
        m3u8_path = urlparse(m3u8_url).path
        path_name_ext = m3u8_path.split("/")[-1]
        parent_url_path = m3u8_url.split(path_name_ext)[0]
        if not bool(output_file.strip()):
            output_file = f"{temp_segments_dir_name}.mp4"

        def pattern(content: str):
            # 570896434.720p-00001.ts
            ts_urls = re.findall(
                r'#EXTINF:.*\n([^\s"\'<>]+?.[a-zA-Z]+-\d+\.ts)', content)
            if ts_urls and 'https://' not in ts_urls[0]:
                ts_urls = [parent_url_path + ts_url for ts_url in ts_urls]
            return ts_urls

        # self._CUSTOM_BASE_URL = (self._PROXY_VIDEO_URL % '').split('/proxy')[0]
        _self = self

        class CustomResponse:
            def __init__(self):
                episode_range = 20
                duration = chapter.get('duration')
                if isinstance(duration, int) and duration > 60000:
                    episode_range = int(math.ceil(duration / 1000 / 7)) + 2

                episode_ts = []
                for i in range(episode_range):
                    ts_url_next = '#EXTINF:6.640000,\n'
                    ts_url_next += _self.get_video_ts(
                        chapter['cover'], i+1, _self._resolution)
                    episode_ts.append(ts_url_next)
                self.text = (
                    "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-ALLOW-CACHE:YES\n#EXT-X-TARGETDURATION:11\n#EXT-X-MEDIA-SEQUENCE:0\n"
                    + '\n'.join(episode_ts)
                    + "\n#EXT-X-ENDLIST"
                )
        has_m3u8 = bool(chapter.get('m3u8Url'))
        if has_m3u8:
            m3u8_url = chapter['m3u8Url']
            self.logger.debug(f"[!] ✅ Found m3u8 url for {chapter['id']}")
        else:
            self.logger.debug(f"[!] ⚠️  No m3u8 url for {chapter['id']}")

        success = await self.download_m3u8(
            downloader,
            m3u8_url,
            pattern,
            output_file,
            temp_segments_dir_name,
            max_attempts,
            progress_callback,
            custom_response=None if has_m3u8 else CustomResponse()
        )
        return success

    async def download_all_episodes(
        self,
        info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False
    ):
        downloader = AsyncTSVideoDownloader(max_concurrent=5)
        # return await self._download_all_episodes(
        #     downloader,
        #     info,
        #     output_dir=output_dir,
        #     with_site_name=with_site_name,
        #     max_attempts=max_attempts,
        #     progress_callback=progress_callback,
        #     is_test=is_test
        # )

        # def custom_temp_segments_dir_name(chapter):
        #     return chapter['id']

        return await self._download_all_episodes_from_m3u8(
            downloader,
            info,
            keys_chaper_info={
                "video_url": lambda chapter: self.get_video_url_play(chapter),
                "temp_segments_dir_name": "id",
                "episode_number": "indexStr",
                # "custom_temp_segments_dir_name": custom_temp_segments_dir_name
            },
            output_dir=output_dir,
            with_site_name=with_site_name,
            max_attempts=max_attempts,
            progress_callback=progress_callback,
            is_test=is_test
        )

    async def test_get_drama_info(self, url: Optional[str] = None):
        self._skip_cached_info = True
        # url = self._LINK_ID % "42000008498/the-last-of-us"
        if not url:
            url = self._LINK_EP % "41000119532_fake-dating-my-rich-nemesis/597968610_Episode-1"
        video_url, drama_id = self.get_drama_id_slug_title(url)
        self.logger.debug(f"Video URL: {video_url}, {drama_id}")
        info = await self.get_drama_info(url)
        if info:
            self.save_test_data(info)
        return info


class ReelShortExtractor(DramaExtractorBase):
    _BASE_URL = "https://www.reelshort.com"
    _LINK_ID = "https://www.reelshort.com/movie/%s"
    _LINK_EP = "https://www.reelshort.com/episodes/%s"
    _BUILD_ID = "cd930bf"
    _LINK_GET_BUILD_ID = f"{_BASE_URL}/search"
    _CLOUD_FOLDER = "drama/reelshort"

    def _get_build_id(self):
        response = self.session_sync.get(self._LINK_GET_BUILD_ID)
        if not isinstance(response, Response):
            return None
        try:
            html = response.text
            nd_match = re.search(
                r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if nd_match:
                data_obj = json.loads(nd_match.group(1))
                props = data_obj.get('props', {})
                build_id = props.get('buildId') or data_obj.get('buildId')
                if build_id:
                    self._BUILD_ID = build_id
                    self.logger.debug(f"Updated buildId: {build_id}")
                    return build_id
        except Exception as e:
            self.logger.error(f"[!] ❌ Error fetching buildId: {e}")
        return None

    def get_drama_id_slug_title(self, url: str):
        url_path = urlparse(url).path.rstrip('/')
        if "/movie/" in url_path:
            slug_title = url_path.split("/movie/")[:2][-1]
            url = self._LINK_ID % slug_title
        elif "/full-episodes/" in url_path:
            slug_title = url_path.split("/full-episodes/")[:2][-1]
            url = self._LINK_ID % slug_title
        elif "/episodes/" in url_path:
            slug = url_path.split("/episodes/")
            if slug[1].startswith('trailer-'):
                slug[1] = slug[1].replace('trailer-', 'episode-1-', 1)
            slug_title = '-'.join(slug[:2][-1].split('-')[2:-1])
            url = self._LINK_EP % slug_title
        else:
            slug_title = ''
            url = self._LINK_ID % slug_title

        return url, slug_title

    def get_video_url_play(self, chapter: dict):
        return chapter.get('video_url') or ''

    def get_cover_url(self, info: dict) -> str:
        return info.get('book_pic', '')

    async def _get_chapter_info(self, book_id: str, chapter_id: str):
        resp = await self.request(
            f'{self._BASE_URL}/api/video/book/getChapterInfo',
            params={
                'book_id': book_id,
                'chapter_id': chapter_id
            },
            headers={
                'Referer': f'{self._BASE_URL}/',
                'Accept': 'application/json'
            }
        )
        if not isinstance(resp, Response):
            if not resp:
                self.logger.error(
                    f"[!] ❌ Error fetching video info: No response received for {book_id} - {chapter_id}")
            else:
                self.logger.error(
                    f"[!] ❌ Error fetching video info: {resp['error']}")
            return None

        if resp.status_code == 200:
            data = resp.json()
            return data

        return None

    async def get_drama_info(self, url: str):
        url, drama_id_with_title_slug = self.get_drama_id_slug_title(url)
        drama_id = drama_id_with_title_slug.split('-')[-1]

        json_url = f"{self._BASE_URL}/_next/data/{self._BUILD_ID}/en/movie/{drama_id_with_title_slug}.json"
        self.logger.debug(f"Fetching video info from: {json_url}")
        response = await self.request(
            json_url,
            impersonate=self.impersonate
        )
        if not response or not isinstance(response, Response) and "error" in response:
            if not response:
                self.logger.error(
                    f"[!] ❌ Error fetching video info: No response received for {url}")
            else:
                self.logger.error(
                    f"[!] ❌ Error fetching video info: {response['error']}")
            return None
        if response.status_code == 200:
            raw_data = response.text
            try:
                data = json.loads(raw_data)
                page_props = data['pageProps']
                info = page_props['data']
                chapter_list = info.get('online_base', [])
                info['online_base'] = []
                if chapter_list and 'is_preview' in chapter_list[0]:
                    del chapter_list[0]
                info['chapterList'] = chapter_list

                self._cache[drama_id] = info
                return info

            except Exception as e:
                self.logger.error(f"[!] ❌ Error processing video info: {e}")

            return None
        else:
            self.logger.error(
                f"[!] ❌ Error: Status code {response.status_code}")
            if self._IS_TESTING:
                with open(current_dir / "error_response.txt", "w", encoding="utf-8", errors="strict") as out_f:
                    out_f.write(response.text)

    async def update_all_episodes(self, info, chunk_size=10):
        drama_id = info['book_id']
        tasks = []
        for chunk in arr_chunk(info['chapterList'], chunk_size):
            async with asyncio.TaskGroup() as tg:
                for chapter_info in chunk:
                    if 'is_preview' in chapter_info:
                        continue
                    chapter_id = chapter_info['chapter_id']
                    if self._IS_TESTING:
                        self.logger.debug(
                            f"[!] 🔍 Fetching video info for episode: {chapter_id}")
                    tasks.append(tg.create_task(
                        self._get_chapter_info(drama_id, chapter_id)))

        result_count = 0
        for task in tasks:
            if task.exception():
                self.logger.error(
                    f"[!] ❌ Error fetching video info: {task.exception()}")
            else:
                result = task.result()
                if result and result.get('code') == 0 and result.get('data'):
                    chapter_id = result['data']['chapter_id']
                    for i, chapter_info in enumerate(info['chapterList']):
                        if chapter_info['chapter_id'] == chapter_id:
                            result_count += 1
                            chapter_info.update(result['data'])
                            break
        if result_count > 0:
            self.logger.info(f"[!] ✅ Found {result_count} episodes")
        self._cache[drama_id] = info
        return info

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        chapter_id: str,
        output_file: str = "",
        max_attempts: int = 2,
        progress_callback: Optional[Callable[[ProgressData], None]] = None,
    ):
        # m3u8_url = self._TEST_URL_DOWNLOAD
        temp_segments_dir_name = chapter_id
        m3u8_path = urlparse(m3u8_url).path
        path_name_ext = m3u8_path.split("/")[-1]
        parent_url_path = m3u8_url.split(path_name_ext)[0]
        # full_path_name = m3u8_url.replace(".m3u8", "")
        # path_name = path_name_ext.replace(".m3u8", "")
        if not bool(output_file.strip()):
            output_file = f"{temp_segments_dir_name}.mp4"

        def pattern(content: str):
            ts_urls = re.findall(
                r'#EXTINF:.*\n([^\s"\'<>]+?-[a-zA-Z]+-\d+\.ts)', content)
            if ts_urls and 'https://' not in ts_urls[0]:
                ts_urls = [parent_url_path + ts_url for ts_url in ts_urls]
            return ts_urls

        success = await self.download_m3u8(
            downloader,
            m3u8_url,
            pattern,
            output_file,
            temp_segments_dir_name,
            max_attempts,
            progress_callback,
        )
        return success

    async def download_all_episodes(
        self,
        info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False
    ):
        downloader = AsyncTSVideoDownloader(max_concurrent=5)
        return await self._download_all_episodes_from_m3u8(
            downloader,
            info,
            keys_chaper_info={
                "video_url": "video_url",
                "temp_segments_dir_name": "chapter_id",
                "episode_number": "serial_number"
            },
            output_dir=output_dir,
            with_site_name=with_site_name,
            max_attempts=max_attempts,
            progress_callback=progress_callback,
            is_test=is_test
        )

    async def test_get_drama_info(self, url: Optional[str] = None):
        self._skip_cached_info = True
        # url = self._LINK_ID % "mic-drop-diva-69c0a20b1dd01a41ad0fdca1"
        url = url or self._LINK_EP % "episode-9-mic-drop-diva-69c0a20b1dd01a41ad0fdca1-vu7h10h4nm"
        video_url, drama_id = self.get_drama_id_slug_title(url)
        self.logger.debug(f"Video URL: {video_url}, {drama_id}")
        info = await self.get_drama_info(url)
        if info:
            info = await self.update_all_episodes(info)
            self.save_test_data(info)
        return info


class DramaBiteExtractor(DramaExtractorBase):
    _BASE_URL = "https://www.dramabite.media"
    _API_URL = _BASE_URL + "/short_video/video_svr"
    _BASE_CDN_VIDEO = "https://cdn-video.miniepisode.media"
    _BASE_CDN_IMAGE = "https://cdn-oss.miniepisode.media"
    _CLOUD_FOLDER = "drama/dramabite"

    _TEST_DRAMA_ID = "14155"

    def get_drama_id(self, url: str):
        try:
            drama_id = re.search(r"[?&#]cid=(\d+)", url).group(1)
            url = f"{self._BASE_URL}/#/play?cid={drama_id}"
            return url, drama_id
        except AttributeError:
            return url, None

    def _get_abs_video(self, path: str):
        if not path:
            return ""
        if str(path).startswith("http://") or str(path).startswith("https://"):
            return str(path)
        return f"{self._BASE_CDN_VIDEO}/{str(path).lstrip('/')}"

    def _get_abs_image(self, path: str):
        if not path:
            return ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        path = path.lstrip('/')
        base = self._BASE_CDN_VIDEO if path.startswith(
            "video/") else self._BASE_CDN_IMAGE
        return f"{base}/{path}"

    async def _api_endpoint(self, endpoint: str, params: dict):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": self._BASE_URL,
            "Referer": self._BASE_URL + "/",
        }
        resp = await self.request(f'{self._API_URL}/{endpoint}', params=params, headers=headers)
        return resp

    async def _get_episode_list(self, drama_id: str):
        resp = await self._api_endpoint('episode_list', {'cid': drama_id})
        return resp

    async def _get_chapter_info(self, drama_id: str, episode_id: str):
        resp = await self._api_endpoint('episode_detail', {'cid': drama_id, 'vid': episode_id})
        return resp

    def get_cover_url(self, entry: dict, resize: Union[bool, str] = True):
        """
        resize: str = h_634,w_476
        """
        path = entry.get('cover') or entry.get('video_cover')
        if path:
            path = self._get_abs_image(path)
            if "?" not in path:
                if isinstance(resize, str) and resize:
                    path += f"?x-oss-process=image/resize,m_fill,{resize}"
                elif resize:
                    path += "?x-oss-process=image/resize,m_fill,h_634,w_476"
            return path
        return ''

    def get_episode_cover_url(self, entry):
        return self.get_cover_url(entry)

    def get_video_url_play(self, entry: dict):
        path = entry.get('video_link') or entry.get(
            'video_link_m3u8') or entry.get('multi_rate_m3u8')
        if path:
            return self._get_abs_video(path)
        return None

    async def get_drama_info(self, url: str):
        url, drama_id = self.get_drama_id(url)
        if not drama_id:
            return None

        async def get_info(info):
            try:
                first_episode_detail = await self._get_chapter_info(drama_id, info['chapterList'][0]['vid'])
                if not first_episode_detail:
                    return None

                first_episode_detail = first_episode_detail.json()
                keys = [
                    'title',
                    'desc',
                    'video_cover',
                    'update_episode',
                    'total_episode',
                    'label_list',
                ]
                try:
                    for key in keys:
                        if key in first_episode_detail:
                            info[key] = first_episode_detail[key]
                except Exception as e:
                    self.logger.error(
                        f"[!] ❌ Error processing video info: {e}")

                preload_episode_links = first_episode_detail.get(
                    'preload_episode_links', [])
                for episode_link in preload_episode_links:
                    try:
                        ep_id = episode_link.get("vid")
                        index = next((i for i, item in enumerate(
                            episode_list) if item["vid"] == ep_id), None)
                        if index is not None:
                            episode_list[index]['link_info'] = episode_link

                    except Exception as e:
                        self.logger.error(
                            f"[!] ❌ Error processing video info: {e}")
                        break

                if len(episode_list) > 0:
                    self.logger.info(
                        f"[!] ✅ Found {len(episode_list)} episodes")

                episode_list[0].update(first_episode_detail)
                info['chapterList'] = episode_list
                return info
            except Exception as e:
                self.logger.error(f"[!] ❌ Error processing video info: {e}")
                return None

        if drama_id in self._cache:
            info = self._cache[drama_id]
            info = await get_info(info)
        else:
            resp_episode_list = await self._get_episode_list(drama_id)
            if not resp_episode_list:
                return None

            if resp_episode_list.status_code == 200:
                episode_list = resp_episode_list.json().get('episode_list', [])
                if not episode_list:
                    return None

                episode_list = sorted(episode_list, key=lambda x: x['vid'])
                info = {
                    "book_id": drama_id,
                    "chapterList": episode_list
                }
                self._cache[drama_id] = info
                info = await get_info(info)
        return info

    async def update_all_episodes(self, info: dict):
        drama_id = info['book_id']
        total_episode = info.get('total_episode') or info.get('update_episode')
        if not total_episode:
            return info
        episode_list = info['chapterList']
        chunk_size = 6
        chunks: List[List[Dict[str, Any]]] = [
            episode_list[i: i + chunk_size]
            for i in range(0, len(episode_list), chunk_size)
        ]
        tasks: List[asyncio.Task] = []
        for chunk in chunks:
            async with asyncio.TaskGroup() as tg:
                for chapter_info in chunk:
                    episode_id = chapter_info['vid']
                    if self._IS_TESTING:
                        self.logger.debug(
                            f"[!] 🔍 Fetching video info for episode: {episode_id}")
                    tasks.append(tg.create_task(
                        self._get_chapter_info(drama_id, episode_id)))

        result_count = 0
        for task in tasks:
            if task.exception():
                self.logger.error(
                    f"[!] ❌ Error fetching video info: {task.exception()}")
            else:
                result = task.result()
                if not isinstance(result, Response):
                    continue
                if result.status_code != 200:
                    self.logger.error(
                        f"[!] ❌ Error fetching video info: {result.status_code}")
                    continue
                result = result.json()
                if not isinstance(result, dict):
                    continue
                if result.get('link_info'):
                    episode_id = result['link_info']['vid']
                    index = next((i for i, item in enumerate(
                        episode_list) if item["vid"] == episode_id), None)
                    if index is not None:
                        result_count += 1
                        episode_list[index].update(result['link_info'])

                    preload_episode_links = result.get(
                        'preload_episode_links', [])
                    for episode_link in preload_episode_links:
                        try:
                            ep_id = episode_link.get("vid")
                            index = next((i for i, item in enumerate(
                                episode_list) if item["vid"] == ep_id), None)
                            if index is not None:
                                episode_list[index]['link_info'] = episode_link

                        except Exception as e:
                            self.logger.error(
                                f"[!] ❌ Error processing video info: {e}")
                            break
                else:
                    self.logger.error(
                        f"[!] ❌ Error fetching video info: {result}")

        if result_count > 0:
            self.logger.info(f"[!] ✅ Found {result_count} episodes")
        info['chapterList'] = episode_list
        self._cache[drama_id] = info
        return info

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        temp_segments_dir_name: Optional[str] = None,
        output_file: str = "",
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
    ):
        # m3u8_url = self._TEST_URL_DOWNLOAD
        # https://cdn-video.miniepisode.media/video/14155/2/0a3b3e3876e69f0a4c2c2462909c2748.m3u8?wsSecret=3612fd81a5c038d1905f88fccd934ed0&wsTime=1776158292
        # match = re.search(r'/([^/]+)/([^/]+)\.m3u8', m3u8_url)
        # temp_segments_dir_name = match.group(2) if match else None

        if not bool(output_file.strip()):
            output_file = f"{temp_segments_dir_name}.mp4"

        m3u8_path = urlparse(m3u8_url).path
        path_name_ext = m3u8_path.split("/")[-1]
        parent_url_path = m3u8_url.split(path_name_ext)[0]

        def pattern(content: str):
            # d331de4098044979aa0a699072145eb8_0000002.ts?wsHlsSession=137222c5a8274821bc44ec0e16ab35f4
            ts_urls = re.findall(
                r'#EXTINF:.*\n([^\s"\'<>]+?_\d+\.ts\?.*)', content)
            if ts_urls and 'https://' not in ts_urls[0]:
                ts_urls = [parent_url_path + ts_url for ts_url in ts_urls]
            return ts_urls

        success = await self.download_m3u8(
            downloader,
            m3u8_url,
            pattern,
            output_file,
            temp_segments_dir_name,
            max_attempts,
            progress_callback,
        )
        return success

    async def download_all_episodes(
        self, info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False,
    ):
        downloader = AsyncTSVideoDownloader(max_concurrent=5)

        def custom_temp_segments_dir_name(chapter):
            m3u8_url = self.get_video_url_play(chapter["link_info"])
            if not m3u8_url:
                return None
            match = re.search(r'/([^/]+)/([^/]+)\.m3u8', m3u8_url)
            temp_segments_dir_name = match.group(2) if match else None
            return temp_segments_dir_name

        return await self._download_all_episodes_from_m3u8(
            downloader,
            info,
            keys_chaper_info={
                "video_url": lambda chapter: self.get_video_url_play(chapter["link_info"]),
                "temp_segments_dir_name": "vid",
                "episode_number": "vid",
                "custom_temp_segments_dir_name": custom_temp_segments_dir_name
            },
            output_dir=output_dir,
            with_site_name=with_site_name,
            max_attempts=max_attempts,
            progress_callback=progress_callback,
            is_test=is_test
        )

    async def test_get_drama_info(self, url: Optional[str] = None):
        self._skip_cached_info = True
        url = url or f"{self._BASE_URL}/#/play?cid={self._TEST_DRAMA_ID}"
        video_url, drama_id = self.get_drama_id(url)
        self.logger.debug(f"Video URL: {video_url}, {drama_id}")
        info = await self.get_drama_info(url)
        if info:
            info['video_cover'] = self.get_cover_url(info)
            info = await self.update_all_episodes(info)
            for episode in info['chapterList']:
                link_info = episode.get('link_info')
                if link_info:
                    episode['video_url'] = self.get_video_url_play(link_info)
                    episode['cover_url'] = self.get_episode_cover_url(
                        link_info)
                # else:
                #     break
            self.save_test_data(info)
        return info


class ShortMovsExtractor(DramaExtractorBase):
    _BASE_URL = "https://www.shortmovs.com"
    _LINK_ID = "https://www.shortmovs.com/m/%s/"
    _LINK_EP = "https://www.shortmovs.com/m/%s/%s.html"
    _CLOUD_FOLDER = "drama/shortmovs"

    _TEST_DRAMA_ID = 'wodexiongdijiaofengxian'
    _TEST_URL_DOWNLOAD = "https://oss.shortmovs.com/c05345a03e2374e10984a6c2611ab129/ba5e46d3_005/index.m3u8"  # Forbidden
    # _TEST_URL_DOWNLOAD = "https://oss.shortmovs.com/c05345a03e2374e10984a6c2611ab129/7d8693ef_004/index.m3u8"

    def get_drama_id(self, url: str):
        match = re.search(r"/m/([^/]+)/", url)
        if match:
            drama_id = match.group(1)
            url = self._LINK_ID % drama_id
            return url, drama_id
        return url, None

    def get_cover_url(self, info: dict) -> str:
        return info.get('video_cover', '')

    def get_video_url_play(self, chapter: dict) -> str:
        return chapter.get('video_url', '')

    async def _get_html(self, url: str):
        resp = await self.request(url)
        if isinstance(resp, Response) and resp.status_code == 200:
            return resp.text
        return None

    def _get_info_from_html(self, html: str):
        title = ""
        desc = ""
        video_cover = ""
        embed_url = ""
        # <script type="application/ld+json">
        script_match = re.search(
            r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        if script_match:
            script = script_match.group(1).strip()
            script = json.loads(script)
            title = script.get('name', '')
            desc = script.get('description', '')
            video_cover = script.get('thumbnailUrl', '')
            embed_url = script.get('embedUrl', '')

        if not all([title, desc, video_cover]):
            h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if h1:
                title = h1.group(1).strip()
            else:
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', html)
                if title_match:
                    title = title_match.group(1).strip()
                else:
                    og_t = re.search(
                        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
                        html, re.IGNORECASE,
                    )
                    if og_t:
                        title = og_t.group(1).strip()

            # <p class="detail-hero__desc">
            desc_match = re.search(
                r'<p[^>]+class="detail-hero__desc"[^>]*>(.*?)</p>', html, re.DOTALL)
            if desc_match:
                desc = desc_match.group(1).strip()
            else:
                # <meta name="description" content="">
                desc_match = re.search(
                    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                if desc_match:
                    desc = desc_match.group(1).strip()
                else:
                    desc_match = re.search(
                        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                    if desc_match:
                        desc = desc_match.group(1).strip()

            for pat in (
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            ):
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    video_cover = m.group(1).replace('&amp;', '&')
                    break

            if not video_cover:
                img_m = re.search(r'<img[^>]+src="(/upload/[^"]+)"', html)
                if img_m:
                    video_cover = f"{self._BASE_URL}{img_m.group(1)}"

        return {
            "title": title,
            "desc": desc,
            "video_cover": video_cover,
            "embed_url": embed_url,
        }

    async def _get_chapter_info(self, drama_id: str, episode_id: str):
        url = self._LINK_EP % (drama_id, episode_id)
        html = await self._get_html(url)
        if not html:
            self.logger.debug("[!] ❌ Error fetching drama info")
            return None

        return {
            "html": html,
            "drama_id": drama_id,
            "episode_id": episode_id,
        }

    def _get_epsode_info_from_html(self, html: str):
        info = self._get_info_from_html(html)
        title = info["title"]
        desc = info["desc"]
        video_cover = info["video_cover"]
        video_url = ''

        if not video_url:
            m = re.search(
                r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*;?\s*</script>', html, re.DOTALL)
            if m:
                try:
                    player = json.loads(m.group(1))
                    player_url = player.get("url", "")
                    if player_url and ".m3u8" in player_url:
                        self.logger.debug(f"✅ Got M3U8 stream URL")
                        video_url = player_url
                    elif player_url and ".mp4" in player_url:
                        self.logger.debug(f"✅ Got MP4 URL")
                        video_url = player_url
                except json.JSONDecodeError as e:
                    self.logger.debug(
                        f"[ShortMovs] player_aaaa JSON parse error: {e}")

        if not video_url:
            # Fallback: search for any m3u8/mp4 URL from oss.shortmovs.com
            m = re.search(
                r'https?://oss\.shortmovs\.com/[^\s"\'<>]+\.m3u8', html)
            if m:
                self.logger.debug(f"✅ Got M3U8 stream URL (fallback)")
                video_url = m.group(0).replace(chr(92)+'/', '/')

        return {
            "title": title,
            # "desc": desc,
            "video_cover": video_cover,
            "video_url": video_url,
        }

    async def get_drama_info(self, url: str):
        url, drama_id = self.get_drama_id(url)
        if not drama_id:
            self.logger.error("❌ Invalid URL or no video ID found")
            return None

        html = await self._get_html(url)

        if not html:
            self.logger.debug("[!] ❌ Error fetching drama info")
            return None

        # get text for class "episode-list" first
        episode_list_match = re.search(
            r'<div[^>]+class="episode-list"[^>]*>(.*?)</body>', html, re.DOTALL)
        episode_list_text = None
        if episode_list_match:
            episode_list_text = episode_list_match.group(1)

        if not episode_list_text:
            return None

        info = self._get_info_from_html(html)
        title = info["title"]
        desc = info["desc"]
        video_cover = info["video_cover"]

        episodes = []
        seen = set()
        for m in re.finditer(
            rf'href="(/m/{re.escape(drama_id)}/(\d+)\.html)"',
            episode_list_text,
        ):
            href, ep_str = m.group(1), m.group(2)
            episode_id = int(ep_str)
            if episode_id in seen:
                self.logger.info(f"[!] ❌ Duplicate episode: {episode_id}")
                continue
            seen.add(episode_id)
            ep_url = self._LINK_EP % (drama_id, ep_str)
            episodes.append({
                "id": episode_id,
                "url": ep_url,
                "title": f"{title} EP{episode_id:02d}",
                "locked": False,
            })

        return {
            "title": title,
            "desc": desc,
            "book_id": drama_id,
            "chapterList": episodes,
            "video_cover": video_cover,
        }

    async def update_all_episodes(self, info, chunk_size=10):
        drama_id = info['book_id']
        tasks: list[asyncio.Task] = []
        for chunk in arr_chunk(info['chapterList'], chunk_size):
            async with asyncio.TaskGroup() as tg:
                for chapter_info in chunk:
                    episode_id = chapter_info['id']
                    if self._IS_TESTING:
                        self.logger.debug(
                            f"[!] 🔍 Fetching video info for episode: {episode_id}")
                    tasks.append(tg.create_task(
                        self._get_chapter_info(drama_id, episode_id)))

        result_count = 0
        for task in tasks:
            if task.exception():
                self.logger.error(
                    f"[!] ❌ Error fetching video info: {task.exception()}")
            else:
                result = task.result()
                if isinstance(result, dict) and result.get('html'):
                    data = self._get_epsode_info_from_html(result['html'])
                    episode_id = result['episode_id']
                    for i, chapter_info in enumerate(info['chapterList']):
                        if chapter_info['id'] == episode_id:
                            result_count += 1
                            chapter_info.update(data)
                            break
        if result_count > 0:
            self.logger.info(f"[!] ✅ Found {result_count} episodes")
        self._cache[drama_id] = info
        return info

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        temp_segments_dir_name: Optional[str] = None,
        output_file: str = "",
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
    ):
        # m3u8_url = self._TEST_URL_DOWNLOAD
        # match = re.search(r'/([^/]+)/index\.m3u8', m3u8_url)
        # temp_segments_dir_name = match.group(1) if match else None

        if not bool(output_file.strip()):
            output_file = f"{temp_segments_dir_name}.mp4"

        pattern = r'https?://t\.shortmovs\.com/[^\s"\'<>]+?segment_\d+\.ts'
        success = await self.download_m3u8(
            downloader,
            m3u8_url,
            pattern,
            output_file,
            temp_segments_dir_name,
            max_attempts,
            progress_callback,
        )
        return success

    async def download_all_episodes(
        self, info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False,
    ):
        downloader = AsyncTSVideoDownloader(max_concurrent=5)

        def custom_temp_segments_dir_name(chapter):
            match = re.search(r'/([^/]+)/index\.m3u8', chapter["video_url"])
            temp_segments_dir_name = match.group(1) if match else None
            return temp_segments_dir_name

        return await self._download_all_episodes_from_m3u8(
            downloader,
            info,
            keys_chaper_info={
                "video_url": "video_url",
                "temp_segments_dir_name": "id",
                "episode_number": "id",
                "custom_temp_segments_dir_name": custom_temp_segments_dir_name
            },
            output_dir=output_dir,
            with_site_name=with_site_name,
            max_attempts=max_attempts,
            progress_callback=progress_callback,
            is_test=is_test
        )

    async def download_segment_async(self, ts_url: str, index: int, retries: int = 1):
        """Download a single TS segment asynchronously with retry logic"""
        temp_dir = Path("temp_segments")
        temp_dir.mkdir(exist_ok=True)
        file_path = temp_dir / f"segment_{index:04d}.ts"

        self.max_concurrent = 1
        self.semaphore = Semaphore(self.max_concurrent)
        headers = {
            "Referer": f"{self._BASE_URL}/",
            "Origin": self._BASE_URL,
        }
        async with self.semaphore:
            for attempt in range(retries):
                try:
                    response = await self.request(ts_url, headers=headers, impersonate="safari172_ios")
                    if not response:
                        continue

                    if response.status_code == 200:
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(response.content)
                        return file_path
                    else:
                        self.logger.error(
                            f"Failed to download segment {index}: HTTP {response.status_code}")

                except Exception as e:
                    self.logger.error(
                        f"Error downloading segment {index} (attempt {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        # Exponential backoff
                        await asyncio.sleep(2 ** attempt)

            return None

    async def test_download_m3u8(self):
        m3u8_url = self._TEST_URL_DOWNLOAD
        headers = {
            "Referer": f"{self._BASE_URL}/",
            "Origin": self._BASE_URL,
        }
        resp = await self.request(m3u8_url, headers=headers, retries=0)
        if isinstance(resp, Response) and resp.status_code == 200:
            playlist = resp.text

            segment_urls = []
            for m in re.finditer(
                r'https?://t\.shortmovs\.com/[^\s"\'<>]+?segment_\d+\.ts',
                playlist,
            ):
                segment_urls.append(m.group(0))

            if not segment_urls:
                self.logger.info(f"❌ No streams found")
                return None

            # self.logger.info(playlist)
            self.logger.info("===============")
            self.logger.info(f"✅ Found {segment_urls[0]} streams")
            self.logger.info(f"✅ Found {len(segment_urls)} streams")
            for i, ts_url in enumerate(segment_urls):
                file_path = await self.download_segment_async(ts_url, index=i)
                if file_path:
                    self.logger.info(f"✅ Downloaded segment {i}")

    async def test_get_drama_info(self, url: Optional[str] = None):
        self._skip_cached_info = True
        url = url or f"{self._BASE_URL}/m/{self._TEST_DRAMA_ID}/1.html"
        video_url, drama_id = self.get_drama_id(url)
        if drama_id:
            url = self._LINK_ID % drama_id
            self.logger.info(f"Video URL: {url}, {drama_id}")

        info = await self.get_drama_info(url)
        if info:
            info = await self.update_all_episodes(info)
            self.save_test_data(info)
        return info


class RushShortsTvExtractor(DramaExtractorBase):
    _BASE_URL = "https://www.rushshortstv.com"
    _LINK_ID = "https://www.rushshortstv.com/video?id=%s"
    _BASE_CDN = "https://resource.rushshortstv.com"
    _CLOUD_FOLDER = "drama/rushshortstv"
    _SECRET_KEY = b"xGcSOxQ9azbXORYc"
    _APP_ID = "1005"

    _TEST_DRAMA_ID = "144"

    def _aes_encrypt(self, plaintext: str) -> str:
        """AES-128-ECB encrypt → uppercase hex string."""
        cipher = AES.new(self._SECRET_KEY, AES.MODE_ECB)
        padded = pad(plaintext.encode("utf-8"), AES.block_size)
        return binascii.hexlify(cipher.encrypt(padded)).decode("ascii").upper()

    def _aes_decrypt(self, hex_str: str) -> str:
        """AES-128-ECB decrypt from hex string → plaintext."""
        cipher = AES.new(self._SECRET_KEY, AES.MODE_ECB)
        raw = binascii.unhexlify(hex_str)
        return unpad(cipher.decrypt(raw), AES.block_size).decode("utf-8")

    def _make_token(self) -> str:
        """Generate an anonymous API token: appId + AES(JSON)."""
        data = {
            "uuid": str(uuid.uuid4()),
            "ip": "",
            "country": None,
            "language": "en-US",
            "os": "pc",
            "_fbp": "",
            "_fbc": "",
        }
        return f"{self._APP_ID}{self._aes_encrypt(json.dumps(data, separators=(',', ':')))}"

    def get_drama_id(self, url: str):
        """Extract video ID from URL."""
        match = re.search(r"[?&]id=(\d+)", url)
        if match:
            drama_id = match.group(1)
            url = self._LINK_ID % drama_id
            return url, drama_id

        match = re.search(r"/video/(\d+)", url)
        if match:
            drama_id = match.group(1)
            url = self._LINK_ID % drama_id
            return url, drama_id

        return url, None

    def _get_abs_media(self, path: str):
        if not path:
            return ""
        if str(path).startswith("http://") or str(path).startswith("https://"):
            return str(path)
        return f"{self._BASE_CDN}/{str(path).lstrip('/')}"

    async def _get_data_from_api(self, endpoint, params=None):
        """GET request to RushTv encrypted API. Returns parsed JSON data."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Token": self._make_token(),
            "Origin": self._BASE_URL,
            "Referer": f"{self._BASE_URL}/",
        }

        url = f"{self._BASE_URL}/api/{endpoint}"
        resp = await self.request(url, params=params, headers=headers)
        if not resp or resp.status_code != 200:
            self.logger.error(
                f"❌ API request failed: {resp.status_code if resp else 'No response'}")
            return None

        text = resp.text.strip().strip('"')

        try:
            dec = self._aes_decrypt(text)
            return json.loads(dec)
        except Exception:
            pass

        try:
            return resp.json()
        except Exception:
            self.logger.error(f"❌ Unparseable response: {text[:200]}")
            return None

    def get_cover_url(self, entry: dict):
        path = entry.get('coverUrl') or entry.get('video_cover')
        if path:
            return self._get_abs_media(path)
        return ''

    def get_video_url_play(self, entry: dict):
        path = entry.get('videoEncryptUrl')
        if path:
            return self._get_abs_media(path)
        return None

    async def get_drama_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch drama info from RushTv."""
        url, drama_id = self.get_drama_id(url)
        if not drama_id:
            self.logger.error("❌ Invalid URL or no video ID found")
            return None

        self.logger.info(f"🔄 Fetching drama info for ID: {drama_id}")

        endpoint = f"video/video/detail?videoId={drama_id}"

        result = await self._get_data_from_api(endpoint)
        if not result:
            self.logger.error("❌ Failed to get data from API")
            return None

        if result.get("code") != 200:
            self.logger.error(
                f"❌ API returned error: {result.get('msg', 'Unknown error')}")
            return None

        video_data = result.get("data", {})
        if not video_data:
            self.logger.error("❌ No video data found in response")
            return None

        title = video_data.get("videoName", "")
        if not title:
            self.logger.error("❌ No title found in video data")
            return None

        self.logger.info(f"✅ Found drama: {title}")

        cover = video_data.get("coverUrl", "")
        cover = self._get_abs_media(cover)
        desc = video_data.get("introduce", "")
        episode_list = video_data.get("episodeDetailList", [])
        total_episodes = video_data.get("episodeNumAll") or len(episode_list)

        status = {
            'collect_count': video_data.get("collectNum", 0),
            'fans_count': video_data.get("fansNum", 0),
            'like_count': video_data.get("likeNum", 0),
        }

        info = {
            "title": title,
            "url": url,
            "book_id": drama_id,
            "video_cover": cover,
            "desc": desc,
            "total_episodes": total_episodes,
            **status,
            "chapterList": episode_list,
        }
        self._cache[drama_id] = info
        return info

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        temp_segments_dir_name: Optional[str] = None,
        output_file: str = "",
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
    ):
        if not bool(output_file.strip()):
            output_file = f"{temp_segments_dir_name}.mp4"

        m3u8_path = urlparse(m3u8_url).path
        path_name_ext = m3u8_path.split("/")[-1]
        parent_url_path = m3u8_url.split(path_name_ext)[0]

        def pattern(content: str):
            # 000005.ts
            ts_urls = re.findall(
                r'#EXTINF:.*\n([^\s"\'<>]+?\d+\.ts)', content)
            if ts_urls and 'https://' not in ts_urls[0]:
                ts_urls = [parent_url_path + ts_url for ts_url in ts_urls]
            return ts_urls

        success = await self.download_m3u8(
            downloader,
            m3u8_url,
            pattern,
            output_file,
            temp_segments_dir_name,
            max_attempts,
            progress_callback,
        )
        return success

    async def download_all_episodes(
        self, info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False,
    ):
        downloader = AsyncTSVideoDownloader(max_concurrent=5)

        def custom_temp_segments_dir_name(chapter):
            m3u8_url = self.get_video_url_play(chapter)
            if not m3u8_url:
                return None
            match = re.search(r'/([^/]+)/index\.m3u8', m3u8_url)
            temp_segments_dir_name = match.group(1) if match else None
            return temp_segments_dir_name

        return await self._download_all_episodes_from_m3u8(
            downloader,
            info,
            keys_chaper_info={
                "video_url": lambda chapter: self.get_video_url_play(chapter),
                "temp_segments_dir_name": "episodeSort",
                "episode_number": "episodeSort",
                "custom_temp_segments_dir_name": custom_temp_segments_dir_name
            },
            output_dir=output_dir,
            with_site_name=with_site_name,
            max_attempts=max_attempts,
            progress_callback=progress_callback,
            is_test=is_test
        )

    async def test_get_drama_info(self, url: Optional[str] = None):
        self._skip_cached_info = True
        url = url or self._LINK_ID % self._TEST_DRAMA_ID
        video_url, drama_id = self.get_drama_id(url)
        self.logger.debug(f"Video URL: {video_url}, {drama_id}")
        info = await self.get_drama_info(url)
        if info:
            self.save_test_data(info)
        return info


class StardustTvExtractor(DramaExtractorBase):
    _BASE_URL = "https://www.stardusttv.net"
    _LINK_EP = "https://www.stardusttv.net/episodes/%s"
    _BASE_CDN_VIDEO = "https://mmcdn-v.stardust-tv.com"
    _BASE_CDN_IMAGE = "https://v.stardust-tv.com"
    _CLOUD_FOLDER = "drama/stardusttv"

    _TEST_DRAMA_ID = "01-playing-games-with-my-newfound-family-17862"

    def get_drama_id(self, url: str):
        """Extract drama ID from URL."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path.startswith("episodes/"):
            episode_slug = path[9:]
            url = self._LINK_EP % episode_slug
        else:
            episode_slug = None

        return url, episode_slug

    def get_cover_url(self, info: dict) -> str:
        return info.get('video_cover') or info.get('cover_snapshot_path', '')

    def get_video_url_play(self, entry: dict):
        cover = entry.get('snapshot_url')
        if cover:
            # .jpg | .png | .jpeg -> .m3u8
            path = urlparse(cover).path.replace("thumbnail_", "")
            if path.endswith(".jpg") or path.endswith(".png"):
                path = path[:-4] + ".m3u8"
            elif path.endswith(".jpeg"):
                path = path[:-5] + ".m3u8"
            return f"{self._BASE_CDN_VIDEO}{quote(path)}"
        return None

    @staticmethod
    def _extract_nuxt_raw(html_text):
        html_text = html_text or ""
        m = re.search(
            r'<script[^>]*id=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>',
            html_text,
            re.IGNORECASE | re.DOTALL,
        )
        return m.group(1) if m else ""

    @staticmethod
    def _resolve_devalue(arr, ref, cache=None, depth=0):
        if cache is None:
            cache = {}
        if depth > 20 or not isinstance(arr, list):
            return ref
        if not isinstance(ref, int) or ref < 0 or ref >= len(arr):
            return ref
        if ref in cache:
            return cache[ref]

        val = arr[ref]
        if val is None or isinstance(val, (str, bool, int, float)):
            cache[ref] = val
            return val

        # Nuxt devalue wrappers like ["ShallowReactive", 1]
        if isinstance(val, list):
            if len(val) == 2 and isinstance(val[0], str) and isinstance(val[1], int):
                if val[0] in ("ShallowReactive", "Reactive", "ShallowRef", "Ref"):
                    resolved = StardustTvExtractor._resolve_devalue(
                        arr, val[1], cache, depth + 1)
                    cache[ref] = resolved
                    return resolved
            resolved = []
            cache[ref] = resolved
            resolved.extend(
                StardustTvExtractor._resolve_devalue(
                    arr, item, cache, depth + 1)
                if isinstance(item, int) else item
                for item in val
            )
            return resolved

        if isinstance(val, dict):
            resolved = {}
            cache[ref] = resolved
            for key, value in val.items():
                resolved[key] = (
                    StardustTvExtractor._resolve_devalue(
                        arr, value, cache, depth + 1)
                    if isinstance(value, int) else value
                )
            return resolved

        cache[ref] = val
        return val

    @classmethod
    def _collect_nuxt_episode_data(cls, html_text: str):
        raw = cls._extract_nuxt_raw(html_text)
        if not raw:
            return {}, []

        try:
            arr = json.loads(raw)
        except Exception:
            return {}, []
        if not isinstance(arr, list):
            return {}, []

        episode_key_names = {
            "sort", "filepath", "name", "auto_filepath", "pre_filepath",
            "snapshot_url", "duration", "display_status",
        }
        video_info_key_names = {
            "english_name", "episode_total", "alioss_cover", "cover_path",
            "chinese_name", "cover_snapshot_path",
        }
        cache = {}
        candidate_video_info = {}
        episodes_by_sort = {}

        for idx, item in enumerate(arr):
            if not isinstance(item, dict):
                continue
            keys = set(item.keys())
            if len(keys & episode_key_names) >= 2:
                try:
                    resolved = cls._resolve_devalue(arr, idx, cache, 0)
                except Exception:
                    continue
                if isinstance(resolved, dict):
                    try:
                        sort_num = int(resolved.get("sort") or 0)
                    except (TypeError, ValueError):
                        sort_num = 0
                    if sort_num > 0 and sort_num not in episodes_by_sort:
                        episodes_by_sort[sort_num] = resolved
            if not candidate_video_info and len(keys & video_info_key_names) >= 2:
                try:
                    resolved_vi = cls._resolve_devalue(arr, idx, cache, 0)
                except Exception:
                    resolved_vi = {}
                if isinstance(resolved_vi, dict):
                    candidate_video_info = resolved_vi

        episodes = [episodes_by_sort[k] for k in sorted(episodes_by_sort)]
        return candidate_video_info, episodes

    async def _get_html_from_episode_url(self, url: str):
        resp = await self.request(url)
        if not resp or resp.status_code != 200:
            return None

        return resp.text

    async def get_drama_info(self, url: str):
        video_url, episode_slug = self.get_drama_id(url)
        self.logger.debug(f"Video URL: {video_url}, {episode_slug}")
        if not episode_slug:
            return None

        drama_id = episode_slug.split("-")[-1]
        html = await self._get_html_from_episode_url(url)
        if not html:
            return None
        info, episodes = self._collect_nuxt_episode_data(html)
        if info:
            info['title'] = info.get(
                'english_name') or info.get('chinese_name')
            info['video_cover'] = info.get('cover_path') or info.get(
                'cover_snapshot_path') or info.get('alioss_cover')
            info['chapterList'] = episodes

        self._cache[drama_id] = info
        return info

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        temp_segments_dir_name: Optional[str] = None,
        output_file: str = "",
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
    ):
        if not bool(output_file.strip()):
            output_file = f"{temp_segments_dir_name}.mp4"

        m3u8_path = urlparse(m3u8_url).path
        path_name_ext = m3u8_path.split("/")[-1]
        parent_url_path = m3u8_url.split(path_name_ext)[0]

        def pattern(content: str):
            # f4bde205d07a4e3bbccaf41e66dfce86/segment-2.ts
            ts_urls = re.findall(
                r'#EXTINF:.*\n([^\s"\'<>]+?\/[a-zA-Z]+-\d+\.ts)', content)
            if ts_urls and 'https://' not in ts_urls[0]:
                ts_urls = [parent_url_path + ts_url for ts_url in ts_urls]
            return ts_urls

        success = await self.download_m3u8(
            downloader,
            m3u8_url,
            pattern,
            output_file,
            temp_segments_dir_name,
            max_attempts,
            progress_callback,
        )
        return success

    async def download_all_episodes(
        self, info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False,
    ):
        downloader = AsyncTSVideoDownloader(max_concurrent=5)

        def custom_temp_segments_dir_name(chapter):
            m3u8_url = self.get_video_url_play(chapter)
            if not m3u8_url:
                return None
            match = re.search(r'/([^/]+)/([^/]+)\.m3u8', m3u8_url)
            temp_segments_dir_name = match.group(2) if match else None
            return temp_segments_dir_name

        return await self._download_all_episodes_from_m3u8(
            downloader,
            info,
            keys_chaper_info={
                "video_url": lambda chapter: self.get_video_url_play(chapter),
                "temp_segments_dir_name": "sort",
                "episode_number": "sort",
                "custom_temp_segments_dir_name": custom_temp_segments_dir_name
            },
            output_dir=output_dir,
            with_site_name=with_site_name,
            max_attempts=max_attempts,
            progress_callback=progress_callback,
            is_test=is_test
        )

    async def test_get_drama_info(self, url: Optional[str] = None):
        self._skip_cached_info = True
        url = url or self._LINK_EP % self._TEST_DRAMA_ID
        video_url, episode_slug = self.get_drama_id(url)
        self.logger.debug(f"Video URL: {video_url}, {episode_slug}")
        info = await self.get_drama_info(url)
        # info = self.load_test_data()
        if info:
            for chapter in info["chapterList"]:
                chapter['video_url'] = self.get_video_url_play(chapter)
            self.save_test_data(info)
        return info


class FlickreelsExtractor(DramaExtractorBase):
    _BASE_URL = "https://www.flickreels.net"
    _LINK_ID = "https://www.flickreels.net/video?id=%s"
    _BASE_CDN = "https://resource.flickreels.net"
    _CLOUD_FOLDER = "drama/flickreels"
    _SECRET_KEY = b"xGcSOxQ9azbXORYc"
    _APP_ID = "1005"

    _TEST_DRAMA_ID = "144"

    def _aes_encrypt(self, plaintext: str) -> str:
        """AES-128-ECB encrypt → uppercase hex string."""
        cipher = AES.new(self._SECRET_KEY, AES.MODE_ECB)
        padded = pad(plaintext.encode("utf-8"), AES.block_size)
        return binascii.hexlify(cipher.encrypt(padded)).decode("ascii").upper()

    def _aes_decrypt(self, hex_str: str) -> str:
        """AES-128-ECB decrypt from hex string → plaintext."""
        cipher = AES.new(self._SECRET_KEY, AES.MODE_ECB)
        raw = binascii.unhexlify(hex_str)
        return unpad(cipher.decrypt(raw), AES.block_size).decode("utf-8")

    def _make_token(self) -> str:
        """Generate an anonymous API token: appId + AES(JSON)."""
        data = {
            "uuid": str(uuid.uuid4()),
            "ip": "",
            "country": None,
            "language": "en-US",
            "os": "pc",
            "_fbp": "",
            "_fbc": "",
        }
        return f"{self._APP_ID}{self._aes_encrypt(json.dumps(data, separators=(',', ':')))}"

    def get_drama_id(self, url: str):
        """Extract video ID from URL."""
        match = re.search(r"[?&]id=(\d+)", url)
        if match:
            drama_id = match.group(1)
            url = self._LINK_ID % drama_id
            return url, drama_id

        match = re.search(r"/video/(\d+)", url)
        if match:
            drama_id = match.group(1)
            url = self._LINK_ID % drama_id
            return url, drama_id

        return url, None

    def _get_abs_media(self, path: str):
        if not path:
            return ""
        if str(path).startswith("http://") or str(path).startswith("https://"):
            return str(path)
        return f"{self._BASE_CDN}/{str(path).lstrip('/')}"

    async def _get_data_from_api(self, endpoint, params=None):
        """GET request to RushTv encrypted API. Returns parsed JSON data."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Token": self._make_token(),
            "Origin": self._BASE_URL,
            "Referer": f"{self._BASE_URL}/",
        }

        url = f"{self._BASE_URL}/api/{endpoint}"
        resp = await self.request(url, params=params, headers=headers)
        if not resp or resp.status_code != 200:
            self.logger.error(
                f"❌ API request failed: {resp.status_code if resp else 'No response'}")
            return None

        text = resp.text.strip().strip('"')

        try:
            dec = self._aes_decrypt(text)
            return json.loads(dec)
        except Exception:
            pass

        try:
            return resp.json()
        except Exception:
            self.logger.error(f"❌ Unparseable response: {text[:200]}")
            return None

    def get_cover_url(self, entry: dict):
        path = entry.get('coverUrl')
        if path:
            return self._get_abs_media(path)
        return None

    def get_video_url_play(self, entry: dict):
        path = entry.get('videoEncryptUrl')
        if path:
            return self._get_abs_media(path)
        return None

    async def get_drama_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch drama info from RushTv."""
        url, drama_id = self.get_drama_id(url)
        if not drama_id:
            self.logger.error("❌ Invalid URL or no video ID found")
            return None

        self.logger.info(f"🔄 Fetching drama info for ID: {drama_id}")

        endpoint = f"video/video/detail?videoId={drama_id}"

        result = await self._get_data_from_api(endpoint)
        if not result:
            self.logger.error("❌ Failed to get data from API")
            return None

        if result.get("code") != 200:
            self.logger.error(
                f"❌ API returned error: {result.get('msg', 'Unknown error')}")
            return None

        video_data = result.get("data", {})
        if not video_data:
            self.logger.error("❌ No video data found in response")
            return None

        title = video_data.get("videoName", "")
        if not title:
            self.logger.error("❌ No title found in video data")
            return None

        self.logger.info(f"✅ Found drama: {title}")

        cover = video_data.get("coverUrl", "")
        cover = self._get_abs_media(cover)
        desc = video_data.get("introduce", "")
        episode_list = video_data.get("episodeDetailList", [])
        total_episodes = video_data.get("episodeNumAll") or len(episode_list)

        status = {
            'collect_count': video_data.get("collectNum", 0),
            'fans_count': video_data.get("fansNum", 0),
            'like_count': video_data.get("likeNum", 0),
        }

        info = {
            "title": title,
            "url": url,
            "book_id": drama_id,
            "video_cover": cover,
            "desc": desc,
            "total_episodes": total_episodes,
            **status,
            "chapterList": episode_list,
        }
        self._cache[drama_id] = info
        return info

    async def download_m3u8_url(
        self,
        downloader: "AsyncTSVideoDownloader",
        m3u8_url: str,
        chapter: Dict[str, Any],
        temp_segments_dir_name: Optional[str] = None,
        output_file: str = "",
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
    ):
        if not bool(output_file.strip()):
            output_file = f"{temp_segments_dir_name}.mp4"

        m3u8_path = urlparse(m3u8_url).path
        path_name_ext = m3u8_path.split("/")[-1]
        parent_url_path = m3u8_url.split(path_name_ext)[0]

        def pattern(content: str):
            # 000005.ts
            ts_urls = re.findall(
                r'#EXTINF:.*\n([^\s"\'<>]+?\d+\.ts)', content)
            if ts_urls and 'https://' not in ts_urls[0]:
                ts_urls = [parent_url_path + ts_url for ts_url in ts_urls]
            return ts_urls

        success = await self.download_m3u8(
            downloader,
            m3u8_url,
            pattern,
            output_file,
            temp_segments_dir_name,
            max_attempts,
            progress_callback,
        )
        return success

    async def download_all_episodes(
        self, info: Dict[str, Any],
        output_dir: Optional[str] = None,
        with_site_name: bool = False,
        max_attempts: int = 2,
        progress_callback: Optional[Callable[["ProgressData"], None]] = None,
        is_test: bool = False,
    ):
        downloader = AsyncTSVideoDownloader(max_concurrent=5)

        def custom_temp_segments_dir_name(chapter):
            m3u8_url = self.get_video_url_play(chapter)
            if not m3u8_url:
                return None
            match = re.search(r'/([^/]+)/index\.m3u8', m3u8_url)
            temp_segments_dir_name = match.group(1) if match else None
            return temp_segments_dir_name

        return await self._download_all_episodes_from_m3u8(
            downloader,
            info,
            keys_chaper_info={
                "video_url": lambda chapter: self.get_video_url_play(chapter),
                "temp_segments_dir_name": "episodeSort",
                "episode_number": "episodeSort",
                "custom_temp_segments_dir_name": custom_temp_segments_dir_name
            },
            output_dir=output_dir,
            with_site_name=with_site_name,
            max_attempts=max_attempts,
            progress_callback=progress_callback,
            is_test=is_test
        )

    async def test_get_drama_info(self, url: Optional[str] = None):
        self._skip_cached_info = True
        url = url or self._LINK_ID % self._TEST_DRAMA_ID
        video_url, drama_id = self.get_drama_id(url)
        self.logger.debug(f"Video URL: {video_url}, {drama_id}")
        info = await self.get_drama_info(url)
        if info:
            self.save_test_data(info)
        return info


# if __name__ == "__main__":
#     # test_drama_extractor()
#     # asyncio.run(fetch_drama_episodes())

#     dramabox = DramaBoxExtractor()
#     asyncio.run(dramabox.test_get_drama_info())
