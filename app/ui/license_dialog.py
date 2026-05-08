import random
import sys
import hashlib
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PySide6Addons import (MessageBoxBase, SubtitleLabel, LineEdit, PushButton,
                           PrimaryPushButton, FluentIcon, InfoBar, CaptionLabel,
                           BodyLabel)

from ..core.license_manager import license_manager
from ..components.override import TransparentToolButton


class LicenseDialog(MessageBoxBase):
    """Custom Dialog for License Activation"""

    def __init__(self, parent=None):
        super().__init__(parent)

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
        self.hw_label = CaptionLabel(
            "Your Hardware ID (Unique to this PC):", self)
        self.hw_id_edit = LineEdit(self)
        self.hw_id_edit.setText(license_manager.hw_id)
        self.hw_id_edit.setReadOnly(True)

        self.copy_btn = PushButton(FluentIcon.COPY, "Copy ID", self)
        self.copy_btn.clicked.connect(self._copy_hw_id)

        self.hw_row = QHBoxLayout()
        self.hw_row.addWidget(self.hw_id_edit)
        self.hw_row.addWidget(self.copy_btn)

        # random calculation for security (simple)
        self.calc_label = BodyLabel("Solve this math problem:")
        self.random_btn = TransparentToolButton(FluentIcon.ROTATE, self)
        self.random_btn.setFixedSize(QSize(20, 20))
        self.random_btn.setIconSize(QSize(12, 12))
        self.random_btn.setToolTip("Generate New Math Problem")
        self.random_btn.clicked.connect(self._generate_random_math)
        self.calc_edit = LineEdit()
        self.calc_edit.setPlaceholderText("Answer")
        self.calc_row = QHBoxLayout()
        self.calc_row.addWidget(self.calc_label)
        self.calc_row.addWidget(self.calc_edit)
        self.calc_row.addWidget(self.random_btn)
        self.calc_row.setAlignment(Qt.AlignCenter)

        self._generate_random_math()
        self.calc_edit.textChanged.connect(self._on_calc_changed)

        # License key section
        self.key_label = CaptionLabel("Enter License Key:", self)
        self.key_edit = LineEdit(self)
        self.key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")

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
            QLabel("Please activate your license to continue using Download Manager."))
        self.viewLayout.addSpacing(15)
        self.viewLayout.addWidget(self.hw_label)
        self.viewLayout.addLayout(self.hw_row)
        self.viewLayout.addSpacing(15)
        self.viewLayout.addLayout(self.calc_row)
        self.viewLayout.addSpacing(15)
        self.viewLayout.addWidget(self.key_label)
        self.viewLayout.addWidget(self.key_edit)
        self.viewLayout.addSpacing(20)
        self.viewLayout.addLayout(self.bottom_layout)

        self.widget.setMinimumWidth(450)

    def _copy_hw_id(self):
        QApplication.clipboard().setText(license_manager.hw_id)
        InfoBar.success("Copied", "Hardware ID copied to clipboard",
                        duration=1500, parent=self)

    def _on_activate_clicked(self):
        key = self.key_edit.text().strip()
        if not key:
            InfoBar.warning(
                "Required", "Please enter a license key", parent=self)
            return

        if license_manager.activate(key):
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
                "Invalid license key for this hardware ID.",
                duration=3000,
                parent=self
            )
            self.key_edit.setFocus()

    @staticmethod
    def generate_license_key(hw_id):
        """Generate a license key for the given hardware ID"""
        return hashlib.sha256((hw_id + "VeasNa").encode()).hexdigest().upper()[:16]

    def _generate_random_math(self):
        self.num1 = random.randint(1, 10)
        self.num2 = random.randint(1, 10)
        self.operator = random.choice(['+', '-', '*', '/'])
        self.calc_label.setText(f"{self.num1} {self.operator} {self.num2} = ?")
        self.calc_edit.clear()
        if hasattr(self, "activate_btn"):
            self.activate_btn.setEnabled(False)
            self.key_edit.clear()

    def _on_calc_changed(self, text):
        try:
            # Safe evaluation for simple math
            expected = eval(f"{self.num1} {self.operator} {self.num2}")
            if text == str(int(expected)):
                self.activate_btn.setEnabled(True)
                license_key = self.generate_license_key(license_manager.hw_id)
                self.key_edit.setText(license_key)
            else:
                self.activate_btn.setEnabled(False)
                self.key_edit.clear()
        except:
            self.activate_btn.setEnabled(False)

    def closeEvent(self, event):
        # if not license_manager.is_activated():
        #     QApplication.quit()
        # else:
        event.accept()
