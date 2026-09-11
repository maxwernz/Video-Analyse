"""Capture the prototype's screens at 1440x900.

    uv run python prototype/presentation_b_qml/capture.py

This drives the real window on a real GPU with the real media, so what lands in
`screenshots/` is what the interface actually renders, video frame included —
not an offscreen approximation. The window is 1440x900 logical on a 2x display
and each grab is resampled down to 1440x900 so the captures are directly
comparable with `docs/design/current-ui/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROTOTYPE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PROTOTYPE_ROOT.parents[1]
for entry in (str(PROJECT_ROOT), str(PROTOTYPE_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from PySide6.QtCore import QElapsedTimer, QEventLoop, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import fixture  # noqa: E402
import run  # noqa: E402

SHOTS = PROTOTYPE_ROOT / "screenshots"
WIDTH, HEIGHT = 1440, 900


def pump(application: QApplication, milliseconds: int) -> None:
    """Run the event loop for a while without blocking rendering."""
    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < milliseconds:
        application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 10)


def grab(window, name: str) -> Path:
    image = window.grabWindow()
    if image.width() != WIDTH:
        # A 2x grab of a 1440x900 window, resampled to the designed size.
        image = image.scaled(
            WIDTH,
            HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    SHOTS.mkdir(parents=True, exist_ok=True)
    destination = SHOTS / name
    image.save(str(destination))
    print(f"    {name}  {image.width()}x{image.height()}")
    return destination


def open_window(application: QApplication, **kwargs):
    """Show the window frameless at exactly 1440x900.

    The machine these captures were taken on is a 1440x900 display, so a
    framed window cannot hold 1440x900 of *content* — the title bar and menu
    bar eat into it, and the grab would have to be stretched to claim the
    designed size. Frameless keeps the real GPU path and the real video while
    making the captured pixels the designed ones.
    """
    engine, workspace = run.create_engine(application, **kwargs)
    window = engine.rootObjects()[0]
    window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
    window.setGeometry(0, 0, WIDTH, HEIGHT)
    window.show()
    pump(application, 800)
    window.setGeometry(0, 0, WIDTH, HEIGHT)
    pump(application, 500)
    if window.width() != WIDTH or window.height() != HEIGHT:
        print(
            f"    warning: window is {window.width()}x{window.height()}, not {WIDTH}x{HEIGHT}",
            file=sys.stderr,
        )
    return engine, workspace, window


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Video Analyse")

    if not fixture.media_is_present():
        print(
            "Build the fixture media first:\n"
            "    uv run python prototype/presentation_b_qml/tools/make_fixture_video.py",
            file=sys.stderr,
        )
        return 1

    print("==> Workspace, Clip-editing and Pending states")
    engine, workspace, window = open_window(application)

    # Let the media decode and land on the canonical frame.
    workspace.restore_canonical_state()
    pump(application, 2500)
    workspace.restore_canonical_state()
    pump(application, 1200)

    grab(window, "01-workspace-clips.png")

    workspace.setSidebarTab("videos")
    pump(application, 500)
    grab(window, "02-workspace-videos.png")

    workspace.setSidebarTab("clips")
    pump(application, 300)

    # The Clip-editing state, entered the way the sidebar enters it.
    workspace.editSelectedClip()
    pump(application, 1600)
    grab(window, "03-clip-editing.png")

    workspace.cancelDraft()
    pump(application, 400)

    # A Pending Clip: the first boundary set, the second not yet.
    workspace.seek(21 * 60_000 + 4_000)
    pump(application, 1200)
    workspace.markBoundary()
    workspace.seek(21 * 60_000 + 13_000)
    pump(application, 1400)
    grab(window, "04-pending-clip.png")

    workspace.cancelPending()
    pump(application, 200)

    # The second boundary opens the editor on a new Clip, paused.
    workspace.seek(21 * 60_000 + 4_000)
    pump(application, 900)
    workspace.markBoundary()
    workspace.seek(21 * 60_000 + 17_500)
    pump(application, 900)
    workspace.markBoundary()
    pump(application, 1600)
    grab(window, "05-clip-editing-new.png")

    window.close()
    pump(application, 400)

    print("==> Empty state")
    empty_engine, empty_workspace, empty_window = open_window(application, empty=True)
    pump(application, 900)
    grab(empty_window, "06-empty-state.png")
    empty_window.close()
    pump(application, 300)

    _ = engine, empty_engine, empty_workspace
    print("==> Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
