import os
import sys
from pathlib import Path

import loguru
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from .config.constants import APP_NAME, APP_VERSION, DIRS
from .ui.main_window import MainWindow

logger = loguru.logger


def main():
    # Setup logger
    log_dir = str(DIRS.user_data_dir)

    os.makedirs(log_dir, exist_ok=True)
    logger.add(
        os.path.join(log_dir, "app.log"),
        rotation="10 MB",
        level="ERROR",
        format="[{time:YYYY-MM-DD HH:mm:ss.SSS}] [{level:^5}]: {message}",
    )

    # Qt High DPI Scaling Factor Rounding Policy
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("VeasNa Coder")
    app.setOrganizationDomain("https://youtube.com/@veasnacoder")

    # load font current directory
    font_path = Path.cwd() / "fonts" / "KantumruyPro.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
