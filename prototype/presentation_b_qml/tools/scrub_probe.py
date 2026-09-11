"""Find out who is responsible for the picture lagging a fast scrub.

    uv run python prototype/presentation_b_qml/tools/scrub_probe.py

The prototype's own measurement shows that dragging the playhead quickly
across a long video decodes almost no frames until the drag stops. That is
either something about rendering into the Qt Quick scene graph — which would
count against Prototype B — or a property of QMediaPlayer, which both
candidates sit on equally. This asks the same question of a Qt Widgets
QVideoWidget and of a QML VideoOutput, at several seek rates.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROTOTYPE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PROTOTYPE_ROOT.parents[1]
for entry in (str(PROJECT_ROOT), str(PROTOTYPE_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from PySide6.QtCore import QEventLoop, QUrl, Qt  # noqa: E402
from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402
from PySide6.QtMultimediaWidgets import QVideoWidget  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

MEDIA = PROTOTYPE_ROOT / "media" / "halbzeit-1.mp4"
DURATION_MS = 45 * 60_000

QML_SURFACE = """
import QtQuick
import QtMultimedia
Item {
    width: 640; height: 360
    VideoOutput { objectName: "output"; anchors.fill: parent }
}
"""


def pump(application, seconds: float) -> None:
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 2)


def measure(application, player: QMediaPlayer, label: str) -> None:
    sink = player.videoSink()
    frames = []
    sink.videoFrameChanged.connect(lambda _f: frames.append(time.perf_counter()))

    # Prime: the FFmpeg backend hands out no frame until playback has begun.
    player.play()
    pump(application, 0.8)
    player.pause()
    pump(application, 0.4)

    print(f"\n  {label}")
    for seeks_per_second in (60, 20, 10, 5):
        player.setPosition(4 * 60_000)
        pump(application, 0.6)
        frames.clear()
        interval = 1.0 / seeks_per_second
        started = time.perf_counter()
        step = 0
        while time.perf_counter() - started < 1.0:
            step += 1
            position = int(4 * 60_000 + (step * interval) * (35 * 60_000))
            player.setPosition(min(position, DURATION_MS - 1000))
            target = started + step * interval
            while time.perf_counter() < target:
                application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 1)
        during = len(frames)
        pump(application, 0.5)
        after = len(frames) - during
        print(f"    {seeks_per_second:>2} seeks/s : {during:>2} frames during, "
              f"{after} more within 500ms of stopping")


def main() -> int:
    if not MEDIA.is_file():
        print("Build the fixture media first.", file=sys.stderr)
        return 1

    application = QApplication(sys.argv)
    print("Frames decoded while seeking repeatedly, by video surface")

    # Qt Widgets surface.
    widget_player = QMediaPlayer()
    video_widget = QVideoWidget()
    video_widget.resize(640, 360)
    widget_player.setVideoOutput(video_widget)
    widget_player.setSource(QUrl.fromLocalFile(str(MEDIA)))
    video_widget.show()
    pump(application, 1.0)
    measure(application, widget_player, "Qt Widgets  (QVideoWidget)")
    video_widget.close()

    # Qt Quick surface.
    view = QQuickView()
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setInitialProperties({})
    source = PROTOTYPE_ROOT / "media" / "_probe_surface.qml"
    source.write_text(QML_SURFACE, encoding="utf-8")
    view.setSource(QUrl.fromLocalFile(str(source)))
    view.resize(640, 360)
    view.show()
    pump(application, 1.0)
    output = view.rootObject().findChild(object, "output")
    quick_player = QMediaPlayer()
    quick_player.setVideoOutput(output)
    quick_player.setSource(QUrl.fromLocalFile(str(MEDIA)))
    pump(application, 1.0)
    measure(application, quick_player, "Qt Quick    (QML VideoOutput)")
    view.close()
    source.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
