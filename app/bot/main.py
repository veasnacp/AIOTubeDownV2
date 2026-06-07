import io
import os
import sys
import re
import asyncio
import shutil
import tempfile
from pathlib import Path
import time
from typing import Optional
from curl_cffi.requests import AsyncSession, request
from loguru import logger
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
from yt_dlp import YoutubeDL


from ..core.download_worker import DownloaderBase
from ..core.extract_manager import extract_url_list, BASE_EXTRACTORS, TYPE_EXTRACTOR
from ..config.settings import settings
from ..extractor._utils import safe_filename
# Add project root to sys.path to run directly or as a module
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Queue for handling downloads sequentially (prevents Telegram blocks and CPU/network overload)
task_queue = asyncio.Queue()

# Load credentials from Environment or Settings Manager
API_ID = int(os.environ.get("TELEGRAM_API_ID")
             or settings.get("telegram_api_id") or 0)
API_HASH = os.environ.get("TELEGRAM_API_HASH") or settings.get(
    "telegram_api_hash") or ""
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or settings.get(
    "telegram_bot_token") or ""

# URL regex pattern
URL_PATTERN = re.compile(r'https?://[^\s/$.?#].[^\s]*', re.IGNORECASE)


def find_urls(text: str) -> list[str]:
    """Finds all URLs in a given string text"""
    return URL_PATTERN.findall(text)


def format_size(size_bytes: int) -> str:
    """Formats raw bytes into a human-readable string format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class ThrottledUpdater:
    """Helper class to throttle Telegram message edits during file uploads to avoid FloodWait"""

    def __init__(self, status_msg, prefix="", interval=3.0):
        self.status_msg = status_msg
        self.prefix = prefix
        self.interval = interval
        self.last_update = 0.0

    def callback(self, current, total):
        now = asyncio.get_event_loop().time()
        if now - self.last_update >= self.interval or current == total:
            self.last_update = now
            percent = (current / total) * 100 if total else 0
            text = f"{self.prefix} **{percent:.1f}%** ({format_size(current)} / {format_size(total)})"
            # Schedule the async message editing without blocking Telethon client's upload
            asyncio.get_event_loop().create_task(self.safe_edit(text))

    async def safe_edit(self, text):
        try:
            await self.status_msg.edit(text)
        except Exception as e:
            logger.debug(f"Throttled progress edit failed: {e}")


class Extractor:
    def __init__(
        self,
        task_id: str,
        urls: list[str],
        extract_options: Optional[dict] = None
    ):
        self.task_id = task_id
        self.urls = urls
        self.with_url_dl = False
        self.is_profile = False
        self.cancel = False

        self.extract_options = {}
        self.update_extract_options(extract_options)

        self.limit = 2
        self.use_per_next_cursor = False
        self.extract_video_type = "videos"

        self.on_stop_worker = self.on_stop_extraction

    def on_stop_extraction(self):
        pass

    def on_start(self, task_id: str, data: dict):
        pass

    def on_progress(self, task_id: str, data: dict):
        pass

    def on_finished(self, task_id: str, data: dict):
        pass

    def on_error(self, task_id: str, error: dict):
        pass

    def update_extract_options(self, extract_options: Optional[dict] = None):
        if isinstance(extract_options, dict):
            self.extract_options.update(extract_options)

    async def run(self):
        self.update_extract_options({
            'limit': self.limit,
            'use_per_next_cursor': self.use_per_next_cursor,
            'youtube_video_type': self.extract_video_type,
        })
        if self.is_profile:
            return []
        else:
            return await self.extract_video_info_list()

    async def extract_video_info_list(self):
        extract_dict = extract_url_list(self.urls)

        for key, value in extract_dict.items():
            if key.split("_")[0] in BASE_EXTRACTORS and len(value) > 0:
                extractor_class = BASE_EXTRACTORS[key.split("_")[0]]
                return await self.run_extractor(extractor_class, value)

        return []

    async def run_extractor(self, extractor_class: TYPE_EXTRACTOR, url_list: list[str]):
        try:
            async with extractor_class() as scout:
                scout.cancel = self.cancel
                scout.set_test_mode(True)

                extractor_name = None
                try:
                    cookies = self.extract_options.get("cookies") or {}
                    extractor_name = scout._CLOUD_FOLDER.split("/")[-1]
                    raw_cookie = cookies.get(extractor_name)
                    if hasattr(scout, "set_cookies") and raw_cookie:
                        scout.set_cookies(raw_cookie)
                except Exception as e:
                    scout.logger.debug(f"Set cookies error: {e}")

                def on_callback_progress(d):
                    if d['status'] == 'progress':
                        self.on_progress(self.task_id, d)
                    elif d['status'] == 'finished':
                        self.on_finished(self.task_id, d)
                    elif d['status'] == 'error':
                        self.on_error(self.task_id, d)

                scout.on_extracting = on_callback_progress
                if extractor_name:
                    self.on_start(self.task_id, {
                        'status': 'start',
                        'extractor': f"{extractor_name}".upper(),
                    })
                if hasattr(scout, "get_video_info_list_yt_dlp"):
                    info_list = await scout.get_video_info_list_yt_dlp(url_list)
                else:
                    info_list = await scout.get_video_info_list(url_list)

                if info_list:
                    scout.save_test_data(info_list)

                self.on_finished(self.task_id, {
                    'status': 'finished',
                    'data': info_list
                })
                return info_list

        except Exception as e:
            self.on_error(self.task_id, {
                'status': 'error',
                'error': str(e)
            })
            return []


def generic_extract(url: str) -> list[dict]:
    """Synchronous fallback extractor using yt_dlp"""
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            return []
        if 'entries' in info:
            return [entry for entry in info['entries'] if entry]
        return [info]


async def extract_video_info(url: str) -> list[dict]:
    task_id = str(time.time())
    extractor = Extractor(task_id=task_id, urls=[url])
    return await extractor.run()


async def extract_video_info_v1(url: str) -> list[dict]:
    """Classifies URL and uses the corresponding app extractor class to parse video details"""
    classified = extract_url_list([url])

    extractor_key = None
    url_list = None
    for key, value in classified.items():
        if len(value) > 0:
            extractor_key = key.split("_")[0]
            url_list = value
            break

    if not extractor_key or extractor_key not in BASE_EXTRACTORS:
        try:
            return await asyncio.to_thread(generic_extract, url)
        except Exception as e:
            logger.error(f"Generic extraction failed for {url}: {e}")
            return []

    extractor_class = BASE_EXTRACTORS[extractor_key]
    try:
        async with extractor_class() as scout:
            scout.set_test_mode(True)

            # Load specific site cookies from settings if available
            cookie_key = f"{extractor_key}_cookie"
            cookie_val = settings.get(cookie_key)
            if hasattr(scout, "set_cookies") and cookie_val:
                try:
                    scout.set_cookies(cookie_val)
                except Exception as e:
                    logger.error(
                        f"Failed to set cookies for {extractor_key}: {e}")

            if hasattr(scout, "get_video_info_list_yt_dlp"):
                info_list = await scout.get_video_info_list_yt_dlp(url_list)
            else:
                info_list = await scout.get_video_info_list(url_list)
            return info_list or []
    except Exception as e:
        logger.error(f"Extractor {extractor_key} failed for {url}: {e}")
        # Fallback to generic extractor
        try:
            return await asyncio.to_thread(generic_extract, url)
        except Exception as e2:
            logger.error(f"Fallback extraction failed: {e2}")
            return []


def download_media(url: str, info: dict, is_mp3: bool, temp_dir: str) -> tuple[str, str, str]:
    options = {
        "resolution": "720",
        "mp3": is_mp3,
        "thumbnail": False,
        "with_site": False,
        "with_username": False,
    }
    task_id = str(time.time())
    filename = info.get('title')
    donwloader = DownloaderBase(
        task_id, url, temp_dir, filename, info, options)

    _info, is_both, video_url, audio_url = donwloader.select_format_for_yt_dlp(
        int(options['resolution']))

    if info.get('extractor') == '__youtube':
        finalpath = donwloader.pre_run()
    else:
        finalpath = video_url
    return finalpath, video_url, audio_url


def download_media_v1(url: str, is_mp3: bool, temp_dir: str) -> str:
    """Synchronous download function run in a separate executor thread"""
    has_ffmpeg = shutil.which("ffmpeg") is not None

    if is_mp3:
        fmt = "bestaudio/best"
    else:
        if has_ffmpeg:
            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        else:
            fmt = "best[ext=mp4]/best"

    outtmpl = os.path.join(temp_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': fmt,
        'outtmpl': outtmpl,
        'noplaylist': True,
        'overwrites': True,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4' if (not is_mp3 and has_ffmpeg) else None,
    }

    if is_mp3 and has_ffmpeg:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        base_path, _ = os.path.splitext(filename)
        expected_exts = ['mp3'] if is_mp3 else ['mp4', 'mkv', 'webm', 'm4a']
        for ext in expected_exts:
            candidate = f"{base_path}.{ext}"
            if os.path.exists(candidate):
                return candidate
        if os.path.exists(filename):
            return filename

        # Fallback directory scan matching basename
        dirname = os.path.dirname(filename)
        basename = os.path.basename(base_path)
        if os.path.exists(dirname):
            for f in os.listdir(dirname):
                if f.startswith(basename):
                    return os.path.join(dirname, f)
        return filename


async def send_large_video(client: TelegramClient, chat: str, url: str, **kwargs):
    try:
        # 1. Download video data stream cleanly via curl_cffi
        async with AsyncSession() as session:
            response = await session.get(url, stream=True, timeout=None)

            if response.status_code != 200:
                raise Exception(
                    f"Failed to fetch video: HTTP {response.status_code}")

            video_stream = io.BytesIO()
            async for chunk in response.aiter_content(chunk_size=65536):
                video_stream.write(chunk)

            video_stream.seek(0)

        # 2. Package dimensions and formatting parameters
        # Replace these numbers with your video details if known (Duration, Width, Height)
        # Standard placeholder values (like duration=0, w=1280, h=720) will force the layout change.
        video_attributes = DocumentAttributeVideo(
            # Duration in seconds (0 works as an auto-fallback)
            duration=0,
            w=1280,                   # Width pixel footprint
            h=720,                    # Height pixel footprint
            supports_streaming=True   # Explicitly inside the attributes wrapper
        )

        # 3. Transmit video payload forcing a rendering box format
        await client.send_file(
            chat,
            video_stream,
            # Instructs Telegram to parse as a playable video box
            attributes=[video_attributes],
            force_document=False,            # Disables generic document wrapper fallback
            video_note=False,
            **kwargs
        )
        print("Video display layout sent successfully.")

    except Exception as e:
        print(f"Error handling large video display stream: {e}")


async def process_task(task):
    """Processes a single download task sequentially"""
    event = task['event']
    url = task['url']
    chat_id = task['chat_id']
    is_mp3 = task['is_mp3']
    status_msg = task['wait_msg']

    # 1. Extraction Phase
    await status_msg.edit("⚙️ **Extracting video details...**")
    info_list = await extract_video_info(url)
    if not info_list:
        await status_msg.edit("❌ **Extraction Failed.**\nMake sure the link is supported, public, and not region-locked.")
        return

    info = info_list[0]
    title = info.get('title') or 'extracted_media'

    extractor = (info.get('extractor') or "").lower()
    is_force_download = extractor in ['__youtube']

    # 2. Download Phase
    await status_msg.edit("📥 **Downloading media to server...**")
    temp_dir = tempfile.mkdtemp()
    try:
        # Run blocking download in a separate thread pool thread
        filepath, video_url, audio_url = await asyncio.to_thread(download_media, url, info, is_mp3, temp_dir)
        logger.info(f"Download completed: {filepath}")

        if (is_force_download) and (not filepath or not os.path.exists(filepath)):
            await status_msg.edit("❌ **Download Failed.**\nCould not fetch the video stream from source.")
            return

        if is_force_download:
            file_size = os.path.getsize(filepath)

        # 3. Upload Phase
        await status_msg.edit("📤 **Preparing to upload to Telegram...**")
        updater = ThrottledUpdater(
            status_msg, prefix="📤 **Uploading to Telegram:**", interval=3.0)

        attributes = []
        if not is_mp3:
            duration = int(info.get('duration') or 0)
            width = int(info.get('width') or 0)
            height = int(info.get('height') or 0)
            if duration or width or height:
                attributes.append(DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                ))

        # Send file with upload progress callback
        cdn_url = video_url and 'cdn' in video_url
        if is_force_download:
            target_send_file = filepath
        else:
            # if not cdn_url:
            #     res = request("GET", video_url,
            #                   impersonate="chrome120", allow_redirects=True)
            #     video_url = res.url
            #     logger.info(f"Video URL: {video_url}")
            target_send_file = video_url or filepath
        try:
            logger.info(f"is_force_download: {is_force_download}")
            logger.info(f"cdn_url: {cdn_url}")
            logger.info(f"send file: {not is_force_download and cdn_url}")
            test = True
            if test:
                logger.info(f"Sending large video: {target_send_file}")
                await send_large_video(
                    client=event.client,
                    chat=chat_id,
                    url=target_send_file,
                    caption=f"🎥 **{title}**\n\nDownloaded via AIOTubeDown Bot",
                    file_name=f"video.mp4",
                    mime_type="video/mp4",
                    # attributes=attributes,
                    reply_to=event.message.id,
                    progress_callback=updater.callback
                )
            else:
                await event.client.send_file(
                    chat_id,
                    target_send_file,
                    caption=f"🎥 **{title}**\n\nDownloaded via AIOTubeDown Bot",
                    attributes=attributes,
                    reply_to=event.message.id,
                    progress_callback=updater.callback
                )
        except Exception as e:
            logger.error(f"Failed to upload file {filepath}: {e}")
            # Send media message if available
            if video_url and audio_url:
                await event.client.send_message(
                    chat_id, f"🎥 **{title}**\n\n[Download Link]({video_url})\n[Audio Download Link]({audio_url})\n\nDownloaded via AIOTubeDown Bot", reply_to=event.message.id)
            elif video_url:
                await event.client.send_message(
                    chat_id, f"🎥 **{title}**\n\n[Download Link]({video_url})\n\nDownloaded via AIOTubeDown Bot", reply_to=event.message.id)
            elif audio_url:
                await event.client.send_message(
                    chat_id, f"🎥 **{title}**\n\n[Download Link]({audio_url})\n\nDownloaded via AIOTubeDown Bot", reply_to=event.message.id)

        # Remove status message once file is uploaded successfully
        await status_msg.delete()

    except Exception as e:
        logger.exception(e)
        await status_msg.edit(f"❌ **Task Failed:** {str(e)}")
    finally:
        # Clean up temp folder files
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Failed to delete temp dir {temp_dir}: {e}")


async def queue_consumer():
    """Sequentially processes tasks from the request queue"""
    while True:
        task = await task_queue.get()
        try:
            await process_task(task)
        except Exception as e:
            logger.error(f"Queue consumer task execution error: {e}")
        finally:
            task_queue.task_done()


async def main():
    if not API_ID or not API_HASH or not BOT_TOKEN:
        logger.critical(
            "Telegram credentials not configured!\n"
            "Please configure TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_BOT_TOKEN environment variables "
            "or set them inside your app configuration settings."
        )
        return

    logger.info("Initializing Telethon Client...")
    client = TelegramClient('aiotubedown_bot', API_ID, API_HASH)

    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        await event.reply(
            "👋 **Welcome to AIOTubeDown Bot!**\n\n"
            "Send me any video/audio link from YouTube, TikTok, Facebook, Douyin, Kuaishou, etc., "
            "and I will download and send it to you.\n\n"
            "💡 **Commands:**\n"
            "• `/mp3 <link>` - Download as MP3 audio\n"
            "• `/help` - Show usage instructions"
        )

    @client.on(events.NewMessage(pattern='/help'))
    async def help_handler(event):
        await event.reply(
            "📖 **Usage Guide:**\n\n"
            "1. Copy the URL/link of the video you want to download.\n"
            "2. Paste it here in the chat.\n"
            "3. The bot will automatically queue, download, and send the file directly to you.\n\n"
            "🎧 **Audio Only:**\n"
            "Prefix your link with `/mp3`, for example:\n"
            "`/mp3 https://www.youtube.com/watch?v=...`"
        )

    @client.on(events.NewMessage)
    async def message_handler(event):
        text = event.message.text
        if not text or text.startswith('/start') or text.startswith('/help'):
            return

        is_mp3 = False
        if text.startswith('/mp3'):
            is_mp3 = True
            text = text[4:].strip()

        urls = find_urls(text)
        if not urls:
            if event.message.text.startswith('/'):
                return  # Ignore unrecognized commands
            await event.reply("❌ No valid links found. Please send a valid video or audio URL.")
            return

        for url in urls:
            # Calculate queue position
            position = task_queue.qsize() + 1

            # Send initial queued status
            wait_msg = await event.reply(
                f"⏳ **Request Queued!**\n"
                f"🔗 Link: `{url}`\n"
                f"👥 Position in queue: `{position}`\n"
                f"Please wait. We process requests sequentially to avoid rate-limiting blocks."
            )

            # Add to sequential processing queue
            await task_queue.put({
                'event': event,
                'url': url,
                'chat_id': event.chat_id,
                'user_id': event.sender_id,
                'message_id': event.message.id,
                'is_mp3': is_mp3,
                'wait_msg': wait_msg
            })

    # Start sequential queue worker in background
    consumer_task = asyncio.create_task(queue_consumer())

    # Start bot client session
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Bot client connected and running!")

    try:
        await client.run_until_disconnected()
    finally:
        consumer_task.cancel()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user.")
