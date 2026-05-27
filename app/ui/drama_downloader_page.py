import asyncio
import copy
import hashlib
import os
import re
import urllib.request
from pathlib import Path
from typing import Callable, Optional, TypeAlias, Union
from urllib.parse import urlparse

from curl_cffi import requests
from curl_cffi.requests import AsyncSession, Session
from loguru import logger
from PySide6.QtCore import (
    QEvent,
    QObject,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    QTime,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6Addons import (
    Action,
    BodyLabel,
    CaptionLabel,
    FlowLayout,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MenuIndicatorType,
)
from PySide6Addons import PrimaryPushButton as _PrimaryPushButton
from PySide6Addons import (
    ProgressBar,
    PushButton,
    ScrollArea,
    StateToolTip,
    SubtitleLabel,
    TabBar,
    TabCloseButtonDisplayMode,
    TogglePushButton,
    ToolButton,
    isDarkTheme,
    setFont,
)

from ..components.icons import FileIcon
from ..components.override import CardWidget, CheckableMenu, NumberInput
from ..components.override import TextAreaInput as TextEdit
from ..components.override import TextInput as LineEdit
from ..components.override import TransparentDropDownToolButton, TransparentToolButton
from ..components.player import VideoPlayerDialog
from ..core._worker import DefaultWorker
from ..extractor._utils import safe_filename
from ..extractor.drama import (
    DramaBiteExtractor,
    DramaBoxExtractor,
    DramaExtractorBase,
    ProgressData,
    ReelShortExtractor,
    RushShortsTvExtractor,
    ShortMovsExtractor,
    StardustTvExtractor,
)
from ..extractor.extends_drama import (
    FacebookExtractor,
    KuaishouExtractor,
    TikTokExtractor,
    YouTubeExtractor,
)
from ..theme import Colors, DarkMode, LightMode
from ..utils.path import reveal_file
from ..utils.validation import is_valid_url


class PrimaryPushButton(_PrimaryPushButton):
    def setStyleSheet(self, styleSheet: str, /) -> None:
        styleSheet = f"{styleSheet}PrimaryPushButton{{color: {Colors.gray_9};}}"
        return super().setStyleSheet(styleSheet)


TYPE_DRAMA_EXTRACTOR: TypeAlias = Optional[Union[
    'DramaExtractorBase',
    'DramaBiteExtractor', 'DramaBoxExtractor',
    'ReelShortExtractor', 'RushShortsTvExtractor',
    'ShortMovsExtractor', 'StardustTvExtractor',
    'KuaishouExtractor', 'TikTokExtractor', 'YouTubeExtractor',
    'FacebookExtractor'
]]


REGEX_DRAMA = [
    (DramaBiteExtractor._BASE_URL, DramaBiteExtractor),
    (DramaBoxExtractor._BASE_URL, DramaBoxExtractor),
    (ReelShortExtractor._BASE_URL, ReelShortExtractor),
    (RushShortsTvExtractor._BASE_URL, RushShortsTvExtractor),
    (ShortMovsExtractor._BASE_URL, ShortMovsExtractor),
    (StardustTvExtractor._BASE_URL, StardustTvExtractor),
    (KuaishouExtractor._BASE_URL, KuaishouExtractor),
    (TikTokExtractor._BASE_URL, TikTokExtractor),
    (YouTubeExtractor._BASE_URL, YouTubeExtractor),
    (FacebookExtractor._BASE_URL, FacebookExtractor),
]

DRAMA_ICONS = {
    "all_drama_downloader": FileIcon.LOGO,
    "dramabox_downloader": FileIcon.DRAMABOX_LOGO,
    "reelshort_downloader": FileIcon.REELSHORT_LOGO,
    "dramabite_downloader": FileIcon.DRAMABITE_LOGO,
    "shortmovs_downloader": FileIcon.SHORTMOVS_LOGO,
    "rushshortstv_downloader": FileIcon.RUSHSHORTSTV_LOGO,
    "stardusttv_downloader": FileIcon.STARDUSTTV_LOGO,
    "kuaishou_downloader": FileIcon.KUAISHOU_LOGO,
    "tiktok_downloader": FileIcon.TIKTOK_LOGO,
    "youtube_downloader": FileIcon.YOUTUBE_LOGO,
    "facebook_downloader": FileIcon.FACEBOOK_LOGO
}

BASEIE_PROFILES = [
    "kuaishou",
    "tiktok",
    "youtube",
    "facebook",
]

CACHE_DRAMA = {}


class DramaExtractTask(DefaultWorker):
    def __init__(self, task_id: int):
        super().__init__(task_id)


class ScrapeSignals(QObject):
    """Signals for the scrape worker"""
    finished = Signal(dict, str)  # info, info_key
    progress = Signal(dict)  # dict[status, url, data(video_info)]
    error = Signal(str)


class ScrapeWorker(QRunnable):
    """Worker task to run async scrape in the background"""

    def __init__(self, extractor: TYPE_DRAMA_EXTRACTOR, url, info_key, tab_id: Optional[str] = None):
        super().__init__()
        self.extractor = copy.copy(extractor) if extractor else None
        self.url = url
        self.info_key = info_key
        self._info: Optional[dict] = None
        self.signals = ScrapeSignals()
        self.mode = "normal"
        self.url_episodes_selected: Optional[list[str]] = None
        self.refresh_build_id_key: Optional[str] = None
        self.options = {
            "limit": None,
            "sort_by": "newest",
            "next_data": None,
            "cursor_continue": "",
            "cursor_position": 0,
            "use_per_next_cursor": True,
            "content_type": "videos",
            "page_id": None
        }
        self.more: Optional[str] = None
        self.tab_id = tab_id
        self.logger = logger.bind(tab_id=self.tab_id)
        if self.extractor:
            self.extractor.logger = self.extractor.logger.bind(
                tab_id=self.tab_id)

    async def update_all_episodes(self, info: dict):
        has_episodes_updated = info.get('episodes_updated', False)
        if not has_episodes_updated \
                and hasattr(self.extractor, 'update_all_episodes') \
                and callable(self.extractor.update_all_episodes):
            self.logger.info(
                f"Updating all episodes for {info.get('drama_title')}")
            new_info = await self.extractor.update_all_episodes(info)
            if new_info:
                for chapter in new_info["chapterList"]:
                    if 'video_url' in chapter:
                        break
                    chapter['video_url'] = self.extractor.get_video_url_play(
                        chapter)
                new_info['episodes_updated'] = True
                info.update(new_info)

        return info

    async def update_episodes_selected(self, url_list: list[str], info: dict):
        if hasattr(self.extractor, 'update_episodes_selected') \
                and callable(self.extractor.update_episodes_selected):
            self.logger.info(
                f"Updating {len(url_list)} episodes for {info.get('drama_title')}")
            info = await self.extractor.update_episodes_selected(url_list, info)
            if info and not hasattr(self.extractor, "_EXTENDS_NAME"):
                has_all_video_url = all(bool(self.extractor.get_video_url_play(
                    chapter)) for chapter in info["chapterList"])
                if has_all_video_url:
                    info['episodes_updated'] = True

        return info

    def on_extracting(self, d):
        self.signals.progress.emit(d)

    def run(self):
        async def _scrape():
            # Reset session for the current thread's event loop to prevent "loop closed" errors
            try:
                if hasattr(self.extractor, 'session') and self.extractor.session:
                    try:
                        await self.extractor.session.close()
                    except Exception:
                        pass
                    try:
                        await self.extractor.session_sync.close()
                    except Exception:
                        pass
            except Exception:
                pass

            # Create a fresh session bound to the current loop
            self.extractor.session = AsyncSession(
                impersonate=getattr(self.extractor, 'impersonate', 'safari170'))
            self.extractor.session_sync = Session(
                impersonate=getattr(self.extractor, 'impersonate', 'safari170'))

            if hasattr(self.extractor, 'get_profile_info'):
                self.extractor.on_extracting = self.on_extracting

            if self.refresh_build_id_key:
                build_id = self.extractor._get_build_id()
                CACHE_DRAMA[self.refresh_build_id_key] = self.extractor._BUILD_ID

                return

            if isinstance(self._info, dict) and self.mode == "update":
                if self.url_episodes_selected:
                    info = await self.update_episodes_selected(self.url_episodes_selected, self._info.copy())
                    self.url_episodes_selected = None
                else:
                    info = await self.update_all_episodes(self._info.copy())
                self._info = None
                self.mode = "normal"
                return info

            self.extractor.set_test_mode(True)
            # info = await self.extractor.test_get_drama_info(self.url)
            info = self.extractor.load_test_data('_drama')
            # info = self._info.copy() if isinstance(self._info, dict) else None
            if not info:
                if hasattr(self.extractor, 'get_profile_info'):
                    limit = self.options["limit"]
                    self.options = self.extractor.get_next_options(
                        more=self.more)
                    if self.more == 'all':
                        self.options["limit"] = limit
                    info = await self.extractor.get_profile_info(
                        self.url,
                        **self.options
                    )
                else:
                    info = await self.extractor.get_drama_info(self.url)
                if info:
                    self.extractor.save_test_data(info, '_drama')
            elif isinstance(info, dict):
                chapter_list = info.get("chapterList")
                if self.more and chapter_list:
                    limit = self.options["limit"]
                    self.options = self.extractor.get_next_options(
                        chapter_list, more=self.more)
                    if self.more == 'all':
                        self.options["limit"] = limit
                    self.logger.debug(f"options: {self.options}")
                    _info = await self.extractor.get_profile_info(
                        self.url,
                        **self.options
                    )
                    if _info and _info.get("chapterList"):
                        info["chapterList"].extend(_info["chapterList"])

            if isinstance(info, dict):
                self._info = info.copy()

            return info

        try:
            # Use asyncio.run for robust loop management and cleanup
            info = asyncio.run(_scrape())

            # self.extractor.set_test_mode(True)
            # # info = asyncio.run(self.extractor.test_get_drama_info())
            # info = self.extractor.load_test_data()

            if isinstance(info, dict):
                self.signals.finished.emit(info, self.info_key)
            else:
                if self.refresh_build_id_key:
                    self.refresh_build_id_key = None
                    self.signals.finished.emit(None, self.info_key)
                    return
                self.signals.error.emit("Failed to scrape drama info")
        except Exception as e:
            self.logger.error(f"ScrapeWorker error: {e}")
            self.signals.error.emit(str(e))


class DownloadSignals(QObject):
    """Signals for the YoutubeDL worker"""
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(dict)


class DramaDownloadWorker(QRunnable):
    """Worker task to run async YoutubeDL in the background"""

    def __init__(self, extractor: TYPE_DRAMA_EXTRACTOR, info, output_dir, tab_id: Optional[str] = None):
        super().__init__()
        self.extractor = copy.copy(extractor) if extractor else None
        self.info = info
        self.output_dir = output_dir
        self.signals = DownloadSignals()
        self.tab_id = tab_id
        self.logger = logger.bind(tab_id=self.tab_id)
        if self.extractor:
            self.extractor.logger = self.extractor.logger.bind(
                tab_id=self.tab_id)

    def on_progress_callback(self, data: "ProgressData"):
        self.signals.progress.emit({
            'current': data.current,
            'total': data.total,
            'description': data.description,
            'percentage': data.percentage,
            'timestamp': data.timestamp,
            'downloaded': data.downloaded,
            'failed': data.failed,
            'batch_num': data.batch_num,
            'total_batches': data.total_batches,
            'remaining': data.remaining,
            'speed': data.speed,
        })

    def run(self):
        async def _download():
            # Reset session for the current thread's event loop to prevent "loop closed" errors
            try:
                # Close old session if it exists to clean up pending tasks/timers
                if hasattr(self.extractor, 'session') and self.extractor.session:
                    await self.extractor.session.close()
            except Exception:
                pass

            # Create a fresh session bound to the current loop
            self.extractor.session = AsyncSession(
                impersonate=getattr(self.extractor, 'impersonate', 'safari170'))

            return await self.extractor.download_all_episodes(
                self.info,
                str(self.output_dir),
                with_site_name=True,
                progress_callback=self.on_progress_callback,
                is_test=False
            )

        try:
            data = asyncio.run(_download())
            if isinstance(data, dict):
                self.signals.finished.emit(data)
        except Exception as e:
            self.logger.error(f"Download error: {e}")
            self.signals.error.emit(str(e))


class ImageLoadSignals(QObject):
    """Signals for the image loader task"""
    result = Signal(QImage)
    error = Signal(str)


class ImageLoadTask(QRunnable):
    """Worker task to fetch and decode images in the background"""

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = ImageLoadSignals()

    def open_request(self, url):
        # Add User-Agent to prevent blocking
        req = urllib.request.Request(
            url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x44) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()

        return data

    def run(self):
        logger.debug(f"ImageLoadTask url: {self.url}")
        try:

            resp = requests.get(self.url, impersonate='safari170', verify=True)
            data = resp.content

            image = QImage()
            if image.loadFromData(data):
                self.signals.result.emit(image)
            else:
                self.signals.error.emit("Invalid image format")
        except Exception as e:
            try:
                data = self.open_request(self.url)
                image = QImage()
                if image.loadFromData(data):
                    self.signals.result.emit(image)
                else:
                    self.signals.error.emit("Invalid image format")
            except Exception as e:
                self.signals.error.emit(str(e))


class ImageLoaderLabel(QLabel):
    """Robust image label that loads content in a background thread and fits aspect ratio perfectly"""

    def __init__(self, text_placeholder="No Image", parent=None):
        super().__init__(parent)
        self.text_placeholder = text_placeholder
        self.placeholder_path = "path/to/your/placeholder.png"
        self.radius = 12 + 6
        self.setAlignment(Qt.AlignCenter)
        self._cache = {}  # url -> QPixmap

    def hash_url(self, url: str):
        return hashlib.md5(url.encode()).hexdigest()

    def loadImage(self, url_str: str):
        """Dispatches a background worker to load the image"""
        if not url_str:
            self._set_placeholder()
            return

        self.setText("Loading...")

        if self.hash_url(url_str) in self._cache:
            pixmap = self._cache[self.hash_url(url_str)]
            self.setPixmap(pixmap)
            return

        self.task = ImageLoadTask(url_str)
        self.task.signals.result.connect(self._on_image_loaded)
        self.task.signals.error.connect(self._on_load_error)
        QThreadPool.globalInstance().start(self.task)

    def _on_image_loaded(self, image: QImage):
        """Runs in main thread: converts QImage to QPixmap and displays it"""
        pixmap = QPixmap.fromImage(image)
        if not pixmap.isNull():
            rounded_pixmap = self._get_rounded_pixmap(pixmap, self.radius)
            self.setPixmap(rounded_pixmap)
            self._cache[self.hash_url(self.task.url)] = rounded_pixmap
        else:
            self._set_placeholder()

    def _on_load_error(self, error_msg: str):
        """Runs in main thread: logs error and shows placeholder"""
        logger.error(f"Image load failed: {error_msg}")
        self._set_placeholder()

    def _get_rounded_pixmap(self, pixmap, radius):
        """Scales the pixmap to fill target size maintaining aspect ratio (Aspect Fill) and applies rounded corners"""
        target_size = self.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            target_size = QSize(270, 360)

        # Scale keeping aspect ratio by expanding to cover the target size
        scaled = pixmap.scaled(
            target_size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )

        # Center crop the scaled pixmap to the target size
        x = (scaled.width() - target_size.width()) // 2
        y = (scaled.height() - target_size.height()) // 2
        cropped = scaled.copy(x, y, target_size.width(), target_size.height())

        # Render rounded corners
        rounded = QPixmap(target_size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        path = QPainterPath()
        path.addRoundedRect(0, 0, target_size.width(),
                            target_size.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)
        painter.end()

        return rounded

    def _set_placeholder(self):
        """Sets the label to the local placeholder or text"""
        placeholder = QPixmap(self.placeholder_path)
        if not placeholder.isNull():
            rounded_placeholder = self._get_rounded_pixmap(
                placeholder, self.radius)
            self.setPixmap(rounded_placeholder)
        else:
            self.setText(self.text_placeholder)

    def cleanup(self):
        if hasattr(self, 'task') and self.task:
            try:
                self.task.signals.result.disconnect()
            except Exception:
                pass
            try:
                self.task.signals.error.disconnect()
            except Exception:
                pass
            self.task = None


class DramaCard(CardWidget):
    """Individual drama card for the grid"""
    selected = Signal(str, int)  # title, ep_count

    def __init__(self, title, ep_count, poster_path=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.ep_count = ep_count
        self.setFixedSize(160, 240)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 5)
        self.layout.setSpacing(5)
        self.setCursor(Qt.PointingHandCursor)

        # Poster Image
        self.poster = QLabel(self)
        self.poster.setFixedSize(160, 200)
        self.poster.setScaledContents(True)
        self.poster.setStyleSheet(
            "border-radius: 8px; background-color: #2c2c2c;")
        self.layout.addWidget(self.poster)

        # Title
        self.title_label = CaptionLabel(title, self)
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.selected.emit(self.title, self.ep_count)


class EpisodeButton(TogglePushButton):
    """Custom toggle button for episodes"""

    def __init__(self, num, is_vip=False, parent=None):
        super().__init__(parent)
        self.num = num
        self.is_vip = is_vip
        self.setFixedSize(60, 40)
        if is_vip:
            self.setText(f"🔏{str(num)}")
        else:
            self.setText(str(num))

    def setStyleSheet(self, styleSheet: str, /) -> None:
        styleSheet = f"""
        {styleSheet}
        PushButton, PushButton[hasIcon=false], PushButton[hasIcon=true] {{padding: 0px;}}
        """
        return super().setStyleSheet(styleSheet)


class DramaSidebar(ScrollArea):
    """Left sidebar for selected drama details"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_downloader = parent
        self.logger = logger.bind(
            tab_id=parent.objectName() if parent else None)
        self.setFixedWidth(300)
        self.view = CardWidget(self, Colors.gray_0, DarkMode.card)
        self.vBoxlayout = QVBoxLayout(self.view)
        self.vBoxlayout.setContentsMargins(15, 15, 15, 15)
        self.vBoxlayout.setSpacing(4)

        # Large Poster
        self.poster = ImageLoaderLabel("Drama Poster", self)
        # Perfect 3:4 Aspect Ratio (270x360)
        self.poster.setFixedSize(270, 360)
        # Let center-cropped Aspect Fill render beautifully
        self.poster.setScaledContents(False)
        self.poster.setAlignment(Qt.AlignCenter)
        self.poster._set_placeholder()
        self.poster_border_color = LightMode.primary
        self.poster.setStyleSheet(
            f"border-radius: 12px; background-color: {Colors.alpha(Colors.gray_6, 0.4)}; font-size: 20px; font-weight: bold; color: gray; border: 2px solid {self.poster_border_color};")
        self.vBoxlayout.addWidget(self.poster, 0, Qt.AlignCenter)

        self.play_btn_container = QWidget(self)
        self.play_btn_container.hide()
        self.play_btn_container.setStyleSheet("background-color: transparent;")
        self.play_btn_container_layout = QHBoxLayout(self.play_btn_container)
        self.play_btn_container_layout.setContentsMargins(0, 0, 0, 0)
        self.play_btn_container_layout.setSpacing(10)

        self.play_btn = PrimaryPushButton("Play", self)
        self.play_btn_container_layout.addWidget(self.play_btn)
        self.vBoxlayout.addWidget(self.play_btn_container)

        self.check_video_btn = ToolButton(FluentIcon.ROTATE, self)
        self.check_video_btn.setToolTip("Check Video")
        self.play_btn_container_layout.addWidget(self.check_video_btn)
        self.check_video_btn.hide()

        # Scroll area to handle long titles
        self.title_scroll = ScrollArea(self)
        self.title_scroll.setWidgetResizable(True)
        self.title_scroll.setFixedHeight(50)  # Enough for 2 lines
        self.title_scroll.setStyleSheet("border: none;")
        self.title_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.title_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Drama Info
        self.title = BodyLabel("Drama Title", self)
        font = self.title.font()
        font.setBold(True)
        font.setPointSize(10)
        self.title.setFont(font)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setMinimumWidth(self.poster.width() - 10)
        self.title.setMaximumWidth(260)
        self.title.adjustSize()
        self.title_scroll.setWidget(self.title)
        self.vBoxlayout.addWidget(self.title_scroll, 0, Qt.AlignCenter)
        self.vBoxlayout.addStretch()

        # Stats
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        # EPs Count Widget Container with 8px radius and dashed border
        self.ep_widget = QWidget(self)
        self.ep_widget.setObjectName("epWidget")
        self.ep_widget.setFixedHeight(50)
        self.ep_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.ep_widget.setStyleSheet(
            f"#epWidget {{ border: 2px dashed {Colors.alpha(self.poster_border_color, 0.7)}; border-radius: 8px; background-color: {Colors.alpha(Colors.gray_6, 0.15)}; }}"
        )
        self.ep_widget_layout = QVBoxLayout(self.ep_widget)
        self.ep_widget_layout.setContentsMargins(5, 8, 5, 8)
        self.ep_widget_layout.setSpacing(0)

        self.ep_count = BodyLabel("0\nEPs", self.ep_widget)
        self.ep_count.setAlignment(Qt.AlignCenter)
        self.ep_count.setStyleSheet(self.ep_count.styleSheet(
        ) + "BodyLabel{border: none; background: transparent;}")
        self.ep_widget_layout.addWidget(self.ep_count)

        # Selected Count Widget Container with 8px radius and dashed border
        self.selected_widget = QWidget(self)
        self.selected_widget.setObjectName("selectedWidget")
        self.selected_widget.setFixedHeight(50)
        self.selected_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.selected_widget.setStyleSheet(
            f"#selectedWidget {{ border: 2px dashed {Colors.alpha(self.poster_border_color, 0.7)}; border-radius: 8px; background-color: {Colors.alpha(Colors.gray_6, 0.15)}; }}"
        )
        self.selected_widget_layout = QVBoxLayout(self.selected_widget)
        self.selected_widget_layout.setContentsMargins(5, 8, 5, 8)
        self.selected_widget_layout.setSpacing(0)

        self.selected_count = BodyLabel("0\nSelected", self.selected_widget)
        self.selected_count.setAlignment(Qt.AlignCenter)
        self.selected_count.setStyleSheet(
            self.selected_count.styleSheet() + "BodyLabel{border: none; background: transparent;}")
        self.selected_widget_layout.addWidget(self.selected_count)

        stats_layout.addWidget(self.ep_widget)
        stats_layout.addWidget(self.selected_widget)
        self.vBoxlayout.addLayout(stats_layout, 1)

        self.info: dict = {}
        self.current_selected_chapter: Optional[dict] = None
        self.extractor: TYPE_DRAMA_EXTRACTOR = DramaExtractorBase()
        self.extractor._CLOUD_FOLDER = ''
        self.output_dir = self.extractor.get_output_dir()

        self.download_workers = set()
        self.update_info_workers = set()

        self.path_layout = QHBoxLayout()

        self.path_edit = LineEdit(self)
        self.path_edit.setPlaceholderText("Save Path...")
        self.path_edit.setText(str(self.output_dir))
        self.path_edit.setReadOnly(True)
        self.path_edit.textChanged.connect(self.path_changed)

        self.open_folder_btn = ToolButton(FluentIcon.LINK, self)
        self.open_folder_btn.setToolTip("Open Download Directory")
        self.open_folder_btn.clicked.connect(self.open_directory)

        self.browse_btn = PushButton("Browse", self)
        self.browse_btn.setToolTip("Select Directory")
        self.browse_btn.clicked.connect(self.browse_path)

        self.path_layout.addWidget(self.path_edit)
        self.path_layout.addWidget(self.open_folder_btn)
        self.path_layout.addWidget(self.browse_btn)
        self.vBoxlayout.addLayout(self.path_layout)

        self.btn_action_layout = QHBoxLayout()
        self.download_btn = PrimaryPushButton(
            FluentIcon.DOWNLOAD, "Download Selected", self)
        self.cancel_btn = PushButton("Cancel", self)
        self.cancel_btn.setToolTip("Cancel Download")

        self.btn_action_layout.addWidget(self.cancel_btn)
        self.btn_action_layout.addWidget(self.download_btn)
        self.vBoxlayout.addLayout(self.btn_action_layout)

        self.setWidget(self.view)
        self.enableTransparentBackground()
        self.setWidgetResizable(True)
        # show scroll bar on hover
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.check_video_btn.clicked.connect(self.check_video)
        self.play_btn.clicked.connect(self.play_video)
        self.download_btn.clicked.connect(self.download_selected)
        self.cancel_btn.clicked.connect(self.cancel_all)

    def cleanup(self):
        # Cleanup poster task
        if hasattr(self, 'poster') and self.poster:
            self.poster.cleanup()

        # Disconnect all update info workers
        for worker in list(self.update_info_workers):
            try:
                worker.signals.finished.disconnect()
            except Exception:
                pass
            try:
                worker.signals.error.disconnect()
            except Exception:
                pass
        self.update_info_workers.clear()

        # Disconnect all download workers
        for worker in list(self.download_workers):
            try:
                worker.signals.progress.disconnect()
            except Exception:
                pass
            try:
                worker.signals.finished.disconnect()
            except Exception:
                pass
            try:
                worker.signals.error.disconnect()
            except Exception:
                pass
        self.download_workers.clear()

    def show_play_btn(self):
        self.play_btn_container.show()
        # if hasattr(self.extractor, '_EXTENDS_NAME'):
        #     self.play_btn_container.show()
        # else:
        #     self.play_btn_container.hide()

    def open_directory(self):
        if not self.current_selected_chapter:
            return

        output_file = self.current_selected_chapter.get('output_file')
        if output_file:
            path = Path(output_file)
        else:
            path = Path(self.path_edit.text()) / \
                safe_filename(self.title.text())

        if path and path.exists():
            if output_file:
                reveal_file(str(path))
            else:
                os.startfile(str(path))

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.output_dir = Path(path)
            self.path_edit.setText(str(self.output_dir))

    def path_changed(self, text):
        self.path_edit.setToolTip(text)

    def check_video(self):
        if not self.current_selected_chapter:
            return
        chapter = self.current_selected_chapter.copy()
        if hasattr(self.extractor, '_EXTENDS_NAME'):
            if chapter.get('sd') and chapter.get('hd'):
                return
            url = chapter.get('url')
        else:
            video_id = chapter.get(
                'chapter_id') or self.extractor.get_chapter_id(chapter)
            # use video_id as url for drama site
            url = video_id

        if not url:
            self.logger.warning("[!] ⚠️ Video URL not found")
            return

        update_worker = ScrapeWorker(
            self.extractor, '', self.info.get('info_key', ''), tab_id=self.parent_downloader.objectName())
        update_worker._info = self.info.copy()
        update_worker.mode = "update"
        update_worker.url_episodes_selected = [url]
        if hasattr(self.extractor, 'update_episodes_selected') \
                and callable(self.extractor.update_episodes_selected):
            self.update_info_workers.add(update_worker)  # Register worker

            def _on_update_info_finished(info, info_key, extractor, worker=None, download=False):
                self._on_update_info_finished(
                    info, info_key, extractor, worker, download)
                self.check_video_btn.hide()

            update_worker.signals.finished.connect(
                lambda i, k, w=update_worker: _on_update_info_finished(i, k, self.extractor, w, download=False))
            update_worker.signals.error.connect(
                lambda e, w=update_worker: self._on_update_info_error(e, w))
            QThreadPool.globalInstance().start(update_worker)
            return

    def play_video(self):
        dialog = VideoPlayerDialog(self.window())
        if not self.current_selected_chapter:
            return

        video_url = self.extractor.get_video_url_play(
            self.current_selected_chapter)

        dialog_title = self.current_selected_chapter.get('title')
        if not dialog_title and hasattr(self.extractor, 'get_chapter_id'):
            video_id = self.extractor.get_chapter_id(
                self.current_selected_chapter)
            if video_id:
                dialog_title = video_id

        output_file = self.current_selected_chapter.get('output_file')
        if output_file:
            path = Path(output_file)
            video_url = output_file if path.exists() else video_url

        if not video_url:
            self.check_video_btn.show()
            self.logger.warning("[!] ⚠️ Video URL not found")
            return
        if not self.check_video_btn.isHidden():
            self.check_video_btn.hide()

        self.logger.debug(f'chapter: {self.current_selected_chapter}')
        if 'width' in self.current_selected_chapter and 'height' in self.current_selected_chapter:
            width = self.current_selected_chapter['width']
            height = self.current_selected_chapter['height']
            if width < height:
                dialog.resizePortrait()
            else:
                dialog.resizeLandscape()
        else:
            dialog.resizePortrait()
        dialog.setVideo(video_url, dialog_title)
        dialog.play()
        dialog.show()

    def download_selected(self):
        if self.selected_count.text() == "0\nSelected" or not self.extractor:
            return

        downloader = self.parent()
        if not downloader or not hasattr(downloader, 'ep_buttons'):
            return

        # Filter chapters based on selected episode buttons
        selected_chapters = []
        for i, btn in enumerate(downloader.ep_buttons):
            if btn.isChecked():
                if i < len(self.info.get('chapterList', [])):
                    selected_chapters.append(self.info['chapterList'][i])

        if not selected_chapters:
            self.logger.warning("No episodes selected for download.")
            return

        update_worker = ScrapeWorker(
            self.extractor, '', self.info.get('info_key', ''), tab_id=self.parent_downloader.objectName())
        update_worker._info = self.info.copy()
        update_worker.mode = "update"
        has_episodes_updated = self.info.get('episodes_updated', False)
        if not has_episodes_updated \
                and hasattr(self.extractor, 'update_all_episodes') \
                and callable(self.extractor.update_all_episodes):
            has_episodes_selected_func = hasattr(
                self.extractor, 'update_episodes_selected')
            if has_episodes_selected_func and len(selected_chapters) == len(self.info.get('chapterList', [])):
                update_worker.url_episodes_selected = None
            else:
                if hasattr(self.extractor, '_EXTENDS_NAME'):
                    update_worker.url_episodes_selected = [
                        self.extractor.get_chapter_url(chapter)
                        for chapter in selected_chapters
                    ]
                else:
                    update_worker.url_episodes_selected = [
                        chapter.get(
                            'chapter_id') or self.extractor.get_chapter_id(chapter)
                        for chapter in selected_chapters
                    ]

            self.update_info_workers.add(update_worker)  # Register worker

            update_worker.signals.finished.connect(
                lambda i, k, w=update_worker: self._on_update_info_finished(i, k, self.extractor, w))
            update_worker.signals.error.connect(
                lambda e, w=update_worker: self._on_update_info_error(e, w))
            QThreadPool.globalInstance().start(update_worker)
            return

        self._download_selected(selected_chapters)

    def _on_update_info_finished(self, info, info_key, extractor: TYPE_DRAMA_EXTRACTOR, worker=None, download=True):
        """
        Callback for successful scrape completion
        """
        self.info.update(info)
        if info_key:
            CACHE_DRAMA[info_key] = self.info
        if worker and worker in self.update_info_workers:
            self.update_info_workers.remove(worker)

        if not download:
            return

        downloader = self.parent()
        selected_chapters = []
        for i, btn in enumerate(downloader.ep_buttons):
            if btn.isChecked():
                if i < len(self.info.get('chapterList', [])):
                    selected_chapters.append(self.info['chapterList'][i])

        if not selected_chapters:
            self.logger.warning("No episodes selected for download.")
            return

        self._download_selected(selected_chapters)

    def _on_update_info_error(self, error, worker=None):
        """
        Callback for failed scrape completion
        """
        if worker and worker in self.update_info_workers:
            self.update_info_workers.remove(worker)

        self.logger.error(f"Failed to update info: {error}")

    def _download_selected(self, selected_chapters):
        # Create a copy of info with only selected chapters to avoid caching issues
        download_info = self.info.copy()
        download_info['chapterList'] = selected_chapters

        self.logger.info(
            f"Downloading {len(selected_chapters)} selected episodes...")

        worker = DramaDownloadWorker(
            self.extractor,
            download_info,
            self.output_dir,
            tab_id=self.parent_downloader.objectName()
        )
        self.download_workers.add(worker)

        worker.signals.progress.connect(self.on_download_progress)
        worker.signals.finished.connect(
            lambda d, w=worker: self.on_download_finished(d, w))
        worker.signals.error.connect(
            lambda d, w=worker: self.on_download_error(d, w))
        QThreadPool.globalInstance().start(worker)

    def on_download_progress(self, d):
        """
        Callback for download progress
        """
        downloader = self.parent()
        if not downloader or not isinstance(downloader, DramaDownloader):
            return

        downloader.progress_bar.setValue(int(d['percentage']))
        downloader.progress_bar.setFormat(
            f"{d['downloaded']}/{d['total']} ({d['percentage']}%) - {d['speed']}")

    def on_download_finished(self, data, worker=None):
        """
        Callback for successful download completion
        """
        self.logger.info(
            f"✅ Download finished: {len(data['success'])} success, {len(data['failed'])} failed")
        if 'info' in data and isinstance(data['info'], dict):
            info = data['info']
            self.info.update(info)
            info_key = self.info.get('info_key', '')

            if info_key:
                CACHE_DRAMA[info_key] = self.info
        if worker and worker in self.download_workers:
            self.download_workers.remove(worker)

    def on_download_error(self, error_info, worker=None):
        """
        Callback for download errors
        """
        self.logger.error(f"Download error: {error_info}")
        if worker and worker in self.download_workers:
            self.download_workers.remove(worker)

    def download_progress(self, d):
        global total, downloaded, speed_str, eta_str
        # if self._is_cancelled:
        #     raise Exception("Cancelled by user")

        total = 0
        downloaded = 0
        speed_str = ""
        eta_str = ""

        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

            speed_str = self.format_speed(speed)
            eta_str = self.format_eta(eta)

            self.logger.info(
                f"Progress: {downloaded}/{total} ({downloaded/total*100:.2f}%)")
            self.logger.info(f"Speed: {speed_str}")
            self.logger.info(f"ETA: {eta_str}")
        elif d['status'] == 'finished':
            self.logger.info(f"Finished: {d['filename']}")

    def cancel_all(self):
        self.logger.info("Canceling all downloads...")
        if self.selected_count.text() == "0\nSelected" or not self.extractor:
            return

        self.extractor.stop_download()

    def format_speed(self, speed):
        if not speed:
            return "0 B/s"
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} TB/s"

    def format_eta(self, seconds):
        if not seconds:
            return "0s"
        mins, secs = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        return f"{hours}h {mins}m {secs}s" if hours > 0 else (f"{mins}m {secs}s" if mins > 0 else f"{secs}s")


class DramaDownloader(QWidget):
    """Main Drama Downloader Interface"""

    def __init__(self, parent: 'DramaDownloaderPage', object_name="all_drama_downloader"):
        super().__init__(parent)
        self.main_page = parent
        self.setObjectName(object_name)
        self.info_key = None

        self.logger = logger.bind(tab_id=object_name)
        self.sink_id = None
        self.scrape_workers = set()  # Registry to keep worker references alive
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        # 1. Right Content Area
        self.content_area = QVBoxLayout()
        self.main_layout.addLayout(self.content_area)

        # 2. Left Sidebar
        self.sidebar = DramaSidebar(self)
        self.main_layout.addWidget(self.sidebar)

        # 2.1 Top Search Bar
        self.search_widget = CardWidget(self)
        self.search_layout = QHBoxLayout(self.search_widget)
        self.search_layout.setContentsMargins(10, 10, 10, 10)
        self.search_layout.setSpacing(10)
        self.url_edit = LineEdit(self.search_widget)
        self.url_edit.setPlaceholderText(
            f"Paste {object_name.split('_')[0].capitalize()} Page or Episode URL...")
        # bind enter key to scrape button
        self.url_edit.returnPressed.connect(self.scrape_episode)
        self.scrape_btn = PrimaryPushButton(FluentIcon.SEARCH, "Scrape", self)
        self.scrape_btn.clicked.connect(self.scrape_episode)
        self.search_layout.addWidget(self.url_edit)
        self.search_layout.addWidget(self.scrape_btn)
        self.content_area.addWidget(self.search_widget)

        self.episode_view = QWidget()
        self.episode_layout = QVBoxLayout(self.episode_view)
        self.episode_layout.setContentsMargins(0, 0, 0, 0)

        self.ep_header = CardWidget()
        self.ep_header_layout = QHBoxLayout(self.ep_header)

        self.ep_title = SubtitleLabel("Episodes", self.ep_header)
        self.ep_range = BodyLabel("", self.ep_header)
        self.ep_range.setStyleSheet(f"color: {LightMode.primary}")

        # self.ep_header_layout.addWidget(self.back_btn)
        self.ep_header_layout.addWidget(
            self.ep_title, alignment=Qt.AlignCenter)
        self.ep_header_layout.addWidget(
            self.ep_range, alignment=Qt.AlignCenter)
        self.ep_header_layout.addStretch(1)

        self.select_all_btn = TogglePushButton(self.ep_header)
        self.select_all_btn.setText("Select All")
        self.select_all_btn.clicked.connect(self.toggle_all_episodes)
        self.ep_header_layout.addWidget(self.select_all_btn)

        self.episode_layout.addWidget(self.ep_header)

        self.scroll_area = ScrollArea(self)

        self.empty_eps_widget = CardWidget(self.scroll_area)
        self.empty_eps_layout = QVBoxLayout(self.empty_eps_widget)
        self.empty_eps_not_found = "No episodes found"
        self.empty_eps_label = SubtitleLabel(
            "Episode will be shown here", self.empty_eps_widget)
        self.empty_eps_label.setAlignment(Qt.AlignCenter)
        self.empty_eps_layout.addWidget(
            self.empty_eps_label, 0, Qt.AlignCenter)

        self.stackWidget = QStackedWidget(self.scroll_area)

        self.grid_container = CardWidget(self.scroll_area)
        self.ep_grid_layout = FlowLayout(self.grid_container)
        self.ep_grid_layout.setSpacing(8)
        self.ep_grid_layout.setContentsMargins(8, 8, 8, 8)

        self.stackWidget.addWidget(self.empty_eps_widget)
        self.stackWidget.addWidget(self.grid_container)
        self.stackWidget.setCurrentWidget(self.empty_eps_widget)
        self.scroll_area.setWidget(self.stackWidget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.enableTransparentBackground()
        self.episode_layout.addWidget(self.scroll_area, 1)

        self.content_area.addWidget(self.episode_view)

        self.view_more_episode: Optional[str] = None
        self.view_more_widget = QWidget()
        self.view_more_layout = QHBoxLayout(self.view_more_widget)
        self.view_more_layout.setContentsMargins(0, 0, 0, 0)
        self.view_more_limit = NumberInput(self)
        self.view_more_limit.setValue(30)
        self.view_more_limit.setMinimumWidth(80)
        self.view_more_limit.setMinimum(0)
        self.view_more_limit.setMaximum(5000)
        self.view_more_limit.setSymbolVisible(False)
        self.view_more_btn = PrimaryPushButton("View More", self)
        self.view_all_btn = PrimaryPushButton("View All", self)

        class PrimaryPushButtonCustom(PrimaryPushButton):
            def setStyleSheet(self, styleSheet: str, /) -> None:
                styleSheet = f"{styleSheet}PrimaryPushButton{{background-color: {Colors.red_6}; color: {Colors.gray_7}; border-color: {Colors.red_4}; border-bottom-color: {Colors.dark_3};}}PrimaryPushButton::hover{{background-color: {Colors.red_5}; border-color: {Colors.red_5}; border-bottom-color: {Colors.dark_3};}}"
                return super().setStyleSheet(styleSheet)

        self.view_more_stop_btn = PrimaryPushButtonCustom("Stop", self)
        self.view_more_layout.addStretch(1)
        self.view_more_layout.addWidget(self.view_more_limit)
        self.view_more_layout.addWidget(self.view_more_btn)
        self.view_more_layout.addWidget(self.view_all_btn)
        self.view_more_layout.addWidget(self.view_more_stop_btn)
        self.content_area.addWidget(self.view_more_widget)
        self.view_more_widget.hide()

        # 2.5 Bottom Log and Progress
        self.log_area = QVBoxLayout()
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.log_area.addWidget(self.progress_bar)

        log_header = QHBoxLayout()
        log_header.setContentsMargins(0, 0, 0, 0)
        log_header.setSpacing(8)
        log_header.addStretch(1)
        log_header.addWidget(CaptionLabel("Log", self))
        self.clear_btn = TransparentToolButton(FluentIcon.DELETE, self)
        log_header.addWidget(self.clear_btn)
        self.log_area.addLayout(log_header)

        self.log_output = TextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(120)
        self.log_output.setPlaceholderText('...')
        self.log_area.addWidget(self.log_output)

        self.loading_bar: Optional[StateToolTip] = None
        # Safe logging: add sink and store ID
        self.sink_id = self.logger.add(
            self.scroll_to_bottom,
            level="INFO",
            filter=lambda record: record["extra"].get(
                "tab_id") == self.objectName(),
            format="[{time:HH:mm:ss}] {message}",
        )
        self.clear_btn.clicked.connect(
            lambda: self.log_output.setPlainText(""))

        self.view_more_btn.clicked.connect(self.on_view_more_episodes)
        self.view_all_btn.clicked.connect(self.on_view_all_episodes)
        self.view_more_stop_btn.clicked.connect(self.on_stop_scraping)
        # self.sink_id = self.logger.add(
        #     self.log_output.append,
        #     level="DEBUG",
        #     enqueue=True,
        #     format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        # )

        # self.test_show_episodes("Heart Thief", 70)
        self.content_area.addLayout(self.log_area)

    def is_profile_page(self):
        object_name = self.objectName().lower()
        if object_name.startswith("all"):
            object_name = urlparse(self.url_edit.text()).netloc.lower()
        return next(
            (True for name in BASEIE_PROFILES if name in object_name), False)

    def cleanup(self):
        # 1. Clean up sidebar workers and poster tasks
        if hasattr(self, 'sidebar') and self.sidebar:
            try:
                self.sidebar.cleanup()
            except Exception as e:
                logger.debug(f"Exception during sidebar cleanup: {e}")

        # 2. Clean up scrape workers in this page
        if hasattr(self, 'scrape_workers') and self.scrape_workers:
            for worker in list(self.scrape_workers):
                try:
                    worker.signals.finished.disconnect()
                except Exception:
                    pass
                try:
                    worker.signals.error.disconnect()
                except Exception:
                    pass
            self.scrape_workers.clear()

        # 3. Clean up loguru logger sink
        if self.sink_id is not None:
            try:
                self.logger.remove(self.sink_id)
            except Exception as e:
                logger.debug(f"Exception during loguru sink removal: {e}")
            self.sink_id = None

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def resizeEvent(self, event):
        if self.loading_bar:
            self._move_loading_bar(self.loading_bar)
        return super().resizeEvent(event)

    def scroll_to_bottom(self, msg: str):
        try:
            self.log_output.append(msg.strip())
            self.log_output.verticalScrollBar().setValue(
                self.log_output.verticalScrollBar().maximum())
        except Exception as e:
            self.logger.debug(f"Exception in scroll_to_bottom: {e}")

    def test_show_episodes(self, title, count):
        self.ep_range.setText(f"(1-{count})")
        self.sidebar.title.setText(title)
        self.sidebar.ep_count.setText(f"{count}\nEPs")

        # Clear existing grid safely
        while self.ep_grid_layout.count():
            item = self.ep_grid_layout.takeAt(0)
            if item:
                item.deleteLater()

        # Add episode buttons
        self.ep_buttons = []
        for i in range(1, count + 1):
            btn = EpisodeButton(i, is_vip=(i > 15),
                                parent=self.grid_container)
            btn.toggled.connect(self.update_selection_count)
            self.ep_grid_layout.addWidget(btn)
            self.ep_buttons.append(btn)

        # Connect bulk selection
        try:
            self.select_all_btn.clicked.disconnect()
        except:
            pass

        self.select_all_btn.clicked.connect(self.toggle_all_episodes)

    def show_episodes(self, title, count):
        self.ep_range.setText(f"1-{count}")
        self.sidebar.title.setText(title)
        self.sidebar.ep_count.setText(f"{count}\nEPs")

        # Clear existing grid safely
        while self.ep_grid_layout.count():
            item = self.ep_grid_layout.takeAt(0)
            if item:
                item.deleteLater()

        # Add episode buttons
        self.ep_buttons = []
        for i in range(1, count + 1):
            btn = EpisodeButton(i, is_vip=(i > 7),
                                parent=self.grid_container)
            btn.toggled.connect(self.update_selection_count)
            self.ep_grid_layout.addWidget(btn)
            self.ep_buttons.append(btn)

        # Connect bulk selection
        try:
            self.select_all_btn.clicked.disconnect()
        except:
            pass

        self.select_all_btn.clicked.connect(self.toggle_all_episodes)

    def append_new_episodes(self, start_idx, count):
        """Appends new episode buttons to the flow layout without clearing existing ones"""
        self.ep_range.setText(f"1-{count}")
        self.sidebar.ep_count.setText(f"{count}\nEPs")

        if not hasattr(self, 'ep_buttons'):
            self.ep_buttons = []

        for i in range(start_idx, count + 1):
            btn = EpisodeButton(i, is_vip=(i > 7), parent=self.grid_container)
            btn.toggled.connect(self.update_selection_count)
            self.ep_grid_layout.addWidget(btn)
            self.ep_buttons.append(btn)

    def on_view_more_episodes(self):
        if not self.is_profile_page() or not self.info_key:
            return

        self.view_more_episode = "next"
        self.scrape_episode()

    def on_view_all_episodes(self):
        if not self.is_profile_page() or not self.info_key:
            return

        self.view_more_episode = "all"
        self.scrape_episode()

    def toggle_all_episodes(self, type="none"):
        if not hasattr(self, 'ep_buttons') or not self.ep_buttons:
            return

        if self.select_all_btn.isChecked() or type == "select":
            self.select_all_btn.setText("Deselect All")
            for btn in self.ep_buttons:
                btn.setChecked(True)
        else:
            self.select_all_btn.setText("Select All")
            for btn in self.ep_buttons:
                btn.setChecked(False)

    def back_to_dramas(self):
        self.sidebar.title.setText("Drama Title")  # Reset or keep last?
        self.update_selection_count()

    def update_selection_count(self):
        selected = sum(1 for b in getattr(
            self, 'ep_buttons', []) if b.isChecked())
        self.sidebar.selected_count.setText(f"{selected}\nSelected")

        if not self.sidebar.info.get('chapterList'):
            return

        info = self.sidebar.info
        # if not hasattr(self.sidebar.extractor, '_EXTENDS_NAME'):
        #     if selected > 0:
        #         for i, btn in enumerate(self.ep_buttons):
        #             if btn.isChecked():
        #                 if i < len(info.get('chapterList', [])):
        #                     self.sidebar.current_selected_chapter = info['chapterList'][i]
        #                 break
        #     else:
        #         self.sidebar.current_selected_chapter = None
        #     return

        if selected > 0:
            self.sidebar.show_play_btn()
            for i, btn in enumerate(self.ep_buttons):
                if btn.isChecked():
                    if i < len(info.get('chapterList', [])):
                        title = info['chapterList'][i].get('title')
                        if title:
                            self.sidebar.title.setText(title)
                        self.sidebar.current_selected_chapter = info['chapterList'][i]
                    break
            thumbnail = self.sidebar.current_selected_chapter.get(
                'thumbnail') or ''
            if thumbnail and thumbnail.startswith("http"):
                self.sidebar.poster.loadImage(thumbnail)
        else:
            self.sidebar.play_btn_container.hide()
            self.sidebar.current_selected_chapter = None
            _prev_title = self.sidebar.title.text()
            self.sidebar.title.setText(info.get('drama_title') or _prev_title)
            self.sidebar.poster.loadImage(
                self.sidebar.extractor.get_cover_url(info))

    def on_stop_scraping(self):
        """Gracefully cancels all active extraction and scraping threads"""
        self.logger.info("🛑 Stop signal. Cancelling scraping...")

        # 1. Stop the current tab sidebar extractor
        if hasattr(self.sidebar, 'extractor') and self.sidebar.extractor:
            self.sidebar.extractor.stop_extraction()

        # 2. Stop all running scrape worker threads on this page
        if hasattr(self, 'scrape_workers') and self.scrape_workers:
            for worker in list(self.scrape_workers):
                if hasattr(worker, 'extractor') and worker.extractor:
                    worker.extractor.stop_extraction()

        # 3. Clean up UI states
        self.view_more_episode = None
        if self.loading_bar:
            self.loading_bar.setTitle("Scrape cancelled 🛑")
            self.loading_bar.setContent("")
            self.loading_bar.setState(True)
            self.loading_bar = None

    def scrape_episode(self):
        if self.scrape_workers:
            InfoBar.warning(
                title="Scraping in progress",
                content="A scraping operation is already running. Please wait or click Stop to cancel.",
                orient=Qt.Horizontal,
                duration=3000,
                position=InfoBarPosition.BOTTOM,
                parent=self
            )
            return

        url = self.url_edit.text()
        if not url:
            self.logger.error("[!] ❌ URL is empty")
            return
        if not is_valid_url(url):
            self.logger.error("[!] ❌ Invalid URL")
            return
        self._get_drama_info(url)

    def _get_drama_info(self, url: str):
        extractor: TYPE_DRAMA_EXTRACTOR = None

        object_name = self.objectName()
        is_default_object_name = object_name == 'all_drama_downloader'
        for (regex, extractor_class) in REGEX_DRAMA:
            netloc = str(urlparse(url).netloc)
            # match (www.|web.|m.)
            if netloc.count(".") >= 2 and re.match(r'^(www\.|web\.|m\.)', netloc):
                netloc = re.sub(r'^(www\.|web\.|m\.)', '', netloc)
                self.logger.debug(f"netloc: {netloc}, regex: {regex}")
            if netloc in regex:
                self.logger.debug(f"Extractor: {extractor_class.__name__}")
                extractor = extractor_class()
                break
        if not extractor:
            self.empty_eps_label.setText(self.empty_eps_not_found)
            self.stackWidget.setCurrentWidget(self.empty_eps_widget)
            self.logger.error("Invalid drama URL")
            return

        extractor_name = extractor.__class__.__name__
        self.logger.debug(f"Extractor name: {extractor_name}")
        self.logger.debug(f"Object name: {object_name}")
        if not is_default_object_name and not object_name.split('_')[0] in extractor_name.lower():
            self.empty_eps_label.setText(self.empty_eps_not_found)
            self.stackWidget.setCurrentWidget(self.empty_eps_widget)
            self.logger.error("Invalid drama URL")
            return

        if hasattr(extractor, '_get_build_id'):
            build_id_key = extractor_name + '-build-id'
            build_id = CACHE_DRAMA.get(build_id_key)
            if build_id is None:
                worker = ScrapeWorker(extractor, url, "",
                                      tab_id=self.objectName())
                worker.refresh_build_id_key = build_id_key
                self.scrape_workers.add(worker)

                def _on_scrape_finished(worker=None):
                    if worker and worker in self.scrape_workers:
                        self.scrape_workers.remove(worker)

                    self._get_drama_info(url)

                worker.signals.finished.connect(
                    lambda: _on_scrape_finished(worker))
                worker.signals.error.connect(self._on_scrape_error)
                QThreadPool.globalInstance().start(worker)
                return
            else:
                extractor._BUILD_ID = build_id
            self.logger.debug(f"build_id: {extractor._BUILD_ID}")

        if hasattr(extractor, 'get_drama_id_slug_title'):
            _, drama_id = extractor.get_drama_id_slug_title(url)
            drama_id = drama_id.split('/')[0]
        else:
            _, drama_id = extractor.get_drama_id(url)
            drama_id = drama_id or ''

        info_key = extractor_name + '-' + drama_id
        self.info_key = info_key
        info = CACHE_DRAMA.get(info_key)
        self.toggle_all_episodes('deselect')

        self.sidebar.extractor = extractor

        self._show_loading_bar(
            f"Scraping data from ID: {drama_id}", 'Please wait...')
        if info and not self.view_more_episode:
            self._on_scrape_finished(info, info_key, extractor)
        else:

            worker = ScrapeWorker(extractor, url, info_key,
                                  tab_id=self.objectName())
            if self.view_more_episode:
                worker._info = info
                worker.more = self.view_more_episode or "next"
                limit = self.view_more_limit.text() or 0
                limit = int(float(limit))
                if limit > 0:
                    worker.options["limit"] = limit

            self.scrape_workers.add(worker)  # Register worker

            worker.signals.progress.connect(
                lambda d: self._on_scrape_progress(d, extractor, info))
            worker.signals.finished.connect(
                lambda i, k, w=worker: self._on_scrape_finished(i, k, extractor, w))
            worker.signals.error.connect(
                lambda e, w=worker: self._on_scrape_error(e, w))
            QThreadPool.globalInstance().start(worker)

    def _on_scrape_progress(self, d, extractor: TYPE_DRAMA_EXTRACTOR, info):
        """Callback while scraping"""
        if info and d['status'] == "progress" and self.view_more_episode == "all":
            chapter = d.get('data')
            if not isinstance(chapter, dict):
                return
            if "moreChapter" not in info:
                info["moreChapter"] = []
            else:
                info["moreChapter"].append(chapter)

            if len(info["moreChapter"]) == 10:
                title = info["drama_title"]
                old_count = len(info["chapterList"])
                info["chapterList"].extend(info["moreChapter"])
                info["moreChapter"] = []
                new_count = len(info["chapterList"])
                self.append_new_episodes(old_count + 1, new_count)

    def _move_loading_bar(self, loading_bar: StateToolTip):
        window_width = self.window().width()
        window_height = self.window().height()
        tooltip_width = loading_bar.width()
        tooltip_height = loading_bar.height()
        x = (window_width - tooltip_width) // 2 - 60
        y = window_height - tooltip_height - 60
        loading_bar.move(x, y)

    def _show_loading_bar(self, title: str, content: str):
        if self.loading_bar:
            return

        self.loading_bar = StateToolTip(
            title,
            content,
            self.main_page
        )
        self._move_loading_bar(self.loading_bar)
        self.loading_bar.show()

    def _close_loading_bar(self):
        if self.loading_bar:
            self.loading_bar.setTitle("Scraped successfully ✅")
            self.loading_bar.setContent("")
            self.loading_bar.setState(True)
            self.loading_bar = None

    def _on_scrape_finished(self, info, info_key, extractor: TYPE_DRAMA_EXTRACTOR, worker=None):
        """Callback when scraping is complete"""
        self.view_more_episode = None
        if not self.is_profile_page():
            self.view_more_widget.hide()
        else:
            self.view_more_widget.show()

        if worker and worker in self.scrape_workers:
            self.scrape_workers.remove(worker)  # Unregister

        QTimer.singleShot(1000, self._close_loading_bar)

        if not isinstance(info, dict):
            self._on_scrape_error("Invalid drama data received")
            return

        title = info.get('bookName') or info.get('title') or info.get('book_title') or info.get(
            'english_name') or "Unknown Drama Title"
        self.show_episodes(title, len(info['chapterList']))
        self.stackWidget.setCurrentWidget(self.grid_container)

        info['drama_title'] = title
        info['info_key'] = info_key
        CACHE_DRAMA[info_key] = info

        self.sidebar.extractor = extractor
        self.sidebar.info = info
        self.sidebar.output_dir = extractor.set_output_dir()
        self.sidebar.path_edit.setText(str(self.sidebar.output_dir))

        try:
            img_url = extractor.get_cover_url(info)
            self.sidebar.poster.loadImage(img_url)
        except Exception as e:
            self.logger.error(f"Error setting poster: {e}")

    def _on_scrape_error(self, error_msg, worker=None):
        """Callback when scraping fails"""
        self.view_more_episode = None
        if worker and worker in self.scrape_workers:
            self.scrape_workers.remove(worker)  # Unregister

        self.empty_eps_label.setText(self.empty_eps_not_found)
        self.stackWidget.setCurrentWidget(self.empty_eps_widget)
        self.logger.error(f"Scrape error: {error_msg}")
        QTimer.singleShot(1000, self._close_loading_bar)


class TabBarComponent(TabBar):
    def _swapItem(self, index: int):
        oldIndex = self.currentIndex()
        if (index == 0 and oldIndex == 1) or (index == 1 and oldIndex == 0):
            return
        return super()._swapItem(index)


class DramaDownloaderPage(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("drama_downloader")

        self.tabCount = 1

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.tabBarWidget = CardWidget(self)
        self.tabBarLayout = QHBoxLayout(self.tabBarWidget)
        self.tabBarLayout.setContentsMargins(0, 0, 0, 0)
        self.tabBarLayout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tabBar = TabBarComponent(self.tabBarWidget)
        self.tabBar.setTabSelectedBackgroundColor(
            Colors.qt_alpha(LightMode.primary, 0.8), Colors.qt_alpha(DarkMode.primary, 0.5))
        self.tabBar.setMovable(True)
        self.tabBar.setScrollable(True)
        self.tabBar.setAddButtonVisible(False)
        self.tabBar.setCloseButtonDisplayMode(
            TabCloseButtonDisplayMode.ON_HOVER)
        self.tabBar.setTabShadowEnabled(False)
        self.tabBarLayout.addWidget(
            self.tabBar)

        self.tabBar.tabCloseRequested.connect(self.removeTab)
        self.tabBar.tabMoved.connect(self.onTabMoved)

        self.stackedWidget = QStackedWidget(self)

        self.drama_icons = DRAMA_ICONS

        self.all_drama_downloader = DramaDownloader(self)
        self.dramabox_downloader: Optional['DramaDownloader'] = None
        self.reelshort_downloader: Optional['DramaDownloader'] = None
        self.dramabite_downloader: Optional['DramaDownloader'] = None
        self.shortmovs_downloader: Optional['DramaDownloader'] = None
        self.rushshortstv_downloader: Optional['DramaDownloader'] = None
        self.stardusttv_downloader: Optional['DramaDownloader'] = None
        self.kuaishou_downloader: Optional['DramaDownloader'] = None
        self.tiktok_downloader: Optional['DramaDownloader'] = None
        self.youtube_downloader: Optional['DramaDownloader'] = None
        self.facebook_downloader: Optional['DramaDownloader'] = None

        self.dramaboxAction = Action(
            DRAMA_ICONS['dramabox_downloader'], self.tr('Dramabox'), checkable=True)
        self.reelshortAction = Action(
            DRAMA_ICONS['reelshort_downloader'], self.tr('Reelshort'), checkable=True)
        self.dramabiteAction = Action(
            DRAMA_ICONS['dramabite_downloader'], self.tr('Dramabite'), checkable=True)
        self.shortmovsAction = Action(
            DRAMA_ICONS['shortmovs_downloader'], self.tr('Shortmovs'), checkable=True)
        self.rushshortstvAction = Action(
            DRAMA_ICONS['rushshortstv_downloader'], self.tr('Rushshortstv'), checkable=True)
        self.stardusttvAction = Action(
            DRAMA_ICONS['stardusttv_downloader'], self.tr('Stardusttv'), checkable=True)
        self.kuaishouAction = Action(
            DRAMA_ICONS['kuaishou_downloader'], self.tr('Kuaishou'), checkable=True)
        self.tiktokAction = Action(
            DRAMA_ICONS['tiktok_downloader'], self.tr('Tiktok'), checkable=True)
        self.youtubeAction = Action(
            DRAMA_ICONS['youtube_downloader'], self.tr('Youtube'), checkable=True)
        self.facebookAction = Action(
            DRAMA_ICONS['facebook_downloader'], self.tr('Facebook'), checkable=True)

        self.object_name_list = ["dramabox_downloader", "reelshort_downloader",
                                 "dramabite_downloader", "shortmovs_downloader",
                                 "rushshortstv_downloader", "stardusttv_downloader",
                                 "kuaishou_downloader", "tiktok_downloader", "youtube_downloader",
                                 "facebook_downloader"]
        self.object_name_dict = {
            "dramabox_downloader": (self.dramabox_downloader, DramaDownloader, self.dramaboxAction),
            "reelshort_downloader": (self.reelshort_downloader, DramaDownloader, self.reelshortAction),
            "dramabite_downloader": (self.dramabite_downloader, DramaDownloader, self.dramabiteAction),
            "shortmovs_downloader": (self.shortmovs_downloader, DramaDownloader, self.shortmovsAction),
            "rushshortstv_downloader": (self.rushshortstv_downloader, DramaDownloader, self.rushshortstvAction),
            "stardusttv_downloader": (self.stardusttv_downloader, DramaDownloader, self.stardusttvAction),
            "kuaishou_downloader": (self.kuaishou_downloader, DramaDownloader, self.kuaishouAction),
            "tiktok_downloader": (self.tiktok_downloader, DramaDownloader, self.tiktokAction),
            "youtube_downloader": (self.youtube_downloader, DramaDownloader, self.youtubeAction),
            "facebook_downloader": (self.facebook_downloader, DramaDownloader, self.facebookAction)
        }

        self.dramaboxAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "dramabox_downloader"))
        self.reelshortAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "reelshort_downloader"))
        self.dramabiteAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "dramabite_downloader"))
        self.shortmovsAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "shortmovs_downloader"))
        self.rushshortstvAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "rushshortstv_downloader"))
        self.stardusttvAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "stardusttv_downloader"))
        self.kuaishouAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "kuaishou_downloader"))
        self.tiktokAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "tiktok_downloader"))
        self.youtubeAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "youtube_downloader"))
        self.facebookAction.toggled.connect(
            lambda checked: self.on_toggle_add_tab(checked, "facebook_downloader"))

        class AddDropDownButton(TransparentDropDownToolButton):
            def setStyleSheet(self, styleSheet: str, /) -> None:
                styleSheet = styleSheet + \
                    f"TransparentDropDownToolButton:checked {{background-color: {Colors.alpha(Colors.white, 0.1)}; border: 1px solid {Colors.alpha(Colors.white, 0.1)}}}"
                return super().setStyleSheet(styleSheet)

        self.add_tab_button = AddDropDownButton(FluentIcon.ADD, self)
        self.add_tab_button.setCheckable(True)
        self.add_tab_button.setChecked(False)
        self.add_tab_button.setMenu(self.createCheckableMenu())
        self.add_tab_button.setFixedHeight(34)
        font = self.font()
        font.setPointSize(12)
        self.add_tab_button.setFont(font)
        # setFont(self.add_tab_button, 12)
        self.tabBar.widgetLayout.insertWidget(
            1, self.add_tab_button, stretch=0, alignment=Qt.AlignLeft)

        # add items to pivot
        self.__initWidget()
        self.setWidget(self.view)
        self.enableTransparentBackground()
        self.setWidgetResizable(True)

    def __initWidget(self):
        self.initLayout()

        self.addSubInterface(
            self.all_drama_downloader,
            'all_drama_downloader',
            self.tr('All Drama'),
            self.drama_icons['all_drama_downloader'],
            True
        )
        self.connectSignalToSlot()

    def connectSignalToSlot(self):
        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)

    def initLayout(self):
        self.tabBar.setTabMaximumWidth(150)

        self.vBoxLayout.addWidget(self.tabBarWidget, 0)
        self.vBoxLayout.addWidget(self.stackedWidget, 1)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(16)

    def addSubInterface(self, widget: QWidget, objectName, text, icon, active=False):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.tabBar.addTab(
            routeKey=objectName,
            text=text,
            icon=icon,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )
        if active:
            self.tabBar.setCurrentTab(objectName)
            # qrouter.push(self.stackedWidget, objectName)
            self.stackedWidget.setCurrentWidget(widget)

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        if not widget:
            return

        self.tabBar.setCurrentTab(widget.objectName())
        # qrouter.push(self.stackedWidget, widget.objectName())

    def createCheckableMenu(self, pos=None):
        menu = CheckableMenu(
            parent=self, indicatorType=MenuIndicatorType.RADIO)

        menu.closedSignal.connect(
            lambda: self.add_tab_button.setChecked(False))

        menu.addActions([
            self.dramaboxAction,
            self.reelshortAction,
            self.dramabiteAction,
            self.shortmovsAction,
            self.rushshortstvAction,
            self.stardusttvAction
        ])

        menu.addSeparator()
        menu.addActions([
            self.youtubeAction,
            self.facebookAction,
            self.tiktokAction,
            self.kuaishouAction
        ])

        if pos is not None:
            menu.exec(pos, ani=True)

        return menu

    def on_toggle_add_tab(self, checked: bool, object_name: str):
        if checked == False:
            for i in range(self.tabBar.count()):
                if self.tabBar.tabItem(i).routeKey() == object_name:
                    self.removeTab(i)
                    break
            return

        item_widget, item_class, item_action = self.object_name_dict.get(
            object_name, (None, None, None))
        item_widget = getattr(self, object_name, None)

        if item_widget or not item_action or not item_class:
            return

        item_widget = item_class(self, object_name=object_name)
        setattr(self, object_name, item_widget)
        self.addSubInterface(
            item_widget,
            object_name,
            self.tr(object_name.split('_')[0].capitalize()),
            self.drama_icons[object_name],
            True
        )
        item_action.setChecked(True)

        self.tabCount += 1

    def removeTab(self, index):
        item = self.tabBar.tabItem(index)
        if not item or item.routeKey() == "all_drama_downloader":
            return

        for key, value in self.object_name_dict.items():
            if item.routeKey() == key:
                widget = getattr(self, key)
                if widget:
                    if hasattr(widget, 'cleanup'):
                        widget.cleanup()
                    widget.deleteLater()
                    setattr(self, key, None)
                    value[2].setChecked(False)
                    break

        # if item.routeKey() == "dramabox_downloader":
        #     if self.dramabox_downloader:
        #         self.dramabox_downloader.deleteLater()
        #         self.dramabox_downloader = None
        #         self.dramaboxAction.setChecked(False)
        # elif item.routeKey() == "reelshort_downloader":
        #     if self.reelshort_downloader:
        #         self.reelshort_downloader.deleteLater()
        #         self.reelshort_downloader = None
        #         self.reelshortAction.setChecked(False)

        self.tabBar.removeTab(index)
        self.tabCount -= 1

        widget = self.findChild(QWidget, item.routeKey())
        if not widget:
            return
        widget.deleteLater()

    def onTabMoved(self, from_index, to_index):
        pass

    def closeEvent(self, event):
        if hasattr(self, 'all_drama_downloader') and self.all_drama_downloader:
            self.all_drama_downloader.cleanup()
        for key in self.object_name_list:
            widget = getattr(self, key, None)
            if widget and hasattr(widget, 'cleanup'):
                widget.cleanup()
        super().closeEvent(event)
