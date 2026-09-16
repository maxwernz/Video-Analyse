"""The presentation state QML reads, and the only place it can change it.

QML gets properties, signals and slots. It never sees an `Analysis`, a `Clip`
or the `Playback`, so a delegate cannot reach past the interface into the
domain, and every rule about what an action means — which playback rate is
selected, how a position is written down, what pressing play does while the
video surface is still being primed — stays here in Python where a test can
reach it without a window.

What this carries today is the transport, the video surface, the timeline, the
sidebar's two lists, the document commands — New, Open, Save, Save As and
Close — which it drives through `application_workflow` rather than deciding
anything about them itself, and the Clip-editing state: the Pending Clip, the
draft held apart from the Analysis while it is edited, and the two ways out of
it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import time
from typing import Protocol
from uuid import UUID

from PySide6.QtCore import QEvent, Property, QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QKeyEvent, QKeySequence

import menu_bar
import timecode
from analysis import AnalysisDocument, SourceVideo, UnsavedChangesChoice
from application_workflow import (
    UNTITLED_ANALYSIS_TITLE,
    ApplicationWorkflow,
    WorkflowPresenter,
)
from clip_editor import (
    END,
    END_BEFORE_START,
    NOT_A_TIME,
    START,
    CategoryModel,
    ClipDraft,
)
from playback import Playback
from sidebar_models import ClipListModel, SourceVideoModel
from timeline_models import RulerModel, TimelineRangeModel


#: The sidebar's two tabs, and the one it opens on.
#:
#: Which one is showing is a property of this session rather than of the
#: Analysis: it lives here and is never written to a file, because reopening
#: an Analysis on a tab somebody left it on a week ago would be a surprise
#: rather than a memory.
SIDEBAR_TABS = ("clips", "videos")


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


class _MenuShortcutFilter(QObject):
    """A window-level key listener for the commands in ``menu_bar.MENUS``."""

    def __init__(self, workspace: "WorkspaceViewModel") -> None:
        super().__init__(workspace)
        self._workspace = workspace

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.KeyPress or bool(watched.property("nativeMenuBar")):
            return False
        if not isinstance(event, QKeyEvent):
            return False
        if not self._workspace.runMenuShortcut(
            int(event.key()), event.modifiers().value
        ):
            return False
        event.accept()
        return True


class WorkspaceViewModel(QObject):
    """One facade over the Analysis document and the playback of its video."""

    documentChanged = Signal()
    playbackChanged = Signal()
    selectionChanged = Signal()
    sidebarTabChanged = Signal()
    pendingChanged = Signal()
    draftChanged = Signal()
    editingChanged = Signal()

    #: The Close command, which is a request of the *window* rather than of
    #: the Analysis: every way out arrives at `requestClose`, so the
    #: unsaved-changes question is asked once and in one place.
    closeRequested = Signal()

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
        self._menu_shortcut_filter: _MenuShortcutFilter | None = None
        self._workflow = ApplicationWorkflow(
            presenter if presenter is not None else _NobodyToAsk(),
            document=document,
            on_analysis_replaced=self._analysis_replaced,
            on_document_changed=self._document_reported,
            on_source_video_added=self._source_video_added,
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

        # Which sidebar tab is showing. Transient by construction: there is
        # nowhere for it to be written down but here.
        self._sidebar_tab = SIDEBAR_TABS[0]

        # The Clip being marked, and the one being edited. Neither is part
        # of the Analysis: a Pending Clip is one boundary and an intention,
        # and a draft is a copy, which is why cancelling either costs
        # nothing and needs no undo.
        self._pending_start_ms: int | None = None
        self._draft: ClipDraft | None = None
        self._boundary_error = ""

        # What the timeline and the sidebar draw. All four are projections of
        # the Analysis; none of them is ever handed a Clip.
        self._ranges = TimelineRangeModel(self)
        self._ruler = RulerModel(self)
        self._clips = ClipListModel(self)
        self._sources = SourceVideoModel(self)
        self._categories = CategoryModel(self)
        self._ruler_width_px = 0.0

        self._playback.position_changed.connect(self._position_reported)
        self._playback.duration_changed.connect(self._duration_reported)
        self._playback.playing_changed.connect(self._playing_reported)

        self._refresh_projections()
        sources = self._document.analysis.source_videos
        if sources:
            self._activate_source(sources[0].id)

    @property
    def document(self) -> AnalysisDocument:
        """The Analysis document this view model was built over.

        Not a Qt property: QML never sees an Analysis document, only the
        properties, slots and item models below. This exists for the same
        reason `ApplicationWorkflow.document` does — so a test can inspect
        the Analysis a view model wraps without a window.
        """

        return self._document

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

    # --- What the sidebar draws -------------------------------------------

    @Property(QObject, constant=True)
    def clipModel(self) -> QObject:
        """Every Clip in the Analysis, grouped by Category and formatted."""

        return self._clips

    @Property(QObject, constant=True)
    def sourceModel(self) -> QObject:
        """Every Source video, with the active one marked."""

        return self._sources

    @Property(str, notify=sidebarTabChanged)
    def sidebarTab(self) -> str:
        return self._sidebar_tab

    @Slot(str)
    def setSidebarTab(self, tab: str) -> None:
        """Show the Clips or the Videos. Nothing else may be shown there."""

        if tab not in SIDEBAR_TABS or tab == self._sidebar_tab:
            return
        self._sidebar_tab = tab
        self.sidebarTabChanged.emit()

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
        self._refresh_projections()
        self.selectionChanged.emit()

    @Slot(str)
    def navigateToClip(self, clip_id: str) -> None:
        """Go to a Clip: its Source video, its start, and its selection.

        This is the Clip list's one action, and it is one action rather than
        three: a coach clicking a Clip in the second half expects the second
        half to be playing at that moment, not to be told to pick the video
        first. It is also the one place selection *does* seek, which is why it
        is a different slot from `selectClip` rather than a flag on it — the
        timeline's grammar (ADR 0006) is that clicking a range never moves the
        playhead.
        """

        identity = _as_uuid(clip_id)
        clip = next(
            (clip for clip in self._document.analysis.clips if clip.id == identity),
            None,
        )
        if clip is None:
            return
        if clip.source_video_id != self._active_source_id:
            self._activate_source(clip.source_video_id)
        self.selectClip(str(clip.id))
        # The playhead is put there as well as the player, because a Source
        # video that has just been activated is still being primed, and
        # priming puts the video back where the playhead says it was.
        self._show_position(clip.start_ms)
        self._seek_now(clip.start_ms)

    @Slot(str)
    def selectSourceVideo(self, source_id: str) -> None:
        """Make a Source video the active one, the Videos tab's one action."""

        identity = _as_uuid(source_id)
        known = {video.id for video in self._document.analysis.source_videos}
        if identity is None or identity not in known:
            return
        if identity == self._active_source_id:
            return
        # The timeline is about to be the new video's, and a Clip of the old
        # one has no range on it to stay selected.
        self.selectClip("")
        self._activate_source(identity)

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
        """Re-project the Analysis onto the timeline and the sidebar.

        Every Clip-changing action arrives with the surface that owns it; this
        is what those tell the interface, and what a test uses to say that the
        Analysis changed underneath it.
        """

        self._refresh_projections()
        self.documentChanged.emit()

    @Slot(str)
    def removeClip(self, clip_id: str) -> None:
        """Remove one Clip and redraw the surfaces that named it."""

        identity = _as_uuid(clip_id)
        known = {clip.id for clip in self._document.analysis.clips}
        if identity is None or identity not in known:
            return
        self._document.analysis.remove_clip(identity)
        if identity == self._selected_clip_id:
            self._selected_clip_id = None
            self.selectionChanged.emit()
        self.refresh()

    @Slot(str)
    def removeCategory(self, category_id: str) -> None:
        """Remove a Category; its Clips become uncategorized in the Analysis."""

        identity = _as_uuid(category_id)
        known = {category.id for category in self._document.analysis.categories}
        if identity is None or identity not in known:
            return
        self._document.analysis.remove_category(identity)
        self.refresh()

    @Slot(str)
    def setAnalysisTitle(self, title: str) -> None:
        """Retitle this Analysis without changing its identity."""

        self._document.analysis.set_title(title)
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

    # --- Marking a Clip, and the state that edits one ----------------------
    #
    # One editing state serves both: completing a second boundary and editing
    # an existing Clip open the same form over the same draft, so there is one
    # editor to learn rather than two. Everything below works on that draft;
    # the Analysis hears about it once, when the analyst keeps it.

    @Property(bool, notify=editingChanged)
    def editing(self) -> bool:
        """Whether the workspace is in the Clip-editing state.

        The shell reads this and gives the editor its 360px; the video comes
        back to full size on the way out without anything having to remember
        how big it used to be.
        """

        return self._draft is not None

    @Property(bool, notify=pendingChanged)
    def pendingActive(self) -> bool:
        """Whether one boundary has been marked and the other has not."""

        return self._pending_start_ms is not None

    @Property(int, notify=pendingChanged)
    def pendingStartMs(self) -> int:
        return self._pending_start_ms or 0

    @Property(str, notify=pendingChanged)
    def pendingText(self) -> str:
        """Where the Clip began and how long it is so far.

        Read against a moving playhead, so it is recomputed rather than
        stored: a Pending Clip grows for as long as it is pending.
        """

        if self._pending_start_ms is None:
            return ""
        length_ms = max(0, self._current_position_ms() - self._pending_start_ms)
        return (
            f"Start {timecode.clock(self._pending_start_ms)}"
            f"  ·  {timecode.duration(length_ms)}"
        )

    @Property(str, notify=pendingChanged)
    def markActionText(self) -> str:
        """What the mark action does next, which is not always the same thing."""

        return "Ende setzen" if self._pending_start_ms is not None else "Clip markieren"

    @Property(QObject, constant=True)
    def categoryModel(self) -> QObject:
        """The Categories the editor offers, with the draft's one marked."""

        return self._categories

    @Property(bool, notify=draftChanged)
    def draftIsNew(self) -> bool:
        return self._draft.is_new if self._draft is not None else False

    @Property(str, notify=draftChanged)
    def draftName(self) -> str:
        return self._draft.name if self._draft is not None else ""

    @Property(str, notify=draftChanged)
    def draftNotes(self) -> str:
        return self._draft.notes if self._draft is not None else ""

    @Property(int, notify=draftChanged)
    def draftStartMs(self) -> int:
        return self._draft.start_ms if self._draft is not None else 0

    @Property(int, notify=draftChanged)
    def draftEndMs(self) -> int:
        return self._draft.end_ms if self._draft is not None else 0

    @Property(str, notify=draftChanged)
    def draftStartText(self) -> str:
        """The start, to the millisecond, in the form the field is sized for."""

        return "" if self._draft is None else timecode.precise(self._draft.start_ms)

    @Property(str, notify=draftChanged)
    def draftEndText(self) -> str:
        return "" if self._draft is None else timecode.precise(self._draft.end_ms)

    @Property(str, notify=draftChanged)
    def draftDurationText(self) -> str:
        """How long the Clip is, as the boundaries either side of it move."""

        if self._draft is None:
            return ""
        return timecode.precise_duration(self._draft.length_ms)

    @Property(str, notify=draftChanged)
    def draftCategoryColor(self) -> str:
        """The draft range's colour, or nothing when it has no Category.

        Nothing rather than a grey: what an uncategorised range looks like is
        the timeline's decision and the token spec's value, and this seam does
        not carry a second spelling of it.
        """

        if self._draft is None or self._draft.category_id is None:
            return ""
        return self._document.analysis.category(self._draft.category_id).color

    @Property(str, notify=draftChanged)
    def draftError(self) -> str:
        """Why the Clip cannot be kept as it stands, in the form's own words."""

        if self._draft is None:
            return ""
        return self._boundary_error or self._draft.error

    @Property(bool, notify=draftChanged)
    def draftValid(self) -> bool:
        return self._draft is not None and not self.draftError

    @Slot()
    def markBoundary(self) -> None:
        """Set the first Clip boundary, or complete it and open the editor.

        The second press is the one that changes what the window is: it stops
        the video, because a Clip is edited against a still frame rather than
        against footage running away underneath the form.
        """

        if self._draft is not None or self._active_source_id is None:
            return
        position_ms = self._current_position_ms()
        if self._pending_start_ms is None:
            self._pending_start_ms = position_ms
            self.pendingChanged.emit()
            return
        first_ms, self._pending_start_ms = self._pending_start_ms, None
        self.pendingChanged.emit()
        self._playback.pause()
        self._open_editor(
            ClipDraft.marked(
                self._active_source_id,
                first_ms,
                position_ms,
                limit_ms=self._duration_ms,
            )
        )

    @Slot()
    def cancelPending(self) -> None:
        """Drop the mark. It was never part of the Analysis."""

        self._abandon_pending()

    @Slot(str)
    def editClip(self, clip_id: str) -> None:
        """Edit an existing Clip, in the state that marks a new one.

        Its Source video is activated and the video is put on the Clip's first
        frame, because a boundary is only worth editing against the picture it
        names.
        """

        identity = _as_uuid(clip_id)
        clip = next(
            (clip for clip in self._document.analysis.clips if clip.id == identity),
            None,
        )
        if clip is None:
            return
        self._abandon_pending()
        if clip.source_video_id != self._active_source_id:
            self._activate_source(clip.source_video_id)
        self.selectClip(str(clip.id))
        self._playback.pause()
        self._open_editor(ClipDraft.of(clip))

    @Slot(str)
    def setDraftName(self, name: str) -> None:
        if self._draft is None or name == self._draft.name:
            return
        self._draft = replace(self._draft, name=str(name))
        self._boundary_error = ""
        self.draftChanged.emit()

    @Slot(str)
    def setDraftNotes(self, notes: str) -> None:
        if self._draft is None or notes == self._draft.notes:
            return
        self._draft = replace(self._draft, notes=str(notes))
        self._boundary_error = ""
        self.draftChanged.emit()

    @Slot(str)
    def setDraftCategory(self, category_id: str) -> None:
        """File the Clip under a Category, or under none at all."""

        if self._draft is None:
            return
        identity = _as_uuid(category_id)
        known = {category.id for category in self._document.analysis.categories}
        if identity not in known:
            identity = None
        self._draft = replace(self._draft, category_id=identity)
        self._boundary_error = ""
        self._categories.refresh(
            self._document.analysis, selected_category_id=identity
        )
        self.draftChanged.emit()

    @Slot(str)
    def setDraftStartText(self, text: str) -> None:
        self._move_boundary(START, timecode.parse(text))

    @Slot(str)
    def setDraftEndText(self, text: str) -> None:
        self._move_boundary(END, timecode.parse(text))

    @Slot(str, int)
    def nudgeDraftBoundary(self, which: str, delta_ms: int) -> None:
        """Move a boundary by a step, for an analyst who is a frame out."""

        if self._draft is None:
            return
        side = START if which == START else END
        self._move_boundary(side, self._draft.boundary_ms(side) + int(delta_ms))

    @Slot(str)
    def takeDraftBoundaryFromPlayhead(self, which: str) -> None:
        """Set a boundary to where the video already is.

        No seek: the frame this names is the one on screen, and asking the
        player to go where it already is would only cost a decode.
        """

        self._move_boundary(
            START if which == START else END,
            self._current_position_ms(),
            scrub=False,
        )

    @Slot()
    def commitDraft(self) -> None:
        """Keep the edited Clip, as one change to the Analysis.

        One change rather than a field at a time: a Clip half-written into the
        document would be a state the Analysis was never meant to hold, and a
        revision the analyst never asked for.
        """

        draft = self._draft
        if draft is None or not self.draftValid:
            return
        analysis = self._document.analysis
        if draft.is_new:
            kept = analysis.add_clip(
                draft.source_video_id,
                draft.name.strip(),
                draft.start_ms,
                draft.end_ms,
                notes=draft.notes,
                category_id=draft.category_id,
            ).id
        else:
            assert draft.clip_id is not None
            analysis.update_clip(
                draft.clip_id,
                name=draft.name.strip(),
                start_ms=draft.start_ms,
                end_ms=draft.end_ms,
                notes=draft.notes,
                category_id=draft.category_id,
            )
            kept = draft.clip_id
        self._selected_clip_id = kept
        self._close_editor()
        self.selectionChanged.emit()

    @Slot()
    def cancelDraft(self) -> None:
        """Leave the editing state, changing nothing.

        A cancelled new Clip never reached the Analysis and a cancelled edit
        was never applied to it, so both cancel paths are one path: drop the
        draft, and there is nothing left to undo.
        """

        self._close_editor()

    # --- Inside the editing state -----------------------------------------

    def _open_editor(self, draft: ClipDraft) -> None:
        self._draft = draft
        self._boundary_error = ""
        self._categories.refresh(
            self._document.analysis, selected_category_id=draft.category_id
        )
        # The playhead goes with the player, because a Source video that was
        # just activated is still being primed and priming puts the video back
        # where the playhead says it was.
        self._show_position(draft.start_ms)
        self._seek_now(draft.start_ms)
        self.draftChanged.emit()
        self.editingChanged.emit()

    def _close_editor(self) -> None:
        if self._draft is None:
            return
        self._draft = None
        self._boundary_error = ""
        self._categories.refresh(self._document.analysis, selected_category_id=None)
        self._refresh_projections()
        self.draftChanged.emit()
        self.editingChanged.emit()
        self.documentChanged.emit()

    def _move_boundary(
        self, which: str, value_ms: int | None, *, scrub: bool = True
    ) -> None:
        """Move one boundary, and take the video with it.

        Scrub-linking is what makes the field worth trusting: the number is
        only useful if the frame it names is on screen while it is being
        typed. A boundary that would end the Clip before it began is refused
        and explained rather than quietly corrected.
        """

        draft = self._draft
        if draft is None:
            return
        moved = draft.with_boundary(which, value_ms, limit_ms=self._duration_ms)
        if moved is None:
            self._boundary_error = NOT_A_TIME if value_ms is None else END_BEFORE_START
            self.draftChanged.emit()
            return
        self._draft = moved
        self._boundary_error = ""
        if scrub:
            self._playback.pause()
            self._show_position(moved.boundary_ms(which))
            self._seek_now(moved.boundary_ms(which))
        self.draftChanged.emit()

    def _abandon_pending(self) -> None:
        """Forget a marked boundary, wherever the abandoning came from."""

        if self._pending_start_ms is None:
            return
        self._pending_start_ms = None
        self.pendingChanged.emit()

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
    def addSourceVideo(self) -> bool:
        """Ask for one Source video and add it to this Analysis."""

        return self._workflow.add_source_video() is not None

    @Slot(list, result=bool)
    def addDroppedSourceVideos(self, urls: list[object]) -> bool:
        """Add every supported local Source video in one window drop."""

        added = False
        for value in urls:
            url = value if isinstance(value, QUrl) else QUrl(str(value))
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if self._workflow.add_dropped_source_video(path):
                added = True
        return added

    @Property(list, constant=True)
    def menus(self) -> list:
        """The menu bar, as data, for the platforms that draw it in the window.

        macOS never reads this: there the same `menu_bar.MENUS` are a real
        parentless `QMenuBar`, which is the system menu bar. Windows and Linux
        have nowhere to put one, so QML draws these instead — from the same
        definition, so the two bars cannot carry different commands.
        """

        return list(menu_bar.menu_model())

    @Slot(str, result=bool)
    def runMenuCommand(self, command: str) -> bool:
        """Run what a menu entry names, or report that nothing names it.

        The dispatch table is the one the `QMenuBar` connects its actions to,
        so an entry that does nothing here is an entry that does nothing there
        — there is no second wiring to forget.
        """

        runner = menu_bar.command_runners(
            self, close_window=self.closeRequested.emit
        ).get(command)
        if runner is None:
            return False
        runner()
        return True

    @Slot(int, int, result=bool)
    def runMenuShortcut(self, key: int, modifiers: int) -> bool:
        """Run the one menu command whose platform sequence was pressed.

        QML passes the raw key event rather than declaring one `Shortcut` per
        command. The comparison is therefore against `menu_bar.MENUS`, the
        same definition that writes both menu bars and their displayed keys.
        """

        pressed = QKeySequence(key | modifiers)
        for entry in menu_bar.entries_of():
            if QKeySequence(entry.shortcut) == pressed:
                return self.runMenuCommand(entry.command)
        return False

    @Slot(QObject)
    def installMenuShortcutHandler(self, window: QObject) -> None:
        """Let one window pass document keys through the shared menu map."""

        if self._menu_shortcut_filter is not None:
            return
        self._menu_shortcut_filter = _MenuShortcutFilter(self)
        window.installEventFilter(self._menu_shortcut_filter)

    @Slot(result=bool)
    def requestClose(self) -> bool:
        """Whether the window may close, asking about unsaved work first.

        Every way out of the application arrives here, so the question is
        asked once and answered in one place.
        """

        return self._workflow.may_replace_analysis()

    def _source_video_added(self, source_video: SourceVideo) -> None:
        """Show the first Source video; leave an existing review uninterrupted."""

        if self._active_source_id is None:
            self._activate_source(source_video.id)
            return
        self._refresh_projections()
        self.documentChanged.emit()

    def _analysis_replaced(self) -> None:
        """A different Analysis is open now; drop everything transient."""

        self._document = self._workflow.document
        self._playback.pause()
        self._playback.unload()
        # Whatever was being primed is gone with the video it belonged to.
        self._priming = False
        # Whatever was being marked or edited belonged to the Analysis that is
        # gone, and there is nothing to keep: neither had reached it.
        self._abandon_pending()
        self._draft = None
        self._boundary_error = ""
        self.draftChanged.emit()
        self.editingChanged.emit()
        self._active_source_id = None
        self._position_ms = 0
        self._duration_ms = 0
        self._selected_clip_id = None
        self._refresh_projections()
        sources = self._document.analysis.source_videos
        if sources:
            self._activate_source(sources[0].id)
        self.selectionChanged.emit()
        self.playbackChanged.emit()

    def _document_reported(self) -> None:
        """The Analysis or its saved state changed; redraw what says so."""

        self.documentChanged.emit()

    # --- The Active Source video ------------------------------------------

    def _activate_source(self, source_id: UUID) -> None:
        # A Clip belongs to the video its first boundary was marked on, so a
        # mark does not survive the video it was made against.
        self._abandon_pending()
        self._active_source_id = source_id
        video = self._document.analysis.source_video(source_id)
        # A different recording is a different length, and the media player
        # announces the new one a moment after its source is set. Until it
        # does, this Source video has no scale at all: keeping the previous
        # one's would draw these Clips against the wrong ruler and read the
        # wrong total time back to the analyst.
        self._forget_duration()
        self._playback.load(video.location)
        self._refresh_projections()
        if video.duration_ms is not None:
            self._duration_reported(video.duration_ms)
        self._prime_video_surface()
        self.documentChanged.emit()
        self.playbackChanged.emit()

    def _forget_duration(self) -> None:
        """Drop the length of whatever was playing, marks and all."""

        self._duration_ms = 0
        if self._ruler_width_px > 0:
            self._ruler.layout(0, self._ruler_width_px)

    def _refresh_projections(self) -> None:
        """Re-project the Analysis onto everything that draws it.

        One call, because the four models are four views of one Analysis and
        the selected Clip is one piece of state: a surface refreshed on its
        own is how a list and a timeline end up disagreeing about which Clip
        is selected.
        """

        analysis = self._document.analysis
        self._ranges.refresh(
            analysis,
            source_video_id=self._active_source_id,
            selected_clip_id=self._selected_clip_id,
        )
        self._clips.refresh(analysis, selected_clip_id=self._selected_clip_id)
        self._sources.refresh(analysis, active_source_id=self._active_source_id)

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
