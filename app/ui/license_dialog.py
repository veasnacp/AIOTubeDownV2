import random
import sys
import hashlib
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PySide6Addons import (MessageBoxBase, SubtitleLabel, LineEdit, PushButton,
                           PrimaryPushButton, FluentIcon, InfoBar, CaptionLabel,
                           BodyLabel)


from ..config.constants import APP_NAME
from ..components.override import TransparentToolButton
from ..components.qt import LcBase


class LicenseDialog(LcBase, MessageBoxBase):
    """Custom Dialog for License Activation"""

    def __init__(self, parent=None):
        LcBase.__init__(self)
        super().__init__(parent)

        self.init_dll()

        # Title bar
        self.title_layout = QHBoxLayout()
        self.titleLabel = SubtitleLabel("License Activation", self)
        self.close_btn = TransparentToolButton(FluentIcon.CLOSE, self)
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

        self.copy_btn = PushButton(FluentIcon.COPY, "Copy ID", self)
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
            QLabel(f"Please activate your license to continue using {APP_NAME}."))
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
