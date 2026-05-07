import hashlib
import shutil
import subprocess

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QIcon, QPixmap

from ..config.constants import DIRS

CACHE_DIR = DIRS.user_cache_path


def hash_path(file_path: str):
    return hashlib.md5(file_path.encode()).hexdigest()


class ThumbnailCache:

    @staticmethod
    def get_thumb_path(media_path: str, file_hash=None):
        if not file_hash:
            file_hash = hash_path(media_path)
        return CACHE_DIR / f"{file_hash}.png"

    @staticmethod
    def generate_thumbnail(media_path: str, file_hash=None):
        thumb_path = ThumbnailCache.get_thumb_path(media_path, file_hash)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"
        if not thumb_path.exists():
            subprocess.run([
                ffmpeg_exe,
                "-y",
                "-i", media_path,
                "-ss", "00:00:01",
                "-vframes", "1",
                "-vf", "scale=320:-1",
                str(thumb_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return QPixmap(str(thumb_path))


class ThumbnailSignals(QObject):
    finished = Signal(str, str, QPixmap)
    error = Signal(str, str, str)


class ThumbnailWorker(QRunnable):

    def __init__(self, media_path: str, file_hash: str):
        super().__init__()
        self.media_path = media_path
        self.file_hash = file_hash
        self.signals = ThumbnailSignals()

    def run(self):
        thumbnail = ThumbnailCache.generate_thumbnail(
            self.media_path, self.file_hash)

        # Try attached picture first (instant if exists)
        # args = [
        #     "-v", "error",
        #     "-i", self.media_path,
        #     "-map", "0:v",
        #     "-c", "copy",
        #     "-f", "image2",
        #     "pipe:1"
        # ]
        # subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.signals.finished.emit(self.file_hash, self.media_path, thumbnail)

    def _extract_keyframe(self, timestamp):

        self.args = [
            "-v", "error",
            "-ss", timestamp,   # fast seek before input
            "-i", self.media_path,
            "-frames:v", "1",
            "-an", "-sn", "-dn",
            "-vf", "scale=320:-1",    # scale immediately for speed
            "-f", "image2",
            "pipe:1"
        ]
        return self.args


class ThumbnailManager(QObject):
    # Signals
    task_finished = Signal(str, str, QPixmap)
    task_error = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(6)  # sweet spot
        self.active_workers = {}

    def generate_thumbnails(self, media_path: str):
        file_hash = hash_path(media_path)
        worker = ThumbnailWorker(media_path, file_hash)
        worker.signals.finished.connect(self.on_finished)
        worker.signals.error.connect(self.on_error)
        self.active_workers[file_hash] = worker
        self.pool.start(worker)

    def on_finished(self, file_hash, media_path, thumbnail):
        if file_hash in self.active_workers:
            del self.active_workers[file_hash]
        self.task_finished.emit(file_hash, media_path, thumbnail)

    def on_error(self, file_hash, media_path, error_msg):
        if file_hash in self.active_workers:
            del self.active_workers[file_hash]
        self.task_error.emit(file_hash, media_path, error_msg)

    def remove_task(self, task_id: str):
        if task_id in self.active_workers:
            self.active_workers[task_id].cancel()
            del self.active_workers[task_id]

    def cache_path(self, media_path: str):
        file_hash = hash_path(media_path)
        cache_path = CACHE_DIR / f"{file_hash}.png"
        return cache_path

    def get_thumbnail(self, media_path: str):
        cache_path = self.cache_path(media_path)
        if cache_path.exists():
            return QPixmap(str(cache_path))
        return None

    def get_thumbnail_as_icon(self, media_path: str):
        pixmap = self.get_thumbnail(media_path)
        if pixmap:
            icon = QIcon()
            icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
            return icon
        return None

    def remove_cache(self, media_path: str):
        cache_path = self.cache_path(media_path)
        if cache_path.exists():
            cache_path.unlink()

    def remove_all_cache(self):
        for file in CACHE_DIR.iterdir():
            if file.is_file() and file.suffix == ".png":
                file.unlink()

    def stop_all(self):
        try:
            for task_id in list(self.active_workers.keys()):
                self.remove_task(task_id)
            self.pool.waitForDone(100)
        except Exception as e:
            print(f"Error stopping thumbnail manager: {e}")


thumbnail_manager = ThumbnailManager()
