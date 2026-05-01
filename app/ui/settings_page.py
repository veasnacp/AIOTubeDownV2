from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QWidget
from PySide6Addons import ComboBox, ComboBoxSettingCard, ExpandLayout
from PySide6Addons import FluentIcon as FIF
from PySide6Addons import (
    FolderListSettingCard,
    HyperlinkCard,
    OptionsConfigItem,
    OptionsSettingCard,
    PrimaryPushSettingCard,
    PushSettingCard,
    RangeSettingCard,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    Theme,
    qconfig,
    setTheme,
    setThemeColor,
)
from PySide6Addons.components.layout.expand_layout import ExpandLayout
from PySide6Addons.components.settings.setting_card import (
    ColorPickerButton,
    SettingCard,
)
from PySide6Addons.components.widgets.button import PushButton
from PySide6Addons.components.widgets.label import CaptionLabel

from ..components.override import CardWidget
from ..theme import Colors, LightMode


class ColorSettingCard(SettingCard):
    """ Custom color setting card """
    colorChanged = Signal(QColor)

    def __init__(self, color, title, content, parent=None):
        super().__init__(FIF.PALETTE, title, content, parent)
        self.colorPicker = ColorPickerButton(color, title, self)
        self.resetBtn = PushButton("Reset", self)
        self.hBoxLayout.setContentsMargins(16, 0, 16, 0)
        self.hBoxLayout.addWidget(self.colorPicker, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(10)
        self.hBoxLayout.addWidget(self.resetBtn, 0, Qt.AlignRight)

        self.colorPicker.colorChanged.connect(self.colorChanged)
        self.resetBtn.clicked.connect(lambda: self.resetColor())

    def resetColor(self):
        self.colorPicker.setColor(LightMode.primary)
        setThemeColor(LightMode.primary)


class CustomComboBoxSettingCard(SettingCard):
    """ Custom combo box setting card """

    def __init__(self, icon, title, content, texts, parent=None):
        super().__init__(icon, title, content, parent)
        self.comboBox = ComboBox(self)
        self.comboBox.addItems(texts)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.comboBox.setFixedWidth(150)


class SettingsPage(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settings")
        self.setWidgetResizable(True)
        self.setViewportMargins(16, 16, 16, 16)
        # self.setStyleSheet("""
        #     QScrollArea {
        #         border: none;
        #     }
        # """)

        self.contentWidget = CardWidget()
        self.setWidget(self.contentWidget)
        self.expand_layout = ExpandLayout(self.contentWidget)

        self.initUI()
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

    def initUI(self):
        # Appearance Group
        appearanceGroup = SettingCardGroup(
            "Appearance", self.contentWidget)
        self.expand_layout.addWidget(appearanceGroup)

        # Theme Card
        self.themeCard = OptionsSettingCard(
            qconfig.themeMode,
            FIF.BRUSH,
            self.tr('Application Theme'),
            self.tr("Change the appearance of your application"),
            texts=[
                self.tr('Light'), self.tr('Dark'),
                self.tr('System')
            ],
            parent=self.contentWidget
        )
        self.themeCard.optionChanged.connect(self.onThemeChanged)
        appearanceGroup.addSettingCard(self.themeCard)

        # Accent Color
        self.accentColorCard = ColorSettingCard(
            QColor(LightMode.primary), "Accent Color", "Change the application accent color", self.contentWidget)
        appearanceGroup.addSettingCard(self.accentColorCard)

        # Window Title Bar
        self.titleBarSwitch = SwitchSettingCard(
            FIF.BRUSH, "Window Title Bar", "Use Windows 11 title bar style", parent=self.contentWidget)
        appearanceGroup.addSettingCard(self.titleBarSwitch)

        # Language
        self.language = PushSettingCard(
            "Change", FIF.BRUSH, "Language", "Choose your preferred language", self.contentWidget)
        appearanceGroup.addSettingCard(self.language)

        # About Group
        aboutGroup = SettingCardGroup(
            "About", self.contentWidget)
        self.expand_layout.addWidget(aboutGroup)

        # Version
        self.versionCard = PushSettingCard(
            "Copy", FIF.INFO, "Version", "1.0.0", self.contentWidget)
        aboutGroup.addSettingCard(self.versionCard)

        # Feedback
        self.feedbackCard = PushSettingCard(
            "Send", FIF.FEEDBACK, "Feedback", "Send us your feedback", self.contentWidget)
        aboutGroup.addSettingCard(self.feedbackCard)

        # Check for Updates
        self.updateCard = PushSettingCard(
            "Check", FIF.UPDATE, "Check for Updates", "Check for the latest version", self.contentWidget)
        aboutGroup.addSettingCard(self.updateCard)

        # License
        self.licenseCard = PushSettingCard(
            "Manage", FIF.CERTIFICATE, "License", "Manage your license", self.contentWidget)
        aboutGroup.addSettingCard(self.licenseCard)

        self.setWidget(self.contentWidget)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        # Set initial value
        current_theme = self.window().property("theme")
        if current_theme == "light":
            self.themeCard.setValue(Theme.LIGHT)
        elif current_theme == "dark":
            self.themeCard.setValue(Theme.DARK)
        else:
            theme = self.window()._fix_theme(current_theme)
            self.themeCard.setValue(theme)

        # Connect signals
        self.themeCard.optionChanged.connect(self.onThemeChanged)
        self.accentColorCard.colorChanged.connect(setThemeColor)
        self.titleBarSwitch.checkedChanged.connect(self.onTitleBarChanged)
        self.language.clicked.connect(self.onLanguageClicked)
        self.feedbackCard.clicked.connect(self.onFeedbackClicked)
        self.updateCard.clicked.connect(self.onUpdateClicked)
        self.licenseCard.clicked.connect(self.onLicenseClicked)

    def onAccentColorClicked(self):
        pass

    def onLanguageClicked(self):
        pass

    def onThemeChanged(self, index):
        if hasattr(self, "window"):
            if isinstance(index, OptionsConfigItem):
                theme = index.value.value
                self.window().set_theme(theme)
                theme = self.window()._fix_theme(theme)
                self.themeCard.setValue(theme)
                return
            themes = [Theme.LIGHT.value, Theme.DARK.value, "system"]
            self.window().set_theme(themes[index])

    def onAccentColorChanged(self, index):
        colors = [Colors.blue_9, Colors.green_9, Colors.red_9, Colors.purple_9, Colors.orange_9,
                  Colors.yellow_9, Colors.teal_9, Colors.pink_9, Colors.cyan_9, Colors.brown_9]
        setThemeColor(colors[index])

    def onTitleBarChanged(self, checked):
        pass

    def onLanguageChanged(self, index):
        pass

    def onFeedbackClicked(self):
        pass

    def onUpdateClicked(self):
        pass

    def onLicenseClicked(self):
        from .license_dialog import LicenseDialog
        dialog = LicenseDialog(self.window())
        dialog.exec()
