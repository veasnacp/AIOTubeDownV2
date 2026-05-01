from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget
from PySide6Addons import (
    CaptionLabel,
    FluentIcon,
    NavigationInterface,
    NavigationItemPosition,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TransparentToolButton,
    setFont,
)


class Sidebar(NavigationInterface):
    """Refactored Sidebar for navigation only"""
    itemClicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent, showMenuButton=True)

        # Add tasks and settings items
        self.addItem(
            routeKey='downloader',
            icon=FluentIcon.DOWNLOAD,
            text='Downloader',
            onClick=lambda: self.itemClicked.emit(
                self.panel.widget('downloader')),
            position=NavigationItemPosition.TOP,
            tooltip='Downloader'
        )

        self.addItem(
            routeKey='drama_downloader',
            icon=FluentIcon.MOVIE,
            text='Drama Downloader',
            onClick=lambda: self.itemClicked.emit(
                self.panel.widget('drama_downloader')),
            position=NavigationItemPosition.TOP,
            tooltip='Drama Downloader'
        )

        self.addItem(
            routeKey='license',
            icon=FluentIcon.FINGERPRINT,
            text='License',
            onClick=lambda: self.itemClicked.emit(
                self.panel.widget('license')),
            position=NavigationItemPosition.BOTTOM,
            tooltip='License'
        )

        self.addItem(
            routeKey='settings',
            icon=FluentIcon.SETTING,
            text='Settings',
            onClick=lambda: self.itemClicked.emit(
                self.panel.widget('settings')),
            position=NavigationItemPosition.BOTTOM,
            tooltip='Settings'
        )
