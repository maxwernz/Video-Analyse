"""What an analyst can do to the video, tested with no window in sight.

The view model is the seam between QML and the rest of the application: every
action the transport can trigger and every value it can show passes through
here, so these tests describe the transport's behaviour without a QML engine,
a graphics backend or a media file. They drive the same `FakePlayback` the
playback tests already use.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QObject, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import timecode  # noqa: E402
from analysis import Analysis, AnalysisDocument  # noqa: E402
from playback import JUMP_INTERVAL_MS, STEP_INTERVAL_MS, FakePlayback  # noqa: E402
from workspace_view_model import (  # noqa: E402
    PLAYBACK_RATES,
    PRIMING_MS,
    WorkspaceViewModel,
)


VIDEO = "/videos/halbzeit-1.mp4"
VIDEO_DURATION_MS = 2_700_000


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


class Scheduler:
    """Stands in for the event loop, so a delay is not a slow test."""

    def __init__(self) -> None:
        self.pending: list[tuple[int, object]] = []

    def __call__(self, delay_ms: int, run) -> None:  # type: ignore[no-untyped-def]
        self.pending.append((delay_ms, run))

    @property
    def delays(self) -> list[int]:
        return [delay for delay, _ in self.pending]

    def elapse(self) -> None:
        """Run everything the view model asked to have run later."""

        due, self.pending = self.pending, []
        for _, run in due:
            run()  # type: ignore[operator]


def analysis_with_a_video() -> Analysis:
    analysis = Analysis("Spiel gegen Kiel")
    analysis.add_source_video(
        "Halbzeit 1", VIDEO, duration_ms=VIDEO_DURATION_MS
    )
    return analysis


@pytest.fixture
def scheduler() -> Scheduler:
    return Scheduler()


@pytest.fixture
def document() -> AnalysisDocument:
    return AnalysisDocument(analysis_with_a_video())


@pytest.fixture
def player(application: QApplication) -> FakePlayback:
    return FakePlayback()


@pytest.fixture
def workspace(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> WorkspaceViewModel:
    model = WorkspaceViewModel(document, player, schedule=scheduler)
    scheduler.elapse()
    return model


# --- The Active Source video -----------------------------------------------


def test_opening_an_analysis_loads_its_first_source_video(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    assert player.location() == VIDEO
    assert workspace.hasVideo is True


def test_an_analysis_with_no_source_video_has_nothing_to_play(
    player: FakePlayback, scheduler: Scheduler
) -> None:
    workspace = WorkspaceViewModel(
        AnalysisDocument.new("Leer"), player, schedule=scheduler
    )

    assert workspace.hasVideo is False
    assert player.is_loaded() is False
    assert workspace.positionText == "00:00:00"
    assert scheduler.pending == []


def test_the_total_time_comes_from_the_analysis_before_the_media_speaks(
    workspace: WorkspaceViewModel,
) -> None:
    """A Source video whose length the Analysis knows shows it immediately."""

    assert workspace.durationMs == VIDEO_DURATION_MS
    assert workspace.durationText == timecode.clock(VIDEO_DURATION_MS)


def test_the_media_s_own_duration_is_preferred_once_it_reports_one(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    player.set_duration(2_701_240)

    assert workspace.durationMs == 2_701_240


# --- Playing ----------------------------------------------------------------


def test_the_transport_plays_and_pauses(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.playPause()
    assert workspace.playing is True
    assert player.is_playing() is True

    workspace.playPause()
    assert workspace.playing is False
    assert player.is_playing() is False


def test_playing_and_pausing_tells_the_interface_something_changed(
    workspace: WorkspaceViewModel,
) -> None:
    reported: list[bool] = []
    workspace.playbackChanged.connect(lambda: reported.append(workspace.playing))

    workspace.playPause()

    assert reported[-1] is True


def test_a_step_moves_one_fixed_interval_whatever_the_rate(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.seek(60_000)
    workspace.setRateIndex(PLAYBACK_RATES.index(2.0))

    workspace.stepForward()
    assert workspace.positionMs == 60_000 + STEP_INTERVAL_MS

    workspace.stepBackward()
    assert workspace.positionMs == 60_000


def test_a_jump_moves_five_seconds(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.seek(60_000)

    workspace.jumpForward()
    assert workspace.positionMs == 60_000 + JUMP_INTERVAL_MS

    workspace.jumpBackward()
    assert workspace.positionMs == 60_000


def test_the_elapsed_time_follows_the_player(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    player.seek(3_723_000)

    assert workspace.positionMs == 3_723_000
    assert workspace.positionText == "01:02:03"


def test_the_interface_hears_about_every_position_the_player_reports(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    reported: list[str] = []
    workspace.playbackChanged.connect(lambda: reported.append(workspace.positionText))

    player.seek(65_000)

    assert reported[-1] == "00:01:05"


# --- Speed -------------------------------------------------------------------


def test_the_speed_control_is_offered_the_rates_the_application_supports(
    workspace: WorkspaceViewModel,
) -> None:
    assert workspace.playbackRates == ["0.5x", "1x", "1.5x", "2x"]


def test_choosing_a_speed_sets_it_on_the_player(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.setRateIndex(3)

    assert player.playback_rate() == 2.0
    assert workspace.playbackRate == 2.0
    assert workspace.playbackRateIndex == 3


def test_which_speed_is_selected_is_decided_here_rather_than_in_qml(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    """The segmented control draws the option this names; it does not look."""

    assert workspace.playbackRateIndex == PLAYBACK_RATES.index(1.0)
    player.set_playback_rate(0.5)
    assert workspace.playbackRateIndex == 0


def test_a_speed_the_application_does_not_offer_is_shown_as_normal_speed(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    player.set_playback_rate(3.7)

    assert workspace.playbackRateIndex == PLAYBACK_RATES.index(1.0)


def test_a_segment_that_does_not_exist_changes_nothing(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.setRateIndex(len(PLAYBACK_RATES))

    assert player.playback_rate() == 1.0


# --- Sound -------------------------------------------------------------------


def test_the_transport_mutes_and_unmutes(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.toggleMuted()
    assert workspace.muted is True
    assert player.is_muted() is True

    workspace.toggleMuted()
    assert workspace.muted is False


def test_the_volume_is_a_level_the_transport_can_set(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.setVolume(0.4)

    assert player.volume() == pytest.approx(0.4)
    assert workspace.volume == pytest.approx(0.4)


def test_a_volume_outside_the_range_is_taken_as_the_nearest_end(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.setVolume(1.8)
    assert workspace.volume == pytest.approx(1.0)

    workspace.setVolume(-0.3)
    assert workspace.volume == pytest.approx(0.0)


def test_turning_the_volume_down_is_not_muting(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.setVolume(0.0)

    assert workspace.muted is False


def test_changing_the_sound_tells_the_interface_something_changed(
    workspace: WorkspaceViewModel,
) -> None:
    reported: list[tuple[bool, float]] = []
    workspace.playbackChanged.connect(
        lambda: reported.append((workspace.muted, workspace.volume))
    )

    workspace.toggleMuted()
    workspace.setVolume(0.25)

    assert reported[-1] == (True, pytest.approx(0.25))


# --- The video surface -------------------------------------------------------


def test_the_qml_video_item_is_handed_to_the_existing_player_seam(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    surfaces: list[QObject | None] = []
    player.set_video_output = surfaces.append  # type: ignore[method-assign]
    item = QObject()

    workspace.attachVideoOutput(item)

    assert surfaces == [item]


# --- Priming the video surface ----------------------------------------------


def test_a_freshly_opened_analysis_shows_a_frame_without_anyone_pressing_play(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> None:
    """Qt's backend decodes nothing until playback has started once.

    So opening an Analysis starts it, briefly, through the public seam — and
    the analyst sees the first frame rather than black.
    """

    started: list[bool] = []
    player.playing_changed.connect(started.append)

    WorkspaceViewModel(document, player, schedule=scheduler)

    assert started == [True]
    assert scheduler.delays == [PRIMING_MS]

    scheduler.elapse()

    assert started == [True, False]
    assert player.is_playing() is False


def test_priming_leaves_the_playhead_where_it_was(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> None:
    workspace = WorkspaceViewModel(document, player, schedule=scheduler)
    player.seek(90)  # the decoder ran for a moment before the pause landed
    scheduler.elapse()

    assert player.position() == 0
    assert workspace.positionMs == 0


def test_priming_is_silent(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> None:
    """A blip of match audio on opening an Analysis is not a first frame."""

    muted_while_priming: list[bool] = []
    player.playing_changed.connect(lambda _: muted_while_priming.append(player.is_muted()))

    workspace = WorkspaceViewModel(document, player, schedule=scheduler)
    scheduler.elapse()

    assert muted_while_priming == [True, True]
    assert player.is_muted() is False
    assert workspace.muted is False


def test_priming_gives_back_the_mute_the_analyst_chose(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> None:
    player.set_muted(True)

    workspace = WorkspaceViewModel(document, player, schedule=scheduler)
    scheduler.elapse()

    assert player.is_muted() is True
    assert workspace.muted is True


def test_the_interface_never_shows_the_priming_play(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> None:
    """Priming is a decoder detail; the transport must not flicker for it."""

    workspace = WorkspaceViewModel(document, player, schedule=scheduler)
    reported: list[tuple[bool, bool]] = []
    workspace.playbackChanged.connect(
        lambda: reported.append((workspace.playing, workspace.muted))
    )

    assert workspace.playing is False
    assert workspace.muted is False

    player.seek(90)
    scheduler.elapse()

    assert (True, True) not in reported
    assert workspace.playing is False


def test_pressing_play_while_the_surface_is_priming_simply_plays(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> None:
    workspace = WorkspaceViewModel(document, player, schedule=scheduler)

    workspace.playPause()

    assert workspace.playing is True
    assert workspace.muted is False
    assert player.is_muted() is False

    scheduler.elapse()

    assert workspace.playing is True
    assert player.is_playing() is True


def test_priming_uses_the_event_loop_when_nobody_supplies_a_schedule(
    application: QApplication, document: AnalysisDocument, player: FakePlayback
) -> None:
    """The production path waits on a real timer, not on a test double."""

    workspace = WorkspaceViewModel(document, player)
    assert player.is_playing() is True

    loop = QEventLoop()
    QTimer.singleShot(PRIMING_MS * 4, loop.quit)
    loop.exec()

    assert player.is_playing() is False
    assert workspace.playing is False


# --- Playback is not part of the Analysis ------------------------------------


def test_nothing_the_transport_does_dirties_the_analysis(
    workspace: WorkspaceViewModel, document: AnalysisDocument, player: FakePlayback
) -> None:
    assert document.dirty is False

    workspace.playPause()
    workspace.stepForward()
    workspace.jumpForward()
    workspace.seek(120_000)
    workspace.setRateIndex(0)
    workspace.toggleMuted()
    workspace.setVolume(0.3)
    workspace.playPause()

    assert document.dirty is False
