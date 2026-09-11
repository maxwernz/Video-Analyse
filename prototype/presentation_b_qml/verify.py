"""Drive the running prototype with real input and report what it does.

    uv run python prototype/presentation_b_qml/verify.py

Screenshots cannot answer the questions this prototype exists to answer. Scrub
smoothness, hit-testing and video compositing are all invisible in a still, so
this sends real mouse events to the real window and measures what comes back.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

PROTOTYPE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PROTOTYPE_ROOT.parents[1]
for entry in (str(PROJECT_ROOT), str(PROTOTYPE_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from PySide6.QtCore import QElapsedTimer, QEventLoop, QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import fixture  # noqa: E402
import run  # noqa: E402

WIDTH, HEIGHT = 1440, 900
results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    print(f"  [{'ok' if passed else 'FAIL'}] {name}{('  — ' + detail) if detail else ''}")


def pump(application: QApplication, milliseconds: int) -> None:
    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < milliseconds:
        application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 5)


def find(root, type_name: str):
    """The one instance of a QML type, by its component file name."""
    for child in root.findChildren(object):
        name = type(child).__name__
        if name.startswith(type_name):
            return child
    return None


def main() -> int:
    application = QApplication(sys.argv)
    if not fixture.media_is_present():
        print("Build the fixture media first.", file=sys.stderr)
        return 1

    engine, workspace = run.create_engine(application)
    window = engine.rootObjects()[0]
    window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
    window.setGeometry(0, 0, WIDTH, HEIGHT)
    window.show()
    pump(application, 1500)
    workspace.restore_canonical_state()
    pump(application, 2000)

    player = workspace._playback._media_player
    sink = player.videoSink()
    frame_times: list[float] = []
    sink.videoFrameChanged.connect(lambda _f: frame_times.append(time.perf_counter()))

    # Geometry of the timeline in window coordinates.
    from PySide6.QtCore import QObject

    strip = window.findChild(QObject, "timeline")
    if strip is None:
        print("could not find the timeline item", file=sys.stderr)
        return 1

    scene_position = strip.mapToScene(QPoint(0, 0).toPointF())
    left = int(scene_position.x())
    top = int(scene_position.y())
    strip_width = int(strip.width())
    duration = workspace.durationMs
    track_y = top + 16 + 22  # middle of the 44px track

    def x_for(position_ms: int) -> int:
        return left + int(position_ms / duration * strip_width)

    print(f"\nTimeline: x={left} y={top} width={strip_width}px  duration={duration}ms")
    print(f"          {duration / strip_width / 1000:.2f} s per pixel\n")

    print("Interaction grammar (ADR 0006)")

    # 1. Pressing empty track scrubs, and selects nothing.
    workspace.selectClip("")
    pump(application, 200)
    empty_ms = 24 * 60_000
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(x_for(empty_ms), track_y))
    pump(application, 700)
    check(
        "pressing empty track scrubs",
        abs(workspace.positionMs - empty_ms) < 6_000,
        f"asked {empty_ms}ms, playhead {workspace.positionMs}ms",
    )
    check("pressing empty track selects nothing", not workspace.hasSelection)

    # 2. Clicking a range scrubs to the click AND selects, without seeking to start.
    clip = next(c for c in workspace._analysis.clips if c.name == "Nachwurf nach Block")
    inside_ms = clip.start_ms + 11_000
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(x_for(inside_ms), track_y))
    pump(application, 700)
    check(
        "clicking a range selects it",
        workspace.selectedClipTitle == clip.name,
        f"selected {workspace.selectedClipTitle!r}",
    )
    check(
        "clicking a range does not seek to its start",
        abs(workspace.positionMs - clip.start_ms) > 2_000,
        f"playhead {workspace.positionMs}ms, Clip starts {clip.start_ms}ms",
    )

    # 3. Double-clicking a range seeks to the Clip start.
    QTest.mouseDClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                      QPoint(x_for(inside_ms), track_y))
    pump(application, 900)
    check(
        "double-clicking a range seeks to the Clip start",
        abs(workspace.positionMs - clip.start_ms) < 900,
        f"playhead {workspace.positionMs}ms, Clip starts {clip.start_ms}ms",
    )

    # 4. A short Clip still has a hit target at the three-pixel minimum.
    short = next(c for c in workspace._analysis.clips if c.name == "Siebenmeter")
    short_width = (short.end_ms - short.start_ms) / duration * strip_width
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(x_for(short.start_ms) + 1, track_y))
    pump(application, 700)
    check(
        "a 6.8s Clip is still clickable",
        workspace.selectedClipTitle == short.name,
        f"drawn {short_width:.1f}px wide, floor is 3px; selected {workspace.selectedClipTitle!r}",
    )

    # 5. Dragging scrubs continuously.
    #
    # Measured at several drag rates, because a synthetic drag that finishes
    # in six milliseconds measures nothing a hand could ever do, and because
    # the interesting question is not whether the event handler is fast — it
    # is — but whether the picture keeps up with the pointer.
    print("\nScrub performance")
    print("  drag rate   handling (median/worst)   frames decoded during 1s of dragging")

    def drag(moves_per_second: int) -> tuple[float, float, int]:
        start_x = x_for(5 * 60_000)
        end_x = x_for(40 * 60_000)
        workspace.seek(5 * 60_000)
        pump(application, 500)
        QTest.mousePress(window, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, QPoint(start_x, track_y))
        pump(application, 120)
        frame_times.clear()
        latencies = []
        interval = 1.0 / moves_per_second
        started = time.perf_counter()
        step = 0
        while time.perf_counter() - started < 1.0:
            step += 1
            fraction = min(1.0, step * interval)
            x = start_x + int((end_x - start_x) * fraction)
            before = time.perf_counter()
            QTest.mouseMove(window, QPoint(x, track_y))
            application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 2)
            latencies.append((time.perf_counter() - before) * 1000)
            target = started + step * interval
            while time.perf_counter() < target:
                application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 1)
        decoded = len(frame_times)
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier, QPoint(x, track_y))
        pump(application, 500)
        return statistics.median(latencies), max(latencies), decoded

    decoded_at = {}
    landed_at = 0
    for rate in (60, 20, 10):
        median_latency, worst_latency, decoded = drag(rate)
        decoded_at[rate] = decoded
        landed_at = workspace.positionMs
        print(f"  {rate:>2}/s        {median_latency:>5.2f}ms / {worst_latency:>5.2f}ms"
              f"          {decoded:>3} of {rate} moves")

    # How long one seek takes to become a visible frame. This is the number a
    # coach feels when they click the timeline once.
    seek_latencies = []
    for index in range(10):
        target = (6 + index * 3) * 60_000
        pump(application, 260)
        frame_times.clear()
        asked_at = time.perf_counter()
        workspace.seek(target)
        while time.perf_counter() - asked_at < 1.0 and not frame_times:
            application.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 1)
        if frame_times:
            seek_latencies.append((frame_times[0] - asked_at) * 1000)
    print(f"  one click to a new frame: median {statistics.median(seek_latencies):.0f}ms, "
          f"worst {max(seek_latencies):.0f}ms  ({len(seek_latencies)}/10 seeks measured)")

    check(
        "dragging lands the playhead where it was released",
        abs(landed_at - 40 * 60_000) < 40_000,
        f"playhead {landed_at}ms after the last drag",
    )
    check(
        "scrub handling stays well under one frame at 60Hz",
        worst_latency < 16.7,
        f"worst {worst_latency:.2f}ms",
    )
    check(
        "the picture follows a hand-speed drag (10-20 moves/s)",
        decoded_at[10] >= 6 and decoded_at[20] >= 8,
        f"{decoded_at[10]} frames at 10/s, {decoded_at[20]} at 20/s",
    )
    check(
        "a single seek reaches the screen within two frames",
        statistics.median(seek_latencies) < 34,
        f"median {statistics.median(seek_latencies):.0f}ms",
    )

    # 6. Playback frame delivery.
    print("\nPlayback")
    workspace.seek(10 * 60_000)
    pump(application, 800)
    frame_times.clear()
    workspace.playPause()
    pump(application, 3000)
    workspace.playPause()
    pump(application, 300)
    if len(frame_times) > 3:
        gaps = [
            (later - earlier) * 1000
            for earlier, later in zip(frame_times, frame_times[1:])
        ]
        print(f"  {len(frame_times)} frames in 3s")
        print(f"  frame interval: median {statistics.median(gaps):.1f}ms, "
              f"worst {max(gaps):.1f}ms (source is 25fps = 40ms)")
        check(
            "playback delivers frames at the source rate",
            20 < statistics.median(gaps) < 60,
            f"median interval {statistics.median(gaps):.1f}ms",
        )
    else:
        check("playback delivers frames", False, f"only {len(frame_times)} frames seen")

    # 7. The scrub-linked Clip editor moves the video.
    print("\nClip editing")
    workspace.editClip(str(clip.id))
    pump(application, 1200)
    check("the second path into the editor pauses playback", not workspace.playing)
    check(
        "opening the editor seeks to the Clip start",
        abs(workspace.positionMs - clip.start_ms) < 900,
        f"playhead {workspace.positionMs}ms",
    )
    workspace.setDraftEndText("00:14:40.000")
    pump(application, 900)
    check(
        "editing a boundary scrubs the video to it",
        abs(workspace.positionMs - (14 * 60_000 + 40_000)) < 900,
        f"playhead {workspace.positionMs}ms",
    )
    check(
        "the duration readout follows the boundary",
        workspace.draftDurationText == "0:28.0",
        f"reads {workspace.draftDurationText!r}",
    )
    revision_before = workspace._analysis.revision
    workspace.cancelDraft()
    pump(application, 400)
    check(
        "cancelling changes nothing in the Analysis",
        workspace._analysis.revision == revision_before,
        f"revision {revision_before}",
    )

    window.close()
    pump(application, 300)

    failed = [name for name, passed, _ in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
