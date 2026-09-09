from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
from types import TracebackType

from PySide6.QtCore import QCoreApplication, QStandardPaths


APPLICATION_NAME = "Video Analyse"
APPLICATION_ID = "de.maxwernz.videoanalyse"
ORGANIZATION_NAME = "maxwernz"


def configure_application_identity() -> None:
    QCoreApplication.setApplicationName(APPLICATION_NAME)
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(APPLICATION_ID)


def resource_path(relative_path: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return Path(bundle_root) / relative_path


def overlay_font_path() -> Path:
    return resource_path("assets/fonts/NotoSans.ttf")


def configure_local_logging() -> Path:
    configured_log_directory = os.environ.get("VIDEO_ANALYSE_LOG_DIR")
    if configured_log_directory:
        log_directory = Path(configured_log_directory)
    else:
        application_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        if not application_data:
            raise RuntimeError(
                "The operating system did not provide an application-data location"
            )
        log_directory = Path(application_data) / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / "video-analyse.log"

    root_logger = logging.getLogger()
    if not any(
        isinstance(handler, RotatingFileHandler)
        and Path(handler.baseFilename) == log_path
        for handler in root_logger.handlers
    ):
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    logging.getLogger(__name__).info("Application logging initialized")
    return log_path


def install_exception_logging() -> None:
    previous_hook = sys.excepthook

    def log_exception(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        logging.getLogger(__name__).critical(
            "Unhandled exception",
            exc_info=(exception_type, exception, traceback),
        )
        previous_hook(exception_type, exception, traceback)

    def log_thread_exception(arguments: threading.ExceptHookArgs) -> None:
        if arguments.exc_value is None:
            logging.getLogger(__name__).critical(
                "Unhandled thread exception without an exception value"
            )
            return
        log_exception(
            arguments.exc_type,
            arguments.exc_value,
            arguments.exc_traceback,
        )

    sys.excepthook = log_exception
    threading.excepthook = log_thread_exception
