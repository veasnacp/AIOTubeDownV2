import os
import time

import humanize
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from PySide6Addons import BodyLabel, PushButton, SubtitleLabel

from ..components.override import MessageBoxBase


class Properties:
    """Detailed properties for a download task"""

    @staticmethod
    def _get_file_type(filename):
        if '.' in filename:
            ext = filename.split('.')[-1].upper()
            return f"{ext} File"
        return "Unknown File Type"

    @staticmethod
    def _get_modified_time(task_data):
        path = os.path.join(task_data.get('save_path') or '',
                            task_data.get('filename') or '')
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        return "File not found"

    @staticmethod
    def _get_details(task_data) -> list[tuple[str, str]]:
        return [
            ("Name:", task_data.get('filename') or 'Unknown'),
            ("Status:", task_data.get('status') or 'Unknown'),
            ("Type:", PropertiesDialog._get_file_type(
                task_data.get('filename') or '')),
            ("Size:", humanize.naturalsize(task_data.get('size_total', 0))),
            ("Created:", task_data.get('date_added') or 'Unknown'),
            ("Modified:", PropertiesDialog._get_modified_time(task_data)),
            ("Location:", task_data.get('save_path') or 'Unknown'),
            ("URL:", task_data.get('url') or 'Unknown')
        ]


class PropertiesDialog(MessageBoxBase, Properties):
    """Detailed properties dialog for a download task"""

    def __init__(self, task_data: dict, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Task Properties", self)
        # hide ok and cancel button
        self.buttonGroup.hide()

        self.form_layout = QVBoxLayout()
        self.form_layout.setSpacing(15)

        # Data mapping
        details = self._get_details(task_data)

        for label_text, value_text in details:
            row = QHBoxLayout()
            label = BodyLabel(label_text, self)
            label.setFixedWidth(80)
            label.setStyleSheet("font-weight: bold;")
            value = BodyLabel(str(value_text), self)
            value.setWordWrap(True)
            row.addWidget(label)
            row.addWidget(value)
            self.form_layout.addLayout(row)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(self.form_layout)

        self.download_btn = PushButton("Close", self)
        self.download_btn.clicked.connect(self.accept)
        self.viewLayout.addWidget(self.download_btn)

        self.widget.setMinimumWidth(450)

    @staticmethod
    def _get_file_type(filename):
        if not isinstance(filename, str):

            return "Unknown"
        if '.' in filename:
            ext = filename.split('.')[-1].upper()
            return f"{ext} File"
        return "Unknown File Type"

    @staticmethod
    def _get_modified_time(task_data):
        path = os.path.join(task_data.get('save_path') or '',
                            task_data.get('filename') or '')
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        return "File not found"

    @staticmethod
    def _get_details(task_data) -> list[tuple[str, str]]:
        return [
            ("Name:", task_data.get('filename') or 'Unknown'),
            ("Status:", task_data.get('status') or 'Unknown'),
            ("Type:", PropertiesDialog._get_file_type(
                task_data.get('filename') or '')),
            ("Size:", humanize.naturalsize(task_data.get('size_total', 0))),
            ("Created:", task_data.get('date_added') or 'Unknown'),
            ("Modified:", PropertiesDialog._get_modified_time(task_data)),
            ("Location:", task_data.get('save_path') or 'Unknown'),
            ("URL:", task_data.get('url') or 'Unknown')
        ]
