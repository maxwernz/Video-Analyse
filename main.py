from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence

from PIL import ImageFont
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QApplication

from app_runtime import (
    configure_application_identity,
    configure_local_logging,
    install_exception_logging,
    overlay_font_path,
)


def _run_smoke_check(app: QApplication, log_path: str) -> dict[str, str]:
    from mainwindow import MainWindow

    font_path = overlay_font_path()
    if not font_path.is_file():
        raise FileNotFoundError(f"Bundled overlay font is missing: {font_path}")
    ImageFont.truetype(str(font_path), 12)

    qt_resource = QFile(":/icons/custom.play.fill.png")
    if not qt_resource.exists():
        raise FileNotFoundError("Bundled Qt resources are unavailable")

    window = MainWindow()
    app.processEvents()
    window.close()
    return {"status": "ok", "font": str(font_path), "log": log_path}


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="video-analyse")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="initialize the application and bundled resources without showing the UI",
    )
    options, qt_arguments = parser.parse_known_args(arguments)

    configure_application_identity()
    app = QApplication([sys.argv[0], *qt_arguments])

    try:
        log_path = configure_local_logging()
        install_exception_logging()
        if options.smoke_test:
            report = _run_smoke_check(app, str(log_path))
            print(json.dumps(report))
            return 0

        from mainwindow import MainWindow

        window = MainWindow()
        window.show()
        return app.exec()
    except Exception:
        logging.getLogger(__name__).exception("Application startup failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
