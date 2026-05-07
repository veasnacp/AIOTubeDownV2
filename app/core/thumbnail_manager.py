import hashlib
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QUrl, Qt, QEventLoop, Slot
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink
from PySide6.QtGui import QIcon, QPixmap

from ..config.constants import DIRS

CACHE_DIR = DIRS.user_cache_path


class ThumbSignals(QObject):
    result = Signal(QPixmap, str, str)


class ThumbnailWorker(QRunnable):
    def __init__(self, video_path: str, file_hash: str):
        super().__init__()
        self.video_path = video_path
        self.file_hash = file_hash
        self.signals = ThumbSignals()
        self._is_cancelled = False
        self._loop = None

    def run(self):
        # 1. Generate Cache Key
        cache_path = CACHE_DIR / f"{self.file_hash}.png"

        # 2. Check Disk Cache first
        if cache_path.exists():
            pix = QPixmap(str(cache_path))
            self.signals.result.emit(pix, self.video_path, self.file_hash)
            return

        # 3. Extract natively if not cached
        player = QMediaPlayer()
        sink = QVideoSink()
        player.setVideoSink(sink)

        self._loop = QEventLoop()

        def on_frame(frame: QPixmap):
            img = frame.toImage().scaled(
                200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            img.save(str(cache_path))  # Save to disk cache
            self.signals.result.emit(QPixmap.fromImage(
                img), self.video_path, self.file_hash)
            if self._loop:
                self._loop.quit()

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        sink.videoFrameChanged.connect(on_frame)
        player.setSource(QUrl.fromLocalFile(self.video_path))
        player.setPosition(1000)  # Jump 1s in
        player.pause()

        if not self._is_cancelled:
            self._loop.exec()

        player.stop()

    def cancel(self):
        self._is_cancelled = True
        if self._loop:
            self._loop.quit()


class ThumbnailManager(QObject):
    # Signals to update the UI
    task_status = Signal(str, str)  # task_id, status
    # task_id, pixmap, video_path, file_hash
    task_finished = Signal(str, QPixmap, str, str)
    task_error = Signal(str, str)  # task_id, error_msg
    task_filename_updated = Signal(str, str)  # task_id, real_filename

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3)
        self.active_workers = {}  # task_id -> DownloadWorker

    def add_task(self, video_path: str):
        file_hash = hashlib.md5(video_path.encode()).hexdigest()
        task_id = file_hash

        worker = ThumbnailWorker(video_path, file_hash)

        worker.signals.result.connect(lambda pixmap, video_path, file_hash: self.on_worker_result(
            task_id, pixmap, video_path, file_hash))

        self.active_workers[task_id] = worker
        self.thread_pool.start(worker)

        return task_id

    def remove_task(self, task_id: str):
        if task_id in self.active_workers:
            self.active_workers[task_id].cancel()
            del self.active_workers[task_id]

    def stop_all(self):
        for task_id in list(self.active_workers.keys()):
            self.remove_task(task_id)
        self.thread_pool.waitForDone(1000)

    def cache_path(self, video_path: str):
        file_hash = hashlib.md5(video_path.encode()).hexdigest()
        cache_path = CACHE_DIR / f"{file_hash}.png"
        return cache_path

    def get_thumbnail(self, video_path: str):
        cache_path = self.cache_path(video_path)
        if cache_path.exists():
            return QPixmap(str(cache_path))
        return None

    def get_thumbnail_as_icon(self, video_path: str):
        pixmap = self.get_thumbnail(video_path)
        if pixmap:
            icon = QIcon()
            icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
            return icon
        return None

    def remove_cache(self, video_path: str):
        cache_path = self.cache_path(video_path)
        if cache_path.exists():
            cache_path.unlink()

    def remove_all_cache(self):
        for file in CACHE_DIR.iterdir():
            if file.is_file() and file.suffix == ".png":
                file.unlink()

    @Slot(QPixmap, str, str)
    def on_worker_result(self, task_id: str, pixmap: QPixmap, video_path: str, file_hash: str):
        self.task_finished.emit(task_id, pixmap, video_path, file_hash)

        if task_id in self.active_workers:
            del self.active_workers[task_id]


thumbnail_manager = ThumbnailManager()
