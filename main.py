from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from PIL import ImageFont
from PySide6.QtCore import QFile
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from app_runtime import (
    REQUIRED_FONT_FAMILIES,
    configure_application_identity,
    configure_local_logging,
    install_exception_logging,
    overlay_font_path,
    register_bundled_fonts,
)
from qml_runtime import (
    show_quick_scene_with_fallback,
    software_rendering_requested,
    use_software_rendering,
)


#: Ask for the QML workspace without a command line.
#:
#: A packaged application is launched by double-clicking it, and neither a
#: macOS bundle nor a Windows shortcut gives anyone a place to type an
#: argument. The migration has to be demonstrable on the packaged application,
#: not only on a developer's checkout, so the flag has an environment spelling
#: as well — the same shape `VIDEO_ANALYSE_SOFTWARE_RENDERING` already uses.
QML_WORKSPACE_VARIABLE = "VIDEO_ANALYSE_QML_WORKSPACE"

#: The two interfaces this application can start into. Widgets is the default
#: for as long as the QML workspace is being built: this is the expand half of
#: an expand-and-contract migration, and nobody loses the interface they have
#: today until #50 removes it.
WIDGETS_INTERFACE = "widgets"
QML_INTERFACE = "qml"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-analyse")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="initialize the application and bundled resources without showing the UI",
    )
    parser.add_argument(
        "--qml",
        action="store_true",
        help="start into the QML workspace instead of the default interface",
    )
    return parser


def selected_interface(
    options: argparse.Namespace, environment: Mapping[str, str] | None = None
) -> str:
    """Which interface a run with these options would start into."""

    if options.qml:
        return QML_INTERFACE
    values = os.environ if environment is None else environment
    if values.get(QML_WORKSPACE_VARIABLE, "").strip():
        return QML_INTERFACE
    return WIDGETS_INTERFACE


def _run_smoke_check(app: QApplication, log_path: str) -> dict[str, object]:
    from mainwindow import MainWindow

    font_path = overlay_font_path()
    if not font_path.is_file():
        raise FileNotFoundError(f"Bundled overlay font is missing: {font_path}")
    ImageFont.truetype(str(font_path), 12)

    qt_resource = QFile(":/icons/custom.play.fill.png")
    if not qt_resource.exists():
        raise FileNotFoundError("Bundled Qt resources are unavailable")

    available = set(QFontDatabase.families())
    registered_families = [
        family for family in REQUIRED_FONT_FAMILIES if family in available
    ]

    window = MainWindow()
    app.processEvents()
    window.close()

    # Packaging a Qt Quick presentation layer is the risk this check exists to
    # retire: the QML engine has to find its bundled scene, and the graphics
    # backend has to draw it, on whatever machine the package landed on.
    scene = show_quick_scene_with_fallback()
    app.processEvents()
    scene.window.close()

    return {
        "status": "ok",
        "font": str(font_path),
        "fonts": registered_families,
        "log": log_path,
        "qml": str(scene.source),
        "sceneRendered": True,
        "renderingBackend": scene.rendering_backend,
        "qmlWarnings": list(scene.warnings),
    }


def _publish_smoke_report(report: dict[str, object]) -> None:
    """Make the smoke report readable however the application was packaged.

    A packaged Windows application has no console attached, so its standard
    output is discarded. `VIDEO_ANALYSE_SMOKE_REPORT` names a file that receives
    the same report, which lets a build verify a windowed executable.
    """

    document = json.dumps(report)
    requested_report_file = os.environ.get("VIDEO_ANALYSE_SMOKE_REPORT")
    if requested_report_file:
        Path(requested_report_file).write_text(document, encoding="utf-8")
    print(document)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    options, qt_arguments = build_argument_parser().parse_known_args(arguments)
    interface = selected_interface(options)

    configure_application_identity()
    if software_rendering_requested():
        # Detection catches a backend that reports its failure. A driver that
        # takes the process down instead reports nothing, so the operator keeps
        # a way to demand software rendering before anything is drawn.
        use_software_rendering()
    app = QApplication([sys.argv[0], *qt_arguments])

    try:
        log_path = configure_local_logging()
        install_exception_logging()
        register_bundled_fonts()
        if options.smoke_test:
            report = _run_smoke_check(app, str(log_path))
            report["interface"] = interface
            _publish_smoke_report(report)
            return 0

        if interface == QML_INTERFACE:
            scene = show_quick_scene_with_fallback()
            # The scene owns the window; holding the engine keeps the whole
            # object tree alive for as long as the application runs.
            _ = scene
            return app.exec()

        from mainwindow import MainWindow

        window = MainWindow()
        window.show()
        return app.exec()
    except Exception:
        logging.getLogger(__name__).exception("Application startup failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
