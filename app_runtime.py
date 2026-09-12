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


UI_FONT_FAMILY = "Inter"
TIMECODE_FONT_FAMILY = "JetBrains Mono"

REQUIRED_FONT_FAMILIES = (UI_FONT_FAMILY, TIMECODE_FONT_FAMILY)

BUNDLED_FONT_FILES = (
    "Inter-Variable.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
)


class FontRegistrationError(RuntimeError):
    """The bundled typography could not be made available to the application.

    Raised rather than tolerated: falling back to whatever the operating system
    provides is the failure this bundling exists to prevent, and a silent
    fallback renders the interface in a face nobody chose.
    """


def bundled_font_paths() -> list[Path]:
    """The font files this application ships and registers at startup."""

    return [resource_path(f"assets/fonts/{name}") for name in BUNDLED_FONT_FILES]


def register_bundled_fonts() -> None:
    """Register the vendored typography, or fail loudly.

    Requires a live QGuiApplication, so call this after the application object
    exists. Every bundled file must load, and every family the visual system
    names must be present afterwards.
    """

    from PySide6.QtGui import QFontDatabase

    for path in bundled_font_paths():
        if not path.is_file():
            raise FontRegistrationError(f"Bundled font is missing: {path}")
        identifier = QFontDatabase.addApplicationFont(str(path))
        if identifier == -1:
            raise FontRegistrationError(f"Bundled font could not be registered: {path}")

    available = set(QFontDatabase.families())
    missing = [family for family in REQUIRED_FONT_FAMILIES if family not in available]
    if missing:
        raise FontRegistrationError(
            "Bundled font families are unavailable after registration: "
            + ", ".join(missing)
        )

    logging.getLogger(__name__).info(
        "Registered bundled font families: %s", ", ".join(REQUIRED_FONT_FAMILIES)
    )


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
