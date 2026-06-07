from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMessageBox, QWidget
from PySide6Addons import BodyLabel, ComboBox, ComboBoxSettingCard, ConfigItem, ExpandLayout
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
    TitleLabel,
    qconfig,
    setTheme,
    setThemeColor,
    MessageBoxBase, SubtitleLabel, LineEdit, PushButton,
    PrimaryPushButton, InfoBar, CaptionLabel
)
from PySide6Addons.components.layout.expand_layout import ExpandLayout
from PySide6Addons.components.settings.setting_card import (
    ColorPickerButton,
    SettingCard,
)
from PySide6Addons.components.widgets.button import PushButton
from PySide6Addons.components.widgets.label import CaptionLabel

from ..config.constants import APP_NAME, DIRS
from ..theme import Colors, DarkMode, LightMode
from ..components.override import TransparentToolButton
from ..components.qt import LcBase

qconfig.file = DIRS.user_data_path / "settings.json"
qconfig.save = lambda: None

qconfig.fontFamilies = ConfigItem(APP_NAME, "FontFamilies", [
    'Segoe UI', 'Battambang', 'Microsoft YaHei', 'PingFang SC'
])


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

        # Sticky Title Label
        self.settingLabel = TitleLabel("Settings", self)
        self.settingLabel.setObjectName("settingLabel")

        self.contentWidget = QWidget()
        self.contentWidget.setObjectName("contentWidget")
        self.expand_layout = ExpandLayout(self.contentWidget)

        self.initUI()

        self.setWidget(self.contentWidget)
        self.setViewportMargins(0, 80, 0, 20)
        self.settingLabel.move(36, 30)

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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

        # add setting card group to layout
        self.expand_layout.setSpacing(28)
        self.expand_layout.setContentsMargins(36, 10, 36, 0)

        # Set initial value
        current_theme = self.window().property("theme")
        if current_theme == "light":
            self.themeCard.setValue(Theme.LIGHT)
        elif current_theme == "dark":
            self.themeCard.setValue(Theme.DARK)
        else:
            theme = self.window()._fix_theme(current_theme)
            self.themeCard.setValue(theme)

        self.dialog = LcDialog(self.window())
        self.dialog.close()

        # Connect signals
        self.themeCard.optionChanged.connect(self.onThemeChanged)
        self.accentColorCard.colorChanged.connect(self.onAccentColorChanged)
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

    def onAccentColorChanged(self, color: QColor):
        setThemeColor(color)
        LightMode.primary = color.name()
        DarkMode.primary = color.name()
        self.update()

    def onTitleBarChanged(self, checked):
        pass

    def onLanguageChanged(self, index):
        pass

    def onFeedbackClicked(self):
        pass

    def onUpdateClicked(self):
        pass

    def onLicenseClicked(self):
        self.dialog.exec()


class LcDialog(LcBase, MessageBoxBase):
    """Custom Dialog for License Activation"""

    def __init__(self, parent=None):
        LcBase.__init__(self)
        super().__init__(parent)

        self.init_dll()

        # Title bar
        self.title_layout = QHBoxLayout()
        self.titleLabel = SubtitleLabel("License Activation", self)
        self.close_btn = TransparentToolButton(FIF.CLOSE, self)
        self.close_btn.setFixedSize(QSize(20, 20))
        self.close_btn.setIconSize(QSize(12, 12))
        self.close_btn.clicked.connect(self.reject)

        self.title_layout.addWidget(self.titleLabel)
        self.title_layout.addStretch(1)
        self.title_layout.addWidget(self.close_btn)

        # Hardware ID section
        self.hw_label = CaptionLabel("Your Hardware ID", self)
        self.hw_id_edit = LineEdit(self)
        self.hw_id = self._cache.get('hw_id') or ''
        self.hw_id_edit.setText(self.hw_id.upper() if self.hw_id else '')
        self.hw_id_edit.setReadOnly(True)

        self.copy_btn = PushButton(FIF.COPY, "Copy ID", self)
        self.copy_btn.clicked.connect(self._copy_hw_id)

        self.hw_row = QHBoxLayout()
        self.hw_row.addWidget(self.hw_id_edit)
        self.hw_row.addWidget(self.copy_btn)

        # License key section
        self.key_label = CaptionLabel("Enter License Key:", self)
        self.key_edit = LineEdit(self)
        self.key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_edit.textChanged.connect(self._on_key_changed)

        # Buttons
        self.buttonGroup.hide()
        self.bottom_layout = QHBoxLayout()
        self.cancel_btn = PushButton("Close", self)
        self.cancel_btn.clicked.connect(self.reject)
        self.activate_btn = PrimaryPushButton("Activate Now", self)
        self.activate_btn.clicked.connect(self._on_activate_clicked)
        self.activate_btn.setEnabled(False)

        self.bottom_layout.addStretch(1)
        self.bottom_layout.addWidget(self.cancel_btn)
        self.bottom_layout.addWidget(self.activate_btn)

        # Main Layout
        self.viewLayout.addLayout(self.title_layout)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(
            BodyLabel(f"Please activate your license to continue using {APP_NAME}."))
        self.viewLayout.addSpacing(15)
        self.viewLayout.addWidget(self.hw_label)
        self.viewLayout.addLayout(self.hw_row)
        self.viewLayout.addSpacing(15)
        self.viewLayout.addWidget(self.key_label)
        self.viewLayout.addWidget(self.key_edit)
        self.viewLayout.addSpacing(20)
        self.viewLayout.addLayout(self.bottom_layout)

        self.widget.setMinimumWidth(450)

        self._load_hwid()
        self._load_backend_url()

    def _copy_hw_id(self):
        QApplication.clipboard().setText(self.hw_id_edit.text().strip())
        InfoBar.success("Copied", "Hardware ID copied to clipboard",
                        duration=1500, parent=self)

    def _on_hwid_result(self, code: int, hwid: str):
        if code == 0:
            self._cache['hw_id'] = hwid.upper()
            self.hw_id_edit.setText(self._cache['hw_id'])
        else:
            QMessageBox.warning(
                self, "Warning", "⚠️ Unable to retrieve HWID. License activation may fail.")

    def _on_backend_url_result(self, code: int, url: str):
        if code == 0 and url:
            self._cache['backend_url'] = url
            self._backend_url = url
            self.check_existing_activation()
        else:
            self.close()

    def _on_verifying_status(self, status: str):
        print("verifying status", status)
        if status == "FAILED":
            self.close()

    def _on_activate_clicked(self):
        key = self.key_edit.text().strip()
        if not key:
            InfoBar.warning(
                "Required", "Please enter a license key", parent=self)
            return

        self.handle_activation(key)

    def _on_activation_result(self, result: int, output: str):
        title, message = self._get_activation_result(result, output)
        if result == 0:
            self._cache['license_key'] = self.key_edit.text().strip().upper()
            InfoBar.success(
                "Activation Successful",
                "Your application has been activated. Thank you!",
                duration=3000,
                parent=self.parent() or self
            )
            self.accept()
        else:
            InfoBar.error(
                "Activation Failed",
                "Invalid license key or Expired.",
                duration=3000,
                parent=self
            )
            self.key_edit.setFocus()

    def _on_key_changed(self, text):
        self.activate_btn.setEnabled(len(text) >= 16)

    def closeEvent(self, event):
        # if not license_manager.is_activated():
        #     QApplication.quit()
        # else:
        event.accept()
