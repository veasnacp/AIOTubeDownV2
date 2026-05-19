
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtWidgets import QAbstractButton, QAbstractSlider, QDialog, QWidget
from PySide6Addons import isDarkTheme
from PySide6Addons.multimedia import VideoWidget

from ..theme import DarkMode, LightMode


class VideoPlayerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window |
                            Qt.WindowType.CustomizeWindowHint |
                            Qt.WindowType.WindowTitleHint |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.videoWidget = VideoWidget(self)

        self.setMinimumWidth(450)
        self.videoWidget.setMinimumWidth(450)
        self._drag_pos = None
        self._aspect_ratio = 16 / 9  # Default aspect ratio

        self.setStyleSheet(f"""
        QDialog {{
            border-radius: 12px;
            background-color: {DarkMode.card if isDarkTheme() else LightMode.card};
        }}
        """)

        # Install event filter to recursively capture drag events on children
        self._setup_drag_filter()

    def _setup_drag_filter(self):
        self.videoWidget.installEventFilter(self)
        for child in self.videoWidget.findChildren(QWidget):
            child.installEventFilter(self)

    def enterEvent(self, event):
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.videoWidget.playBar.fadeIn()
        super().leaveEvent(event)

    def eventFilter(self, obj, event) -> bool:
        # Ignore clicks/drags on interactive controls or anything inside the play bar
        if (isinstance(obj, (QAbstractButton, QAbstractSlider)) or
                obj.inherits("QAbstractButton") or
                obj.inherits("QAbstractSlider") or
                obj == self.videoWidget.playBar or
                self.videoWidget.playBar.isAncestorOf(obj)):
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.pos()
        elif event.type() == QEvent.Type.MouseMove:
            if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            self._drag_pos = None

        return super().eventFilter(obj, event)

    def _update_video_geometry(self):
        if not hasattr(self, '_aspect_ratio'):
            self._aspect_ratio = 16 / 9

        dialog_w = self.width()
        dialog_h = self.height()

        if dialog_w <= 0 or dialog_h <= 0:
            return

        if dialog_w / dialog_h > self._aspect_ratio:
            # Bound by height
            h = dialog_h
            w = int(h * self._aspect_ratio)
        else:
            # Bound by width
            w = dialog_w
            h = int(w / self._aspect_ratio)

        x = (dialog_w - w) // 2
        y = (dialog_h - h) // 2
        self.videoWidget.setGeometry(x, y, w, h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_video_geometry()

    def resizePortrait(self):
        self._aspect_ratio = 9 / 16
        self.setMinimumHeight(800)
        self.resize(450, 800)
        self._update_video_geometry()

    def resizeLandscape(self):
        self._aspect_ratio = 16 / 9
        self.setMinimumHeight(450)
        self.resize(800, 450)
        self._update_video_geometry()

    def setVideo(self, file_path_or_url: str):
        if not file_path_or_url:
            self.setWindowTitle("No Media Loaded")
            return

        scheme = urlparse(file_path_or_url).scheme
        if 'http' in scheme:
            basename = urlparse(file_path_or_url).path.split("/")[-1]
            self.setWindowTitle(basename)
            self.videoWidget.setVideo(QUrl(file_path_or_url))
        else:
            basename = Path(file_path_or_url).name
            self.setWindowTitle(basename)
            self.videoWidget.setVideo(QUrl.fromLocalFile(file_path_or_url))

    def play(self):
        self.videoWidget.play()

    def pause(self):
        self.videoWidget.pause()

    def stop(self):
        self.videoWidget.stop()

    def isPlaying(self):
        return self.videoWidget.player.isPlaying()
