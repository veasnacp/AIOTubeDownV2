import os
import sys

import loguru
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .config.constants import DIRS
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

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
