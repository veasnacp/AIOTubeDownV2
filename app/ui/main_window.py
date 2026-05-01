import os
import sys
from pathlib import Path

import darkdetect
import loguru
from PySide6.QtCore import QFile, QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6Addons import (
    Action,
    FluentIcon,
    FluentWindow,
    MSFluentTitleBar,
    MSFluentWindow,
    NavigationItemPosition,
    TabWidget,
    Theme,
    ToolButton,
    TransparentPushButton,
    TransparentToolButton,
    getFont,
    isDarkTheme,
    setFont,
    setTheme,
    setThemeColor,
)

from ..common import resource_rc
from ..components import FileIcon
from ..components.override import CardWidget, RoundMenu
from ..config.constants import APP_VERSION_BETA
from ..core.download_manager import manager
from ..core.extract_manager import extract_manager
from ..core.license_manager import license_manager
from ..theme import Colors, DarkMode, LightMode
from .downloader_page import DownloaderPage
from .drama_downloader_page import DramaDownloaderPage
from .license_dialog import LicenseDialog
from .license_interface import LicenseInterface
from .settings_page import SettingsPage
from .sidebar import Sidebar

logger = loguru.logger


class LicenseThread(QThread):
    license_dialog = Signal()

    def run(self):
        self.license_dialog.emit()


setThemeColor(LightMode.primary)


class PushButtonHover(TransparentPushButton):
    def _postInit(self):
        self.isActive = False
        self.setFont(getFont(13, QFont.Weight.Normal))
        self.setObjectName('pushButtonHover')
        return super()._postInit()

    def defaultStyleSheet(self, styleSheet=""):
        styleSheet += (f"""
PushButtonHover {{
    border-radius: 6px;
    padding: 4px 8px 5px 8px;
    background-color: transparent;
}}
PushButtonHover:checked, PushButtonHover:checked:pressed, PushButtonHover:pressed, PushButtonHover:hover {{
    background-color: #e9ecef;
}}

MainWindow[theme=dark] PushButtonHover {{
    color: #f5f5f5;
}}
MainWindow[theme=dark] PushButtonHover:checked, MainWindow[theme=dark] PushButtonHover:checked:pressed, PushButtonHover:pressed, MainWindow[theme=dark] PushButtonHover:hover {{
    background-color: {Colors.alpha(Colors.white, 0.2)};
}}
""")
        return styleSheet

    def setStyleSheet(self, styleSheet):
        styleSheet = self.defaultStyleSheet(styleSheet)
        return super().setStyleSheet(styleSheet)

    def onPress(self, event):
        pass

    def onRelease(self, event):
        pass

    def onContextMenu(self, event):
        pass

    def mousePressEvent(self, event):
        self.onPress(event)
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.onRelease(event)
        self.setChecked(False)
        return super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.onContextMenu(event)
        return super().contextMenuEvent(event)

    def toggleActive(self):
        self.isActive = not self.isActive
        self.setProperty('isActive', not self.isActive)
        self.setStyle(QApplication.style())


class MainWindow(MSFluentWindow):
    """The Main Shell with the Sidebar and Downloader Page"""

    def __init__(self):
        super().__init__()
        self.isWin11 = not (
            sys.platform != 'win32' or sys.getwindowsversion().build < 22000)
        self._lightBackgroundColor = QColor(Colors.gray_4)
        self._darkBackgroundColor = QColor(DarkMode.card)

        self.titleBar: MSFluentTitleBar = self.titleBar

        self.setWindowTitle(APP_VERSION_BETA)

        icon_path = FileIcon.LOGO.path()
        if QFile(icon_path).exists():
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(
                64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon = QIcon(pixmap)
        else:
            icon = FluentIcon.FOLDER.icon(Theme.DARK)
        self.setWindowIcon(icon)
        self.setMinimumSize(800, 540)
        self.resize(1200, 800)

        self.titleBarHLayout = self.titleBar.hBoxLayout

        self.setMicaEffectEnabled(False)
        self.set_theme('dark')

        # 1. Sidebar
        # self.sidebar_nav = Sidebar(self)
        # self.sidebar_nav.setCurrentItem("downloader")
        # self.sidebar_nav.itemClicked.connect(self.on_sidebar_item_clicked)
        # self.hBoxLayout.insertWidget(0, self.sidebar_nav)
        # self.navigationInterface.hide()

        self.stackedWidget.setContentsMargins(0, 0, 0, 0)

        self.init_interface()
        # QApplication.processEvents()
        self.init_title_bar_menus()

        # load window center
        desktop = self.screen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

    def init_interface(self):
        self.downloader_page = DownloaderPage(self)
        self.drama_downloader_page = DramaDownloaderPage(self)
        self.settings_interface = SettingsPage(self)

        self.addSubInterface(self.downloader_page,
                             FluentIcon.DOWNLOAD, "Download")
        self.addSubInterface(self.drama_downloader_page,
                             FluentIcon.MOVIE, "Drama")
        self.addSubInterface(self.settings_interface,
                             FluentIcon.SETTING, "Settings", position=NavigationItemPosition.BOTTOM)

    def init_title_bar_menus(self):
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        self.titleBar.minBtn.setToolTip('Minimize')
        self.titleBar.maxBtn.setToolTip('Maximize')
        self.titleBar.closeBtn.setToolTip('Close')

        # Create "Tasks" button and menu
        self.tasks_btn = PushButtonHover(parent=self)
        self.tasks_btn.setText("Tasks")
        self.tasks_btn.setFixedWidth(60)
        self.tasks_btn.setCheckable(True)

        tasks_menu = RoundMenu(parent=self)
        tasks_menu.addAction(
            Action(self.tr("New Text File"), shortcut="Ctrl+N"))
        tasks_menu.addAction(Action(self.tr("Add new download"),
                                    triggered=self.downloader_page.add_url_test))
        tasks_menu.addAction(
            Action(self.tr("Add new download from clipboard")))

        # Open Recent Submenu
        open_recent_menu = RoundMenu(self.tr("Open Recent"), parent=tasks_menu)
        open_recent_menu.addAction(Action(self.tr("Clear Recently Opened")))
        tasks_menu.addMenu(open_recent_menu)

        tasks_menu.addSeparator()
        tasks_menu.addAction(
            Action(self.tr("Exit"), shortcut="Ctrl+F4", triggered=self.close))

        # Create "Help" button and menu
        self.help_btn = PushButtonHover(parent=self)
        self.help_btn.setText(self.tr("Help"))
        self.help_btn.setFixedWidth(50)
        self.help_btn.setCheckable(True)

        help_menu = RoundMenu(parent=self)
        help_menu.addAction(Action(self.tr("About")))

        self.tasks_btn.onPress = lambda event: self.help_btn.setChecked(False)
        self.help_btn.onPress = lambda event: self.tasks_btn.setChecked(False)
        tasks_menu.onClose = lambda: self.tasks_btn.setChecked(False)
        help_menu.onClose = lambda: self.help_btn.setChecked(False)
        self.tasks_btn.clicked.connect(lambda: tasks_menu.exec(
            self.tasks_btn.mapToGlobal(self.tasks_btn.rect().bottomLeft())
        ))
        self.help_btn.clicked.connect(lambda: help_menu.exec(
            self.help_btn.mapToGlobal(self.help_btn.rect().bottomLeft())
        ))

        self.titleBarHLayout.removeWidget(self.titleBar.titleLabel)
        self.titleBarHLayout.removeWidget(self.titleBar.iconLabel)

        self.titleBar.iconLabel.setFixedSize(24, 24)
        self.titleBar.iconLabel.setPixmap(
            QIcon(self.windowIcon()).pixmap(24, 24))
        self.titleBarHLayout.insertWidget(
            0, self.titleBar.iconLabel, 0, Qt.AlignLeft)
        self.titleBarHLayout.insertWidget(
            1, self.titleBar.titleLabel, 0, Qt.AlignLeft)
        self.titleBarHLayout.insertWidget(2, self.tasks_btn, 0, Qt.AlignLeft)
        self.titleBarHLayout.insertWidget(3, self.help_btn, 0, Qt.AlignLeft)
        self.titleBarHLayout.insertSpacing(0, 10)
        # self.titleBarHLayout.insertSpacing(2, 30)

    def _fix_theme(self, theme: str):
        theme = theme.lower()
        _theme = Theme.DARK
        if theme == 'auto' or theme == 'system':
            if darkdetect.isDark():
                _theme = Theme.DARK
            else:
                _theme = Theme.LIGHT
        elif theme == "dark":
            _theme = Theme.DARK
        elif theme == "light":
            _theme = Theme.LIGHT

        return _theme

    def set_theme(self, theme: str):
        _theme = self._fix_theme(theme)
        theme = _theme.value.lower()
        self.setProperty('theme', theme)
        self.update()
        setTheme(_theme)

    def show_license_dialog(self):
        if not license_manager.is_activated():
            dialog = LicenseDialog(self)
            if not dialog.exec():
                logger.info("License activation cancelled. Exiting.")
                dialog.close()

    def on_sidebar_item_clicked(self, item):
        route = item.property('routeKey')
        if route:
            interface = self.findChild(QWidget, route)
            if interface:
                self.stackedWidget.setCurrentWidget(interface)
