"""THROWAWAY PROTOTYPE A -- redesigned Qt Widgets presentation layer.

Answers one question: can a carefully redesigned, mostly native Qt Widgets
interface reach the reference visual quality, and what does it cost in custom
painting to get there?

    uv run python prototype/presentation_a_widgets/run.py

Not production code. Nothing here reads or writes an Analysis file.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from prototype.presentation_a_widgets import (  # noqa: E402
    fixture,
    fonts,
    theme,
    tokens,
    window,
)

SCREENSHOTS = HERE / "screenshots"
MEDIA = HERE / "media"
TEST_VIDEOS = {
    "halbzeit-1.mp4": (MEDIA / "PROTOTYPE-halbzeit-1-wipe-me.mp4", 240),
    "halbzeit-2.mp4": (MEDIA / "PROTOTYPE-halbzeit-2-wipe-me.mp4", 200),
}
TEST_VIDEO = TEST_VIDEOS["halbzeit-1.mp4"][0]
POSTER = MEDIA / "poster.png"

CAPTURE_WIDTH = tokens.WINDOW_MIN_WIDTH
CAPTURE_HEIGHT = tokens.WINDOW_MIN_HEIGHT

_SCREENS = (
    ("01-workspace", window.WORKSPACE),
    ("02-clip-editing", window.EDITING),
    ("03-empty-state", window.EMPTY),
)


# ---------- media, generated once, never committed as real footage ----------


def _ffmpeg() -> str | None:
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover - prototype
        return None


def ensure_media() -> dict[str, Path] | None:
    """Synthetic clips so playback and scrubbing can be measured for real.

    These are test patterns, not handball footage. They exist so the decode and
    scrub questions are answered by running code rather than by estimate. Two
    distinct files, because the domain model rightly refuses to accept the same
    Source video twice.
    """
    binary = _ffmpeg()
    if binary is None:
        return None
    MEDIA.mkdir(parents=True, exist_ok=True)
    built: dict[str, Path] = {}
    for name, (destination, seconds) in TEST_VIDEOS.items():
        built[name] = destination
        if destination.exists():
            continue
        command = [
            binary, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(destination),
        ]
        result = subprocess.run(command, capture_output=True)
        if result.returncode != 0:
            print(result.stderr.decode()[-800:], file=sys.stderr)
            return None
    return built


def ensure_poster() -> Path | None:
    """One decoded frame, so the stage in the screenshots is not a black box."""
    if POSTER.exists():
        return POSTER
    videos = ensure_media()
    binary = _ffmpeg()
    if videos is None or binary is None:
        return None
    video = videos["halbzeit-1.mp4"]
    # Blurred and desaturated hard, so the stage reads as a dark video frame
    # rather than as a colour-bar test card competing with the interface.
    command = [
        binary, "-y", "-hide_banner", "-loglevel", "error",
        "-ss", "37", "-i", str(video),
        "-vf",
        "gblur=sigma=60,hue=s=0.10,eq=brightness=-0.10:contrast=0.80,"
        "vignette=PI/4,scale=960:540",
        "-frames:v", "1", str(POSTER),
    ]
    if subprocess.run(command, capture_output=True).returncode != 0:
        return None
    return POSTER


# ---------- assembly ----------


def build_application(argv: list[str] | None = None) -> QApplication:
    application = QApplication.instance() or QApplication(argv or sys.argv)
    application.setApplicationName("Video Analyse -- Prototype A")
    fonts.load()
    application.setStyleSheet(theme.stylesheet())
    application.setFont(fonts.ui())
    return application


def build_window(*, use_real_media: bool) -> window.Workspace:
    poster = ensure_poster()

    if use_real_media:
        from playback.media import MediaPlayerPlayback

        videos = ensure_media()
        if videos is None:
            print("No ffmpeg available; falling back to faked playback.", file=sys.stderr)
            return build_window(use_real_media=False)
        locations = {name: str(path) for name, path in videos.items()}
        durations = {
            name: TEST_VIDEOS[name][1] * 1000 for name in videos
        }
        content = fixture.build(media_locations=locations, media_durations=durations)
        player = MediaPlayerPlayback()
        workspace = window.Workspace(content, player, poster=None)
        from PySide6.QtMultimediaWidgets import QVideoWidget

        surface = QVideoWidget()
        surface.setAspectRatioMode(Qt.KeepAspectRatio)
        player.set_video_output(surface)
        workspace._stage.set_surface(surface)
        return workspace

    from playback.fake import FakePlayback

    content = fixture.build()
    return window.Workspace(
        content, FakePlayback(), poster=poster, drive_fake_playback=True
    )


# ---------- capture and measurement ----------


def capture() -> None:
    application = build_application([sys.argv[0], "-platform", "offscreen"])
    workspace = build_window(use_real_media=False)
    workspace.resize(CAPTURE_WIDTH, CAPTURE_HEIGHT)
    workspace.show()
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)

    for name, screen in _SCREENS:
        workspace.show_screen(screen)
        application.processEvents()
        workspace.repaint()
        application.processEvents()
        image = workspace.grab()
        destination = SCREENSHOTS / f"{name}-1440x900.png"
        image.save(str(destination))
        print(f"{destination.name}  {image.width()}x{image.height()}")


def benchmark(frames: int = 600) -> None:
    """What the timeline actually costs per frame, cached and uncached."""
    application = build_application([sys.argv[0], "-platform", "offscreen"])
    workspace = build_window(use_real_media=False)
    workspace.resize(CAPTURE_WIDTH, CAPTURE_HEIGHT)
    workspace.show()
    application.processEvents()

    surface = workspace._timeline
    duration = max(1, surface._duration_ms)
    print(f"timeline width: {surface.width()}px, duration: {duration / 1000:.0f}s")

    started = time.perf_counter()
    for frame in range(frames):
        surface.set_position(int(duration * frame / frames))
        surface.repaint()
    cached = (time.perf_counter() - started) / frames * 1000

    started = time.perf_counter()
    for frame in range(frames):
        surface.set_position(int(duration * frame / frames))
        surface.refresh()  # force a full rebuild of ruler and ranges
        surface.repaint()
    uncached = (time.perf_counter() - started) / frames * 1000

    print(f"playhead-only repaint : {cached:.3f} ms/frame  ({1000 / cached:6.0f} fps)")
    print(f"full rebuild repaint  : {uncached:.3f} ms/frame  ({1000 / uncached:6.0f} fps)")


def media_check(seconds: float = 4.0, seeks: int = 40) -> None:
    """Play and scrub real media, and report what the pipeline actually does.

    Compositing quality needs eyes on a real screen, but decode throughput and
    seek latency are measurable here, so they are measured rather than guessed.
    """
    from PySide6.QtCore import QEventLoop, QTimer

    application = build_application([sys.argv[0], "-platform", "offscreen"])
    workspace = build_window(use_real_media=True)
    workspace.resize(CAPTURE_WIDTH, CAPTURE_HEIGHT)
    workspace.show()

    player = workspace._player
    updates: list[int] = []
    player.position_changed.connect(updates.append)

    def spin(milliseconds: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    spin(1500)  # let the media load and become seekable
    print(f"loaded: {player.is_loaded()}  duration: {player.duration() / 1000:.1f}s")

    updates.clear()
    player.play()
    started = time.perf_counter()
    spin(int(seconds * 1000))
    player.pause()
    elapsed = time.perf_counter() - started
    print(
        f"playback: {len(updates)} position updates in {elapsed:.1f}s "
        f"({len(updates) / elapsed:.0f} per second)"
    )

    latencies: list[float] = []
    duration = max(1, player.duration())
    for index in range(seeks):
        target = int(duration * (index + 1) / (seeks + 1))
        moment = time.perf_counter()
        player.seek(target)
        spin(1)
        latencies.append((time.perf_counter() - moment) * 1000)
    latencies.sort()
    print(
        f"scrub: {seeks} seeks, median {latencies[len(latencies) // 2]:.1f} ms, "
        f"worst {latencies[-1]:.1f} ms"
    )


def smoke() -> None:
    application = build_application([sys.argv[0], "-platform", "offscreen"])
    workspace = build_window(use_real_media=False)
    workspace.resize(CAPTURE_WIDTH, CAPTURE_HEIGHT)
    workspace.show()
    for _name, screen in _SCREENS:
        workspace.show_screen(screen)
        application.processEvents()
    print("prototype A smoke check passed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--screen",
        choices=[window.WORKSPACE, window.EDITING, window.EMPTY],
        default=window.WORKSPACE,
        help="which state to open in (also Ctrl+1/2/3 in the Ansicht menu)",
    )
    parser.add_argument(
        "--media",
        action="store_true",
        help="run against real media through QMediaPlayer instead of FakePlayback",
    )
    parser.add_argument("--capture", action="store_true", help="write the screenshots")
    parser.add_argument("--benchmark", action="store_true", help="measure paint cost")
    parser.add_argument(
        "--media-check",
        action="store_true",
        help="play and scrub real media, reporting throughput and seek latency",
    )
    parser.add_argument("--smoke", action="store_true", help="build every screen and exit")
    arguments = parser.parse_args(argv)

    if arguments.capture:
        capture()
        return 0
    if arguments.benchmark:
        benchmark()
        return 0
    if arguments.media_check:
        media_check()
        return 0
    if arguments.smoke:
        smoke()
        return 0

    application = build_application()
    workspace = build_window(use_real_media=arguments.media)
    workspace.resize(CAPTURE_WIDTH, CAPTURE_HEIGHT)
    workspace.show_screen(arguments.screen)
    workspace.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
