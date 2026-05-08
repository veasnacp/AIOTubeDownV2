from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PySide6Addons import (FluentIcon, InfoBar,
                           SubtitleLabel, BodyLabel, SimpleCardWidget,
                           LineEdit, PrimaryPushButton, PushButton, setFont)

from ..core.license_manager import license_manager


class LicenseInterface(QWidget):
    """The License Management interface"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("LicenseInterface")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(20)

        # Title
        self.title_label = SubtitleLabel("License Management", self)
        setFont(self.title_label, 28)
        self.main_layout.addWidget(self.title_label)

        # Status Card
        self.status_card = SimpleCardWidget(self)
        status_layout = QVBoxLayout(self.status_card)

        self.status_header = BodyLabel("Activation Status:", self)
        setFont(self.status_header, 18)

        self.status_badge = QLabel()
        self._update_status_ui()

        status_row = QHBoxLayout()
        status_row.addWidget(self.status_header)
        status_row.addWidget(self.status_badge)
        status_row.addStretch(1)

        status_layout.addLayout(status_row)
        self.main_layout.addWidget(self.status_card)

        # Hardware Info Card
        self.hw_card = SimpleCardWidget(self)
        hw_layout = QVBoxLayout(self.hw_card)

        hw_title = BodyLabel("Hardware Identification", self)
        setFont(hw_title, 16)
        hw_layout.addWidget(hw_title)

        self.hw_id_edit = LineEdit(self)
        self.hw_id_edit.setText(license_manager.hw_id)
        self.hw_id_edit.setReadOnly(True)

        copy_btn = PushButton(FluentIcon.COPY, "Copy Hardware ID", self)
        copy_btn.clicked.connect(self._copy_hw_id)

        hw_row = QHBoxLayout()
        hw_row.addWidget(self.hw_id_edit)
        hw_row.addWidget(copy_btn)
        hw_layout.addLayout(hw_row)

        self.main_layout.addWidget(self.hw_card)

        # Activation Card
        self.activation_card = SimpleCardWidget(self)
        self.act_layout = QVBoxLayout(self.activation_card)

        act_title = BodyLabel("Activate License", self)
        setFont(act_title, 16)
        self.act_layout.addWidget(act_title)

        self.key_edit = LineEdit(self)
        self.key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")

        self.activate_btn = PrimaryPushButton("Apply License Key", self)
        self.activate_btn.clicked.connect(self._on_activate_clicked)

        act_row = QHBoxLayout()
        act_row.addWidget(self.key_edit)
        act_row.addWidget(self.activate_btn)
        self.act_layout.addLayout(act_row)

        self.main_layout.addWidget(self.activation_card)

        self.main_layout.addStretch(1)

    def _update_status_ui(self):
        is_act = license_manager.is_activated()
        if is_act:
            self.status_badge.setText(" ACTIVATED ")
            self.status_badge.setStyleSheet("""
                background-color: #28a745;
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            """)
        else:
            self.status_badge.setText(" NOT ACTIVATED ")
            self.status_badge.setStyleSheet("""
                background-color: #dc3545;
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            """)

    def _copy_hw_id(self):
        QApplication.clipboard().setText(license_manager.hw_id)
        InfoBar.success(
            "Success", "Hardware ID copied to clipboard", duration=2000, parent=self)

    def _on_activate_clicked(self):
        key = self.key_edit.text().strip()
        if not key:
            return

        if license_manager.activate(key):
            self._update_status_ui()
            InfoBar.success(
                "Congratulations", "Application successfully activated!", duration=4000, parent=self)
            self.key_edit.clear()
        else:
            InfoBar.error(
                "Invalid Key", "The license key provided is invalid for this machine.", duration=4000, parent=self)
