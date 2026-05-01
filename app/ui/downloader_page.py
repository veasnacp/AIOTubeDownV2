import os
import sqlite3

import humanize
from loguru import logger
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, Signal, Slot
from PySide6.QtGui import QColor, QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from PySide6Addons import (
    BodyLabel,
    CaptionLabel,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    PushButton,
    ScrollArea,
    SegmentedWidget,
    SimpleCardWidget,
    SubtitleLabel,
    TransparentToolButton,
    isDarkTheme,
    qconfig,
)

from ..components.override import CardWidget
from ..core.download_manager import manager
from ..core.extract_manager import extract_manager
from ..db.database import db
from ..theme import Colors, DarkMode, LightMode
from .action_panel import ActionPanel
from .add_url_dialog import AddUrlDialog
from .download_table import DownloadTable


class DownloaderPage(ScrollArea):
    """The main downloader interface containing the action panel and download table"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("downloader")
        self.enableTransparentBackground()
        self.setWidgetResizable(True)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Action Panel
        self.action_panel = ActionPanel(self)
        self.main_layout.addWidget(self.action_panel)

        self.main_table_layout = QVBoxLayout()
        self.main_table_layout.setContentsMargins(0, 0, 0, 0)
        self.main_table_layout.setSpacing(10)

        # 2 Header (Tabs + Toggle)
        self.header_container = CardWidget()
        self.header_layout = QHBoxLayout(self.header_container)
        self.tabs = SegmentedWidget(self.header_container)
        self.tabs.addItem("All", "All", icon=FluentIcon.HISTORY)
        self.tabs.addItem("Downloading", "Downloading",
                          icon=FluentIcon.DOWNLOAD)
        self.tabs.addItem("Completed", "Completed", icon=FluentIcon.COMPLETED)
        self.tabs.addItem("Uncompleted", "Uncompleted", icon=FluentIcon.CANCEL)
        self.tabs.setCurrentItem("All")
        self.tabs.currentItemChanged.connect(self.filter_tasks)

        self.toggle_detail_btn = TransparentToolButton(
            FluentIcon.INFO, self.header_container)
        self.toggle_detail_btn.setToolTip("Show Sidebar")
        self.toggle_detail_btn.clicked.connect(self.toggle_file_detail)

        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.tabs)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.toggle_detail_btn)

        self.main_table_layout.addWidget(self.header_container)

        # 3. Table Container
        self.table_container = CardWidget()
        self.main_table_layout.addWidget(self.table_container)

        self.table_layout = QVBoxLayout(self.table_container)
        self.table_layout.setContentsMargins(20, 20, 20, 20)
        self.table_layout.setSpacing(10)

        # 3.2 Table
        self.download_table = DownloadTable(self.table_container)
        self.download_table.resume_requested.connect(self.resume_selected)
        self.download_table.stop_requested.connect(self.stop_selected)
        self.download_table.remove_requested.connect(
            self.remove_selected_tasks)
        self.download_table.redownload_requested.connect(
            self.redownload_selected)
        self.table_layout.addWidget(self.download_table)

        self.main_layout.addLayout(self.main_table_layout)

        # 3.3 File Detail
        self.file_detail = CardWidget(self)
        self.file_detail.setLightBackgroundColor(Colors.gray_0)
        self.file_detail.setDarkBackgroundColor(DarkMode.card)
        self.file_detail.setFixedWidth(280)
        self.file_detail.setMaximumWidth(280)
        self.file_detail_layout = QVBoxLayout(self.file_detail)
        self.file_detail_layout.setContentsMargins(20, 20, 20, 20)
        self.file_detail_layout.setSpacing(15)
        self.file_detail_layout.setAlignment(Qt.AlignTop)
        self.main_layout.addWidget(self.file_detail)

        # File Detail UI Elements
        self.thumbnail_area = SimpleCardWidget(self.file_detail)
        self.thumbnail_area.setFixedSize(240, 160)
        self.thumbnail_layout = QVBoxLayout(self.thumbnail_area)
        self.thumbnail_icon = TransparentToolButton(
            FluentIcon.DOCUMENT, self.thumbnail_area)
        self.thumbnail_icon.setIconSize(QSize(80, 80))
        self.thumbnail_layout.addWidget(self.thumbnail_icon, 0, Qt.AlignCenter)
        self.file_detail_layout.addWidget(self.thumbnail_area)

        self.filename_row = QHBoxLayout()
        self.file_icon_small = TransparentToolButton(
            FluentIcon.DOCUMENT, self.file_detail)
        self.file_icon_small.setIconSize(QSize(24, 24))
        self.filename_label = CaptionLabel("No selection", self.file_detail)
        self.filename_label.setWordWrap(True)
        self.filename_row.addWidget(self.file_icon_small)
        self.filename_row.addWidget(self.filename_label)
        self.file_detail_layout.addLayout(self.filename_row)

        # self.share_btn = PushButton(
        #     FluentIcon.SHARE, "Share", self.file_detail)
        # self.file_detail_layout.addWidget(self.share_btn)

        self.details_header = BodyLabel("Details", self.file_detail)
        self.file_detail_layout.addWidget(self.details_header)

        # Details Grid-like layout
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(8)

        self.detail_items = {}
        for key in ["Type", "Size", "File location", "Date modified"]:
            row = QHBoxLayout()
            label = CaptionLabel(key, self.details_container)
            value = CaptionLabel("-", self.details_container)
            value.setWordWrap(True)
            value.setAlignment(Qt.AlignRight)
            row.addWidget(label)
            row.addWidget(value, 1)
            self.details_layout.addLayout(row)
            self.detail_items[key] = value

        self.file_detail_layout.addWidget(self.details_container)

        self.properties_btn = PushButton(
            FluentIcon.SETTING, "Properties", self.file_detail)
        self.file_detail_layout.addStretch(1)
        self.file_detail_layout.addWidget(self.properties_btn)

        # Animation for File Detail
        self.detail_animation = QPropertyAnimation(
            self.file_detail, b"maximumWidth")
        self.detail_animation.setDuration(100)
        self.detail_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.detail_animation.finished.connect(self._on_animation_finished)

        # Initially hidden or showing placeholder
        self.file_detail.hide()
        self.thumbnail_area.hide()
        self.details_container.hide()
        # self.share_btn.hide()
        self.properties_btn.hide()

        # Connect Table Selection
        self.download_table.itemSelectionChanged.connect(
            self.on_selection_changed)

        # Connect Manager Signals
        manager.task_progress.connect(self.download_table.update_progress)
        manager.task_status.connect(self.download_table.update_status)
        manager.task_finished.connect(self.on_download_success)
        manager.task_error.connect(self.on_download_error)
        manager.task_filename_updated.connect(
            self.download_table.update_filename)

        extract_manager.task_finished.connect(self.on_extract_success)
        extract_manager.task_error.connect(self.on_extract_error)

        # Connect Action Panel Signals
        self.action_panel.add_url_clicked.connect(self.add_url_test)
        self.action_panel.stop_clicked.connect(self.stop_selected)
        self.action_panel.stop_all_clicked.connect(manager.stop_all)
        self.action_panel.delete_clicked.connect(self.remove_selected_tasks)

        # self.update_theme()
        # qconfig.themeChanged.connect(self.update_theme)

    def resizeEvent(self, event: QResizeEvent) -> None:
        if self.window().width() < 960:
            self.file_detail.hide()
            self.toggle_detail_btn.setEnabled(False)
        else:
            self.toggle_detail_btn.setEnabled(True)
        return super().resizeEvent(event)

    def update_theme(self):
        bg = 'transparent'
        if isDarkTheme():
            bg = DarkMode.alpha(DarkMode.background, 0.4)

        self.setStyleSheet(
            f"QScrollArea{{border: none; border-top-left-radius: 7px; background: {bg}}}")

        if self.widget():
            self.widget().setStyleSheet(f"QWidget{{background: {bg}}}")

    def add_url_test(self):
        dialog = AddUrlDialog(self.window())
        if dialog.exec():
            urls = dialog.get_urls()
            options = dialog.get_options()
            extract_manager.start_extraction(urls)
            extract_manager.options = options

    def remove_selected_tasks(self, task_id=None):
        if task_id and isinstance(task_id, int):
            manager.remove_task(task_id)
        else:
            rows = self.download_table.selectionModel().selectedRows()
            for idx in rows:
                item = self.download_table.item(idx.row(), 0)
                if item:
                    manager.remove_task(item.data(Qt.UserRole))
        self.download_table.load_tasks()

    def filter_tasks(self, index=None):
        item = self.tabs.currentItem()
        if not item:
            return
        target_text = item.text()
        for row in range(self.download_table.rowCount()):
            cell = self.download_table.item(row, 2)
            if not cell:
                continue
            row_status = cell.text()
            if target_text == "All":
                self.download_table.setRowHidden(row, False)
            elif target_text == "Downloading" and row_status == "Downloading":
                self.download_table.setRowHidden(row, False)
            elif target_text == "Completed" and row_status == "Completed":
                self.download_table.setRowHidden(row, False)
            elif target_text == "Uncompleted":
                is_uncompleted = row_status in [
                    "Stopped", "Error", "Cancelled", "Queued"]
                self.download_table.setRowHidden(row, not is_uncompleted)
            else:
                self.download_table.setRowHidden(row, True)

    def stop_selected(self, task_id=None):
        if task_id and isinstance(task_id, int):
            manager.stop_task(task_id)
        else:
            rows = self.download_table.selectionModel().selectedRows()
            for idx in rows:
                item = self.download_table.item(idx.row(), 0)
                if item:
                    manager.stop_task(item.data(Qt.UserRole))

    def resume_selected(self, task_id=None):
        if task_id and isinstance(task_id, int):
            manager.resume_task(task_id)
        else:
            rows = self.download_table.selectionModel().selectedRows()
            for idx in rows:
                item = self.download_table.item(idx.row(), 0)
                if item:
                    manager.resume_task(item.data(Qt.UserRole))

    def redownload_selected(self, task_id=None):
        if task_id and isinstance(task_id, int):
            manager.redownload_task(task_id)
        else:
            rows = self.download_table.selectionModel().selectedRows()
            for idx in rows:
                item = self.download_table.item(idx.row(), 0)
                if item:
                    manager.redownload_task(item.data(Qt.UserRole))

    def on_download_success(self, task_id, filepath):
        InfoBar.success(
            "Download Complete", f"File saved to: {filepath}", duration=5000, parent=self.window())
        self.filter_tasks()

    def on_download_error(self, task_id, error_msg):
        InfoBar.error(
            "Download Error", f"Error: {error_msg}", duration=5000, parent=self.window())
        self.filter_tasks()

    def on_extract_success(self, task_id, data):
        status = data.get("status")
        info_list = data.get("data")
        if status == "finished":
            for info in info_list:
                if not info:
                    continue
                url = info.get('url')
                filename = info.get('title')
                options = extract_manager.options
                manager.add_task(
                    url, filename, options['path'],
                    category=options['category'], info=info,
                    options={
                        "resolution": options['resolution'], "mp3": options['mp3']}
                )
                task_data = {
                    'id': task_id, 'url': url, 'filename': filename,
                    'save_path': options['path'], 'category': options['category'],
                    'status': 'Downloading', 'size_total': 0, 'size_downloaded': 0
                }
                self.download_table.add_task_to_table(task_data)

    def toggle_file_detail(self):
        is_visible = self.file_detail.isVisible()
        self.detail_animation.stop()

        if is_visible:
            self.detail_animation.setStartValue(self.file_detail.width())
            self.detail_animation.setEndValue(0)
            self.toggle_detail_btn.setToolTip("Show Sidebar")
        else:
            self.file_detail.show()
            self.detail_animation.setStartValue(self.file_detail.width())
            self.detail_animation.setEndValue(280)
            self.toggle_detail_btn.setToolTip("Hide Sidebar")

        self.detail_animation.start()

    def _on_animation_finished(self):
        if self.file_detail.maximumWidth() == 0:
            self.file_detail.hide()

    def on_selection_changed(self):
        selected_rows = self.download_table.selectionModel().selectedRows()
        count = len(selected_rows)

        if count == 0:
            self.filename_label.setText("No selection")
            self.thumbnail_area.hide()
            self.details_container.hide()
            # self.share_btn.hide()
            self.properties_btn.hide()
            self.thumbnail_icon.setIcon(FluentIcon.DOCUMENT)
        elif count == 1:
            self.thumbnail_area.show()
            row = selected_rows[0].row()
            item = self.download_table.item(row, 0)
            if item:
                task_id = item.data(Qt.UserRole)
                self.update_file_detail(task_id)
        else:
            self.filename_label.setText(f"{count} tasks selected")
            self.thumbnail_area.hide()
            self.details_container.hide()
            # self.share_btn.show()  # Maybe show bulk actions
            self.properties_btn.hide()
            self.thumbnail_icon.setIcon(FluentIcon.FOLDER)

    def update_file_detail(self, task_id):
        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        task = conn.execute(
            "SELECT * FROM downloads WHERE id=?", (task_id,)).fetchone()
        conn.close()

        if task:
            task = dict(task)
            self.filename_label.setText(task.get('filename', 'Unknown'))

            # Update detail labels
            ext = os.path.splitext(task.get('filename', ''))[
                1].upper().replace('.', '')
            self.detail_items["Type"].setText(f"{ext} File" if ext else "File")

            size = task.get('size_total', 0)
            self.detail_items["Size"].setText(humanize.naturalsize(size))

            save_path = task.get('save_path')
            basename = None
            if save_path:
                basename = os.path.basename(save_path)
            self.detail_items["File location"].setText(basename or '-')
            if save_path:
                self.detail_items["File location"].setToolTip(save_path)
            self.detail_items["Date modified"].setText(
                task.get('date_added', '-'))

            self.details_container.show()
            # self.share_btn.show()
            self.properties_btn.show()

            # Set icon based on extension if possible
            self.thumbnail_icon.setIcon(FluentIcon.VIDEO if ext in [
                                        'MP4', 'MKV', 'AVI'] else FluentIcon.MUSIC if ext == 'MP3' else FluentIcon.DOCUMENT)
            self.file_icon_small.setIcon(self.thumbnail_icon.icon())

    def on_extract_error(self, task_id, d):
        error_msg = d.get("error")
        InfoBar.error(
            "Extract Error", f"Error: {error_msg}", duration=5000, parent=self.window())
