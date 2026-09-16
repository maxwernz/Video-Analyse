from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PIL import ImageFont
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from analysis import new_analysis_document
from app_runtime import (
    REQUIRED_FONT_FAMILIES,
    configure_application_identity,
    configure_local_logging,
    install_exception_logging,
    overlay_font_path,
    register_bundled_fonts,
)
from category_template_settings import installation_category_template_store
from playback import MediaPlayerPlayback
from qml_runtime import (
    show_quick_scene_with_fallback,
    software_rendering_requested,
    use_software_rendering,
)
from menu_bar import build_menu_bar, native_menu_bar_available
from workspace_presenter import WorkspacePresenter
from workspace_view_model import WorkspaceViewModel


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-analyse")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="initialize the application and bundled QML workspace without showing the UI",
    )
    return parser


def build_workspace_context() -> dict[str, WorkspaceViewModel]:
    """What the QML window is given, and the whole vocabulary it has.

    One view model over one Analysis document and one player. QML never sees
    either of them; it sees this. The application opens into a new Analysis
    seeded with the default Category template — `new_analysis_document` is
    the same construction `ApplicationWorkflow.new_analysis` uses for File >
    New, so the Analysis an analyst starts from and the one File > New hands
    them cannot diverge. Every document command after that runs through the
    same workflow — the presenter is the only part of that which knows what a
    dialog is.
    """

    template_store = installation_category_template_store()
    view_model = WorkspaceViewModel(
        new_analysis_document(template_store=template_store),
        MediaPlayerPlayback(),
        presenter=WorkspacePresenter(),
        template_store=template_store,
    )
    return {"workspace": view_model}


def _run_smoke_check(app: QApplication, log_path: str) -> dict[str, object]:
    font_path = overlay_font_path()
    if not font_path.is_file():
        raise FileNotFoundError(f"Bundled overlay font is missing: {font_path}")
    ImageFont.truetype(str(font_path), 12)

    available = set(QFontDatabase.families())
    registered_families = [
        family for family in REQUIRED_FONT_FAMILIES if family in available
    ]

    # The QML engine has to find its bundled scene, and the graphics backend has
    # to draw it, on whatever machine the package landed on.
    context = build_workspace_context()
    scene = show_quick_scene_with_fallback(context_objects=context)
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
    parser = build_argument_parser()
    options, qt_arguments = parser.parse_known_args(arguments)
    if any(
        argument == "--qml" or argument.startswith("--qml=")
        for argument in qt_arguments
    ):
        parser.error("unrecognized arguments: --qml")
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
            report["interface"] = "qml"
            _publish_smoke_report(report)
            return 0

        context = build_workspace_context()
        # Asked before the window is shown: a restored Analysis should be
        # what the window first draws, not something that replaces an
        # already-visible empty one a moment later.
        context["workspace"].offerRecoveryIfAvailable()
        scene = show_quick_scene_with_fallback(context_objects=context)
        # On macOS the menu bar is a real QMenuBar with no parent — the system
        # menu bar — so nothing else is holding it, and Close goes through the
        # window, which is where the unsaved-changes question is asked.
        # Everywhere else the menu bar lives inside the QML window, drawn from
        # the same `menu_bar.MENUS`, and nothing is built here.
        menu_bar = (
            build_menu_bar(context["workspace"], close_window=scene.window.close)
            if native_menu_bar_available()
            else None
        )
        # The scene owns the window; holding the engine keeps the whole object
        # tree alive for as long as the application runs, and the context
        # objects are published rather than owned, so they have to outlive this
        # scope too.
        _ = (scene, context, menu_bar)
        return app.exec()
    except Exception:
        logging.getLogger(__name__).exception("Application startup failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
