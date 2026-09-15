"""The presentation state QML reads, and the only place it can change it.

QML gets properties, signals and slots. It never sees an `Analysis`, a `Clip`
or the `Playback`, so a delegate cannot reach past the interface into the
domain, and every rule about what an action means — which playback rate is
selected, how a position is written down, what pressing play does while the
video surface is still being primed — stays here in Python where a test can
reach it without a window.

What this carries today is the transport, the video surface, the timeline, and
the document commands — New, Open, Save, Save As and Close — which it drives
through `application_workflow` rather than deciding anything about them itself.
The Clip list and the Clip editor arrive with the tickets that own them, each
extending this same seam.
"""

from __future__ import annotations

from collections.abc import Callable
import time
from typing import Protocol
from uuid import UUID

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot

import timecode
from analysis import AnalysisDocument, UnsavedChangesChoice
from application_workflow import (
    UNTITLED_ANALYSIS_TITLE,
    ApplicationWorkflow,
    WorkflowPresenter,
)
from playback import Playback
from timeline_models import RulerModel, TimelineRangeModel


#: The speeds the segmented control offers, in the order it draws them.
PLAYBACK_RATES = (0.5, 1.0, 1.5, 2.0)

#: The speed a Source video opens at, and the one an unrecognised rate reads as.
NORMAL_RATE = 1.0

#: How long the video surface is played for before being put back.
#:
#: Long enough that Qt's FFmpeg backend has decoded and presented a frame,
#: short enough that nobody sees the picture move. The prototype measured this
#: on macOS; it is a decoder warm-up rather than a wall-clock guarantee, and a
#: backend that needs longer shows its first frame late rather than never.
PRIMING_MS = 140

#: How often the interpolated playhead is recomputed, in milliseconds.
#:
#: `QMediaPlayer` reports a position roughly sixteen times a second and offers
#: no way to ask for more, so a playhead bound straight to it visibly steps.
#: Redrawing at about sixty a second is what makes it move instead.
INTERPOLATION_INTERVAL_MS = 16

#: How far ahead of the last reported position the playhead may be carried.
#:
#: Interpolation fills the gap between two reports; it does not replace them.
#: A player that stops reporting — buffering, a decoder stall, the end of the
#: file — must leave the playhead standing rather than run it off the track.
MAXIMUM_INTERPOLATION_MS = 250

#: How far behind the drawn playhead a report may land and still be smoothed.
#:
#: Reports arrive late rather than early, so one that is slightly behind what
#: is drawn is the same playback, not a jump. Snapping back to it would be the
#: stutter interpolation exists to remove; anything further is a real seek.
LATE_REPORT_TOLERANCE_MS = 150

#: How many seeks a second a scrub may ask the media player for.
#:
#: Beyond about twenty the player coalesces them and the picture stops
#: following the pointer. Measured identically on Qt Widgets and Qt Quick, so
#: it is a property of the media player rather than of either surface.
SCRUB_SEEKS_PER_SECOND = 20

#: The shortest gap between two scrub seeks, from the rate above.
SCRUB_INTERVAL_MS = 1_000 // SCRUB_SEEKS_PER_SECOND

#: Schedules work for later. Injectable so that priming is testable as
#: behaviour rather than as a wait.
Schedule = Callable[[int, Callable[[], None]], None]

#: Reads a monotonic time in seconds. Injectable for the same reason.
Clock = Callable[[], float]


class Ticker(Protocol):
    """Runs something repeatedly, until asked to stop.

    The playhead's own heartbeat, kept behind an interface so that "the
    playhead moved between two reports" is a test rather than a wait.
    """

    def start(self, interval_ms: int, run: Callable[[], None]) -> None: ...

    def stop(self) -> None: ...


def _after(delay_ms: int, run: Callable[[], None]) -> None:
    QTimer.singleShot(delay_ms, run)


class _NobodyToAsk:
    """The presenter a workspace gets when it was built without one.

    A workspace can be built for the transport alone — the playback tests do
    exactly that — and such a workspace has no window to put a question in. It
    therefore answers every question the only way that cannot lose an
    analyst's work: it refuses.
    """

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        return UnsavedChangesChoice.CANCEL

    def choose_analysis_to_open(self) -> str | None:
        return None

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        return None

    def choose_source_video(self) -> str | None:
        return None

    def report_failure(self, title: str, message: str) -> None:
        return None


class _TimerTicker:
    """The real heartbeat: a repeating `QTimer` on the event loop."""

    def __init__(self, parent: QObject) -> None:
        self._run: Callable[[], None] | None = None
        self._timer = QTimer(parent)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._beat)

    def start(self, interval_ms: int, run: Callable[[], None]) -> None:
        self._run = run
        self._timer.start(interval_ms)

    def stop(self) -> None:
        self._timer.stop()
        self._run = None

    def _beat(self) -> None:
        if self._run is not None:
            self._run()


class WorkspaceViewModel(QObject):
    """One facade over the Analysis document and the playback of its video."""

    documentChanged = Signal()
    playbackChanged = Signal()
    selectionChanged = Signal()

    def __init__(
        self,
        document: AnalysisDocument,
        playback: Playback,
        parent: QObject | None = None,
        *,
        schedule: Schedule = _after,
        presenter: WorkflowPresenter | None = None,
        clock: Clock = time.monotonic,
        ticker: Ticker | None = None,
    ) -> None:
        super().__init__(parent)
        self._workflow = ApplicationWorkflow(
            presenter if presenter is not None else _NobodyToAsk(),
            document=document,
            on_analysis_replaced=self._analysis_replaced,
            on_document_changed=self._document_reported,
        )
        self._document = document
        self._playback = playback
        self._playback.setParent(self)
        self._schedule = schedule
        self._clock = clock
        self._ticker: Ticker = _TimerTicker(self) if ticker is None else ticker

        self._active_source_id: UUID | None = None
        self._selected_clip_id: UUID | None = None
        self._position_ms = 0
        self._duration_ms = 0
        self._priming = False
        self._muted_before_priming = False

        # The playhead, between two things the player said.
        self._position_at = clock()
        self._position_floor_ms = 0
        self._following = False

        # The scrub, and what the throttle is holding back.
        self._last_seek_at = float("-inf")
        self._held_scrub_ms: int | None = None
        self._flush_scheduled = False

        # What the timeline draws. Both are projections of the Analysis and
        # of the Active Source video's length; neither is ever handed a Clip.
        self._ranges = TimelineRangeModel(self)
        self._ruler = RulerModel(self)
        self._ruler_width_px = 0.0

        self._playback.position_changed.connect(self._position_reported)
        self._playback.duration_changed.connect(self._duration_reported)
        self._playback.playing_changed.connect(self._playing_reported)

        sources = self._document.analysis.source_videos
        if sources:
            self._activate_source(sources[0].id)

    # --- What QML is allowed to see ---------------------------------------

    @Property(bool, notify=documentChanged)
    def hasVideo(self) -> bool:
        """Whether there is an Active Source video to act on at all."""

        return self._active_source_id is not None

    @Property(int, notify=playbackChanged)
    def positionMs(self) -> int:
        """Where the playhead is *now*, not where the player last said it was.

        The difference is the whole of the smooth-playhead fix: between two
        reports this reads ahead of the player by however long ago it spoke.
        """

        return self._current_position_ms()

    @Property(int, notify=playbackChanged)
    def durationMs(self) -> int:
        return self._duration_ms

    @Property(str, notify=playbackChanged)
    def positionText(self) -> str:
        return timecode.clock(self._current_position_ms())

    @Property(str, notify=playbackChanged)
    def durationText(self) -> str:
        return timecode.clock(self._duration_ms)

    @Property(bool, notify=playbackChanged)
    def playing(self) -> bool:
        # Priming is a decoder detail. Reporting it would flicker the play
        # control on every newly opened Analysis.
        return False if self._priming else self._playback.is_playing()

    @Property(bool, notify=playbackChanged)
    def muted(self) -> bool:
        return self._muted_before_priming if self._priming else self._playback.is_muted()

    @Property(float, notify=playbackChanged)
    def volume(self) -> float:
        return self._playback.volume()

    @Property(float, notify=playbackChanged)
    def playbackRate(self) -> float:
        return self._playback.playback_rate()

    @Property(list, constant=True)
    def playbackRates(self) -> list:
        return [f"{rate:g}x" for rate in PLAYBACK_RATES]

    @Property(int, notify=playbackChanged)
    def playbackRateIndex(self) -> int:
        """Which speed is selected.

        Deciding that is not the segmented control's business: it draws
        whichever option this names.
        """

        rate = self._playback.playback_rate()
        for index, candidate in enumerate(PLAYBACK_RATES):
            if abs(candidate - rate) < 0.001:
                return index
        return PLAYBACK_RATES.index(NORMAL_RATE)

    # --- What the timeline draws ------------------------------------------

    @Property(QObject, constant=True)
    def rangeModel(self) -> QObject:
        """The Clip ranges of the Active Source video, in milliseconds."""

        return self._ranges

    @Property(QObject, constant=True)
    def rulerModel(self) -> QObject:
        """The ruler's marks, already chosen for the width the track got."""

        return self._ruler

    @Property(str, notify=selectionChanged)
    def selectedClipId(self) -> str:
        return "" if self._selected_clip_id is None else str(self._selected_clip_id)

    # --- What QML is allowed to do ----------------------------------------

    @Slot(QObject)
    def attachVideoOutput(self, video_output: QObject) -> None:
        """Hand the Qt Quick video item to the existing playback seam.

        `Playback.set_video_output` already takes a plain `QObject`, and a
        `VideoOutput` carries the `videoSink` property `QMediaPlayer` looks
        for, so the Qt Quick surface attaches through the seam unmodified.
        """

        self._playback.set_video_output(video_output)

    @Slot()
    def playPause(self) -> None:
        if self._priming:
            # The analyst got there first. Keep the play that priming started
            # rather than pausing something they never saw start.
            self._end_priming()
            return
        self._playback.play_pause()

    @Slot()
    def stepForward(self) -> None:
        self._playback.step_forward()

    @Slot()
    def stepBackward(self) -> None:
        self._playback.step_backward()

    @Slot()
    def jumpForward(self) -> None:
        self._playback.jump_forward()

    @Slot()
    def jumpBackward(self) -> None:
        self._playback.jump_backward()

    @Slot(int)
    def seek(self, position_ms: int) -> None:
        self._seek_now(int(position_ms))

    # --- The one seek surface ---------------------------------------------

    @Slot(float, float)
    def layoutRuler(self, width_px: float, duration_ms: float) -> None:
        """Rule the track for the width it actually got.

        Which interval stays legible at a given width is arithmetic about the
        recording rather than about the drawing, so the timeline reports its
        width and is given marks back.
        """

        self._ruler_width_px = float(width_px)
        self._ruler.layout(int(duration_ms), self._ruler_width_px)

    @Slot(int, result=str)
    def timeText(self, position_ms: int) -> str:
        """The hover tooltip's timecode, written where every other one is."""

        return timecode.clock(int(position_ms))

    @Slot(str)
    def selectClip(self, clip_id: str) -> None:
        """Select a Clip without seeking.

        ADR 0006: clicking a range selects it *without moving the playhead to
        its start*. The scrub the same click performs is the timeline's, and
        it goes where the pointer is, not where the Clip begins.
        """

        identity = _as_uuid(clip_id)
        known = {clip.id for clip in self._document.analysis.clips}
        if identity not in known:
            identity = None
        if identity == self._selected_clip_id:
            return
        self._selected_clip_id = identity
        self._refresh_ranges()
        self.selectionChanged.emit()

    @Slot(int)
    def scrubTo(self, position_ms: int) -> None:
        """Follow a drag, at a rate the media player can actually follow.

        Asked for more than about twenty seeks a second, `QMediaPlayer`
        coalesces them and the picture stops moving with the pointer — the
        defect this throttle exists to fix. Only the newest position is ever
        held, so the video lands where the pointer went rather than trailing
        it through every position it passed through on the way.

        The playhead itself is not throttled. It follows the pointer at once,
        because a held seek is a late *picture*, not a late playhead.
        """

        target = int(position_ms)
        since_ms = (self._clock() - self._last_seek_at) * 1_000
        if since_ms >= SCRUB_INTERVAL_MS and self._held_scrub_ms is None:
            self._seek_now(target)
            return

        self._held_scrub_ms = target
        self._show_position(target)
        if not self._flush_scheduled:
            self._flush_scheduled = True
            self._schedule(max(0, int(SCRUB_INTERVAL_MS - since_ms)), self._flush_scrub)

    @Slot()
    def endScrub(self) -> None:
        """Land the video exactly where the drag ended.

        A held seek that the release simply dropped would leave the picture on
        the last position the throttle let through rather than on the one the
        analyst chose.
        """

        self._flush_scrub()

    @Slot()
    def refresh(self) -> None:
        """Re-project the Analysis onto the timeline.

        Every Clip-changing action arrives with the surface that owns it; this
        is what those tell the timeline, and what a test uses to say that the
        Analysis changed underneath it.
        """

        self._refresh_ranges()
        self.documentChanged.emit()

    @Slot()
    def toggleMuted(self) -> None:
        self._playback.toggle_muted()
        self.playbackChanged.emit()

    @Slot(float)
    def setVolume(self, volume: float) -> None:
        """Set the level. Turning the bench audio down is not muting it."""

        self._playback.set_volume(float(volume))
        self.playbackChanged.emit()

    @Slot(int)
    def setRateIndex(self, index: int) -> None:
        if 0 <= index < len(PLAYBACK_RATES):
            self._playback.set_playback_rate(PLAYBACK_RATES[index])
            self.playbackChanged.emit()

    # --- The Analysis this window is about --------------------------------
    #
    # The commands themselves belong to `application_workflow`, which decides
    # what each one means and when a person has to be asked. What lives here
    # is the asking: a slot QML can call, and the two values the toolbar and
    # the window title draw from.

    @Property(str, notify=documentChanged)
    def analysisTitle(self) -> str:
        """What the toolbar calls this Analysis, named even when it is not."""

        return self._workflow.analysis.title.strip() or UNTITLED_ANALYSIS_TITLE

    @Property(bool, notify=documentChanged)
    def dirty(self) -> bool:
        return self._workflow.document.dirty

    @Property(str, notify=documentChanged)
    def windowTitle(self) -> str:
        """The Analysis and its unsaved state, as the workflow writes them."""

        return self._workflow.window_title

    @Slot(result=bool)
    def newAnalysis(self) -> bool:
        return self._workflow.new_analysis()

    @Slot(result=bool)
    def openAnalysis(self) -> bool:
        return self._workflow.open_analysis()

    @Slot(result=bool)
    def saveAnalysis(self) -> bool:
        return self._workflow.save()

    @Slot(result=bool)
    def saveAnalysisAs(self) -> bool:
        return self._workflow.save_as()

    @Slot(result=bool)
    def requestClose(self) -> bool:
        """Whether the window may close, asking about unsaved work first.

        Every way out of the application arrives here, so the question is
        asked once and answered in one place.
        """

        return self._workflow.may_replace_analysis()

    def _analysis_replaced(self) -> None:
        """A different Analysis is open now; drop everything transient."""

        self._document = self._workflow.document
        self._playback.pause()
        self._playback.unload()
        # Whatever was being primed is gone with the video it belonged to.
        self._priming = False
        self._active_source_id = None
        self._position_ms = 0
        self._duration_ms = 0
        sources = self._document.analysis.source_videos
        if sources:
            self._activate_source(sources[0].id)
        self.playbackChanged.emit()

    def _document_reported(self) -> None:
        """The Analysis or its saved state changed; redraw what says so."""

        self.documentChanged.emit()

    # --- The Active Source video ------------------------------------------

    def _activate_source(self, source_id: UUID) -> None:
        self._active_source_id = source_id
        video = self._document.analysis.source_video(source_id)
        self._playback.load(video.location)
        self._refresh_ranges()
        if video.duration_ms is not None:
            self._duration_reported(video.duration_ms)
        self._prime_video_surface()
        self.documentChanged.emit()

    def _refresh_ranges(self) -> None:
        self._ranges.refresh(
            self._document.analysis,
            source_video_id=self._active_source_id,
            selected_clip_id=self._selected_clip_id,
        )

    def _prime_video_surface(self) -> None:
        """Make a newly loaded Source video show a frame instead of black.

        Qt's FFmpeg backend hands the video sink nothing until playback has
        actually started once: seeking a stopped player moves the position and
        decodes no frame, so an Analysis opens black until somebody presses
        play. The surface is therefore primed with a very short play and then
        put back exactly where it was — muted, because a blip of match audio
        is not a first frame, and without telling the interface, because a
        transport that flickered would be a second defect in place of the
        first.

        This is a property of `QMediaPlayer` rather than of QML — Qt Widgets
        meets it too — and it is done entirely through the public seam.
        """

        if self._priming or not self._playback.is_loaded():
            return
        self._priming = True
        self._muted_before_priming = self._playback.is_muted()
        self._playback.set_muted(True)
        self._playback.play()
        self._schedule(PRIMING_MS, self._finish_priming)

    def _finish_priming(self) -> None:
        if not self._priming:
            return
        resume_at = self._position_ms
        self._playback.pause()
        self._end_priming()
        self._playback.seek(resume_at)

    def _end_priming(self) -> None:
        """Stop priming and give the analyst back the sound they chose."""

        self._priming = False
        self._playback.set_muted(self._muted_before_priming)
        self._follow_playback()
        self.playbackChanged.emit()

    # --- Seeking ----------------------------------------------------------

    def _seek_now(self, position_ms: int) -> None:
        """Ask the player for a position, and remember when we asked.

        Any seek the throttle was still holding is dropped: it belongs to a
        drag this seek has overtaken, and letting it arrive afterwards would
        take the video back to where the pointer used to be. Double-clicking a
        range is exactly that case — the press that selected the Clip is still
        held when the second click asks for the Clip's start.
        """

        self._held_scrub_ms = None
        self._last_seek_at = self._clock()
        self._playback.seek(position_ms)

    def _flush_scrub(self) -> None:
        """Make the seek the throttle held back, if it is still held."""

        self._flush_scheduled = False
        if self._held_scrub_ms is None:
            return
        target, self._held_scrub_ms = self._held_scrub_ms, None
        self._seek_now(target)

    # --- A playhead that moves between two reports -------------------------

    def _current_position_ms(self) -> int:
        """Where the playhead is, reported position plus elapsed playback."""

        position = self._position_ms
        if self._following:
            elapsed_ms = max(0.0, self._clock() - self._position_at) * 1_000
            carried = min(
                elapsed_ms * self._playback.playback_rate(), MAXIMUM_INTERPOLATION_MS
            )
            position = max(position + int(carried), self._position_floor_ms)
            if self._duration_ms > 0:
                # Interpolation may not carry the playhead past the end of the
                # recording. A position the player itself reports is taken as
                # it comes: the media knows its own length better than we do.
                position = min(position, self._duration_ms)
        return max(0, position)

    def _show_position(self, position_ms: int) -> None:
        """Put the playhead somewhere and start interpolating from there."""

        self._position_ms = max(0, int(position_ms))
        self._position_at = self._clock()
        self._position_floor_ms = self._position_ms
        self.playbackChanged.emit()

    def _follow_playback(self) -> None:
        """Start or stop the heartbeat, to match what the player is doing."""

        following = self._playback.is_playing() and not self._priming
        if following == self._following:
            return
        if following:
            self._position_at = self._clock()
            self._position_floor_ms = self._position_ms
            self._following = True
            self._ticker.start(INTERPOLATION_INTERVAL_MS, self._interpolate)
        else:
            # Stop where the playhead was drawn rather than where the player
            # last spoke, so pausing does not twitch backwards.
            self._position_ms = self._current_position_ms()
            self._position_floor_ms = self._position_ms
            self._following = False
            self._ticker.stop()

    def _interpolate(self) -> None:
        """One heartbeat: nothing new was reported, but time passed."""

        if not self._following:
            self._ticker.stop()
            return
        self._position_floor_ms = self._current_position_ms()
        self.playbackChanged.emit()

    # --- What the player reports ------------------------------------------

    def _position_reported(self, position_ms: int) -> None:
        if self._priming:
            # The playhead does not move for a play nobody asked for.
            return
        reported = max(0, int(position_ms))
        drawn = self._current_position_ms()
        self._position_ms = reported
        self._position_at = self._clock()
        # A report that lands just behind the drawn playhead is the same
        # playback arriving late; one further behind is a real seek.
        self._position_floor_ms = (
            drawn
            if self._following and 0 <= drawn - reported <= LATE_REPORT_TOLERANCE_MS
            else reported
        )
        self.playbackChanged.emit()

    def _duration_reported(self, duration_ms: int) -> None:
        """Trust the Analysis until the media reports something better."""

        if duration_ms <= 0:
            return
        self._duration_ms = int(duration_ms)
        if self._ruler_width_px > 0:
            # The length is what the ruler is a ruler of: a scale that arrived
            # late still has to reach the marks.
            self._ruler.layout(self._duration_ms, self._ruler_width_px)
        self.playbackChanged.emit()

    def _playing_reported(self, _playing: bool) -> None:
        if self._priming:
            return
        self._follow_playback()
        self.playbackChanged.emit()


def _as_uuid(value: str) -> UUID | None:
    """Read an identity QML carries as a string, or report that it is not one."""

    try:
        return UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return None
