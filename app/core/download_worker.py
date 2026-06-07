import os
import shutil
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..core.convert_worker import VideoConverter
from ..core.download_base import DownloaderBase, populate_yt_dlp_formats


class WorkerSignals(QObject):
    # task_id, downloaded, total, speed, eta
    progress = Signal(int, int, int, str, str)
    status_changed = Signal(int, str)  # task_id, status
    finished = Signal(int, str)  # task_id, filepath
    error = Signal(int, str)  # task_id, message
    filename_updated = Signal(int, str)  # task_id, real_filename


class DownloadWorker(QRunnable, DownloaderBase):
    def __init__(
        self,
        task_id,
        url,
        output_dir,
        filename,
        info: Optional[dict] = None,
        options: Optional[dict] = None
    ):
        QRunnable.__init__(self)
        DownloaderBase.__init__(
            self,
            task_id,
            url,
            output_dir,
            filename,
            info,
            options
        )
        self.videoConverter = VideoConverter()
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        self.signals.status_changed.emit(self.task_id, "Downloading")

        if self.info:
            self.run_yt_dlp()
        else:
            self.run_yt_dlp()
