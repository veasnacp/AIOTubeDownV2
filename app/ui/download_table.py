import os
import sqlite3
import subprocess

import humanize
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)
from PySide6Addons import FluentIcon, ProgressBar, TableWidget, TransparentToolButton

from ..components.override import RoundMenu
from ..db.database import db
from ..utils.path import reveal_file, trigger_windows_open_with
from .properties_dialog import PropertiesDialog


class DownloadTable(TableWidget):
    """The main table widget to show download list"""
    resume_requested = Signal(object)
    stop_requested = Signal(object)
    remove_requested = Signal(object)
    redownload_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Filename", "Size", "Status", "Timeleft", "Transfer Rate", "Progress"
        ])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        # header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.setColumnWidth(5, 150)  # Progress bar column

        self.verticalHeader().hide()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)

        self.setBorderRadius(8)
        # self.setBorderVisible(True)
        self.setWordWrap(False)

        self.load_tasks()

        # Header sorting (disabled by default, enabled by MainWindow when safe)
        self.setSortingEnabled(False)
        header.sectionClicked.connect(self._handle_sort)

    def contextMenuEvent(self, event):
        row = self.rowAt(event.pos().y())
        if row == -1:
            return

        # Find task_id for this row
        item = self.item(row, 0)
        if not item:
            return

        task_id = item.data(Qt.UserRole)
        status = self.item(row, 2).text()

        if task_id is None:
            return

        # Check if multiple rows are selected and row is among them
        selected_rows = self.selectionModel().selectedRows()
        is_multi = len(selected_rows) > 1
        is_clicked_selected = any(idx.row() == row for idx in selected_rows)

        # If part of multi-selection, we operate on collective selection
        target_id = None if (is_multi and is_clicked_selected) else task_id

        menu = RoundMenu(parent=self)

        # Actions
        open_action = QAction("Open", icon=FluentIcon.FOLDER_ADD.icon())
        open_action.triggered.connect(lambda: self._open_file(task_id))
        open_with_action = QAction(
            "Open with...", icon=FluentIcon.APPLICATION.icon())
        open_with_action.triggered.connect(lambda: self._open_with(task_id))
        open_folder_action = QAction(
            "Open folder", icon=FluentIcon.FOLDER.icon())
        open_folder_action.triggered.connect(
            lambda: self._open_folder(task_id))

        resume_action = QAction("Resume", icon=FluentIcon.PLAY.icon())
        resume_action.triggered.connect(
            lambda: self.resume_requested.emit(target_id))
        stop_action = QAction("Stop", icon=FluentIcon.PAUSE.icon())
        stop_action.triggered.connect(
            lambda: self.stop_requested.emit(target_id))
        redownload_action = QAction("Redownload", icon=FluentIcon.SYNC.icon())
        redownload_action.triggered.connect(
            lambda: self.redownload_requested.emit(target_id))

        remove_action = QAction("Remove", icon=FluentIcon.DELETE.icon())
        remove_action.triggered.connect(
            lambda: self.remove_requested.emit(target_id))
        properties_action = QAction("Properties", icon=FluentIcon.INFO.icon())
        properties_action.triggered.connect(
            lambda: self._show_properties(task_id, status))

        # Disable logic
        can_open = status.lower() in [
            '✅', 'finished', 'completed', 'complete', 'done', 'success']
        open_action.setEnabled(can_open)
        open_with_action.setEnabled(can_open)

        can_resume = status.lower() in ['❌', 'stopped', 'cancelled', 'error']
        resume_action.setEnabled(can_resume)

        can_stop = status.lower() in [
            '⏳', 'downloading', 'progressing', 'queued', 'paused']
        stop_action.setEnabled(can_stop)

        if not (is_multi and is_clicked_selected):
            menu.addAction(open_action)
            menu.addAction(open_with_action)
            menu.addAction(open_folder_action)
            menu.addSeparator()

        menu.addAction(resume_action)
        menu.addAction(stop_action)
        menu.addAction(redownload_action)
        menu.addSeparator()
        menu.addAction(remove_action)

        # Properties only makes sense for single task
        if not (is_multi and is_clicked_selected):
            menu.addSeparator()
            menu.addAction(properties_action)

        menu.exec(event.globalPos())

    def _open_file(self, task_id):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT filename, save_path FROM downloads WHERE id=?", (task_id,)).fetchone()
        conn.close()
        if row and row[1] and row[0]:
            path = os.path.join(row[1], row[0])
            if os.path.exists(path):
                os.startfile(path)

    def _open_with(self, task_id):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT filename, save_path FROM downloads WHERE id=?", (task_id,)).fetchone()
        conn.close()
        if row and row[1] and row[0]:
            path = os.path.join(row[1], row[0])
            if os.path.exists(path):
                trigger_windows_open_with(path)

    def _open_folder(self, task_id):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT filename, save_path FROM downloads WHERE id=?", (task_id,)).fetchone()
        conn.close()
        if row and row[1] and row[0]:
            path = os.path.join(row[1], row[0])
            if os.path.exists(path):
                reveal_file(path)

    def _handle_sort(self, index):
        # We can implement specific sorting logic here if needed
        # QTableWidget handles basic sorting automatically when setSortingEnabled(True)
        pass

    def set_sorting_safe(self, is_safe):
        self.setSortingEnabled(is_safe)

    def _show_properties(self, task_id, status):
        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM downloads WHERE id=?", (task_id,)).fetchone()
        conn.close()
        if row:
            data = dict(row)
            data['status'] = status
            dialog = PropertiesDialog(data, self.window())
            dialog.exec()

    def load_tasks(self):
        old_sorting = self.isSortingEnabled()
        self.setSortingEnabled(False)
        self.setRowCount(0)
        tasks = db.get_all_tasks()
        print(tasks)
        for task in tasks:
            self.add_task_to_table(task)
        self.setSortingEnabled(old_sorting)

    def add_task_to_table(self, task):
        row = self.rowCount()
        self.insertRow(row)

        task_id = task['id']

        # 0. Filename
        item0 = QTableWidgetItem(task.get('filename', 'Unknown'))
        item0.setData(Qt.UserRole, task_id)
        self.setItem(row, 0, item0)

        # 1. Size
        size_str = humanize.naturalsize(task.get('size_total', 0))
        self.setItem(row, 1, QTableWidgetItem(size_str))

        # 2. Status
        status = task.get('status', 'Queued')
        self.setItem(row, 2, QTableWidgetItem(self.get_status_text(status)))
        self.item(row, 2).setToolTip(status)

        # 3. Timeleft
        self.setItem(row, 3, QTableWidgetItem(task.get('eta', '')))

        # 4. Transfer Rate
        self.setItem(row, 4, QTableWidgetItem(task.get('speed', '')))

        # 5. Progress Bar
        progress_bar = ProgressBar(self)
        progress_bar.setMaximumWidth(self.columnWidth(5) - 10)
        if task.get('status', '').lower() in \
                ['finished', 'completed', 'complete', 'done', 'success']:
            progress_bar.setValue(100)
        else:
            total = task.get('size_total', 1)
            downloaded = task.get('size_downloaded', 0)
            percent = int((downloaded / total) * 100) if total > 0 else 0
            progress_bar.setValue(percent)
        self.setCellWidget(row, 5, progress_bar)

    def _find_row_by_task_id(self, task_id):
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.data(Qt.UserRole) == task_id:
                return row
        return -1

    def get_status_text(self, status):
        _status = status.lower()
        if _status in ['finished', 'completed', 'complete', 'done', 'success']:
            _status = '✅'
        elif _status in ['stopped', 'cancelled', 'error']:
            _status = '❌'
        elif _status in ['downloading', 'progressing', 'queued', 'paused']:
            _status = '⏳'
        return _status

    @Slot(int, int, int, str, str)
    def update_progress(self, task_id, downloaded, total, speed, eta):
        row = self._find_row_by_task_id(task_id)
        if row == -1:
            return

        # Update progress bar
        pbar = self.cellWidget(row, 5)
        if pbar:
            percent = int((downloaded / total) * 100) if total > 0 else 0
            pbar.setValue(percent)

        # Update speed
        self.setItem(row, 4, QTableWidgetItem(speed))

        # Update ETA
        self.setItem(row, 3, QTableWidgetItem(eta))

        # Update total size if it was 0 before (common for streaming URLs)
        if total > 0:
            size_str = humanize.naturalsize(total)
            self.setItem(row, 1, QTableWidgetItem(size_str))

    @Slot(int, str)
    def update_status(self, task_id, status):
        row = self._find_row_by_task_id(task_id)
        if row == -1:
            return
        _status = self.get_status_text(status)
        self.item(row, 2).setToolTip(status)
        self.setItem(row, 2, QTableWidgetItem(_status))

    @Slot(int, str)
    def update_filename(self, task_id, filename):
        row = self._find_row_by_task_id(task_id)
        if row == -1:
            return
        item = QTableWidgetItem(filename)
        item.setData(Qt.UserRole, task_id)
        self.setItem(row, 0, item)
