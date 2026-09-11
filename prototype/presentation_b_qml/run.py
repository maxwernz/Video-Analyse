"""Run the QML presentation prototype.

    uv run python prototype/presentation_b_qml/run.py

The application layer is the real one: the Analysis, the AnalysisDocument, the
ApplicationWorkflow and the Playback all come from the production packages
unchanged, and only the presentation above them is new.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROTOTYPE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PROTOTYPE_ROOT.parents[1]
for entry in (str(PROJECT_ROOT), str(PROTOTYPE_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenuBar  # noqa: E402

import fixture  # noqa: E402
from icons import IconProvider  # noqa: E402
from playback import FakePlayback, MediaPlayerPlayback  # noqa: E402
from viewmodels import WorkspaceViewModel  # noqa: E402

FONT_FILES = (
    "Inter-Variable.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
)


def load_fonts() -> list[str]:
    """Bundle the typography, so both platforms render the same window.

    ``visual-tokens.md`` says these live in ``assets/fonts/``. They do not —
    see FINDINGS.md. The prototype carries its own copies rather than tuning
    the token to whatever the machine happens to have installed.
    """
    loaded = []
    for name in FONT_FILES:
        path = PROTOTYPE_ROOT / "fonts" / name
        identifier = QFontDatabase.addApplicationFont(str(path))
        if identifier == -1:
            print(f"warning: could not load bundled font {name}", file=sys.stderr)
            continue
        loaded.extend(QFontDatabase.applicationFontFamilies(identifier))
    return loaded


def build_menu_bar(application: QApplication) -> QMenuBar:
    """A real QMenuBar with no parent: on macOS, the system menu bar.

    The visual system is owned; the menu bar is behaviour and stays native.
    Keeping it out of QML is also the honest test — a Qt Quick MenuBar would
    have drawn a menu strip inside the window, which is the wordmark strip
    mistake with different words in it.
    """
    menu_bar = QMenuBar()

    file_menu = menu_bar.addMenu("Datei")
    file_menu.addAction("Neue Analyse")
    file_menu.addAction("Analyse öffnen …")
    file_menu.addSeparator()
    file_menu.addAction("Speichern")
    file_menu.addAction("Speichern unter …")
    file_menu.addSeparator()
    file_menu.addAction("Video hinzufügen …")
    file_menu.addAction("Zusammenschnitt exportieren …")

    edit_menu = menu_bar.addMenu("Bearbeiten")
    edit_menu.addAction("Clip markieren")
    edit_menu.addAction("Clip bearbeiten")

    view_menu = menu_bar.addMenu("Ansicht")
    view_menu.addAction("Seitenleiste ein-/ausblenden")
    view_menu.addAction("Vollbild")

    return menu_bar


def create_engine(
    application: QApplication,
    *,
    empty: bool = False,
    still: str = "",
    fake_playback: bool = False,
) -> tuple[QQmlApplicationEngine, WorkspaceViewModel]:
    load_fonts()

    document = fixture.empty_document() if empty else fixture.canonical_document()
    playback = FakePlayback() if fake_playback else MediaPlayerPlayback()
    workspace = WorkspaceViewModel(document, playback)

    engine = QQmlApplicationEngine()
    engine.addImageProvider("icon", IconProvider())

    context = engine.rootContext()
    context.setContextProperty("workspace", workspace)
    context.setContextProperty("clipModel", workspace.clips)
    context.setContextProperty("rangeModel", workspace.ranges)
    context.setContextProperty("rulerModel", workspace.ruler)
    context.setContextProperty("sourceModel", workspace.videos)
    context.setContextProperty("categoryModel", workspace.categories)
    context.setContextProperty("captureStill", still)

    engine.addImportPath(str(PROTOTYPE_ROOT / "qml"))
    engine.load(QUrl.fromLocalFile(str(PROTOTYPE_ROOT / "qml" / "Main.qml")))
    if not engine.rootObjects():
        raise SystemExit("QML failed to load")

    if not empty:
        workspace.restore_canonical_state()
    return engine, workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="presentation-b-qml")
    parser.add_argument(
        "--empty",
        action="store_true",
        help="render the empty state instead of the canonical fixture",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="load the interface and report, without showing it (packaging check)",
    )
    parser.add_argument(
        "--fake-playback",
        action="store_true",
        help="drive the interface from playback.FakePlayback instead of real media",
    )
    options = parser.parse_args(argv)

    if (
        not options.empty
        and not options.fake_playback
        and not options.smoke_test
        and not fixture.media_is_present()
    ):
        print(
            "The fixture media is missing. Build it once with:\n"
            "    uv run python prototype/presentation_b_qml/tools/make_fixture_video.py",
            file=sys.stderr,
        )
        return 1

    application = QApplication(sys.argv)
    application.setApplicationName("Video Analyse")

    if options.smoke_test:
        # The same shape of check `scripts/build_macos.sh` runs against the
        # packaged application: prove the bundle can build its interface.
        import json

        from PySide6.QtCore import QElapsedTimer, QEventLoop

        with_media = fixture.media_is_present()
        engine, workspace = create_engine(
            application, empty=not with_media, fake_playback=not with_media
        )
        window = engine.rootObjects()[0]
        report = {
            "status": "ok",
            "qml": str(PROTOTYPE_ROOT / "qml" / "Main.qml"),
            "window": f"{int(window.width())}x{int(window.height())}",
            "fonts": ", ".join(sorted(set(load_fonts()))) or "none",
            "mode": workspace.mode,
        }
        if with_media:
            # Prove the packaged multimedia backend actually decodes, rather
            # than only that the QML loaded.
            player = workspace._playback._media_player
            elapsed = QElapsedTimer()
            elapsed.start()
            while elapsed.elapsed() < 4000 and not player.hasVideo():
                application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 10)
            report["media"] = Path(player.source().toLocalFile()).name
            report["hasVideo"] = player.hasVideo()
            report["durationMs"] = player.duration()
            report["mediaError"] = player.errorString() or "none"
        print(json.dumps(report))
        return 0

    menu_bar = build_menu_bar(application)
    engine, workspace = create_engine(
        application,
        empty=options.empty,
        fake_playback=options.fake_playback,
    )
    _ = menu_bar, workspace
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
