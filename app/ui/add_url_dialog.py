from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
from PySide6Addons import (
    CheckBox,
    FlowLayout,
    FluentIcon,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    SubtitleLabel,
    TransparentToolButton,
)

from ..components.override import CardWidget, MessageBoxBase, NumberInput
from ..components.override import SelectComboBox as ComboBox
from ..components.override import TextAreaInput as TextEdit
from ..components.override import TextInput as LineEdit
from ..config.constants import APP_NAME, DIRS
from ..theme import Colors
from ..utils.validation import is_valid_url


class AddUrlDialog(MessageBoxBase):
    """Deep clone of the 'Enter URLs' dialog in the provided image"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title_layout = QHBoxLayout()
        self.titleLabel = SubtitleLabel("Enter URLs", self)
        self.close_btn = TransparentToolButton(FluentIcon.CLOSE, self)
        self.close_btn.setFixedSize(QSize(20, 20))
        self.close_btn.setIconSize(QSize(12, 12))
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self.reject)
        self.title_layout.addWidget(self.titleLabel)
        self.title_layout.addStretch(1)
        self.title_layout.addWidget(self.close_btn)
        # hide ok and cancel button
        self.buttonGroup.hide()

        self.main_card = CardWidget(self, Colors.web_wash)
        self.main_layout = QVBoxLayout(self.main_card)
        # Stat labels
        self.stats_layout = QHBoxLayout()
        self.total_label = StrongBodyLabel("Total links: 0", self)
        self.total_label.setStyleSheet(f"color: {Colors.green_7};")
        self.invalid_label = StrongBodyLabel("Invalid: 0", self)
        self.invalid_label.setStyleSheet(f"color: {Colors.red_7};")
        self.stats_layout.addWidget(self.total_label)
        self.stats_layout.addWidget(self.invalid_label)
        self.stats_layout.addStretch(1)

        # URL Input
        self.url_edit = TextEdit(self)
        self.url_edit.setPlaceholderText(
            "Paste your links here (one per line)...")
        self.url_edit.setMinimumHeight(200)
        self.url_edit.textChanged.connect(self._update_stats)

        # Options Group
        self.options_group = CardWidget(self)
        self.options_layout = FlowLayout(self.options_group)
        self.options_layout.setContentsMargins(8, 8, 8, 8)
        self.options_layout.setSpacing(8)

        # Options Row 1
        self.cb_site_folder = CheckBox("Folder with Site", self)
        self.cb_user_folder = CheckBox("Folder with Username", self)
        self.cb_thumbnail = CheckBox("Download with Thumbnail", self)
        self.options_layout.addWidget(self.cb_site_folder)
        self.options_layout.addWidget(self.cb_user_folder)
        self.options_layout.addWidget(self.cb_thumbnail)

        self.cb_site_folder.setChecked(True)
        self.cb_user_folder.setChecked(True)
        self.cb_site_folder.checkStateChanged.connect(
            lambda: self._update_download_folder())
        self.cb_user_folder.checkStateChanged.connect(
            lambda: self._update_download_folder())

        # Options Row 2
        self.cb_mp3 = CheckBox("Download with MP3", self)
        self.options_layout.addWidget(self.cb_mp3)

        # Path Selection
        self.path_layout = QHBoxLayout()
        self.path_edit = LineEdit(self)
        self.downloads_path = DIRS.user_downloads_path.joinpath(APP_NAME)
        self._update_download_folder()
        self.browse_btn = PushButton(FluentIcon.FOLDER, "Select Folder", self)
        self.browse_btn.clicked.connect(self._browse_folder)
        self.path_layout.addWidget(self.path_edit)
        self.path_layout.addWidget(self.browse_btn)

        # Bottom Controls
        self.bottom_layout = QHBoxLayout()
        self.count_spin = NumberInput(self)
        self.count_spin.setValue(10)
        self.count_spin.setMinimumWidth(80)
        self.count_spin.setMinimum(0)
        self.count_spin.setMaximum(5000)
        self.count_spin.setSymbolVisible(False)

        self.cat_combo = ComboBox(self)
        self.cat_combo.addItems(["Videos", "Audio", "Documents", "Archives"])
        self.cat_combo.setFixedWidth(100)

        self.res_combo = ComboBox(self)
        self.res_combo.addItems(
            # ad 2k, 4k
            [
                "360 - Low",
                "480 - SD",
                "720 - HD",
                "1080 - Full HD",
                "1440p - 2K",
                "2160p - 4K",
            ]
        )
        # set 720p default
        self.res_combo.setCurrentIndex(2)
        self.res_combo.setFixedWidth(130)

        self.provider_combo = ComboBox(self)
        self.provider_combo.addItems(["Default", "Youtube", "Direct"])
        self.provider_combo.setFixedWidth(100)

        self.download_btn = PrimaryPushButton("Download", self)
        self.download_btn.clicked.connect(self.accept)

        self.bottom_layout.addWidget(self.count_spin)
        self.bottom_layout.addWidget(self.cat_combo)
        self.bottom_layout.addWidget(self.res_combo)
        self.bottom_layout.addWidget(self.provider_combo)
        self.bottom_layout.addStretch(1)
        self.bottom_layout.addWidget(self.download_btn)

        # Add to main layout
        self.viewLayout.addLayout(self.title_layout)
        self.main_layout.addLayout(self.stats_layout)
        self.main_layout.addWidget(self.url_edit)
        self.main_layout.addWidget(self.options_group)
        self.main_layout.addLayout(self.path_layout)
        self.main_layout.addLayout(self.bottom_layout)
        self.viewLayout.addWidget(self.main_card)

        self.viewLayout.setSpacing(10)
        self.viewLayout.setContentsMargins(10, 10, 10, 10)

        self.widget.setMinimumWidth(600)

    def _update_stats(self):
        valid_urls, invalid_urls = self.get_urls()
        self.total_label.setText(
            f"Total links: {len([*valid_urls, *invalid_urls])}")
        self.invalid_label.setText(f"Invalid: {len(invalid_urls)}")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Download Folder", self.path_edit.text())
        if folder:
            self.downloads_path = Path(folder)
            self.path_edit.setText(folder)

    def _update_download_folder(self):
        site_name = "%SITE%" if self.cb_site_folder.isChecked() else ""
        user_name = "%USERNAME%" if self.cb_user_folder.isChecked() else ""
        self.path_edit.setText(
            str(self.downloads_path.joinpath(site_name, user_name)))

    def get_urls(self):
        text = self.url_edit.toPlainText().strip()
        if not text:
            return [], []
        valid_urls = []
        invalid_urls = []
        for u in text.split('\n'):
            u = u.strip()
            if not u:
                continue
            if is_valid_url(u):
                valid_urls.append(u)
            else:
                invalid_urls.append(u)
        return valid_urls, invalid_urls

    def get_options(self):
        # 0: 360, 1: 480, 2: 720, 3: 1080, 4: 1440, 5: 2160
        res_map = {0: "360", 1: "480", 2: "720",
                   3: "1080", 4: "1440", 5: "2160"}
        return {
            "path": str(self.downloads_path),
            "category": self.cat_combo.currentText(),
            "resolution": res_map.get(self.res_combo.currentIndex(), "720"),
            "mp3": self.cb_mp3.isChecked(),
            "thumbnail": self.cb_thumbnail.isChecked(),
            "with_site": self.cb_site_folder.isChecked(),
            "with_username": self.cb_user_folder.isChecked()
        }
