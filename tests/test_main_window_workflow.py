"""The regression contract for the behaviour issue #29 delivered.

This file is the one thing standing between the QML migration (#37) and a
silent loss of behaviour. It used to drive `MainWindow` and Qt Widgets; #49
re-pointed it at the view-model seam — `workspace_view_model.WorkspaceViewModel`
and the workflow, document and playback seams beneath it — so that it survives
the deletion of the Widgets interface in #50. The re-pointing was done while
*both* interfaces were still running, because that is the only moment at which
a weakened assertion and a broken feature can be told apart: every case below
was proved, one at a time, to go red when the behaviour it describes was
deliberately broken in the production code and green again when it was put
back.

**No later ticket may modify this suite except to add cases.** Not to make a
refactor compile, not to follow a rename, not to "simplify" an assertion. If a
change to the application makes a case here fail, the change is wrong until
somebody has said out loud why the behaviour should be different. The file name
is deliberately unchanged: #37, `docs/design/qml-migration-plan.md` and
`docs/development-workflow.md` all name this path as the contract, and those
references stay true.

Everything here is driven with no window, no QML engine and no media: the
person who would stand in front of a dialog is `RecordingPresenter`, and the
event loop is `Loop`, following the patterns already established in
`tests/test_workspace_document_actions.py`, `tests/test_workspace_clip_editor.py`
and `tests/test_workspace_sidebar.py`.

Coverage changes made in the move (#49), stated here rather than lost quietly.
Each is marked again at the case it affects:

1. *An empty Category is no longer a row of its own.* The Widgets tree drew a
   node per Category whether or not it held Clips; the QML Clip list groups
   only Categories that have Clips (`tests/test_workspace_sidebar.py::
   test_a_category_with_no_clips_has_no_row_of_its_own`). The surviving half —
   an empty Category is still in the Analysis and still offered to file a Clip
   under — is asserted instead.
2. *Typing an unknown Category name no longer creates a Category.* The Widgets
   form had a free-text Category box. ADR 0007 replaced it with a fixed set of
   chips over the Categories the Analysis already has, and creating Categories
   belongs to #18. The case now asserts the part that survives: filing two
   Clips under one Category does not duplicate it.
3. *Refusals are shown in the form rather than in a modal.* The Widgets
   interface reported a rejected Clip or boundary through `QMessageBox`; the
   editor reports it through `draftError`, and an invalid draft cannot be
   committed at all. The assertion "the Analysis is unchanged and the analyst
   is told why" is kept in that form.
4. *Geometry is not a view-model concern.* Three Widgets cases measured pixel
   layout — sidebar left of the video, timeline beneath it, the editor's room
   beside the video, the window fitting a small laptop. The view model
   expresses that state as `editing`, which is asserted here; the geometry
   itself is covered by `tests/test_qml_workspace.py::
   test_the_editor_takes_its_room_from_the_video_and_gives_it_back` and by the
   theme-metric tests in the same file. There is no seam here at which a
   window's width can be asked for, and inventing one would have been a worse
   answer than saying so.
5. *Pixel-to-millisecond mapping is QML's.* The timeline cases used to click
   and drag real pixels. What remains here is the seam's half — what a scrub,
   a click, a double click and a selection do to the player and the Analysis.
   That pixels land on the right milliseconds is `tests/test_qml_timeline.py`.
6. *0.25x is not a speed this application offers.* The Widgets combo box had
   it; `workspace_view_model.PLAYBACK_RATES` does not. The case asserts the
   same behaviour — choosing a speed sets a numeric rate on the player —
   against a speed the application actually offers.
7. *The mark action is disabled rather than explained.* Marking a Clip with no
   Source video raised an information dialog in the Widgets interface; the QML
   transport binds the action's enabled state to `hasVideo`. The behaviour
   that mattered — nothing is marked and the transport does not pretend
   otherwise — is asserted unchanged.
8. *Renaming an Analysis is now a view-model action.* The Widgets interface
   renamed through `QInputDialog`; the behaviour — a retitled Analysis keeps
   its identity and the interface shows the new title — is driven through
   `WorkspaceViewModel.setAnalysisTitle` and read back off the seam.
9. *A Category colour is no longer muted for rendering.* ADR 0007 replaced
    coloured Category text with a harmonised palette drawn as a colour bar, so
    there is no muting to assert. The surviving half — the Analysis's own
    colour is never changed by being drawn, and the row carries it verbatim —
    is asserted instead.
"""

from __future__ import annotations

import importlib.util
import os
from collections.abc import Callable
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import timecode  # noqa: E402
import workspace_view_model as workspace_module  # noqa: E402
from analysis import (  # noqa: E402
    Analysis,
    AnalysisDocument,
    RecoverySnapshotStore,
    UnsavedChangesChoice,
    new_analysis_document,
)
from application_workflow import APPLICATION_TITLE, UNTITLED_ANALYSIS_TITLE  # noqa: E402
from clip_editor import END_BEFORE_START, NO_TITLE  # noqa: E402
from playback import FakePlayback  # noqa: E402
from sidebar_models import UNCATEGORIZED_LABEL  # noqa: E402
from workspace_view_model import (  # noqa: E402
    PLAYBACK_RATES,
    SCRUB_INTERVAL_MS,
    PRIMING_MS,
    SIDEBAR_TABS,
    WorkspaceViewModel,
)


#: The Categories `new_analysis_document` seeds, in the order it seeds them.
TEMPLATE_CATEGORIES = ("Abwehr", "Angriff", "Tor")


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


class RecordingPresenter:
    """The person the workflow asks, written down instead of shown a dialog.

    This is what replaces the patched `QFileDialog` and `QMessageBox` of the
    Widgets suite: every question and every report is recorded, so a case can
    still say "the analyst was told" without a window to say it in.

    Every method answers through the same completion-based contract
    `WorkspacePresenter` does — issue #69's async dialogs — by calling
    `on_result` immediately, on the same call stack. That keeps every
    assertion in this frozen suite unchanged: a command still settles
    before the call that started it returns, exactly as it always did,
    because nothing here actually waits for a person.
    """

    def __init__(self) -> None:
        self.choice = UnsavedChangesChoice.CANCEL
        self.analysis_to_open: str | None = None
        self.destination: str | None = None
        self.source_video: str | None = None
        self.questions = 0
        self.failures: list[tuple[str, str]] = []

    def ask_unsaved_changes(
        self, on_result: Callable[[UnsavedChangesChoice], None]
    ) -> None:
        self.questions += 1
        on_result(self.choice)

    def ask_external_change_conflict(
        self, on_result: Callable[[object], None]
    ) -> None:
        from analysis import ExternalChangeChoice

        on_result(ExternalChangeChoice.CANCEL)

    def offer_recovered_analysis(self, on_result: Callable[[bool], None]) -> None:
        on_result(False)

    def choose_analysis_to_open(self, on_result: Callable[[str | None], None]) -> None:
        on_result(self.analysis_to_open)

    def choose_analysis_destination(
        self, suggested_name: str, on_result: Callable[[str | None], None]
    ) -> None:
        on_result(self.destination)

    def choose_source_video(self, on_result: Callable[[str | None], None]) -> None:
        on_result(self.source_video)

    def report_failure(self, title: str, message: str) -> None:
        self.failures.append((title, message))


class Loop:
    """Stands in for the event loop: a clock, a schedule and a ticker.

    Priming, interpolation and scrub throttling are all statements about time.
    Time here moves only when a case moves it, so none of them is a wait.
    """

    def __init__(self) -> None:
        self.now_ms = 0.0
        self._due: list[tuple[float, object]] = []
        self.tick_interval_ms: int | None = None
        self._tick: object | None = None
        self._next_tick_ms = 0.0

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
def presenter() -> RecordingPresenter:
    return RecordingPresenter()


@pytest.fixture
def player(application: QApplication) -> FakePlayback:
    return FakePlayback()


@pytest.fixture
def document() -> AnalysisDocument:
    """A new, empty, saved Analysis — what opening the application gives."""

    return new_analysis_document()


@pytest.fixture
def workspace(
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> WorkspaceViewModel:
    return WorkspaceViewModel(
        document,
        player,
        presenter=presenter,
        schedule=loop.schedule,
        clock=loop.clock,
        ticker=loop,
        # Isolated from any real installation location: this suite's saves
        # and closes must never touch an actual analyst's Recovery data.
        recovery_store=RecoverySnapshotStore(tmp_path / "recovery"),
    )


# --- Driving the seam the way an analyst drives the interface ---------------


def add_video(
    workspace: WorkspaceViewModel,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
    name: str = "first-half.mp4",
) -> Path:
    """Add one Source video, and let its surface finish being primed."""

    video_path = tmp_path / name
    video_path.write_bytes(f"not a real video: {video_path.name}".encode())
    presenter.source_video = str(video_path)
    assert workspace.addSourceVideo() is True
    presenter.source_video = None
    loop.advance(PRIMING_MS * 2)
    return video_path


def category_id(workspace: WorkspaceViewModel, name: str) -> str:
    """The identity of a Category, as the editor's chooser offers it."""

    for row in workspace.categoryModel.rows():
        if row["name"] == name:
            return str(row["categoryId"])
    raise AssertionError(f"no Category named {name!r} is offered")


def mark_clip(
    workspace: WorkspaceViewModel,
    name: str = "Fast break",
    category: str | None = "Angriff",
    start_ms: int = 1_000,
    end_ms: int = 2_000,
) -> str:
    """Mark a Clip the way the transport does: two boundaries, then the form."""

    workspace.seek(start_ms)
    workspace.markBoundary()
    workspace.seek(end_ms)
    workspace.markBoundary()
    assert workspace.editing is True, "the second boundary opened no editor"
    workspace.setDraftName(name)
    if category is not None:
        workspace.setDraftCategory(category_id(workspace, category))
    workspace.commitDraft()
    return workspace.selectedClipId


def set_boundaries(
    workspace: WorkspaceViewModel, start_ms: int, end_ms: int
) -> None:
    """Type both boundaries, in the order that never inverts the Clip.

    Each field is applied as it is typed, so moving a Clip later means moving
    its end first; a form that applied both at once would not have to care.
    """

    if end_ms >= workspace.draftStartMs:
        workspace.setDraftEndText(timecode.precise(end_ms))
        workspace.setDraftStartText(timecode.precise(start_ms))
    else:
        workspace.setDraftStartText(timecode.precise(start_ms))
        workspace.setDraftEndText(timecode.precise(end_ms))


def clip_rows(workspace: WorkspaceViewModel) -> list[dict]:
    return [row for row in workspace.clipModel.rows() if row["kind"] == "clip"]


def category_rows(workspace: WorkspaceViewModel) -> list[dict]:
    return [row for row in workspace.clipModel.rows() if row["kind"] == "category"]


def category_row(workspace: WorkspaceViewModel, name: str) -> dict | None:
    return next((row for row in category_rows(workspace) if row["title"] == name), None)


def clips_under(workspace: WorkspaceViewModel, category: str) -> list[dict]:
    return [row for row in clip_rows(workspace) if row["categoryName"] == category]


def clip_row(workspace: WorkspaceViewModel, name: str) -> dict:
    return next(row for row in clip_rows(workspace) if row["title"] == name)


def source_rows(workspace: WorkspaceViewModel) -> list[dict]:
    return list(workspace.sourceModel.rows())


def active_source(workspace: WorkspaceViewModel) -> dict | None:
    return next((row for row in source_rows(workspace) if row["active"]), None)


def ranges(workspace: WorkspaceViewModel) -> list[dict]:
    return list(workspace.rangeModel.rows())


def save_to(
    workspace: WorkspaceViewModel, presenter: RecordingPresenter, path: Path
) -> None:
    presenter.destination = str(path)
    assert workspace.saveAnalysis() is True
    presenter.destination = None


# --- The Analysis owns its own state ---------------------------------------


def test_no_clip_or_category_collection_is_shared_between_workspaces(
    application: QApplication, presenter: RecordingPresenter
) -> None:
    """Two Analyses open in one process never see each other's work.

    The Widgets version of this case asserted that `TreeWidget` and
    `ClipHandler` carried no class-level Clip or Category collections. Those
    classes go with #50; the behaviour they could break does not, so it is
    asserted where it now lives — one Analysis per workspace, nothing static.
    """

    first = WorkspaceViewModel(
        new_analysis_document(), FakePlayback(), presenter=presenter
    )
    second_document = new_analysis_document()
    second = WorkspaceViewModel(
        second_document, FakePlayback(), presenter=RecordingPresenter()
    )

    analysis = second_document.analysis
    video = analysis.add_source_video("halbzeit-1.mp4", "/videos/halbzeit-1.mp4")
    konter = analysis.add_category("Konter", color="#F59E0B")
    analysis.add_clip(video.id, "Gegenstoss", 1_000, 2_000, category_id=konter.id)
    second.refresh()
    first.refresh()

    assert clip_rows(second) != []
    assert clip_rows(first) == []
    assert [row["title"] for row in category_rows(second)] == ["Konter"]
    assert category_rows(first) == []


def test_a_new_workspace_starts_with_an_empty_saved_analysis(
    workspace: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    assert document.analysis.source_videos == ()
    assert document.analysis.clips == ()
    assert workspace.dirty is False
    assert workspace.hasVideo is False
    assert clip_rows(workspace) == []


def test_a_category_without_clips_is_still_there_to_file_a_clip_under(
    workspace: WorkspaceViewModel,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 1: an empty Category has no row, but is not lost.

    The Widgets tree drew a node for every Category in the template. The QML
    Clip list groups only Categories that hold Clips, which is a deliberate
    decision of #44. What must not be lost is that the template's Categories
    survive and can still be chosen, so that is what is asserted.
    """

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace, name="Fast break", category="Angriff")

    assert [row["title"] for row in category_rows(workspace)] == ["Angriff"]

    workspace.editClip(clip_row(workspace, "Fast break")["clipId"])
    offered = [row["name"] for row in workspace.categoryModel.rows()]
    workspace.cancelDraft()

    assert offered == list(TEMPLATE_CATEGORIES)


def test_adding_a_video_adds_a_source_video_and_dirties_the_document(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    video_path = add_video(workspace, presenter, loop, tmp_path)

    assert [source.location for source in document.analysis.source_videos] == [
        str(video_path)
    ]
    assert document.analysis.title == "first-half"
    assert workspace.analysisTitle == "first-half"
    assert workspace.dirty is True


def test_creating_a_clip_goes_through_the_analysis_and_is_rendered(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)

    mark_clip(workspace, name="Fast break", category="Angriff")

    clip = document.analysis.clips[0]
    assert clip.name == "Fast break"
    assert clip.start_ms == 1_000
    assert clip.end_ms == 2_000
    assert clip.category_id is not None
    assert document.analysis.category(clip.category_id).name == "Angriff"
    assert workspace.editing is False

    assert [row["clipId"] for row in clips_under(workspace, "Angriff")] == [
        str(clip.id)
    ]


def test_filing_two_clips_under_one_category_does_not_duplicate_it(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 2: the editor chooses Categories, it does not make them.

    The Widgets form created a Category from a typed name, and this case
    guarded against creating it twice. ADR 0007 replaced that with a fixed set
    of chips, and Category management belongs to #18; what survives is that
    two Clips filed under one Category leave one Category.
    """

    add_video(workspace, presenter, loop, tmp_path)

    mark_clip(workspace, name="Fast break", category="Angriff")
    mark_clip(
        workspace, name="Second", category="Angriff", start_ms=3_000, end_ms=4_000
    )

    names = [category.name for category in document.analysis.categories]
    assert names.count("Angriff") == 1
    assert [row["title"] for row in category_rows(workspace)] == ["Angriff"]
    assert len(clips_under(workspace, "Angriff")) == 2


def test_editing_a_clip_updates_the_analysis_in_place(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]

    workspace.editClip(str(clip.id))
    assert workspace.editing is True
    workspace.setDraftName("Fast break finish")
    workspace.setDraftNotes("Left wing")
    workspace.setDraftCategory(category_id(workspace, "Abwehr"))
    workspace.commitDraft()

    updated = document.analysis.clip(clip.id)
    assert updated.name == "Fast break finish"
    assert updated.notes == "Left wing"
    assert updated.category_id is not None
    assert document.analysis.category(updated.category_id).name == "Abwehr"
    assert len(document.analysis.clips) == 1
    assert workspace.editing is False
    assert [row["clipId"] for row in clips_under(workspace, "Abwehr")] == [str(clip.id)]
    assert category_row(workspace, "Angriff") is None


def test_editing_a_clips_boundaries_moves_it_in_the_analysis(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """The boundaries are part of the form, and the Analysis accepts them."""

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]

    workspace.editClip(str(clip.id))
    set_boundaries(workspace, 4_000, 9_500)
    workspace.commitDraft()

    updated = document.analysis.clip(clip.id)
    assert (updated.start_ms, updated.end_ms) == (4_000, 9_500)
    assert updated.name == clip.name
    assert workspace.editing is False


def test_editing_boundaries_is_not_limited_to_a_24_hour_clock(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Media positions are durations, so their hours may exceed one day."""

    add_video(workspace, presenter, loop, tmp_path)
    clip = document.analysis.add_clip(
        document.analysis.source_videos[0].id,
        "Long recording",
        90_000_000,
        90_005_000,
    )
    workspace.refresh()

    workspace.editClip(str(clip.id))

    assert workspace.draftStartMs == 90_000_000
    assert workspace.draftStartText == "25:00:00.000"

    set_boundaries(workspace, 93_600_000, 93_605_000)
    workspace.commitDraft()

    updated = document.analysis.clip(clip.id)
    assert (updated.start_ms, updated.end_ms) == (93_600_000, 93_605_000)


def test_boundaries_the_model_rejects_are_reported_and_change_nothing(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 3: the interval invariant is reported in the form.

    It is still the Analysis's invariant and the form still only reports it;
    what changed is that the report is `draftError` rather than a modal, and
    that an invalid draft cannot be committed at all.
    """

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]

    workspace.editClip(str(clip.id))
    workspace.setDraftEndText(timecode.precise(4_000))
    workspace.setDraftStartText(timecode.precise(9_000))
    workspace.commitDraft()

    assert document.analysis.clip(clip.id) == clip
    assert workspace.draftError == END_BEFORE_START
    assert workspace.draftValid is False
    assert workspace.editing is True


def test_cancelling_an_edit_leaves_the_clip_and_the_workspace_as_they_were(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 4: leaving the editing state is `editing`, not a width.

    The Widgets case asserted that the Clip-editor area went back to zero
    pixels. The QML shell binds that room to `editing`, and that the 360px is
    taken and given back is `tests/test_qml_workspace.py::
    test_the_editor_takes_its_room_from_the_video_and_gives_it_back`.
    """

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]

    workspace.editClip(str(clip.id))
    workspace.setDraftName("Never applied")
    set_boundaries(workspace, 4_000, 9_500)
    workspace.cancelDraft()

    assert document.analysis.clip(clip.id) == clip
    assert workspace.editing is False
    assert workspace.draftName == ""


def test_editing_a_clip_from_the_clips_list_opens_the_paused_editing_state(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """One editor serves both paths, and it keeps a paused frame beside it."""

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]
    player.play()

    workspace.editClip(str(clip.id))

    assert player.is_playing() is False
    assert workspace.playing is False
    assert player.position() == clip.start_ms
    assert workspace.editing is True
    assert workspace.draftName == clip.name
    assert (workspace.draftStartMs, workspace.draftEndMs) == (
        clip.start_ms,
        clip.end_ms,
    )


def test_editing_an_existing_clip_abandons_the_pending_clip(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """The workspace is in one editing state at a time, and the mark says so."""

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]
    workspace.seek(30_000)
    workspace.markBoundary()
    assert workspace.pendingActive is True

    workspace.editClip(str(clip.id))

    assert workspace.pendingActive is False
    assert workspace.markActionText == "Clip markieren"
    assert workspace.editing is True
    assert workspace.draftIsNew is False


def test_the_editing_form_carries_the_whole_clip(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Title, Category, both boundaries and notes all survive the round trip."""

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace, name="Fast break", category="Angriff")
    clip = document.analysis.clips[0]

    workspace.editClip(str(clip.id))
    workspace.setDraftNotes("Left wing")
    set_boundaries(workspace, 4_000, 9_500)
    workspace.commitDraft()

    workspace.editClip(str(clip.id))
    assert workspace.draftName == "Fast break"
    assert [row["name"] for row in workspace.categoryModel.rows() if row["selected"]] == [
        "Angriff"
    ]
    assert (workspace.draftStartMs, workspace.draftEndMs) == (4_000, 9_500)
    assert workspace.draftNotes == "Left wing"


def test_a_clip_without_a_title_is_reported_and_cannot_be_kept(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 3 again: the refusal is in the form, not in a modal."""

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]

    workspace.editClip(str(clip.id))
    workspace.setDraftName("   ")
    workspace.commitDraft()

    assert document.analysis.clip(clip.id) == clip
    assert workspace.draftError == NO_TITLE
    assert workspace.draftValid is False
    assert workspace.editing is True


def test_a_rejected_clip_change_leaves_the_document_as_it_was(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    save_to(workspace, presenter, tmp_path / "match.analysis")
    clip = document.analysis.clips[0]
    revision = document.analysis.revision

    workspace.editClip(str(clip.id))
    workspace.setDraftName("   ")
    workspace.setDraftCategory(category_id(workspace, "Abwehr"))
    workspace.commitDraft()

    assert document.analysis.clip(clip.id) == clip
    assert document.analysis.revision == revision
    assert document.dirty is False
    assert workspace.dirty is False


def test_removing_a_clip_removes_it_from_the_analysis(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]

    workspace.removeClip(str(clip.id))

    assert document.analysis.clips == ()
    assert clip_rows(workspace) == []
    assert ranges(workspace) == []


def test_removing_a_category_keeps_its_clips_uncategorized(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    clip = document.analysis.clips[0]

    assert clip.category_id is not None
    workspace.removeCategory(str(clip.category_id))

    assert document.analysis.clip(clip.id).category_id is None
    assert category_row(workspace, "Angriff") is None
    rendered = clip_rows(workspace)
    assert [row["clipId"] for row in rendered] == [str(clip.id)]
    assert rendered[0]["categoryName"] == UNCATEGORIZED_LABEL


def test_renaming_the_analysis_retitles_it_without_touching_its_identity(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    analysis_id = document.analysis.id

    workspace.setAnalysisTitle("Spiel gegen Musterstadt")

    assert document.analysis.title == "Spiel gegen Musterstadt"
    assert document.analysis.id == analysis_id
    assert workspace.analysisTitle == "Spiel gegen Musterstadt"


def test_playback_position_and_selection_do_not_dirty_the_document(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    save_to(workspace, presenter, tmp_path / "match.analysis")
    assert workspace.dirty is False
    clip_id = clip_rows(workspace)[0]["clipId"]

    workspace.seek(4_200)
    player.set_duration(90_000)
    workspace.selectClip(clip_id)
    workspace.setSidebarTab("videos")
    workspace.navigateToClip(clip_id)

    assert document.dirty is False
    assert workspace.dirty is False


# --- Saving, opening and the unsaved-changes gate ---------------------------


def test_saving_and_reopening_preserves_identities_and_content(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    analysis_id = document.analysis.id
    clip_id = clip_rows(workspace)[0]["clipId"]
    analysis_path = tmp_path / "match.analysis"

    save_to(workspace, presenter, analysis_path)

    assert workspace.dirty is False
    assert analysis_path.read_bytes().lstrip().startswith(b"{")

    presenter.analysis_to_open = str(analysis_path)
    assert workspace.openAnalysis() is True
    loop.advance(PRIMING_MS * 2)

    reopened = AnalysisDocument.new()
    reopened.load(analysis_path)
    assert reopened.analysis.id == analysis_id

    assert workspace.analysisTitle == "first-half"
    assert [row["clipId"] for row in clip_rows(workspace)] == [clip_id]
    assert clip_rows(workspace)[0]["title"] == "Fast break"
    assert clips_under(workspace, "Angriff")[0]["clipId"] == clip_id
    assert workspace.dirty is False


def test_filing_a_clip_under_a_category_and_taking_it_off_round_trips_through_save_and_reopen(
    workspace: WorkspaceViewModel,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """#68: the startup Analysis must offer the same Categories File > New does.

    Filing survives a save and reopen because a Clip's `category_id` is
    ordinary Analysis content; taking the Category off again and reopening
    once more proves the codec preserves "no Category" just as faithfully as
    it preserves one, rather than defaulting an absent field back onto the
    first Category in the file.
    """

    add_video(workspace, presenter, loop, tmp_path)
    clip_id = mark_clip(workspace, category="Angriff")
    analysis_path = tmp_path / "match.analysis"
    save_to(workspace, presenter, analysis_path)

    presenter.analysis_to_open = str(analysis_path)
    assert workspace.openAnalysis() is True
    loop.advance(PRIMING_MS * 2)
    presenter.analysis_to_open = None

    assert clips_under(workspace, "Angriff")[0]["clipId"] == clip_id

    workspace.editClip(clip_id)
    workspace.setDraftCategory("")
    workspace.commitDraft()
    save_to(workspace, presenter, analysis_path)

    presenter.analysis_to_open = str(analysis_path)
    assert workspace.openAnalysis() is True
    loop.advance(PRIMING_MS * 2)
    presenter.analysis_to_open = None

    assert clips_under(workspace, "Angriff") == []
    assert clip_row(workspace, "Fast break")["categoryName"] == "Ohne Kategorie"


def test_a_cancelled_save_prevents_close_and_keeps_unsaved_work(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    presenter.choice = UnsavedChangesChoice.SAVE
    presenter.destination = None

    assert workspace.requestClose() is False

    assert document.dirty is True
    assert len(document.analysis.clips) == 1
    assert len(clip_rows(workspace)) == 1


def test_cancelling_the_prompt_keeps_the_current_analysis_loaded(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    presenter.choice = UnsavedChangesChoice.CANCEL

    assert workspace.newAnalysis() is False

    assert len(document.analysis.clips) == 1
    assert len(clip_rows(workspace)) == 1
    assert presenter.questions == 1


def test_discarding_starts_a_new_empty_analysis(
    workspace: WorkspaceViewModel,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    presenter.choice = UnsavedChangesChoice.DISCARD

    assert workspace.newAnalysis() is True

    assert clip_rows(workspace) == []
    assert source_rows(workspace) == []
    assert workspace.hasVideo is False
    assert workspace.analysisTitle == UNTITLED_ANALYSIS_TITLE
    assert workspace.dirty is False


# --- Several Source videos in one Analysis ---------------------------------


def test_adding_a_second_video_keeps_the_first_and_its_clips(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)

    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")

    assert [source.display_name for source in document.analysis.source_videos] == [
        "first-half.mp4",
        "second-half.mp4",
    ]
    assert [row["name"] for row in source_rows(workspace)] == [
        "first-half.mp4",
        "second-half.mp4",
    ]
    assert len(document.analysis.clips) == 1
    assert document.analysis.title == "first-half"


def test_a_dropped_video_is_added_to_the_current_analysis(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    dropped = tmp_path / "second-half.MOV"
    dropped.write_bytes(f"not a real video: {dropped.name}".encode())

    assert workspace.addDroppedSourceVideos([QUrl.fromLocalFile(str(dropped))]) is True

    assert len(document.analysis.source_videos) == 2


def test_a_dropped_file_of_another_kind_is_ignored(
    workspace: WorkspaceViewModel, document: AnalysisDocument, tmp_path: Path
) -> None:
    note = tmp_path / "notes.txt"
    note.write_text("nothing to see", encoding="utf-8")

    assert workspace.addDroppedSourceVideos([QUrl.fromLocalFile(str(note))]) is False
    assert document.analysis.source_videos == ()


def test_the_window_title_reports_the_analysis_and_its_dirty_state(
    workspace: WorkspaceViewModel,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    assert workspace.windowTitle == f"{UNTITLED_ANALYSIS_TITLE} — {APPLICATION_TITLE}"

    add_video(workspace, presenter, loop, tmp_path)
    assert workspace.windowTitle == f"• first-half — {APPLICATION_TITLE}"

    save_to(workspace, presenter, tmp_path / "match.analysis")
    assert workspace.windowTitle == f"first-half — {APPLICATION_TITLE}"

    mark_clip(workspace)
    assert workspace.windowTitle == f"• first-half — {APPLICATION_TITLE}"


def test_save_as_writes_the_analysis_to_a_second_file(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    save_to(workspace, presenter, tmp_path / "match.analysis")

    copy_path = tmp_path / "copy.analysis"
    presenter.destination = str(copy_path)
    assert workspace.saveAnalysisAs() is True

    assert copy_path.is_file()
    assert document.path == copy_path
    assert workspace.dirty is False


def test_a_failed_open_leaves_the_current_analysis_untouched(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    broken = tmp_path / "broken.analysis"
    broken.write_text("{ not json", encoding="utf-8")
    presenter.choice = UnsavedChangesChoice.DISCARD
    presenter.analysis_to_open = str(broken)

    assert workspace.openAnalysis() is False

    assert len(document.analysis.clips) == 1
    assert len(clip_rows(workspace)) == 1
    assert workspace.analysisTitle == "first-half"
    assert presenter.failures != []


def test_adding_a_video_does_not_interrupt_the_one_under_review(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    first_video = add_video(workspace, presenter, loop, tmp_path)

    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")

    first = document.analysis.source_videos[0]
    assert first.location == str(first_video)
    active = active_source(workspace)
    assert active is not None
    assert active["sourceId"] == str(first.id)
    assert player.location() == str(first_video)

    mark_clip(workspace, name="Fast break")
    assert document.analysis.clips[0].source_video_id == first.id


# --- The transport ---------------------------------------------------------


def test_navigating_to_a_clip_seeks_the_player_to_its_start(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    clip_id = mark_clip(workspace, start_ms=12_000, end_ms=14_000)

    workspace.seek(0)
    workspace.navigateToClip(clip_id)

    assert player.position() == 12_000
    assert workspace.positionMs == 12_000


def test_a_clip_is_marked_against_the_player_position(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    player.play()
    workspace.seek(30_000)
    workspace.markBoundary()
    workspace.seek(35_000)

    workspace.markBoundary()

    assert player.is_playing() is False
    assert workspace.editing is True
    assert (workspace.draftStartMs, workspace.draftEndMs) == (30_000, 35_000)
    assert workspace.draftIsNew is True


def test_the_play_control_follows_what_the_player_is_actually_doing(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)

    player.play()
    assert workspace.playing is True

    player.step_backward()
    assert workspace.playing is False


def test_choosing_a_playback_speed_sets_a_numeric_rate(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 6: 0.25x is not one of the speeds this application has."""

    add_video(workspace, presenter, loop, tmp_path)

    workspace.setRateIndex(PLAYBACK_RATES.index(0.5))

    assert player.playback_rate() == 0.5
    assert workspace.playbackRate == 0.5
    assert workspace.playbackRateIndex == PLAYBACK_RATES.index(0.5)


def test_adding_a_video_makes_it_the_active_source_video_of_the_player(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    video_path = add_video(workspace, presenter, loop, tmp_path)

    assert player.is_loaded() is True
    assert player.location() == str(video_path)
    assert workspace.hasVideo is True

    presenter.choice = UnsavedChangesChoice.DISCARD
    workspace.newAnalysis()

    assert player.is_loaded() is False
    assert workspace.hasVideo is False


def test_playing_stepping_and_speed_never_dirty_the_document(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace)
    save_to(workspace, presenter, tmp_path / "match.analysis")

    workspace.playPause()
    workspace.seek(20_000)
    workspace.stepForward()
    workspace.stepBackward()
    workspace.jumpForward()
    workspace.jumpBackward()
    workspace.setRateIndex(PLAYBACK_RATES.index(2.0))
    workspace.toggleMuted()
    workspace.setVolume(0.4)
    workspace.playPause()

    assert document.dirty is False
    assert workspace.dirty is False


def test_the_play_control_does_not_claim_to_play_with_no_video_loaded(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    workspace.playPause()

    assert player.is_playing() is False
    assert workspace.playing is False


# --- The shape of the workspace --------------------------------------------


def test_the_workspace_is_composed_in_code_without_the_designer_window() -> None:
    """The Designer main window is retired; see ADR 0005."""

    repository_root = Path(workspace_module.__file__).parent

    assert importlib.util.find_spec("Ui_main_window") is None
    assert not (repository_root / "main_window.ui").exists()
    assert not (repository_root / "Ui_main_window.py").exists()


def test_an_analysis_without_source_videos_renders_the_normal_workspace(
    workspace: WorkspaceViewModel,
) -> None:
    """There is no separate welcome screen; only the player's place changes."""

    assert workspace.hasVideo is False
    assert SIDEBAR_TABS == ("clips", "videos")
    assert workspace.sidebarTab == "clips"
    assert source_rows(workspace) == []
    assert clip_rows(workspace) == []
    assert ranges(workspace) == []


def test_the_call_to_action_adds_a_video_and_gives_way_to_the_player(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "first-half.mp4"
    video_path.write_bytes(f"not a real video: {video_path.name}".encode())
    presenter.source_video = str(video_path)

    assert workspace.addSourceVideo() is True
    loop.advance(PRIMING_MS * 2)

    assert [source.location for source in document.analysis.source_videos] == [
        str(video_path)
    ]
    assert workspace.hasVideo is True


def test_the_clip_editing_state_takes_its_room_beside_the_video(
    workspace: WorkspaceViewModel,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 4: the room is `editing`; the pixels are the shell's."""

    add_video(workspace, presenter, loop, tmp_path)
    assert workspace.editing is False

    workspace.seek(30_000)
    workspace.markBoundary()
    workspace.seek(35_000)
    workspace.markBoundary()

    assert workspace.editing is True

    workspace.cancelDraft()
    assert workspace.editing is False


def test_the_transport_reports_where_the_player_is(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(5_400_000)

    workspace.seek(12_000)

    assert workspace.positionText == "00:00:12"
    assert workspace.durationText == "01:30:00"


def test_a_category_colour_is_drawn_without_changing_the_analysis(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 10: drawing a Category never edits its colour.

    The Widgets interface muted the colour to draw Category text with it; ADR
    0007 replaced that with a colour bar in the harmonised palette, so there is
    no muting left to assert. What survives is that the row carries exactly the
    colour the Analysis holds, and that the Analysis's own value is untouched.
    """

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace, category="Angriff")
    category = document.analysis.category_named("Angriff")

    assert category is not None
    assert category.color == "#EF4444"
    row = category_row(workspace, "Angriff")
    assert row is not None
    assert row["categoryColor"] == "#EF4444"
    assert clips_under(workspace, "Angriff")[0]["categoryColor"] == "#EF4444"
    assert ranges(workspace)[0]["color"] == "#EF4444"
    unchanged_category = document.analysis.category_named("Angriff")
    assert unchanged_category is not None
    assert unchanged_category.color == "#EF4444"


# --- The one seek surface --------------------------------------------------
#
# Coverage change 5: what a pixel on the track means in milliseconds is QML's
# arithmetic and is covered by `tests/test_qml_timeline.py`. What is here is
# the seam's half of the same grammar (ADR 0006).


def test_the_timeline_shows_the_clips_of_the_active_source_video_only(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(60_000)
    clip_id = mark_clip(workspace, name="Fast break", start_ms=30_000, end_ms=40_000)
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    first, second = document.analysis.source_videos

    workspace.selectSourceVideo(str(second.id))
    loop.advance(PRIMING_MS * 2)

    active = active_source(workspace)
    assert active is not None
    assert active["sourceId"] == str(second.id)
    assert ranges(workspace) == []

    workspace.selectSourceVideo(str(first.id))
    loop.advance(PRIMING_MS * 2)

    assert [row["clipId"] for row in ranges(workspace)] == [clip_id]
    assert (ranges(workspace)[0]["startMs"], ranges(workspace)[0]["endMs"]) == (
        30_000,
        40_000,
    )


def test_scrubbing_the_timeline_moves_the_player_to_that_time(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(60_000)

    workspace.scrubTo(30_000)

    assert player.position() == 30_000
    assert workspace.positionMs == 30_000


def test_selecting_a_clip_range_does_not_move_the_playhead(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """ADR 0006: the click scrubs to the pointer, not to the Clip's start."""

    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(60_000)
    clip_id = mark_clip(workspace, name="Fast break", start_ms=30_000, end_ms=40_000)

    loop.advance(SCRUB_INTERVAL_MS * 2)
    workspace.scrubTo(35_000)
    workspace.selectClip(clip_id)

    assert workspace.selectedClipId == clip_id
    assert player.position() == 35_000
    selected = next(row for row in ranges(workspace) if row["selected"])
    assert [row["title"] for row in clip_rows(workspace) if row["selected"]] == [
        "Fast break"
    ]
    assert selected["title"] == "Fast break"
    assert (selected["startMs"], selected["endMs"]) == (30_000, 40_000)
    assert clip_row(workspace, "Fast break")["startText"] == "00:00:30"
    assert clip_row(workspace, "Fast break")["durationText"] == timecode.duration(
        10_000
    )


def test_double_clicking_a_clip_range_seeks_to_the_clip_start(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(60_000)
    clip_id = mark_clip(workspace, name="Fast break", start_ms=30_000, end_ms=40_000)
    loop.advance(SCRUB_INTERVAL_MS * 2)
    workspace.scrubTo(35_000)

    workspace.navigateToClip(clip_id)

    assert player.position() == 30_000
    assert workspace.selectedClipId == clip_id


def test_navigating_to_a_clip_activates_its_source_video_and_the_timeline_follows(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """The seam the Clips sidebar tab (#15) navigates through."""

    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(60_000)
    second_video = add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    second = document.analysis.source_videos[1]
    clip = document.analysis.add_clip(second.id, "Counter", 20_000, 25_000)
    workspace.refresh()

    workspace.navigateToClip(str(clip.id))
    loop.advance(PRIMING_MS * 2)

    active = active_source(workspace)
    assert active is not None
    assert active["sourceId"] == str(second.id)
    assert player.location() == str(second_video)
    assert player.position() == 20_000
    assert workspace.selectedClipId == str(clip.id)
    assert [row["clipId"] for row in ranges(workspace)] == [str(clip.id)]


def test_the_timeline_never_dirties_the_analysis_document(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
    player: FakePlayback,
) -> None:
    """Selection and playhead are transient, exactly like playback state."""

    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(60_000)
    clip_id = mark_clip(workspace, start_ms=30_000, end_ms=40_000)
    save_to(workspace, presenter, tmp_path / "match.analysis")
    assert workspace.dirty is False

    loop.advance(SCRUB_INTERVAL_MS * 2)
    workspace.scrubTo(35_000)
    workspace.selectClip(clip_id)
    workspace.navigateToClip(clip_id)
    workspace.layoutRuler(600.0, 60_000.0)
    workspace.selectSourceVideo(str(document.analysis.source_videos[0].id))

    assert document.dirty is False
    assert workspace.dirty is False


def test_navigating_within_the_active_source_video_does_not_reload_it(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Reloading would drop the frame under review and the known duration."""

    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(60_000)
    clip_id = mark_clip(workspace, start_ms=30_000, end_ms=40_000)

    workspace.navigateToClip(clip_id)

    assert player.duration() == 60_000
    assert workspace.durationMs == 60_000
    assert player.position() == 30_000


def test_dragging_along_the_timeline_scrubs_the_player_continuously(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(60_000)

    workspace.scrubTo(6_000)
    assert player.position() == 6_000

    loop.advance(100)
    workspace.scrubTo(30_000)
    workspace.endScrub()
    loop.advance(100)

    assert player.position() == 30_000
    assert workspace.positionMs == 30_000


class LateDurationPlayback(FakePlayback):
    """Media that still reports the previous length just after it is loaded.

    Real media behaves this way: the player announces the new duration a
    moment after its source is set.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stale_duration = 0

    def load(self, location: str) -> None:
        previous_duration = self.duration()
        super().load(location)
        self._stale_duration = previous_duration

    def set_duration(self, duration_ms: int) -> None:
        self._stale_duration = 0
        super().set_duration(duration_ms)

    def duration(self) -> int:
        return self._stale_duration or super().duration()


def test_a_previous_source_videos_length_never_scales_the_active_one(
    application: QApplication,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """The timeline draws no time scale until the player reports one."""

    player = LateDurationPlayback()
    workspace = WorkspaceViewModel(
        new_analysis_document(),
        player,
        presenter=presenter,
        schedule=loop.schedule,
        clock=loop.clock,
        ticker=loop,
    )
    add_video(workspace, presenter, loop, tmp_path)
    player.set_duration(5_400_000)
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    workspace.layoutRuler(600.0, 5_400_000.0)

    workspace.selectSourceVideo(str(source_rows(workspace)[1]["sourceId"]))
    loop.advance(PRIMING_MS * 2)

    assert player.duration() == 5_400_000
    assert workspace.durationMs == 0
    assert workspace.durationText == "00:00:00"
    assert workspace.rulerModel.rows() == ()


# --- The Clips and Videos sidebar (#15) ------------------------------------


def test_the_videos_tab_lists_every_source_video_of_the_analysis(
    workspace: WorkspaceViewModel,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")

    workspace.setSidebarTab("videos")

    assert workspace.sidebarTab == "videos"
    assert [row["name"] for row in source_rows(workspace)] == [
        "first-half.mp4",
        "second-half.mp4",
    ]


def test_selecting_a_source_video_switches_the_player_to_it(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Coverage change 5: choosing a row is the slot; the click is QML's.

    That a row in the Videos tab is a hit target and that clicking it calls
    this slot is `tests/test_qml_sidebar.py::
    test_choosing_a_source_video_in_the_videos_tab_activates_it`; the
    replacement keyboard path is covered there too.
    """

    add_video(workspace, presenter, loop, tmp_path)
    second_video = add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    second = document.analysis.source_videos[1]

    workspace.selectSourceVideo(str(second.id))
    loop.advance(PRIMING_MS * 2)

    active = active_source(workspace)
    assert active is not None
    assert active["sourceId"] == str(second.id)
    assert player.location() == str(second_video)


def test_marking_a_clip_without_a_video_leaves_the_transport_honest(
    workspace: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    """Coverage change 7: the mark action is disabled rather than explained."""

    assert workspace.hasVideo is False

    workspace.markBoundary()

    assert workspace.pendingActive is False
    assert workspace.markActionText == "Clip markieren"
    assert workspace.editing is False
    assert document.analysis.clips == ()


def test_each_clip_row_names_the_source_video_it_belongs_to(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """The cue that keeps the Clips tab readable while Videos is not visible."""

    add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace, name="Fast break")
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    workspace.selectSourceVideo(str(document.analysis.source_videos[1].id))
    loop.advance(PRIMING_MS * 2)
    mark_clip(workspace, name="Counter", start_ms=3_000, end_ms=4_000)

    assert {row["title"]: row["sourceCue"] for row in clip_rows(workspace)} == {
        "Fast break": "first-half.mp4",
        "Counter": "second-half.mp4",
    }


def test_selecting_a_clip_in_the_clips_tab_activates_its_source_video(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    first_video = add_video(workspace, presenter, loop, tmp_path)
    clip_id = mark_clip(workspace, name="Fast break", start_ms=12_000, end_ms=14_000)
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    workspace.selectSourceVideo(str(document.analysis.source_videos[1].id))
    loop.advance(PRIMING_MS * 2)

    workspace.navigateToClip(clip_id)
    loop.advance(PRIMING_MS * 2)

    active = active_source(workspace)
    assert active is not None
    assert active["sourceId"] == str(
        document.analysis.source_videos[0].id
    )
    assert player.location() == str(first_video)
    assert player.position() == 12_000
    assert workspace.selectedClipId == clip_id


def test_a_new_clip_is_bound_to_the_source_video_it_was_marked_on(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    second = document.analysis.source_videos[1]
    workspace.selectSourceVideo(str(second.id))
    loop.advance(PRIMING_MS * 2)

    mark_clip(workspace, name="Counter", start_ms=10_000, end_ms=12_000)

    clip = document.analysis.clips[0]
    assert clip.source_video_id == second.id
    assert (clip.start_ms, clip.end_ms) == (10_000, 12_000)


def test_a_pending_clip_cannot_produce_a_clip_on_another_source_video(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """A Pending Clip belongs to the Source video its start was marked on."""

    add_video(workspace, presenter, loop, tmp_path)
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    workspace.seek(30_000)
    workspace.markBoundary()
    assert workspace.pendingActive is True

    workspace.selectSourceVideo(str(document.analysis.source_videos[1].id))
    loop.advance(PRIMING_MS * 2)
    workspace.seek(5_000)
    workspace.markBoundary()

    assert document.analysis.clips == ()
    assert workspace.editing is False
    assert workspace.pendingActive is True
    assert workspace.pendingStartMs == 5_000


def test_switching_source_video_discards_a_clip_that_was_never_created(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    workspace.seek(30_000)
    workspace.markBoundary()
    workspace.seek(35_000)
    workspace.markBoundary()
    assert workspace.editing is True

    workspace.cancelDraft()
    workspace.selectSourceVideo(str(document.analysis.source_videos[1].id))
    loop.advance(PRIMING_MS * 2)

    assert workspace.editing is False
    assert workspace.pendingActive is False
    assert document.analysis.clips == ()


def test_cancelling_a_marked_clip_leaves_nothing_behind(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    add_video(workspace, presenter, loop, tmp_path)
    workspace.seek(30_000)
    workspace.markBoundary()
    workspace.seek(35_000)
    workspace.markBoundary()

    workspace.cancelDraft()

    assert document.analysis.clips == ()
    assert workspace.editing is False
    assert workspace.pendingActive is False
    assert clip_rows(workspace) == []


def test_several_source_videos_and_their_clips_survive_save_and_reopen(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    first_video = add_video(workspace, presenter, loop, tmp_path)
    mark_clip(workspace, name="Fast break")
    second_video = add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    workspace.selectSourceVideo(str(document.analysis.source_videos[1].id))
    loop.advance(PRIMING_MS * 2)
    mark_clip(workspace, name="Counter", start_ms=10_000, end_ms=12_000)
    belongs_to = {row["title"]: row["sourceCue"] for row in clip_rows(workspace)}
    analysis_path = tmp_path / "match.analysis"
    save_to(workspace, presenter, analysis_path)

    presenter.analysis_to_open = str(analysis_path)
    assert workspace.openAnalysis() is True
    loop.advance(PRIMING_MS * 2)

    assert [row["name"] for row in source_rows(workspace)] == [
        first_video.name,
        second_video.name,
    ]
    assert {row["title"]: row["sourceCue"] for row in clip_rows(workspace)} == belongs_to


def test_the_sidebar_tab_and_the_active_source_video_are_never_stored(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """Display state is not analytical work: it neither dirties nor persists."""

    first_video = add_video(workspace, presenter, loop, tmp_path)
    clip_id = mark_clip(workspace, name="Fast break")
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    analysis_path = tmp_path / "match.analysis"
    save_to(workspace, presenter, analysis_path)
    assert workspace.dirty is False

    workspace.setSidebarTab("videos")
    workspace.selectSourceVideo(str(document.analysis.source_videos[1].id))
    loop.advance(PRIMING_MS * 2)
    workspace.navigateToClip(clip_id)
    loop.advance(PRIMING_MS * 2)

    assert document.dirty is False
    assert workspace.dirty is False

    presenter.analysis_to_open = str(analysis_path)
    assert workspace.openAnalysis() is True
    loop.advance(PRIMING_MS * 2)

    # The tab is session state and deliberately survives; what must not
    # survive is anything the file could have carried.
    assert workspace.sidebarTab == "videos"
    active = active_source(workspace)
    assert active is not None
    assert active["name"] == first_video.name
    assert player.location() == str(first_video)


# --- Protecting unsaved work (#19) -------------------------------------------


class RecordingRecoveryScheduler:
    """A debounce scheduler a case fires by hand instead of waiting on it."""

    def __init__(self) -> None:
        self.schedule_count = 0
        self.cancel_count = 0
        self._pending = None

    def schedule(self, run) -> None:  # type: ignore[no-untyped-def]
        self.schedule_count += 1
        self._pending = run

    def cancel(self) -> None:
        self.cancel_count += 1
        self._pending = None

    def fire(self) -> None:
        assert self._pending is not None, "nothing was scheduled"
        pending, self._pending = self._pending, None
        pending()


def test_marking_a_clip_arms_recovery_but_switching_video_and_saving_do_not_linger(
    application: QApplication,
    presenter: RecordingPresenter,
    loop: Loop,
    tmp_path: Path,
) -> None:
    """The Recovery contract this ticket adds, driven the same way as the rest
    of this suite: no window, no QML engine, no media.

    A durable Clip change arms a debounced Recovery snapshot; switching the
    Active Source video does not; and a successful save removes it, so a
    clean close never leaves stale Recovery data an analyst was never told
    about behind.
    """

    document = new_analysis_document()
    recovery_store = RecoverySnapshotStore(tmp_path / "recovery")
    scheduler = RecordingRecoveryScheduler()
    workspace = WorkspaceViewModel(
        document,
        FakePlayback(),
        presenter=presenter,
        schedule=loop.schedule,
        clock=loop.clock,
        ticker=loop,
        recovery_store=recovery_store,
        recovery_scheduler=scheduler,
    )
    add_video(workspace, presenter, loop, tmp_path)
    add_video(workspace, presenter, loop, tmp_path, "second-half.mp4")
    scheduler.schedule_count = 0  # ignore whatever adding the Source videos armed

    mark_clip(workspace, name="Fast break")
    assert scheduler.schedule_count == 1
    scheduler.fire()
    assert recovery_store.read() is not None

    scheduler.schedule_count = 0
    workspace.selectSourceVideo(str(document.analysis.source_videos[1].id))
    loop.advance(PRIMING_MS * 2)
    assert scheduler.schedule_count == 0, "the Active Source video is not content"

    save_to(workspace, presenter, tmp_path / "match.analysis")
    assert workspace.dirty is False
    assert recovery_store.read() is None
