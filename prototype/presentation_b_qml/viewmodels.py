"""The presentation state QML reads, and the only place it can change it.

QML gets properties, signals and slots. It never sees an ``Analysis``, a
``Clip`` or the ``Playback``, so a delegate cannot reach past the interface
into the domain, and every rule about what an action means stays here in
Python. The prototype's kill condition — logic leaking into JavaScript — is
enforced by this file being the whole vocabulary QML has.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

import fixture
import timecode
from analysis import AnalysisDocument, Clip, UnsavedChangesChoice
from application_workflow import ApplicationWorkflow
from models import (
    CategoryModel,
    ClipListModel,
    RulerModel,
    SourceVideoModel,
    TimelineRangeModel,
)
from playback import Playback

PLAYBACK_RATES = (0.5, 1.0, 1.5, 2.0)
MINIMUM_CLIP_MS = 200
NEW_CLIP_NAME = "Neuer Clip"


@dataclass
class ClipDraft:
    """The Clip being edited, held apart from the Analysis until it is kept.

    Editing works on a copy so that a cancelled edit needs no undo, and so
    that scrub-linked boundaries can move the video around without every
    intermediate value reaching the Analysis and marking it dirty.
    """

    source_video_id: UUID
    name: str
    start_ms: int
    end_ms: int
    notes: str
    category_id: UUID | None
    clip_id: UUID | None = None

    @property
    def is_new(self) -> bool:
        return self.clip_id is None

    @classmethod
    def of(cls, clip: Clip) -> ClipDraft:
        return cls(
            source_video_id=clip.source_video_id,
            name=clip.name,
            start_ms=clip.start_ms,
            end_ms=clip.end_ms,
            notes=clip.notes,
            category_id=clip.category_id,
            clip_id=clip.id,
        )


class _SilentPresenter:
    """A prototype stands in for the person at every workflow decision."""

    def __init__(self) -> None:
        self.failures: list[tuple[str, str]] = []

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        return UnsavedChangesChoice.DISCARD

    def choose_analysis_to_open(self) -> str | None:
        return None

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        return None

    def choose_source_video(self) -> str | None:
        return None

    def report_failure(self, title: str, message: str) -> None:
        self.failures.append((title, message))


class WorkspaceViewModel(QObject):
    """One facade over the Analysis document, the playback and the selection."""

    documentChanged = Signal()
    selectionChanged = Signal()
    playbackChanged = Signal()
    modeChanged = Signal()
    sidebarTabChanged = Signal()
    pendingChanged = Signal()
    draftChanged = Signal()

    def __init__(
        self,
        document: AnalysisDocument,
        playback: Playback,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = _SilentPresenter()
        self._workflow = ApplicationWorkflow(self._presenter, document=document)
        self._playback = playback
        self._playback.setParent(self)

        self._active_source_id: UUID | None = None
        self._selected_clip_id: UUID | None = None
        self._pending_start_ms: int | None = None
        self._draft: ClipDraft | None = None
        self._position_ms = 0
        self._duration_ms = 0

        self.clips = ClipListModel(self)
        self.ranges = TimelineRangeModel(self)
        self.ruler = RulerModel(self)
        self.videos = SourceVideoModel(self)
        self.categories = CategoryModel(self)

        self._playback.position_changed.connect(self._position_reported)
        self._playback.duration_changed.connect(self._duration_reported)
        self._playback.playing_changed.connect(lambda _: self.playbackChanged.emit())

        first = self._analysis.source_videos
        if first:
            self._activate_source(first[0].id)
        self._refresh_all()

    # --- What QML is allowed to see ---------------------------------------

    @property
    def _analysis(self):
        return self._workflow.analysis

    @Property(str, notify=documentChanged)
    def analysisTitle(self) -> str:
        return self._analysis.title or "Unbenannte Analyse"

    @Property(bool, notify=documentChanged)
    def dirty(self) -> bool:
        return self._workflow.document.dirty

    @Property(str, notify=documentChanged)
    def windowTitle(self) -> str:
        return self._workflow.window_title

    @Property(int, notify=documentChanged)
    def sourceCount(self) -> int:
        return len(self._analysis.source_videos)

    @Property(str, notify=modeChanged)
    def mode(self) -> str:
        """`empty`, `workspace` or `editing` — the shell renders one of three."""
        if not self._analysis.source_videos:
            return "empty"
        return "editing" if self._draft is not None else "workspace"

    _sidebar_tab = "clips"
    _sidebar_visible = True

    @Property(bool, notify=sidebarTabChanged)
    def sidebarVisible(self) -> bool:
        return self._sidebar_visible

    @Slot()
    def toggleSidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        self.sidebarTabChanged.emit()

    @Property(str, notify=sidebarTabChanged)
    def sidebarTab(self) -> str:
        return self._sidebar_tab

    @Property(str, notify=documentChanged)
    def activeSourceName(self) -> str:
        if self._active_source_id is None:
            return ""
        return self._analysis.source_video(self._active_source_id).display_name

    @Property(bool, notify=documentChanged)
    def activeSourceMissing(self) -> bool:
        if self._active_source_id is None:
            return False
        location = self._analysis.source_video(self._active_source_id).location
        return not Path(location).is_file()

    # Playback

    @Property(int, notify=playbackChanged)
    def positionMs(self) -> int:
        return self._position_ms

    @Property(int, notify=playbackChanged)
    def durationMs(self) -> int:
        return self._duration_ms

    @Property(str, notify=playbackChanged)
    def positionText(self) -> str:
        return timecode.clock(self._position_ms)

    @Property(str, notify=playbackChanged)
    def durationText(self) -> str:
        return timecode.clock(self._duration_ms)

    @Property(bool, notify=playbackChanged)
    def playing(self) -> bool:
        return self._playback.is_playing()

    @Property(bool, notify=playbackChanged)
    def muted(self) -> bool:
        return self._playback.is_muted()

    @Property(float, notify=playbackChanged)
    def playbackRate(self) -> float:
        return self._playback.playback_rate()

    @Property(list, constant=True)
    def playbackRates(self) -> list:
        return [f"{rate:g}x" for rate in PLAYBACK_RATES]

    @Property(int, notify=playbackChanged)
    def playbackRateIndex(self) -> int:
        """Which rate is selected. Deciding that is not the segmented
        control's business — it draws whichever option this names."""
        rate = self._playback.playback_rate()
        for index, candidate in enumerate(PLAYBACK_RATES):
            if abs(candidate - rate) < 0.001:
                return index
        return PLAYBACK_RATES.index(1.0)

    # Selection

    @Property(bool, notify=selectionChanged)
    def hasSelection(self) -> bool:
        return self._selected_clip_id is not None

    @Property(str, notify=selectionChanged)
    def selectedClipTitle(self) -> str:
        clip = self._selected_clip()
        return clip.name if clip else ""

    @Property(str, notify=selectionChanged)
    def selectedClipRange(self) -> str:
        clip = self._selected_clip()
        if clip is None:
            return ""
        return (
            f"{timecode.clock(clip.start_ms)} – {timecode.clock(clip.end_ms)}"
            f"  ·  {timecode.duration(clip.end_ms - clip.start_ms)}"
        )

    @Property(str, notify=selectionChanged)
    def selectedClipCategory(self) -> str:
        clip = self._selected_clip()
        if clip is None or clip.category_id is None:
            return ""
        return self._analysis.category(clip.category_id).name

    # The Pending Clip

    @Property(bool, notify=pendingChanged)
    def pendingActive(self) -> bool:
        return self._pending_start_ms is not None

    @Property(int, notify=pendingChanged)
    def pendingStartMs(self) -> int:
        return self._pending_start_ms or 0

    @Property(str, notify=pendingChanged)
    def pendingText(self) -> str:
        if self._pending_start_ms is None:
            return ""
        length = max(0, self._position_ms - self._pending_start_ms)
        return (
            f"Start {timecode.clock(self._pending_start_ms)}"
            f"  ·  {timecode.duration(length)}"
        )

    @Property(str, notify=pendingChanged)
    def markActionText(self) -> str:
        return "Ende setzen" if self._pending_start_ms is not None else "Clip markieren"

    # --- What QML is allowed to do ----------------------------------------

    @Slot(QObject)
    def attachVideoOutput(self, video_output: QObject) -> None:
        """Hand the Qt Quick video item to the existing playback seam.

        ``Playback.set_video_output`` already takes a plain ``QObject``, and a
        ``VideoOutput`` carries the ``videoSink`` property QMediaPlayer looks
        for, so the QML surface attaches through the production seam unchanged.
        """
        self._playback.set_video_output(video_output)

    @Slot()
    def playPause(self) -> None:
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

    @Slot()
    def toggleMuted(self) -> None:
        self._playback.toggle_muted()
        self.playbackChanged.emit()

    @Slot(int)
    def setRateIndex(self, index: int) -> None:
        if 0 <= index < len(PLAYBACK_RATES):
            self._playback.set_playback_rate(PLAYBACK_RATES[index])
            self.playbackChanged.emit()

    @Slot(int)
    def seek(self, position_ms: int) -> None:
        self._playback.seek(int(position_ms))

    @Slot(str)
    def setSidebarTab(self, tab: str) -> None:
        if tab != self._sidebar_tab and tab in ("clips", "videos"):
            self._sidebar_tab = tab
            self.sidebarTabChanged.emit()

    @Slot(str)
    def selectClip(self, clip_id: str) -> None:
        """Select without seeking — clicking a range must not move the playhead."""
        self._select(_as_uuid(clip_id))

    @Slot(str)
    def navigateToClip(self, clip_id: str) -> None:
        """Activate the Clip's Source video and seek to its start."""
        identity = _as_uuid(clip_id)
        if identity is None:
            return
        clip = self._analysis.clip(identity)
        if clip.source_video_id != self._active_source_id:
            self._activate_source(clip.source_video_id)
        self._select(identity)
        self._playback.seek(clip.start_ms)

    @Slot(str)
    def selectSourceVideo(self, source_id: str) -> None:
        identity = _as_uuid(source_id)
        if identity is not None and identity != self._active_source_id:
            self._activate_source(identity)
            self._select(None)
            self._refresh_all()

    @Slot(float, float)
    def layoutRuler(self, width_px: float, duration_ms: float) -> None:
        self.ruler.layout(int(duration_ms), width_px)

    @Slot(int, result=str)
    def timeText(self, position_ms: int) -> str:
        """The hover tooltip's timecode, formatted where every other one is."""
        return timecode.clock(position_ms)

    @Slot()
    def markBoundary(self) -> None:
        """Set the first Clip boundary, or complete it and open the editor."""
        if self._active_source_id is None:
            return
        if self._pending_start_ms is None:
            self._pending_start_ms = self._position_ms
            self.pendingChanged.emit()
            return
        start = min(self._pending_start_ms, self._position_ms)
        end = max(self._pending_start_ms, self._position_ms)
        if end - start < MINIMUM_CLIP_MS:
            end = start + MINIMUM_CLIP_MS
        self._pending_start_ms = None
        self.pendingChanged.emit()
        self._playback.pause()
        self._open_editor(
            ClipDraft(
                source_video_id=self._active_source_id,
                name=NEW_CLIP_NAME,
                start_ms=start,
                end_ms=self._clamped(end),
                notes="",
                category_id=None,
            )
        )

    @Slot()
    def cancelPending(self) -> None:
        if self._pending_start_ms is not None:
            self._pending_start_ms = None
            self.pendingChanged.emit()

    @Slot()
    def editSelectedClip(self) -> None:
        clip = self._selected_clip()
        if clip is None:
            return
        if clip.source_video_id != self._active_source_id:
            self._activate_source(clip.source_video_id)
        self._playback.pause()
        self._playback.seek(clip.start_ms)
        self._open_editor(ClipDraft.of(clip))

    @Slot(str)
    def editClip(self, clip_id: str) -> None:
        self.selectClip(clip_id)
        self.editSelectedClip()

    # --- The Clip editor ---------------------------------------------------

    @Property(str, notify=draftChanged)
    def draftName(self) -> str:
        return self._draft.name if self._draft else ""

    @Property(str, notify=draftChanged)
    def draftNotes(self) -> str:
        return self._draft.notes if self._draft else ""

    @Property(str, notify=draftChanged)
    def draftStartText(self) -> str:
        return timecode.precise(self._draft.start_ms) if self._draft else ""

    @Property(str, notify=draftChanged)
    def draftEndText(self) -> str:
        return timecode.precise(self._draft.end_ms) if self._draft else ""

    @Property(int, notify=draftChanged)
    def draftStartMs(self) -> int:
        return self._draft.start_ms if self._draft else 0

    @Property(int, notify=draftChanged)
    def draftEndMs(self) -> int:
        return self._draft.end_ms if self._draft else 0

    @Property(str, notify=draftChanged)
    def draftDurationText(self) -> str:
        if self._draft is None:
            return ""
        return timecode.duration(self._draft.end_ms - self._draft.start_ms)

    @Property(str, notify=draftChanged)
    def draftCategoryName(self) -> str:
        if self._draft is None or self._draft.category_id is None:
            return "Ohne Kategorie"
        return self._analysis.category(self._draft.category_id).name

    @Property(str, notify=draftChanged)
    def draftCategoryColor(self) -> str:
        if self._draft is None or self._draft.category_id is None:
            return "#5E646C"
        return self._analysis.category(self._draft.category_id).color

    @Property(bool, notify=draftChanged)
    def draftIsNew(self) -> bool:
        return self._draft.is_new if self._draft else False

    @Property(str, notify=draftChanged)
    def draftError(self) -> str:
        """Why the Clip cannot be kept yet, in the words the form shows."""
        if self._draft is None:
            return ""
        if not self._draft.name.strip():
            return "Ein Clip braucht einen Titel."
        if self._draft.end_ms <= self._draft.start_ms:
            return "Das Ende muss nach dem Start liegen."
        return ""

    @Property(bool, notify=draftChanged)
    def draftValid(self) -> bool:
        return self._draft is not None and not self.draftError

    @Slot(str)
    def setDraftName(self, name: str) -> None:
        if self._draft is not None and name != self._draft.name:
            self._draft.name = name
            self.draftChanged.emit()

    @Slot(str)
    def setDraftNotes(self, notes: str) -> None:
        if self._draft is not None and notes != self._draft.notes:
            self._draft.notes = notes
            self.draftChanged.emit()

    @Slot(str)
    def setDraftCategory(self, category_id: str) -> None:
        if self._draft is None:
            return
        self._draft.category_id = _as_uuid(category_id)
        self.categories.refresh(
            self._analysis, selected_category_id=self._draft.category_id
        )
        self.draftChanged.emit()

    @Slot(str)
    def setDraftStartText(self, text: str) -> None:
        self._set_boundary("start", timecode.parse(text))

    @Slot(str)
    def setDraftEndText(self, text: str) -> None:
        self._set_boundary("end", timecode.parse(text))

    @Slot(str, int)
    def nudgeDraftBoundary(self, which: str, delta_ms: int) -> None:
        if self._draft is None:
            return
        current = self._draft.start_ms if which == "start" else self._draft.end_ms
        self._set_boundary(which, current + delta_ms)

    @Slot(str)
    def takeDraftBoundaryFromPlayhead(self, which: str) -> None:
        """Set a boundary to where the video already is."""
        self._set_boundary(which, self._position_ms, scrub=False)

    def _set_boundary(self, which: str, value: int | None, *, scrub: bool = True) -> None:
        """Move one boundary, keeping the interval valid and the video in step.

        Scrub-linking is what makes the field trustworthy: the number is only
        useful if the frame it names is on screen while it is being typed.
        """
        if self._draft is None or value is None:
            self.draftChanged.emit()
            return
        value = self._clamped(value)
        if which == "start":
            self._draft.start_ms = min(value, self._draft.end_ms - MINIMUM_CLIP_MS)
            self._draft.start_ms = max(0, self._draft.start_ms)
        else:
            self._draft.end_ms = max(value, self._draft.start_ms + MINIMUM_CLIP_MS)
            self._draft.end_ms = self._clamped(self._draft.end_ms)
        if scrub:
            self._playback.pause()
            self._playback.seek(
                self._draft.start_ms if which == "start" else self._draft.end_ms
            )
        self.draftChanged.emit()

    @Slot()
    def commitDraft(self) -> None:
        """Keep the edited Clip, as one change to the Analysis."""
        draft = self._draft
        if draft is None or not self.draftValid:
            return
        analysis = self._analysis
        if draft.is_new:
            clip = analysis.add_clip(
                draft.source_video_id,
                draft.name.strip(),
                draft.start_ms,
                draft.end_ms,
                notes=draft.notes,
                category_id=draft.category_id,
            )
            kept = clip.id
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
        self._draft = None
        self._selected_clip_id = kept
        self._close_editor()

    @Slot()
    def cancelDraft(self) -> None:
        """Leave the editing state, changing nothing.

        A cancelled new Clip never reached the Analysis and a cancelled edit
        was never applied to it, so both cancel paths are the same path.
        """
        self._draft = None
        self._close_editor()

    # --- Internals ---------------------------------------------------------

    def _open_editor(self, draft: ClipDraft) -> None:
        self._draft = draft
        self.categories.refresh(self._analysis, selected_category_id=draft.category_id)
        self._playback.seek(draft.start_ms)
        self.draftChanged.emit()
        self.modeChanged.emit()

    def _close_editor(self) -> None:
        self._refresh_all()
        self.draftChanged.emit()
        self.modeChanged.emit()
        self.documentChanged.emit()

    def _selected_clip(self) -> Clip | None:
        if self._selected_clip_id is None:
            return None
        try:
            return self._analysis.clip(self._selected_clip_id)
        except Exception:
            return None

    def _select(self, clip_id: UUID | None) -> None:
        if clip_id == self._selected_clip_id:
            return
        self._selected_clip_id = clip_id
        self.clips.refresh(self._analysis, selected_clip_id=clip_id)
        self.ranges.refresh(
            self._analysis,
            source_video_id=self._active_source_id,
            selected_clip_id=clip_id,
        )
        self.selectionChanged.emit()

    def _activate_source(self, source_id: UUID) -> None:
        self._active_source_id = source_id
        video = self._analysis.source_video(source_id)
        self._playback.load(video.location)
        if video.duration_ms is not None:
            self._duration_reported(video.duration_ms)
        self._prime_video_surface()
        self.documentChanged.emit()

    def _prime_video_surface(self) -> None:
        """Make a newly loaded Source video show a frame instead of black.

        Qt's FFmpeg backend hands the video sink nothing until playback has
        actually started once: seeking a stopped player moves the position and
        decodes no frame. So the surface is primed with a very short play,
        and then put back exactly where it was. This is a property of
        QMediaPlayer rather than of QML — Widgets would meet it too — and it
        is done entirely through the existing Playback seam.
        """
        if not self._playback.is_loaded():
            return
        self._playback.play()
        QTimer.singleShot(140, self._finish_priming)

    def _finish_priming(self) -> None:
        self._playback.pause()
        self._playback.seek(self._position_ms)

    def _clamped(self, position_ms: int) -> int:
        limit = self._duration_ms
        position_ms = max(0, int(position_ms))
        return min(position_ms, limit) if limit > 0 else position_ms

    def _position_reported(self, position_ms: int) -> None:
        self._position_ms = int(position_ms)
        self.playbackChanged.emit()
        if self._pending_start_ms is not None:
            self.pendingChanged.emit()

    def _duration_reported(self, duration_ms: int) -> None:
        """Trust the Analysis until the media reports something better."""
        if duration_ms <= 0:
            return
        self._duration_ms = int(duration_ms)
        self.playbackChanged.emit()

    def _refresh_all(self) -> None:
        self.clips.refresh(self._analysis, selected_clip_id=self._selected_clip_id)
        self.ranges.refresh(
            self._analysis,
            source_video_id=self._active_source_id,
            selected_clip_id=self._selected_clip_id,
        )
        self.videos.refresh(self._analysis, active_source_id=self._active_source_id)
        self.categories.refresh(self._analysis, selected_category_id=None)
        self.documentChanged.emit()
        self.selectionChanged.emit()
        self.modeChanged.emit()

    # --- Prototype convenience --------------------------------------------

    def restore_canonical_state(self) -> None:
        """Put the fixture into the exact state the screenshots specify."""
        analysis = self._analysis
        if not analysis.source_videos:
            return
        clip = fixture.selected_clip(analysis)
        self._select(clip.id)
        self._playback.seek(fixture.PLAYHEAD_MS)
        self._position_reported(fixture.PLAYHEAD_MS)


def _as_uuid(value: str) -> UUID | None:
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None
