from PySide6.QtGui import QColor, QFont, Qt
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Signal, QObject

from PySide6Addons import FluentIcon as FIF
from PySide6Addons import (
    IconWidget,
    StrongBodyLabel,
    Theme,
    getFont,
)


def use_opacity(widget: QWidget, opacity: float, parent: QObject | None = None):
    # set the opacity
    opacity_effect = QGraphicsOpacityEffect(parent)
    opacity_effect.setOpacity(opacity)
    widget.setGraphicsEffect(opacity_effect)
    return opacity_effect


class IconCard(QFrame):
    """ Icon card """

    clicked = Signal()

    def __init__(self, text: str, icon: FIF, bg_color: str, hover_bg_color: str, parent=None):
        super().__init__(parent=parent)
        self.setStyleSheet(f"""
IconCard {{
    background-color: {str(bg_color)};
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 6px;
}}
IconCard:hover {{
    background-color: {str(hover_bg_color)};
}}
IconCard > StrongBodyLabel {{
    color: #ffffff;
}}
""")

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon = icon.icon(Theme.DARK)
        self.isSelected = False

        self.iconWidget = IconWidget(self.icon, self)
        self.nameLabel = StrongBodyLabel(text, self)
        self.nameLabel.setTextColor(light=QColor(255, 255, 255))
        self.nameLabel.setFont(getFont(12, QFont.Weight.Bold))
        self.vBoxLayout = QVBoxLayout(self)

        self.setFixedSize(64, 64)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(1, 8, 1, 8)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.iconWidget.setFixedSize(22, 22)
        self.vBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignHCenter)
        self.vBoxLayout.addSpacing(14)
        self.vBoxLayout.addWidget(self.nameLabel, 0, Qt.AlignHCenter)

        # text = self.nameLabel.fontMetrics().elidedText(icon.value, Qt.ElideRight, 90)
        # self.nameLabel.setText(text)

    def mouseReleaseEvent(self, e):
        self.isSelected = not self.isSelected

    def mousePressEvent(self, e):
        self.isSelected = not self.isSelected
        self.clicked.emit()

    def setDisabled(self, a0):
        use_opacity(self, 1 if not a0 else 0.6)
        return super().setDisabled(a0)
