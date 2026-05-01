import os

from PySide6.QtCore import QObject, QSettings, Signal

from ..config.constants import APP_NAME, APP_VERSION


class SettingsManager(QObject):
    settings_changed = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.settings = QSettings(APP_NAME, "Config")
        self.initialize_defaults()

    def initialize_defaults(self):
        defaults = {
            "download_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
            "max_threads": 5,
            "max_segments": 16,
            "auto_start": True,
            "theme": "Auto",
            "accent_color": "#0078d4",
            "clipboard_watcher": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }
        for key, val in defaults.items():
            if not self.settings.contains(key):
                self.settings.setValue(key, val)

    def get(self, key, default=None):
        return self.settings.value(key, default)

    def set(self, key, value):
        self.settings.setValue(key, value)
        self.settings_changed.emit(key, value)


settings = SettingsManager()
