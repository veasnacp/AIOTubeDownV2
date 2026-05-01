from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6Addons import (MessageBoxBase, SubtitleLabel, TextEdit, CheckBox,
                             LineEdit, PushButton, PrimaryPushButton, ComboBox,
                             CaptionLabel, SpinBox, FluentIcon, TransparentToolButton)
import os

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

        # Stat labels
        self.stats_layout = QHBoxLayout()
        self.total_label = CaptionLabel("Total links: 0", self)
        self.total_label.setStyleSheet("color: #28a745;")
        self.invalid_label = CaptionLabel("Invalid: 0", self)
        self.invalid_label.setStyleSheet("color: #dc3545;")
        self.stats_layout.addWidget(self.total_label)
        self.stats_layout.addWidget(self.invalid_label)
        self.stats_layout.addStretch(1)

        # URL Input
        self.url_edit = TextEdit(self)
        self.url_edit.setPlaceholderText("Paste your links here (one per line)...")
        self.url_edit.setMinimumHeight(200)
        self.url_edit.textChanged.connect(self._update_stats)

        # Options Row 1
        self.options_layout1 = QHBoxLayout()
        self.cb_site_folder = CheckBox("Folder with Site", self)
        self.cb_user_folder = CheckBox("Folder with Username", self)
        self.cb_thumbnail = CheckBox("Download with Thumbnail", self)
        self.options_layout1.addWidget(self.cb_site_folder)
        self.options_layout1.addWidget(self.cb_user_folder)
        self.options_layout1.addWidget(self.cb_thumbnail)
        self.options_layout1.addStretch(1)

        # Options Row 2
        self.options_layout2 = QHBoxLayout()
        self.cb_mp3 = CheckBox("Download with MP3", self)
        self.options_layout2.addWidget(self.cb_mp3)
        self.options_layout2.addStretch(1)

        # Path Selection
        self.path_layout = QHBoxLayout()
        self.path_edit = LineEdit(self)
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", "DownloadManager")
        self.path_edit.setText(default_path)
        self.browse_btn = PushButton(FluentIcon.FOLDER, "Select Folder", self)
        self.browse_btn.clicked.connect(self._browse_folder)
        self.path_layout.addWidget(self.path_edit)
        self.path_layout.addWidget(self.browse_btn)

        # Bottom Controls
        self.bottom_layout = QHBoxLayout()
        self.count_spin = SpinBox(self)
        self.count_spin.setValue(1)
        self.count_spin.setFixedWidth(80)

        self.cat_combo = ComboBox(self)
        self.cat_combo.addItems(["Videos", "Audio", "Documents", "Archives"])
        self.cat_combo.setFixedWidth(100)

        self.res_combo = ComboBox(self)
        self.res_combo.addItems(["1080 - Full HD", "720 - HD", "480 - SD", "360 - Low"])
        self.res_combo.setCurrentIndex(1)
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
        self.viewLayout.addLayout(self.stats_layout)
        self.viewLayout.addWidget(self.url_edit)
        self.viewLayout.addLayout(self.options_layout1)
        self.viewLayout.addLayout(self.options_layout2)
        self.viewLayout.addLayout(self.path_layout)
        self.viewLayout.addLayout(self.bottom_layout)

        self.widget.setMinimumWidth(600)

    def _update_stats(self):
        urls = self.get_urls()
        self.total_label.setText(f"Total links: {len(urls)}")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.path_edit.text())
        if folder:
            self.path_edit.setText(folder)

    def get_urls(self):
        text = self.url_edit.toPlainText().strip()
        if not text: return []
        return [u.strip() for u in text.split('\n') if u.strip()]

    def get_options(self):
        res_map = {0: "1080", 1: "720", 2: "480", 3: "360"}
        return {
            "path": self.path_edit.text(),
            "category": self.cat_combo.currentText(),
            "resolution": res_map.get(self.res_combo.currentIndex(), "720"),
            "mp3": self.cb_mp3.isChecked(),
            "thumbnail": self.cb_thumbnail.isChecked(),
            "site_folder": self.cb_site_folder.isChecked(),
            "user_folder": self.cb_user_folder.isChecked()
        }
