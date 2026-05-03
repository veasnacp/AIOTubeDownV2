from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6Addons import CaptionLabel, FluentIcon, PrimaryPushButton

from ..components.icon_card import IconCard, use_opacity
from ..theme import Colors


class ActionPanel(QWidget):
    """The vertical panel with colored action buttons shown in the IDM image"""
    add_url_clicked = Signal()
    stop_clicked = Signal()
    stop_all_clicked = Signal()
    delete_clicked = Signal()
    delete_all_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # self.setFixedWidth(80)
        self.box_layout = QVBoxLayout(self)
        self.box_layout.setContentsMargins(0, 0, 0, 0)
        self.box_layout.setSpacing(15)
        self.box_layout.setAlignment(Qt.AlignTop)

        # 1. Add URL [Green]
        self.add_btn = self._add_btn(
            "Add URL", FluentIcon.ADD, Colors.green_8, Colors.green_9, self.add_url_clicked)
        # 2. Stop [Purple]
        self.stop_btn = self._add_btn(
            "Stop", FluentIcon.PAUSE, Colors.pink_8, Colors.pink_9, self.stop_clicked)
        # 3. Stop All [Orange]
        self.stop_all_btn = self._add_btn(
            "Stop All", FluentIcon.PAUSE, Colors.orange_8, Colors.orange_9, self.stop_all_clicked)
        # 4. Delete [Light Red]
        self.del_btn = self._add_btn(
            "Delete", FluentIcon.DELETE, Colors.red_6, Colors.red_9, self.delete_clicked)
        # 5. Delete All [Red]
        self.del_all_btn = self._add_btn(
            "Delete All", FluentIcon.DELETE, Colors.red_8, Colors.red_9, self.delete_all_clicked)

        self.box_layout.addStretch(1)

    def _add_btn(self, text, icon, color, hover_color, signal):
        iconWidget = IconCard(text, icon, color, hover_color, self)
        state = 'normal' if text in ['Add URL',
                                     'Stop All', 'Delete All'] else 'disabled'
        if state == "disabled":
            iconWidget.setDisabled(True)
            use_opacity(iconWidget, 0.6)
        iconWidget.clicked.connect(signal.emit)
        iconWidget.setToolTip(text)
        self.box_layout.addWidget(iconWidget)
        return iconWidget
