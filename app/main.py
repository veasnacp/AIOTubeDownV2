import os
import sys

import loguru
from platformdirs import user_data_dir
from PySide6 import QtWidgets

from .config.constants import APP_NAME
from .ui.main_window import MainWindow

logger = loguru.logger


def main():
    # Setup logger
    log_dir = user_data_dir(APP_NAME)
    os.makedirs(log_dir, exist_ok=True)
    logger.add(os.path.join(log_dir, "app.log"),
               rotation="10 MB", level="INFO")

    # logger.info("Starting VeasNa Download Manager...")

    app = QtWidgets.QApplication(sys.argv)

    # Apply theme from settings
    # Theme handling will go here later

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
