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
    MAXIMUM_INTERPOLATION_MS,
    PLAYBACK_RATES,
    PRIMING_MS,
    SCRUB_INTERVAL_MS,
    SCRUB_SEEKS_PER_SECOND,
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


# --- The timeline ------------------------------------------------------------
#
# Everything the one seek surface can show or do, with no window: the ranges it
# draws, the ruler it is given, selection, the interpolated playhead and the
# throttle that keeps a scrub following the pointer.


class Loop:
    """Stands in for the event loop: a clock, a schedule and a ticker.

    Interpolation and throttling are both statements about time, and a test
    that waited for real milliseconds would be slow where it was not flaky.
    Time here moves only when a test moves it.
    """

    def __init__(self) -> None:
        self.now_ms = 0.0
        self._due: list[tuple[float, object]] = []
        self.tick_interval_ms: int | None = None
        self._tick: object | None = None
        self._next_tick_ms = 0.0

    # The three seams the view model is given.

    def clock(self) -> float:
        return self.now_ms / 1000.0

    def schedule(self, delay_ms: int, run) -> None:  # type: ignore[no-untyped-def]
        self._due.append((self.now_ms + delay_ms, run))

    def start(self, interval_ms: int, run) -> None:  # type: ignore[no-untyped-def]
        self.tick_interval_ms = interval_ms
        self._tick = run
        self._next_tick_ms = self.now_ms + interval_ms

    def stop(self) -> None:
        self.tick_interval_ms = None
        self._tick = None

    @property
    def ticking(self) -> bool:
        return self._tick is not None

    # What a test does to it.

    def advance(self, milliseconds: float) -> None:
        """Move time forward, running whatever falls due on the way."""

        target = self.now_ms + milliseconds
        while True:
            pending = [when for when, _ in self._due]
            if self._tick is not None:
                pending.append(self._next_tick_ms)
            due_at = min(pending, default=None)
            if due_at is None or due_at > target:
                break
            self.now_ms = max(self.now_ms, due_at)
            ready = [entry for entry in self._due if entry[0] <= self.now_ms]
            self._due = [entry for entry in self._due if entry[0] > self.now_ms]
            for _, run in ready:
                run()  # type: ignore[operator]
            if self._tick is not None and self._next_tick_ms <= self.now_ms:
                self._next_tick_ms = self.now_ms + (self.tick_interval_ms or 1)
                self._tick()  # type: ignore[operator]
        self.now_ms = target


@pytest.fixture
def loop() -> Loop:
    return Loop()


@pytest.fixture
def timeline(
    document: AnalysisDocument, player: FakePlayback, loop: Loop
) -> WorkspaceViewModel:
    model = WorkspaceViewModel(
        document, player, schedule=loop.schedule, clock=loop.clock, ticker=loop
    )
    loop.advance(PRIMING_MS * 2)
    player.set_duration(VIDEO_DURATION_MS)
    return model


def ranges(workspace: WorkspaceViewModel) -> tuple:
    return workspace.rangeModel.rows()


def a_clip(document: AnalysisDocument, start_ms: int, end_ms: int, *, name: str = "Tor"):
    analysis = document.analysis
    return analysis.add_clip(analysis.source_videos[0].id, name, start_ms, end_ms)


# --- What the timeline draws -------------------------------------------------


def test_the_timeline_shows_the_clips_of_the_active_source_video(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    a_clip(document, 60_000, 70_000, name="Gegenstoss")
    timeline.refresh()

    assert [
        (row["startMs"], row["endMs"], row["title"]) for row in ranges(timeline)
    ] == [(60_000, 70_000, "Gegenstoss")]


def test_a_clip_of_another_source_video_is_not_on_this_timeline(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    """One timeline, one time scale: the Active Source video's (ADR 0006)."""

    analysis = document.analysis
    second = analysis.add_source_video("Halbzeit 2", "/videos/halbzeit-2.mp4")
    analysis.add_clip(second.id, "Tor", 1_000, 2_000)
    timeline.refresh()

    assert ranges(timeline) == ()


def test_the_ranges_read_in_the_order_they_happen(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    a_clip(document, 120_000, 130_000, name="Zweiter")
    a_clip(document, 20_000, 30_000, name="Erster")
    timeline.refresh()

    assert [row["title"] for row in ranges(timeline)] == ["Erster", "Zweiter"]


def test_a_range_carries_its_category_colour(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    analysis = document.analysis
    category = analysis.add_category("Tore", color="#E2564A")
    clip = a_clip(document, 10_000, 20_000)
    analysis.update_clip(clip.id, category_id=category.id)
    timeline.refresh()

    assert ranges(timeline)[0]["color"] == "#E2564A"


def test_a_clip_with_no_category_leaves_its_colour_to_the_theme(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    """The one place a colour is written down stays `Theme.qml`."""

    a_clip(document, 10_000, 20_000)
    timeline.refresh()

    assert ranges(timeline)[0]["color"] == ""


def test_an_analysis_with_no_source_video_has_nothing_to_draw(
    player: FakePlayback, loop: Loop
) -> None:
    workspace = WorkspaceViewModel(
        AnalysisDocument.new("Leer"),
        player,
        schedule=loop.schedule,
        clock=loop.clock,
        ticker=loop,
    )

    assert workspace.rangeModel.rows() == ()


# --- The ruler ---------------------------------------------------------------


def test_the_ruler_is_laid_out_for_the_width_the_track_got(
    timeline: WorkspaceViewModel,
) -> None:
    timeline.layoutRuler(1_200, VIDEO_DURATION_MS)

    labels = [row["label"] for row in timeline.rulerModel.rows() if row["label"]]
    assert labels[:2] == ["00:00", "05:00"]


def test_a_narrower_track_is_ruled_more_coarsely(
    timeline: WorkspaceViewModel,
) -> None:
    timeline.layoutRuler(1_200, VIDEO_DURATION_MS)
    wide = len(timeline.rulerModel.rows())

    timeline.layoutRuler(400, VIDEO_DURATION_MS)

    assert len(timeline.rulerModel.rows()) < wide


def test_the_ruler_is_redrawn_when_the_media_reports_its_real_length(
    timeline: WorkspaceViewModel, player: FakePlayback
) -> None:
    """The length arrives after the first layout, and the scale changes."""

    timeline.layoutRuler(1_200, VIDEO_DURATION_MS)

    player.set_duration(4 * 60_000)

    labels = [row["label"] for row in timeline.rulerModel.rows() if row["label"]]
    assert labels[:2] == ["00:00", "00:15"]


def test_the_hover_tooltip_reads_the_time_the_rest_of_the_interface_reads(
    timeline: WorkspaceViewModel,
) -> None:
    assert timeline.timeText(3_723_000) == timecode.clock(3_723_000)


# --- Selection ---------------------------------------------------------------


def test_clicking_a_range_selects_its_clip_without_moving_the_playhead(
    timeline: WorkspaceViewModel, document: AnalysisDocument, player: FakePlayback
) -> None:
    """ADR 0006: selection never seeks to the Clip's start."""

    clip = a_clip(document, 600_000, 620_000)
    timeline.refresh()
    player.seek(10_000)

    timeline.selectClip(str(clip.id))

    assert timeline.selectedClipId == str(clip.id)
    assert timeline.positionMs == 10_000
    assert player.position() == 10_000


def test_the_selected_range_is_the_one_the_timeline_draws_as_selected(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    first = a_clip(document, 10_000, 20_000, name="Erster")
    a_clip(document, 30_000, 40_000, name="Zweiter")
    timeline.refresh()

    timeline.selectClip(str(first.id))

    assert [row["selected"] for row in ranges(timeline)] == [True, False]


def test_selecting_nothing_clears_the_selection(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    clip = a_clip(document, 10_000, 20_000)
    timeline.refresh()
    timeline.selectClip(str(clip.id))

    timeline.selectClip("")

    assert timeline.selectedClipId == ""
    assert [row["selected"] for row in ranges(timeline)] == [False]


def test_selecting_a_clip_that_is_gone_selects_nothing(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    clip = a_clip(document, 10_000, 20_000)
    timeline.refresh()
    timeline.selectClip(str(clip.id))

    document.analysis.remove_clip(clip.id)
    timeline.selectClip(str(clip.id))

    assert timeline.selectedClipId == ""


def test_a_selection_tells_the_interface_something_changed(
    timeline: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    clip = a_clip(document, 10_000, 20_000)
    timeline.refresh()
    changed: list[str] = []
    timeline.selectionChanged.connect(lambda: changed.append(timeline.selectedClipId))

    timeline.selectClip(str(clip.id))
    timeline.selectClip(str(clip.id))

    assert changed == [str(clip.id)]


def test_double_clicking_a_range_seeks_to_the_clip_start(
    timeline: WorkspaceViewModel, document: AnalysisDocument, player: FakePlayback
) -> None:
    """The second half of the ADR's grammar, and the only part that seeks."""

    clip = a_clip(document, 600_000, 620_000)
    timeline.refresh()

    timeline.seek(clip.start_ms)

    assert player.position() == 600_000
    assert timeline.positionMs == 600_000


# --- A playhead that does not step -------------------------------------------


def test_the_playhead_moves_between_the_positions_the_player_reports(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    """The player speaks about sixteen times a second; the playhead does not."""

    timeline.playPause()
    player.seek(10_000)

    loop.advance(40)

    assert timeline.positionMs == pytest.approx(10_040, abs=2)


def test_the_playhead_is_redrawn_far_more_often_than_the_player_speaks(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    timeline.playPause()
    player.seek(0)
    redraws: list[int] = []
    timeline.playbackChanged.connect(lambda: redraws.append(timeline.positionMs))

    loop.advance(1_000)

    assert len(redraws) >= 30
    assert redraws == sorted(redraws)


def test_a_paused_playhead_stands_still(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    player.seek(10_000)

    loop.advance(500)

    assert timeline.positionMs == 10_000
    assert loop.ticking is False


def test_pausing_stops_the_playhead_where_it_had_got_to(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    timeline.playPause()
    player.seek(10_000)
    loop.advance(200)

    timeline.playPause()
    loop.advance(500)

    assert timeline.positionMs == pytest.approx(10_200, abs=20)
    assert loop.ticking is False


def test_the_playhead_moves_at_the_speed_the_video_is_playing_at(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    timeline.setRateIndex(PLAYBACK_RATES.index(2.0))
    timeline.playPause()
    player.seek(10_000)

    loop.advance(100)

    assert timeline.positionMs == pytest.approx(10_200, abs=4)


def test_the_playhead_never_runs_past_the_end_of_the_video(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    timeline.playPause()
    player.seek(VIDEO_DURATION_MS - 10)

    loop.advance(1_000)

    assert timeline.positionMs == VIDEO_DURATION_MS


def test_the_playhead_never_steps_backwards_when_a_report_lands_behind_it(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    """Reports arrive late; a playhead that snapped back would stutter."""

    timeline.playPause()
    player.seek(10_000)
    loop.advance(50)
    shown = timeline.positionMs

    player.seek(10_020)

    assert timeline.positionMs >= shown


def test_a_seek_backwards_while_playing_moves_the_playhead_back(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    """The floor that stops a stutter must not swallow a real seek."""

    timeline.playPause()
    player.seek(600_000)
    loop.advance(50)

    player.seek(10_000)

    assert timeline.positionMs == pytest.approx(10_000, abs=4)


def test_a_player_that_stops_speaking_does_not_run_the_playhead_away(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    """Interpolation fills a gap between reports; it does not replace them."""

    timeline.playPause()
    player.seek(10_000)

    loop.advance(10_000)

    assert timeline.positionMs <= 10_000 + MAXIMUM_INTERPOLATION_MS


def test_the_playhead_does_not_move_for_the_priming_play_nobody_asked_for(
    document: AnalysisDocument, player: FakePlayback, loop: Loop
) -> None:
    workspace = WorkspaceViewModel(
        document, player, schedule=loop.schedule, clock=loop.clock, ticker=loop
    )

    loop.advance(PRIMING_MS // 2)

    assert workspace.positionMs == 0
    assert loop.ticking is False


# --- A scrub the picture can follow ------------------------------------------


def test_the_first_scrub_of_a_drag_reaches_the_player_at_once(
    timeline: WorkspaceViewModel, player: FakePlayback
) -> None:
    timeline.scrubTo(60_000)

    assert player.position() == 60_000


def test_a_fast_drag_is_throttled_to_what_the_player_can_follow(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    """Beyond about twenty a second the player coalesces seeks and stalls."""

    seeks: list[int] = []
    player.position_changed.connect(seeks.append)

    for step in range(200):
        timeline.scrubTo(step * 1_000)
        loop.advance(5)
    timeline.endScrub()

    assert len(seeks) <= SCRUB_SEEKS_PER_SECOND + 2


def test_a_throttled_drag_still_moves_the_playhead_with_the_pointer(
    timeline: WorkspaceViewModel, player: FakePlayback
) -> None:
    """The picture lags a frame behind the pointer; the playhead does not."""

    timeline.scrubTo(60_000)
    timeline.scrubTo(61_000)

    assert player.position() == 60_000
    assert timeline.positionMs == 61_000


def test_only_the_place_the_pointer_ended_up_is_seeked_to(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    timeline.scrubTo(60_000)
    timeline.scrubTo(61_000)
    timeline.scrubTo(62_000)

    loop.advance(SCRUB_INTERVAL_MS)

    assert player.position() == 62_000


def test_a_slow_drag_is_not_throttled_at_all(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    seeks: list[int] = []
    player.position_changed.connect(seeks.append)

    for step in range(4):
        timeline.scrubTo(step * 1_000)
        loop.advance(SCRUB_INTERVAL_MS * 2)

    assert seeks == [0, 1_000, 2_000, 3_000]


def test_letting_go_lands_the_video_exactly_where_the_drag_ended(
    timeline: WorkspaceViewModel, player: FakePlayback
) -> None:
    """A held seek that the release discarded would leave the wrong frame."""

    timeline.scrubTo(60_000)
    timeline.scrubTo(61_000)

    timeline.endScrub()

    assert player.position() == 61_000


def test_letting_go_of_a_drag_that_held_nothing_changes_nothing(
    timeline: WorkspaceViewModel, player: FakePlayback
) -> None:
    timeline.scrubTo(60_000)

    timeline.endScrub()

    assert player.position() == 60_000


def test_the_held_seek_is_made_once_and_not_again(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    seeks: list[int] = []
    player.position_changed.connect(seeks.append)

    timeline.scrubTo(60_000)
    timeline.scrubTo(61_000)
    timeline.endScrub()
    loop.advance(SCRUB_INTERVAL_MS * 2)

    assert seeks == [60_000, 61_000]


def test_nothing_the_timeline_does_dirties_the_analysis(
    timeline: WorkspaceViewModel, document: AnalysisDocument, loop: Loop
) -> None:
    assert document.dirty is False

    timeline.layoutRuler(1_200, VIDEO_DURATION_MS)
    timeline.scrubTo(60_000)
    timeline.scrubTo(61_000)
    loop.advance(SCRUB_INTERVAL_MS)
    timeline.endScrub()
    timeline.selectClip("")

    assert document.dirty is False


def test_a_seek_overtakes_a_scrub_the_throttle_was_still_holding(
    timeline: WorkspaceViewModel, player: FakePlayback, loop: Loop
) -> None:
    """Double-clicking a range is exactly this: a held press, then a seek.

    A held seek that arrived afterwards would take the video back to where the
    pointer used to be, a moment after it had been asked for somewhere else.
    """

    timeline.scrubTo(60_000)
    timeline.scrubTo(61_000)

    timeline.seek(100_000)
    loop.advance(SCRUB_INTERVAL_MS * 2)

    assert player.position() == 100_000


def test_the_playhead_uses_the_event_loop_when_nobody_supplies_a_ticker(
    document: AnalysisDocument, player: FakePlayback
) -> None:
    """The injected heartbeat is for tests; the application gets a real one."""

    workspace = WorkspaceViewModel(document, player)
    loop = QEventLoop()
    QTimer.singleShot(PRIMING_MS * 2, loop.quit)
    loop.exec()

    workspace.playPause()
    player.seek(10_000)
    waited = QEventLoop()
    QTimer.singleShot(120, waited.quit)
    waited.exec()

    assert workspace.positionMs > 10_000

    workspace.playPause()
