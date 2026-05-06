import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from ..db.database import db
from .download_worker import DownloadWorker


class DownloadManager(QObject):
    # Signals to update the UI
    # task_id, downloaded, total, speed, eta
    task_progress = Signal(int, int, int, str, str)
    task_status = Signal(int, str)  # task_id, status
    task_finished = Signal(int, str)  # task_id, filepath
    task_error = Signal(int, str)  # task_id, error_msg
    task_filename_updated = Signal(int, str)  # task_id, real_filename

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3)
        self.active_workers = {}  # task_id -> DownloadWorker
        self.last_db_update = {}  # task_id -> last_timestamp

    def add_task(self, url, filename, output_dir, category="Other", info: Optional[dict] = None, options=None):
        # 1. Add to Database
        metadata_json = json.dumps(options) if options else None
        if info:
            url = info.get('url')
            filename = info.get('title')
        task_id = db.add_task(url, filename, output_dir,
                              category, metadata_json=metadata_json)

        # 2. Create Worker
        worker = DownloadWorker(task_id, url, output_dir,
                                filename, info, options=options)

        # 3. Connect Signals
        worker.signals.progress.connect(self.on_worker_progress)
        worker.signals.status_changed.connect(self.on_worker_status)
        worker.signals.finished.connect(self.on_worker_finished)
        worker.signals.error.connect(
            lambda task_id, error_msg: self.on_worker_error(task_id, error_msg, url))
        worker.signals.filename_updated.connect(
            self.on_worker_filename_updated)

        # 4. Store and Execute
        self.active_workers[task_id] = worker
        self.thread_pool.start(worker)

        return task_id

    @Slot(int, int, int, str, str)
    def on_worker_progress(self, task_id, downloaded, total, speed, eta):
        self.task_progress.emit(task_id, downloaded, total, speed, eta)

        # Periodic database update (throttled every 2 seconds)
        now = time.time()
        last = self.last_db_update.get(task_id, 0)
        if now - last > 2.0:
            db.update_task(task_id, size_total=total,
                           size_downloaded=downloaded, speed=speed, eta=eta)
            self.last_db_update[task_id] = now

    @Slot(int, str)
    def on_worker_status(self, task_id, status):
        self.task_status.emit(task_id, status)
        db.update_task(task_id, status=status)

    @Slot(int, str)
    def on_worker_finished(self, task_id, filepath):
        filepath = Path(filepath)
        self.task_finished.emit(task_id, str(filepath))
        db.update_task(
            task_id,
            filename=filepath.name,
            save_path=str(filepath.parent),
            status="Completed",
            date_completed=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        if task_id in self.active_workers:
            del self.active_workers[task_id]

    @Slot(int, str)
    def on_worker_error(self, task_id, error_msg, url):
        self.task_error.emit(task_id, error_msg)
        db.update_task(task_id, url=url, status="Error", error_msg=error_msg)
        if task_id in self.active_workers:
            del self.active_workers[task_id]

    @Slot(int, str)
    def on_worker_filename_updated(self, task_id, real_filename):
        logger.debug(
            f'on_worker_filename_updated {task_id} {real_filename}')
        self.task_filename_updated.emit(task_id, real_filename)
        db.update_task(task_id, filename=real_filename)

    def stop_task(self, task_id):
        if task_id in self.active_workers:
            self.active_workers[task_id].is_cancelled = True
            self.active_workers[task_id].cancel()
            del self.active_workers[task_id]
            db.update_task(task_id, status="Stopped")

    def stop_all(self):
        for task_id in list(self.active_workers.keys()):
            self.stop_task(task_id)

    def remove_task(self, task_id):
        self.stop_task(task_id)
        db.remove_task(task_id)

    def resume_task(self, task_id):
        if task_id in self.active_workers:
            return

        # Get data from DB
        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        task = conn.execute(
            "SELECT * FROM downloads WHERE id=?", (task_id,)).fetchone()
        conn.close()

        if task:
            options = json.loads(task['metadata_json']
                                 ) if task['metadata_json'] else {}
            worker = DownloadWorker(
                task_id, task['url'], task['save_path'], task['filename'], options=options)
            worker.signals.progress.connect(self.on_worker_progress)
            worker.signals.status_changed.connect(self.on_worker_status)
            worker.signals.finished.connect(self.on_worker_finished)
            worker.signals.error.connect(self.on_worker_error)
            worker.signals.filename_updated.connect(
                self.on_worker_filename_updated)

            self.active_workers[task_id] = worker
            self.thread_pool.start(worker)

    def redownload_task(self, task_id):
        self.stop_task(task_id)
        db.update_task(task_id, size_downloaded=0, status="Queued")
        self.resume_task(task_id)


manager = DownloadManager()
