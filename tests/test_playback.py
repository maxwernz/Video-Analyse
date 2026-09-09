from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from playback import JUMP_INTERVAL_MS, STEP_INTERVAL_MS, FakePlayback  # noqa: E402


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def player(application: QApplication) -> FakePlayback:
    playback = FakePlayback()
    playback.load("/videos/first-half.mp4")
    playback.set_duration(90_000)
    return playback


def test_stepping_moves_a_fixed_interval_whatever_the_playback_rate(
    player: FakePlayback,
) -> None:
    player.seek(10_000)
    player.set_playback_rate(0.25)
    player.step_forward()
    at_quarter_speed = player.position()

    player.seek(10_000)
    player.set_playback_rate(2.0)
    player.step_forward()

    assert at_quarter_speed == 10_000 + STEP_INTERVAL_MS
    assert player.position() == at_quarter_speed


def test_stepping_stays_inside_the_active_source_video(player: FakePlayback) -> None:
    player.seek(0)
    player.step_backward()
    assert player.position() == 0

    player.seek(90_000)
    player.step_forward()
    assert player.position() == 90_000


def test_stepping_pauses_so_the_frame_stepped_to_stays_on_screen(
    player: FakePlayback,
) -> None:
    player.play()
    player.step_forward()

    assert player.is_playing() is False


def _record_playing(player: FakePlayback) -> list[bool]:
    reported: list[bool] = []
    player.playing_changed.connect(reported.append)
    return reported


def test_every_entry_point_that_pauses_reports_the_same_way(
    player: FakePlayback,
) -> None:
    reported = _record_playing(player)

    player.play()
    player.pause()
    player.play()
    player.play_pause()
    player.play()
    player.step_backward()

    assert reported == [True, False, True, False, True, False]


def test_pausing_an_already_paused_video_reports_nothing_new(
    player: FakePlayback,
) -> None:
    reported = _record_playing(player)

    player.pause()

    assert reported == []
    assert player.is_playing() is False


def test_a_video_that_is_not_loaded_does_not_start_playing() -> None:
    player = FakePlayback()
    reported = _record_playing(player)

    player.play_pause()

    assert player.is_playing() is False
    assert reported == []


def test_the_duration_of_the_active_source_video_is_readable_and_observable(
    application: QApplication,
) -> None:
    player = FakePlayback()
    durations: list[int] = []
    player.duration_changed.connect(durations.append)

    player.load("/videos/first-half.mp4")
    player.set_duration(90_000)

    assert player.duration() == 90_000
    assert durations == [0, 90_000]


def test_unloading_forgets_the_active_source_video(player: FakePlayback) -> None:
    player.seek(10_000)
    player.play()

    player.unload()

    assert player.is_loaded() is False
    assert player.is_playing() is False
    assert player.position() == 0
    assert player.duration() == 0


def test_the_playback_rate_is_set_from_a_number(player: FakePlayback) -> None:
    player.set_playback_rate(0.25)

    assert player.playback_rate() == 0.25


def test_media_player_playback_is_not_a_widget_and_builds_no_layout(
    application: QApplication,
) -> None:
    from PySide6.QtWidgets import QWidget

    from playback import MediaPlayerPlayback

    player = MediaPlayerPlayback()

    assert not isinstance(player, QWidget)
    assert player.is_loaded() is False
    assert player.playback_rate() == 1.0


def test_media_player_playback_loads_a_source_video_from_its_location(
    application: QApplication,
    tmp_path,
) -> None:
    from playback import MediaPlayerPlayback

    video_path = tmp_path / "first-half.mp4"
    video_path.write_bytes(b"not a real video")
    player = MediaPlayerPlayback()

    player.load(str(video_path))

    assert player.is_loaded() is True
    assert player.location() == str(video_path)

    player.unload()

    assert player.is_loaded() is False
    assert player.location() is None


def test_jumping_moves_a_fixed_interval_whatever_the_playback_rate(
    player: FakePlayback,
) -> None:
    player.seek(20_000)
    player.set_playback_rate(0.25)
    player.jump_forward()
    assert player.position() == 20_000 + JUMP_INTERVAL_MS

    player.set_playback_rate(2.0)
    player.jump_backward()
    assert player.position() == 20_000


def test_a_seek_made_before_the_media_can_seek_is_applied_once_it_can() -> None:
    player = FakePlayback()
    player.load("/videos/first-half.mp4")
    player.set_seekable(False)

    player.seek(12_000)
    assert player.position() == 0

    player.set_seekable(True)

    assert player.position() == 12_000


def test_a_later_seek_replaces_the_one_still_waiting() -> None:
    player = FakePlayback()
    player.load("/videos/first-half.mp4")
    player.set_seekable(False)

    player.seek(12_000)
    player.seek(20_000)
    player.set_seekable(True)

    assert player.position() == 20_000


def test_loading_another_source_video_drops_a_seek_meant_for_the_last_one() -> None:
    player = FakePlayback()
    player.load("/videos/first-half.mp4")
    player.set_seekable(False)
    player.seek(12_000)

    player.load("/videos/second-half.mp4")
    player.set_seekable(True)

    assert player.position() == 0


def test_both_playbacks_report_the_same_location_for_the_same_video(
    application: QApplication,
    tmp_path,
) -> None:
    """A native path in, a native path out, whatever the platform separator."""
    from playback import MediaPlayerPlayback

    video_path = tmp_path / "first-half.mp4"
    video_path.write_bytes(b"not a real video")
    real = MediaPlayerPlayback()
    fake = FakePlayback()

    real.load(str(video_path))
    fake.load(str(video_path))

    assert real.location() == fake.location() == str(video_path)
    assert real.location() == os.fspath(video_path)
