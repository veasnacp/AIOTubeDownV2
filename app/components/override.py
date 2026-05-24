from typing import Optional, Union

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from PySide6Addons import CheckableMenu as FluentCheckableMenu
from PySide6Addons import ComboBox
from PySide6Addons import FluentIcon as FIF
from PySide6Addons import FluentIconBase, LineEdit, MenuAnimationType, MenuIndicatorType
from PySide6Addons import MessageBoxBase as FluentMessageBoxBase
from PySide6Addons import NavigationBar as FluentNavigationBar
from PySide6Addons import NavigationBarPushButton as FluentNavigationBarPushButton
from PySide6Addons import NavigationItemPosition
from PySide6Addons import RoundMenu as FluentRoundMenu
from PySide6Addons import SegmentedItem as SimpleSegmentedItem
from PySide6Addons import SegmentedWidget, SimpleCardWidget, SpinBox, TextEdit
from PySide6Addons import ToolTip as QFTooltip
from PySide6Addons import ToolTipFilter, ToolTipPosition
from PySide6Addons import (
    TransparentDropDownToolButton as FluentTransparentDropDownToolButton,
)
from PySide6Addons import TransparentToolButton as FluentTransparentToolButton
from PySide6Addons import drawIcon, isDarkTheme, setFont, themeColor
from PySide6Addons.common.color import autoFallbackThemeColor
from PySide6Addons.components.widgets.combo_box import ComboBoxMenu
from PySide6Addons.components.widgets.menu import LineEditMenu, TextEditMenu

from ..theme import Colors, DarkMode, LightMode


class TransparentDropDownToolButton(FluentTransparentDropDownToolButton):
    ...


class TransparentToolButton(FluentTransparentToolButton):
    ...


class ToolTip(QFTooltip):
    def setStyleSheet(self, styleSheet):
        styleSheet = styleSheet + \
            f"MainWindow[theme=dark] ToolTip > #container {{background-color: {DarkMode.popover}}}"
        return super().setStyleSheet(styleSheet)


class CreateTooltipFilter(ToolTipFilter):
    "Tool tip filter"

    def _createToolTip(self):
        return ToolTip(self.parent().toolTip(), self.parent().window())


def installTooltipFilter(widget: QWidget, showDelay=300, position=ToolTipPosition.TOP):
    widget.installEventFilter(CreateTooltipFilter(widget, showDelay, position))


class RoundMenu(FluentRoundMenu):
    _styleSheet = f"""
MainWindow MenuActionListWidget {{
    background-color: {LightMode.card};
}}

MainWindow[theme=dark] MenuActionListWidget {{
    background-color: {DarkMode.popover};
}}

MainWindow[theme=dark] MenuActionListWidget::item {{
    color: white;
}}

MainWindow[theme=dark] MenuActionListWidget::item:disabled {{
    color: rgba(255, 255, 255, 0.4);
}}
MainWindow[theme=dark] MenuActionListWidget::item:hover {{
    background-color: rgba(255, 255, 255, 0.08);
}}

MainWindow[theme=dark] MenuActionListWidget::item:selected {{
    background-color: rgba(255, 255, 255, 0.08);
    color: white;
}}

MainWindow[theme=dark] MenuActionListWidget::item:selected:active {{
    background-color: rgba(255, 255, 255, 0.06);
    color: rgba(255, 255, 255, 0.7);
}}
"""

    def __init__(self, title: str = "", styleSheet="", parent=None):
        super().__init__(title, parent=parent)
        self._styleSheet += styleSheet
        self.view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view.setContentsMargins(4, 4, 4, 4)

    def setStyleSheet(self, styleSheet):
        return super().setStyleSheet(styleSheet + self._styleSheet)

    def exec(self, pos, ani=True, aniType=MenuAnimationType.FADE_IN_DROP_DOWN):
        return super().exec(pos, ani, aniType)

    def onClose(self):
        pass

    def closeEvent(self, e):
        self.onClose()
        super().closeEvent(e)
        # self = None


class CheckableMenu(FluentCheckableMenu):
    """ Checkable menu """
    _styleSheet = RoundMenu._styleSheet

    def __init__(self, title="", parent=None, indicatorType=MenuIndicatorType.CHECK, styleSheet=""):
        super().__init__(title, parent, indicatorType)
        self._styleSheet += styleSheet
        self.view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view.setContentsMargins(4, 4, 4, 4)

    def setStyleSheet(self, styleSheet):
        styleSheet += self._styleSheet
        return super().setStyleSheet(styleSheet)

    def exec(self, pos, ani=True, aniType=MenuAnimationType.FADE_IN_DROP_DOWN):
        return super().exec(pos, ani, aniType)

    def onClose(self):
        pass

    def closeEvent(self, e):
        self.onClose()
        super().closeEvent(e)
        # self = None


def additional_stylesheet_input(widget_name: str):
    return f"""
MainWindow[theme=light] {widget_name}:focus {{
    background-color: {LightMode.input};
}}
MainWindow[theme=dark] {widget_name}:focus {{
    background-color: {DarkMode.input};
}}
"""


class NumberInputMenu(TextEditMenu):
    def __init__(self, parent):
        super().__init__(parent)

    def setStyleSheet(self, styleSheet):
        styleSheet += RoundMenu._styleSheet
        return super().setStyleSheet(styleSheet)


class TextInput(LineEdit):
    disabledContextMenu = False

    def __init__(self, parent=None):
        super().__init__(parent)

    def setDisabledContextMenu(self, val: bool):
        self.disabledContextMenu = val

    # def setStyleSheet(self, styleSheet):
    #     styleSheet = styleSheet + additional_stylesheet_input('LineEdit')
    #     return super().setStyleSheet(styleSheet)

    def contextMenuEvent(self, e: QMouseEvent):
        if self.disabledContextMenu:
            return
        menu = LineEditMenu(self)
        menu.setStyleSheet(menu.styleSheet() + '\n' + RoundMenu._styleSheet)
        menu.exec(e.globalPos(), True)


class TextAreaInput(TextEdit):
    disabledContextMenu = False

    def setDisabledContextMenu(self, val: bool):
        self.disabledContextMenu = val

    # def setStyleSheet(self, styleSheet):
    #     styleSheet += additional_stylesheet_input('TextEdit')
    #     return super().setStyleSheet(styleSheet)

    def contextMenuEvent(self, e: QMouseEvent):
        if self.disabledContextMenu:
            return
        menu = TextEditMenu(self)
        menu.setStyleSheet(menu.styleSheet() + '\n' + RoundMenu._styleSheet)
        menu.exec(e.globalPos(), True)


class NumberInput(SpinBox):
    disabledContextMenu = False

    def setDisabledContextMenu(self, val: bool):
        self.disabledContextMenu = val

    def setStyleSheet(self, styleSheet):
        styleSheet += additional_stylesheet_input('SpinBox')
        return super().setStyleSheet(styleSheet)

    def _showContextMenu(self, pos):
        if self.disabledContextMenu:
            return
        menu = LineEditMenu(self.lineEdit())
        menu.setStyleSheet(menu.styleSheet() + '\n' + RoundMenu._styleSheet)
        menu.exec(self.mapToGlobal(pos), True)


class SelectComboBox(ComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)

    def _createComboMenu(self):
        menu = ComboBoxMenu(self)
        menu.setStyleSheet(menu.styleSheet() + '\n' + RoundMenu._styleSheet)
        return menu


class CardWidget(SimpleCardWidget):
    def __init__(
        self,
        parent=None,
        light_background_color: Optional[Union[str, QColor]] = None,
        dark_background_color: Optional[Union[str, QColor]] = None,
        disableAnimation: bool = True
    ):
        self._light_background_color = light_background_color or Colors.qt_alpha(
            LightMode.card_soft_light, 0.7)
        self._dark_background_color = dark_background_color or DarkMode.card_soft_light
        super().__init__(parent)
        self.disableAnimation = disableAnimation
        if self.disableAnimation:
            self.backgroundColorAni.setDuration(0)
        # self.setBackgroundColor(
        #     self._dark_background_color, self._light_background_color)
        self.createShadowEffect()

    def setDarkBackgroundColor(self, color: Union[str, QColor]):
        self._dark_background_color = color

    def setLightBackgroundColor(self, color: Union[str, QColor]):
        self._light_background_color = color

    def setBackgroundColor(
        self,
        dark_color: Union[str, QColor],
        light_color: Union[str, QColor]
    ):
        self.setDarkBackgroundColor(dark_color)
        self.setLightBackgroundColor(light_color)

    def _normalBackgroundColor(self):
        if isinstance(self._light_background_color, str):
            light_color = QColor(self._light_background_color)
        else:
            light_color = self._light_background_color
        if isinstance(self._dark_background_color, str):
            dark_color = QColor(self._dark_background_color)
        else:
            dark_color = self._dark_background_color

        return (
            dark_color if isDarkTheme() else light_color
        )

    def _hoverBackgroundColor(self):
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self):
        return self._normalBackgroundColor()

    def createShadowEffect(self, offset=QPoint(0, 8), blurRadius=5, normalColor=QColor(0, 0, 0, 0)):
        self.shadowEffect = QGraphicsDropShadowEffect(self)
        self.shadowEffect.setOffset(offset)
        self.shadowEffect.setBlurRadius(blurRadius)
        self.shadowEffect.setColor(normalColor)
        return self.shadowEffect


class SegmentedItem(SimpleSegmentedItem):
    def setStyleSheet(self, styleSheet):
        styleSheet = f"""{styleSheet}
SegmentedItem[isSelected=false], SegmentedItem[isSelected=true] {{
    padding-top: 6px; padding-bottom: 6px; margin: 0px
}}
"""
        return super().setStyleSheet(styleSheet)


class SegmentedControl(SegmentedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.offset = QPoint(0, 0)
        self.blurRadius = 6
        self.normalColor = QColor(0, 0, 0, 0)
        self.marginY = 8
        self.setContentsMargins(*tuple([self.marginY]*4))

    def setStyleSheet(self, styleSheet):
        styleSheet = f"""{styleSheet}
MainWindow[theme=light] SegmentedControl {{ background-color: {LightMode.card}}}
MainWindow[theme=dark] SegmentedControl {{ background-color: {DarkMode.card}}}
"""
        return super().setStyleSheet(styleSheet)

    def insertItem(self, index: int, routeKey: str, text: str, onClick=None, icon=None):
        if routeKey in self.items:
            return

        item = SegmentedItem(text, self)
        if icon:
            item.setIcon(icon)

        self.insertWidget(index, routeKey, item, onClick)
        return item

    def paintEvent(self, e):
        QWidget.paintEvent(self, e)

        if not self.currentItem():
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        # draw background
        if isDarkTheme():
            painter.setPen(QColor(255, 255, 255, 14))
            painter.setBrush(QColor(255, 255, 255, 30))
        else:
            painter.setPen(QColor(0, 0, 0, 19))
            painter.setBrush(QColor(LightMode.muted))

        item = self.currentItem()
        rect = item.rect().adjusted(
            1, 1, -1, -1).translated(int(self.slideAni.value()), self.marginY)
        painter.drawRoundedRect(rect, 5, 5)

        # draw indicator
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(themeColor())

        x = int(self.currentItem().width() / 2 - 8 + self.slideAni.value())
        painter.drawRoundedRect(
            QRectF(x, self.height() - 3.5, 16, 3), 1.5, 1.5)

    def _createShadowEffect(self):
        self.shadowEffect = QGraphicsDropShadowEffect(self)
        self.shadowEffect.setOffset(self.offset)
        self.shadowEffect.setBlurRadius(self.blurRadius)
        self.shadowEffect.setColor(self.normalColor)
        return self.shadowEffect


class MessageBoxBase(FluentMessageBoxBase):
    def setStyleSheet(self, styleSheet: str, /) -> None:
        styleSheet = f"""{styleSheet}
MainWindow MessageBoxBase, MainWindow MessageBoxBase #centerWidget {{ background-color: {LightMode.card}; border: 1px solid rgba(144, 144, 142, 0.2);}}
MainWindow[theme=dark] MessageBoxBase, MainWindow[theme=dark] MessageBoxBase #centerWidget {{ background-color: {DarkMode.card}; border: 1px solid rgba(144, 144, 142, 0.2);}}
"""
        return super().setStyleSheet(styleSheet)


class NavigationBarPushButton(FluentNavigationBarPushButton):
    def __init__(self, icon: Union[str, QIcon, FIF], text: str, isSelectable: bool, selectedIcon=None, parent=None):
        super().__init__(icon, text, isSelectable, selectedIcon, parent)
        self.isCompacted = False
        self.lightSelectedTextColor = QColor(Colors.black)
        self.darkSelectedTextColor = self.darkSelectedColor

    def _drawIcon(self, painter: QPainter):
        # if (self.isPressed or not self.isEnter) and not (self.isSelected or self.isAboutSelected):
        #     painter.setOpacity(0.6)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        if self._isSelectedTextVisible:
            rect = QRectF(16, 6, 30, 30)
        else:
            rect = QRectF(16, 6 + self.iconAni.offset, 30, 30)

        selectedIcon = self._selectedIcon or self._icon

        if isinstance(selectedIcon, FluentIconBase) and (self.isSelected or self.isAboutSelected):
            color = autoFallbackThemeColor(
                self.lightSelectedColor, self.darkSelectedColor)
            selectedIcon.render(painter, rect, fill=color.name())
        elif self.isSelected or self.isAboutSelected:
            drawIcon(selectedIcon, painter, rect)
        else:
            drawIcon(self._icon, painter, rect)

    def _drawText(self, painter: QPainter):
        if self.isSelected and not self._isSelectedTextVisible:
            return

        if self.isSelected or self.isAboutSelected:
            painter.setPen(autoFallbackThemeColor(
                self.lightSelectedTextColor or self.lightSelectedColor,
                self.darkSelectedTextColor or self.darkSelectedColor
            ))
        else:
            painter.setPen(Qt.white if isDarkTheme() else Qt.black)

        painter.setFont(self.font())
        rect = QRect(0, 32, self.width(), 26)
        painter.drawText(rect, Qt.AlignCenter, self.text())


class NavigationBar(FluentNavigationBar):
    def insertItem(self, index: int, routeKey: str, icon: Union[str, QIcon, FluentIconBase], text: str, onClick=None,
                   selectable=True, selectedIcon=None, position=NavigationItemPosition.TOP):
        """ insert navigation tree item

        Parameters
        ----------
        index: int
            the insert position of parent widget

        routeKey: str
            the unique name of item

        icon: str | QIcon | FluentIconBase
            the icon of navigation item

        text: str
            the text of navigation item

        onClick: callable
            the slot connected to item clicked signal

        selectable: bool
            whether the item is selectable

        selectedIcon: str | QIcon | FluentIconBase
            the icon of navigation item in selected state

        position: NavigationItemPosition
            where the button is added
        """
        if routeKey in self.items:
            return

        w = NavigationBarPushButton(icon, text, selectable, selectedIcon, self)
        w.setSelectedColor(self.lightSelectedColor, self.darkSelectedColor)
        w.setSelectedTextVisible(self.isSelectedTextVisible())
        self.insertWidget(index, routeKey, w, onClick, position)
        return w
