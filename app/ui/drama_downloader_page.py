import asyncio
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
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
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
    InfoBadge,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MenuIndicatorType,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    ScrollArea,
    StateToolTip,
    SubtitleLabel,
    TabBar,
    TabCloseButtonDisplayMode,
    TogglePushButton,
    TransparentDropDownToolButton,
    TransparentToolButton,
    isDarkTheme,
    qrouter,
    setFont,
)

from ..components.icons import FileIcon
from ..components.override import CardWidget, CheckableMenu
from ..components.override import TextAreaInput as TextEdit
from ..components.override import TextInput as LineEdit
from ..core._worker import DefaultWorker
from ..extractor.drama import (
    DramaBiteExtractor,
    DramaBoxExtractor,
    DramaExtractorBase,
    ProgressData,
    ReelShortExtractor,
    RushTvExtractor,
    ShortMovsExtractor,
    StardustTvExtractor,
)
from ..theme import Colors, DarkMode, LightMode

TYPE_DRAMA_EXTRACTOR: TypeAlias = Optional[Union[
    'DramaExtractorBase',
    'DramaBiteExtractor', 'DramaBoxExtractor',
    'ReelShortExtractor', 'RushTvExtractor',
    'ShortMovsExtractor', 'StardustTvExtractor'
]]


REGEX_DRAMA = [
    (DramaBiteExtractor._BASE_URL, DramaBiteExtractor),
    (DramaBoxExtractor._BASE_URL, DramaBoxExtractor),
    (ReelShortExtractor._BASE_URL, ReelShortExtractor),
    (RushTvExtractor._BASE_URL, RushTvExtractor),
    (ShortMovsExtractor._BASE_URL, ShortMovsExtractor),
    (StardustTvExtractor._BASE_URL, StardustTvExtractor),
]

DRAMA_ICONS = {
    "all_drama_downloader": FileIcon.LOGO,
    "dramabox_downloader": FileIcon.DRAMABOX_LOGO,
    "reelshort_downloader": FileIcon.REELSHORT_LOGO,
    "dramabite_downloader": FileIcon.DRAMABITE_LOGO,
    "shortmovs_downloader": FileIcon.SHORTMOVS_LOGO,
    "rushshortstv_downloader": FileIcon.RUSHSHORTSTV_LOGO,
    "stardusttv_downloader": FileIcon.STARDUSTTV_LOGO,
}

CACHE_DRAMA = {}


class DramaExtractTask(DefaultWorker):
    def __init__(self, task_id: int):
        super().__init__(task_id)


class ScrapeSignals(QObject):
    """Signals for the scrape worker"""
    finished = Signal(dict, str)  # info, info_key
    error = Signal(str)


class ScrapeWorker(QRunnable):
    """Worker task to run async scrape in the background"""

    def __init__(self, extractor: TYPE_DRAMA_EXTRACTOR, url, info_key):
        super().__init__()
        self.extractor = extractor
        self.url = url
        self.info_key = info_key
        self._info = None
        self.signals = ScrapeSignals()

    async def update_all_episodes(self, info: dict):
        has_episodes_updated = info.get('episodes_updated', False)
        if not has_episodes_updated \
                and hasattr(self.extractor, 'update_all_episodes') \
                and callable(self.extractor.update_all_episodes):
            logger.info(
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

    def run(self):
        async def _scrape():
            # Reset session for the current thread's event loop to prevent "loop closed" errors
            try:
                if hasattr(self.extractor, 'session') and self.extractor.session:
                    await self.extractor.session.close()
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

            if isinstance(self._info, dict):
                info = await self.update_all_episodes(self._info.copy())
                self._info = None
                return info

            self.extractor.set_test_mode(True)
            # info = await self.extractor.test_get_drama_info(self.url)
            info = self.extractor.load_test_data()
            if not info:
                info = await self.extractor.get_drama_info(self.url)
                if info:
                    self.extractor.save_test_data(info)
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
                self.signals.error.emit("Failed to scrape drama info")
        except Exception as e:
            logger.error(f"ScrapeWorker error: {e}")
            self.signals.error.emit(str(e))


class DownloadSignals(QObject):
    """Signals for the YoutubeDL worker"""
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(dict)


class DownloadWorker(QRunnable):
    """Worker task to run async YoutubeDL in the background"""

    def __init__(self, extractor: TYPE_DRAMA_EXTRACTOR, info, output_dir):
        super().__init__()
        self.extractor = extractor
        self.info = info
        self.output_dir = output_dir
        self.signals = DownloadSignals()

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
            logger.error(f"Download error: {e}")
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
    """Robust image label that loads content in a background thread"""

    def __init__(self, text_placeholder="No Image", parent=None):
        super().__init__(parent)
        self.text_placeholder = text_placeholder
        self.placeholder_path = "path/to/your/placeholder.png"
        self.radius = 12
        self.setAlignment(Qt.AlignCenter)

    def loadImage(self, url_str: str):
        """Dispatches a background worker to load the image"""
        if not url_str:
            self._set_placeholder()
            return

        task = ImageLoadTask(url_str)
        task.signals.result.connect(self._on_image_loaded)
        task.signals.error.connect(self._on_load_error)
        QThreadPool.globalInstance().start(task)

    def _on_image_loaded(self, image: QImage):
        """Runs in main thread: converts QImage to QPixmap and displays it"""
        pixmap = QPixmap.fromImage(image)
        if not pixmap.isNull():
            # Respect scaling if set
            if self.hasScaledContents():
                pixmap = pixmap.scaled(
                    self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

            self.setPixmap(self._get_rounded_pixmap(pixmap, self.radius))
        else:
            self._set_placeholder()

    def _on_load_error(self, error_msg: str):
        """Runs in main thread: logs error and shows placeholder"""
        logger.error(f"Image load failed: {error_msg}")
        self._set_placeholder()

    def _get_rounded_pixmap(self, pixmap, radius):
        """Crops a pixmap to have rounded corners"""
        size = pixmap.size()
        rounded = QPixmap(size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        path = QPainterPath()
        path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded

    def _set_placeholder(self):
        """Sets the label to the local placeholder or text"""
        placeholder = QPixmap(self.placeholder_path)
        if not placeholder.isNull():
            if self.hasScaledContents():
                placeholder = placeholder.scaled(
                    self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(self._get_rounded_pixmap(placeholder, self.radius))
        else:
            self.setText(self.text_placeholder)


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


class DramaSidebar(ScrollArea):
    """Left sidebar for selected drama details"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.view = CardWidget(self, Colors.gray_0, DarkMode.card)
        self.vBoxlayout = QVBoxLayout(self.view)
        self.vBoxlayout.setContentsMargins(15, 15, 15, 15)
        self.vBoxlayout.setSpacing(15)

        # Large Poster
        self.poster = ImageLoaderLabel("Drama Poster", self)
        self.poster.setFixedSize(270, 380)
        self.poster.setScaledContents(True)
        self.poster.setAlignment(Qt.AlignCenter)
        self.poster._set_placeholder()
        self.poster.setStyleSheet(
            f"border-radius: 12px; background-color: {Colors.alpha(Colors.gray_6, 0.4)}; font-size: 20px; font-weight: bold; color: gray; border: 2px solid {LightMode.primary};")
        self.vBoxlayout.addWidget(self.poster, 0, Qt.AlignCenter)

        # Drama Info
        self.title = SubtitleLabel("Drama Title", self)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        self.vBoxlayout.addWidget(self.title)

        # Stats
        stats_layout = QHBoxLayout()
        self.ep_count = BodyLabel("0\nEPs", self)
        self.ep_count.setAlignment(Qt.AlignCenter)
        self.selected_count = BodyLabel("0\nSelected", self)
        self.selected_count.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.ep_count)
        stats_layout.addWidget(self.selected_count)
        self.vBoxlayout.addLayout(stats_layout, 1)

        self.info: dict = {}
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

        self.browse_btn = PushButton("Browse", self)
        self.browse_btn.setToolTip("Select Directory")
        self.browse_btn.clicked.connect(self.browse_path)

        self.path_layout.addWidget(self.path_edit)
        self.path_layout.addWidget(self.browse_btn)
        self.vBoxlayout.addLayout(self.path_layout)

        self.download_btn = PrimaryPushButton(
            FluentIcon.DOWNLOAD, "Download Selected", self)
        self.vBoxlayout.addWidget(self.download_btn)

        self.cancel_btn = PushButton("Cancel", self)
        self.vBoxlayout.addWidget(self.cancel_btn)

        self.setWidget(self.view)
        self.enableTransparentBackground()
        self.setWidgetResizable(True)
        # show scroll bar on hover
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.download_btn.clicked.connect(self.download_selected)
        self.cancel_btn.clicked.connect(self.cancel_all)

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.output_dir = Path(path)
            self.path_edit.setText(str(self.output_dir))

    def path_changed(self, text):
        self.path_edit.setToolTip(text)

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
            logger.warning("No episodes selected for download.")
            return

        update_workder = ScrapeWorker(
            self.extractor, '', self.info.get('info_key', ''))
        update_workder._info = self.info.copy()
        has_episodes_updated = self.info.get('episodes_updated', False)
        if not has_episodes_updated \
                and hasattr(self.extractor, 'update_all_episodes') \
                and callable(self.extractor.update_all_episodes):
            self.update_info_workers.add(update_workder)  # Register worker

            update_workder.signals.finished.connect(
                lambda i, k, w=update_workder: self._on_update_info_finished(i, k, self.extractor, w))
            update_workder.signals.error.connect(
                lambda e, w=update_workder: self._on_update_info_error(e, w))
            QThreadPool.globalInstance().start(update_workder)
            return

        self._download_selected(selected_chapters)

    def _on_update_info_finished(self, info, info_key, extractor: TYPE_DRAMA_EXTRACTOR, worker=None):
        """
        Callback for successful scrape completion
        """
        self.info.update(info)
        if info_key:
            CACHE_DRAMA[info_key] = self.info
        if worker and worker in self.update_info_workers:
            self.update_info_workers.remove(worker)

        downloader = self.parent()
        selected_chapters = []
        for i, btn in enumerate(downloader.ep_buttons):
            if btn.isChecked():
                if i < len(self.info.get('chapterList', [])):
                    selected_chapters.append(self.info['chapterList'][i])

        if not selected_chapters:
            logger.warning("No episodes selected for download.")
            return

        self._download_selected(selected_chapters)

    def _on_update_info_error(self, error, worker=None):
        """
        Callback for failed scrape completion
        """
        if worker and worker in self.update_info_workers:
            self.update_info_workers.remove(worker)

        logger.error(f"Failed to scrape drama info: {error}")

    def _download_selected(self, selected_chapters):
        # Create a copy of info with only selected chapters to avoid caching issues
        download_info = self.info.copy()
        download_info['chapterList'] = selected_chapters

        logger.info(
            f"Downloading {len(selected_chapters)} selected episodes...")

        worker = DownloadWorker(
            self.extractor,
            download_info,
            self.output_dir,
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
        logger.info(
            f"✅ Download finished: {len(data['success'])} success, {len(data['failed'])} failed")
        if 'info' in data and isinstance(data['info'], dict):
            info = data['info']
            self.info.update(info)
            info_key = self.info.get('info_key', '')
            print('info_key:', info_key)
            if info_key:
                CACHE_DRAMA[info_key] = self.info
        if worker and worker in self.download_workers:
            self.download_workers.remove(worker)

    def on_download_error(self, error_info, worker=None):
        """
        Callback for download errors
        """
        logger.error(f"Download error: {error_info}")
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

            logger.info(
                f"Progress: {downloaded}/{total} ({downloaded/total*100:.2f}%)")
            logger.info(f"Speed: {speed_str}")
            logger.info(f"ETA: {eta_str}")
        elif d['status'] == 'finished':
            logger.info(f"Finished: {d['filename']}")

    def cancel_all(self):
        logger.info("Canceling all downloads...")
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

    def __init__(self, parent=None, object_name="all_drama_downloader"):
        super().__init__(parent)
        self.setObjectName(object_name)

        self.logger = logger
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

        # 2.5 Bottom Log and Progress
        self.log_area = QVBoxLayout()
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.log_area.addWidget(self.progress_bar)

        log_header = QHBoxLayout()
        log_header.addWidget(CaptionLabel("Log", self))
        log_header.addStretch(1)
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
            format="[{time:HH:mm:ss}] {message}",
        )
        # self.sink_id = self.logger.add(
        #     self.log_output.append,
        #     level="DEBUG",
        #     enqueue=True,
        #     format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        # )

        # self.test_show_episodes("Heart Thief", 70)
        self.content_area.addLayout(self.log_area)

    def closeEvent(self, event):
        if self.sink_id is not None:
            self.logger.remove(self.sink_id)
        super().closeEvent(event)

    def scroll_to_bottom(self, msg: str):
        self.log_output.append(msg.strip())
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum())

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

    def scrape_episode(self):
        url = self.url_edit.text()
        self._get_drama_info(url)

    def _get_drama_info(self, url: str):
        extractor: TYPE_DRAMA_EXTRACTOR = None

        object_name = self.objectName()
        is_default_object_name = object_name == 'all_drama_downloader'
        for (regex, extractor_class) in REGEX_DRAMA:
            if re.match(regex, url):
                extractor = extractor_class()
                break
        if not extractor:
            self.empty_eps_label.setText(self.empty_eps_not_found)
            self.stackWidget.setCurrentWidget(self.empty_eps_widget)
            self.logger.error("Invalid drama URL")
            return

        extractor_name = extractor.__class__.__name__
        if not is_default_object_name and not object_name.split('_')[0] in extractor_name.lower():
            self.empty_eps_label.setText(self.empty_eps_not_found)
            self.stackWidget.setCurrentWidget(self.empty_eps_widget)
            self.logger.error("Invalid drama URL")
            return

        if hasattr(extractor, '_get_build_id'):
            build_id_key = extractor_name + '-build-id'
            build_id = CACHE_DRAMA.get(build_id_key)
            if build_id is None:
                build_id = extractor._get_build_id()
                CACHE_DRAMA[build_id_key] = extractor._BUILD_ID
            else:
                extractor._BUILD_ID = build_id

        # print("build_id: ", extractor._BUILD_ID)
        if hasattr(extractor, 'get_drama_id_slug_title'):
            _, drama_id = extractor.get_drama_id_slug_title(url)
            drama_id = drama_id.split('/')[0]
        else:
            _, drama_id = extractor.get_drama_id(url)
            drama_id = drama_id or ''

        info_key = extractor_name + '-' + drama_id
        info = CACHE_DRAMA.get(info_key)

        self.toggle_all_episodes('deselect')

        self.sidebar.extractor = extractor

        if info:
            self._on_scrape_finished(info, info_key, extractor)
        else:
            self.loading_bar = StateToolTip(
                f"Scraping data from {urlparse(url).path.split('/')[-1]}",
                'Please wait...',
                self.window()
            )
            # move to bottom center
            window_width = self.window().width()
            window_height = self.window().height()
            tooltip_width = self.loading_bar.width()
            tooltip_height = self.loading_bar.height()
            x = (window_width - tooltip_width) // 2
            y = window_height - tooltip_height - 30
            self.loading_bar.move(x, y)
            self.loading_bar.show()

            worker = ScrapeWorker(extractor, url, info_key)
            self.scrape_workers.add(worker)  # Register worker

            worker.signals.finished.connect(
                lambda i, k, w=worker: self._on_scrape_finished(i, k, extractor, w))
            worker.signals.error.connect(
                lambda e, w=worker: self._on_scrape_error(e, w))
            QThreadPool.globalInstance().start(worker)

    def _on_scrape_finished(self, info, info_key, extractor: TYPE_DRAMA_EXTRACTOR, worker=None):
        """Callback when scraping is complete"""
        if worker and worker in self.scrape_workers:
            self.scrape_workers.remove(worker)  # Unregister

        def on_closed():
            if self.loading_bar:
                self.loading_bar.setTitle("Scraped successfully ✅")
                self.loading_bar.setContent("")
                self.loading_bar.setState(True)
                self.loading_bar = None

        QTimer.singleShot(1000, on_closed)

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
        if worker and worker in self.scrape_workers:
            self.scrape_workers.remove(worker)  # Unregister

        if hasattr(self, 'loading_bar'):
            self.loading_bar = None

        self.empty_eps_label.setText(self.empty_eps_not_found)
        self.stackWidget.setCurrentWidget(self.empty_eps_widget)
        self.logger.error(f"Scrape error: {error_msg}")


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
        self.tabBar = TabBar(self.tabBarWidget)
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

        self.stackedWidget = QStackedWidget(self)

        self.drama_icons = DRAMA_ICONS

        self.all_drama_downloader = DramaDownloader(self)
        self.dramabox_downloader: Optional['DramaDownloader'] = None
        self.reelshort_downloader: Optional['DramaDownloader'] = None
        self.dramabite_downloader: Optional['DramaDownloader'] = None
        self.shortmovs_downloader: Optional['DramaDownloader'] = None
        self.rushshortstv_downloader: Optional['DramaDownloader'] = None
        self.stardusttv_downloader: Optional['DramaDownloader'] = None

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

        self.object_name_list = ["dramabox_downloader", "reelshort_downloader",
                                 "dramabite_downloader", "shortmovs_downloader",
                                 "rushshortstv_downloader", "stardusttv_downloader"]
        self.object_name_dict = {
            "dramabox_downloader": (self.dramabox_downloader, DramaDownloader, self.dramaboxAction),
            "reelshort_downloader": (self.reelshort_downloader, DramaDownloader, self.reelshortAction),
            "dramabite_downloader": (self.dramabite_downloader, DramaDownloader, self.dramabiteAction),
            "shortmovs_downloader": (self.shortmovs_downloader, DramaDownloader, self.shortmovsAction),
            "rushshortstv_downloader": (self.rushshortstv_downloader, DramaDownloader, self.rushshortstvAction),
            "stardusttv_downloader": (self.stardusttv_downloader, DramaDownloader, self.stardusttvAction),
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
        setFont(self.add_tab_button, 12)
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
                if getattr(self, key):
                    getattr(self, key).deleteLater()
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
