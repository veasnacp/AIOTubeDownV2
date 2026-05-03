from enum import Enum

from platformdirs import PlatformDirs


class DownloadStatus(Enum):
    QUEUED = "Queued"
    DOWNLOADING = "Downloading"
    PAUSED = "Paused"
    COMPLETE = "Complete"
    ERROR = "Error"
    MERGING = "Merging"


class TaskCategory(Enum):
    ALL = "All"
    VIDEO = "Video"
    AUDIO = "Audio"
    DOCS = "Documents"
    ARCHIVES = "Archives"
    PROGRAMS = "Programs"
    OTHER = "Other"


APP_NAME = "AIOTubeDown"
APP_VERSION = "1.0.0"
APP_VERSION_BETA = f"{APP_NAME} [Beta] V{APP_VERSION}"
DB_NAME = "downloads.db"
DEFAULT_MAX_THREADS = 5
DEFAULT_MAX_SEGMENTS = 16
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

DIRS = PlatformDirs(APP_NAME, False)
