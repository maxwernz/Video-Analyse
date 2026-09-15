"""The Clip-editing state, as an analyst uses it, with no window running.

Marking a Clip and editing one are the same state: a draft held apart from the
Analysis, a form over it, and two ways out. Everything that matters about it —
that completing the second boundary pauses the video and opens the editor,
that a boundary moves the video to the frame it names, that saving reaches the
Analysis exactly once, and that neither cancel path leaves anything behind —
is behaviour of the view-model seam rather than of any pixel, so it is tested
here against the fake player.

What needs a window — that the form is a form, that its bindings resolve, and
that the buttons in it are wired to these slots — is in
`tests/test_qml_clip_editor.py`.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

import timecode  # noqa: E402
from analysis import Analysis, AnalysisDocument, Clip  # noqa: E402
from clip_editor import MINIMUM_CLIP_MS, NEW_CLIP_NAME  # noqa: E402
from playback import FakePlayback  # noqa: E402
from workspace_view_model import WorkspaceViewModel  # noqa: E402


FIRST_HALF = "/videos/halbzeit-1.mp4"
SECOND_HALF = "/videos/halbzeit-2.mp4"
HALF_MS = 45 * 60_000


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


class Scheduler:
    """The event loop, stood in for, so priming is not a wait."""

    def __init__(self) -> None:
        self.pending: list[tuple[int, object]] = []

    def __call__(self, delay_ms: int, run) -> None:  # type: ignore[no-untyped-def]
        self.pending.append((delay_ms, run))

    def elapse(self) -> None:
        due, self.pending = self.pending, []
        for _, run in due:
            run()  # type: ignore[operator]


@pytest.fixture
def analysis() -> Analysis:
    analysis = Analysis("SG Beispiel - TV Muster")
    analysis.add_source_video("halbzeit-1.mp4", FIRST_HALF, duration_ms=HALF_MS)
    analysis.add_source_video("halbzeit-2.mp4", SECOND_HALF, duration_ms=HALF_MS)
    analysis.add_category("Tore", color="#E2564A")
    analysis.add_category("Abwehr", color="#4BA46A")
    return analysis


@pytest.fixture
def document(analysis: Analysis) -> AnalysisDocument:
    return AnalysisDocument(analysis)


@pytest.fixture
def player(application: QApplication) -> FakePlayback:
    return FakePlayback()


@pytest.fixture
def scheduler() -> Scheduler:
    return Scheduler()


@pytest.fixture
def workspace(
    document: AnalysisDocument, player: FakePlayback, scheduler: Scheduler
) -> WorkspaceViewModel:
    view_model = WorkspaceViewModel(document, player, schedule=scheduler)
    # Let the newly activated Source video finish being primed, so that what
    # the tests below see playing or paused is the analyst's doing.
    scheduler.elapse()
    player.set_duration(HALF_MS)
    return view_model


def at(workspace: WorkspaceViewModel, player: FakePlayback, position_ms: int) -> None:
    """Put the video, and the playhead, where the analyst has scrubbed to."""

    workspace.seek(position_ms)


def mark_a_clip(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    start_ms: int,
    end_ms: int,
) -> None:
    """The two presses that make a Clip, from the position of each."""

    at(workspace, player, start_ms)
    workspace.markBoundary()
    at(workspace, player, end_ms)
    workspace.markBoundary()


# --- The Pending Clip ------------------------------------------------------


def test_the_workspace_opens_with_no_pending_clip_and_no_editor(
    workspace: WorkspaceViewModel,
) -> None:
    assert workspace.pendingActive is False
    assert workspace.editing is False


def test_the_first_boundary_marks_a_pending_clip_without_touching_the_analysis(
    workspace: WorkspaceViewModel, player: FakePlayback, analysis: Analysis
) -> None:
    at(workspace, player, 600_000)
    workspace.markBoundary()

    assert workspace.pendingActive is True
    assert workspace.pendingStartMs == 600_000
    assert workspace.editing is False
    assert analysis.clips == ()


def test_the_pending_clip_says_where_it_began_and_how_long_it_is_so_far(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    at(workspace, player, 600_000)
    workspace.markBoundary()
    at(workspace, player, 612_000)

    assert timecode.clock(600_000) in workspace.pendingText
    assert timecode.duration(12_000) in workspace.pendingText


def test_the_mark_action_says_which_of_the_two_presses_is_next(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    first = workspace.markActionText
    at(workspace, player, 600_000)
    workspace.markBoundary()

    assert workspace.markActionText != first


def test_a_boundary_cannot_be_marked_without_a_source_video(
    application: QApplication, player: FakePlayback, scheduler: Scheduler
) -> None:
    empty = WorkspaceViewModel(AnalysisDocument.new("Ohne Video"), player, schedule=scheduler)

    empty.markBoundary()

    assert empty.pendingActive is False
    assert empty.editing is False


def test_switching_source_video_abandons_the_mark_made_on_the_other_one(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    analysis: Analysis,
    scheduler: Scheduler,
) -> None:
    """A Clip belongs to the video its start was marked on, or to nothing."""

    at(workspace, player, 600_000)
    workspace.markBoundary()

    workspace.selectSourceVideo(str(analysis.source_videos[1].id))
    scheduler.elapse()

    assert workspace.pendingActive is False


def test_a_pending_clip_can_be_abandoned_on_purpose(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    at(workspace, player, 600_000)
    workspace.markBoundary()

    workspace.cancelPending()

    assert workspace.pendingActive is False
    assert workspace.editing is False


# --- Entering the editing state --------------------------------------------


def test_the_second_boundary_pauses_the_video_and_opens_the_editor(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    at(workspace, player, 600_000)
    workspace.markBoundary()
    player.play()
    at(workspace, player, 612_000)

    workspace.markBoundary()

    assert workspace.editing is True
    assert workspace.playing is False
    assert workspace.pendingActive is False
    assert workspace.draftIsNew is True
    assert workspace.draftStartMs == 600_000
    assert workspace.draftEndMs == 612_000


def test_a_clip_marked_backwards_still_begins_before_it_ends(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    """An analyst who saw the moment first and rewound has marked a Clip."""

    mark_a_clip(workspace, player, 612_000, 600_000)

    assert workspace.draftStartMs == 600_000
    assert workspace.draftEndMs == 612_000


def test_two_presses_at_the_same_moment_still_make_a_clip_with_a_length(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 600_000)

    assert workspace.draftEndMs - workspace.draftStartMs >= MINIMUM_CLIP_MS


def test_a_clip_marked_at_the_very_end_stays_inside_the_recording(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, HALF_MS, HALF_MS)

    assert workspace.draftEndMs <= HALF_MS
    assert workspace.draftStartMs < workspace.draftEndMs


def test_a_new_clip_arrives_named_so_the_form_is_never_blank(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    assert workspace.draftName == NEW_CLIP_NAME
    assert workspace.draftValid is True


def test_the_editor_shows_the_boundaries_it_is_editing_to_the_millisecond(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_400, 612_000)

    assert workspace.draftStartText == timecode.precise(600_400)
    assert workspace.draftEndText == timecode.precise(612_000)


# --- Editing an existing Clip ----------------------------------------------


@pytest.fixture
def clip(analysis: Analysis) -> Clip:
    return analysis.add_clip(
        analysis.source_videos[0].id,
        "Gegenstoss",
        600_000,
        612_000,
        notes="Zweite Welle",
        category_id=analysis.categories[0].id,
    )


def test_the_same_state_edits_an_existing_clip(
    workspace: WorkspaceViewModel, clip: Clip, player: FakePlayback
) -> None:
    workspace.refresh()

    workspace.editClip(str(clip.id))

    assert workspace.editing is True
    assert workspace.draftIsNew is False
    assert workspace.draftName == "Gegenstoss"
    assert workspace.draftNotes == "Zweite Welle"
    assert workspace.draftStartMs == clip.start_ms
    assert workspace.draftEndMs == clip.end_ms
    assert workspace.playing is False


def test_editing_a_clip_of_another_source_video_activates_that_video(
    workspace: WorkspaceViewModel,
    analysis: Analysis,
    player: FakePlayback,
    scheduler: Scheduler,
) -> None:
    other = analysis.add_clip(
        analysis.source_videos[1].id, "Tor", 100_000, 104_000
    )
    workspace.refresh()

    workspace.editClip(str(other.id))
    scheduler.elapse()

    assert player.location() == SECOND_HALF
    assert workspace.editing is True


def test_editing_a_clip_that_is_not_in_the_analysis_opens_nothing(
    workspace: WorkspaceViewModel,
) -> None:
    workspace.editClip("not-a-clip")

    assert workspace.editing is False


def test_opening_the_editor_shows_the_frame_the_clip_begins_on(
    workspace: WorkspaceViewModel, clip: Clip, player: FakePlayback
) -> None:
    at(workspace, player, 0)
    workspace.refresh()

    workspace.editClip(str(clip.id))

    assert player.position() == clip.start_ms


def test_marking_a_clip_while_editing_one_is_not_a_second_pending_clip(
    workspace: WorkspaceViewModel, clip: Clip, player: FakePlayback
) -> None:
    workspace.refresh()
    workspace.editClip(str(clip.id))

    workspace.markBoundary()

    assert workspace.pendingActive is False
    assert workspace.draftIsNew is False


# --- The boundaries, and the video that follows them ------------------------


def test_adjusting_a_boundary_seeks_the_video_to_that_frame(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.setDraftStartText("00:09:55.500")
    assert workspace.draftStartMs == 595_500
    assert player.position() == 595_500

    workspace.setDraftEndText("00:10:20.000")
    assert workspace.draftEndMs == 620_000
    assert player.position() == 620_000


def test_a_boundary_the_analyst_is_typing_does_not_run_the_video_on(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    player.play()

    workspace.setDraftStartText("00:09:55.500")

    assert player.is_playing() is False


def test_a_boundary_can_be_nudged_a_frame_at_a_time_from_the_steppers(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.nudgeDraftBoundary("start", -100)
    workspace.nudgeDraftBoundary("end", 100)

    assert workspace.draftStartMs == 599_900
    assert workspace.draftEndMs == 612_100
    assert player.position() == 612_100


def test_a_boundary_can_be_taken_from_where_the_video_already_is(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    at(workspace, player, 605_000)

    workspace.takeDraftBoundaryFromPlayhead("end")

    assert workspace.draftEndMs == 605_000


def test_the_duration_updates_as_the_boundaries_move(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    assert workspace.draftDurationText == timecode.precise_duration(12_000)

    workspace.setDraftEndText("00:10:18.400")

    assert workspace.draftDurationText == timecode.precise_duration(18_400)


def test_a_boundary_may_not_be_taken_past_the_end_of_the_recording(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.setDraftEndText("99:00:00.000")

    assert workspace.draftEndMs == HALF_MS


def test_an_end_before_its_start_is_refused_with_an_explanation(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    """Silently swapping them would move a cut the analyst did not move."""

    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.setDraftEndText("00:09:00.000")

    assert workspace.draftEndMs == 612_000
    assert workspace.draftError != ""
    assert workspace.draftValid is False


def test_a_start_after_its_end_is_refused_the_same_way(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.setDraftStartText("00:11:00.000")

    assert workspace.draftStartMs == 600_000
    assert workspace.draftError != ""


def test_a_refused_boundary_leaves_the_video_where_it_was(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    at(workspace, player, 606_000)

    workspace.setDraftEndText("00:09:00.000")

    assert player.position() == 606_000


def test_the_explanation_goes_away_once_the_boundaries_are_sound_again(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    workspace.setDraftEndText("00:09:00.000")

    workspace.setDraftEndText("00:10:30.000")

    assert workspace.draftError == ""
    assert workspace.draftValid is True
    assert workspace.draftEndMs == 630_000


def test_a_boundary_that_is_not_a_time_at_all_is_refused_with_an_explanation(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.setDraftEndText("Halbzeit")

    assert workspace.draftEndMs == 612_000
    assert workspace.draftError != ""


def test_a_clip_without_a_title_cannot_be_kept_and_says_why(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.setDraftName("   ")

    assert workspace.draftValid is False
    assert workspace.draftError != ""


# --- The Category chooser ---------------------------------------------------


def test_the_editor_offers_every_category_in_the_analysis(
    workspace: WorkspaceViewModel, player: FakePlayback, analysis: Analysis
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    rows = workspace.categoryModel.rows()

    assert [row["name"] for row in rows] == [
        category.name for category in analysis.categories
    ]
    assert [row["selected"] for row in rows] == [False, False]


def test_choosing_a_category_marks_it_chosen_and_colours_the_draft_range(
    workspace: WorkspaceViewModel, player: FakePlayback, analysis: Analysis
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    tore = analysis.categories[0]

    workspace.setDraftCategory(str(tore.id))

    assert [row["selected"] for row in workspace.categoryModel.rows()] == [True, False]
    assert workspace.draftCategoryColor == tore.color


def test_a_category_can_be_taken_off_again(
    workspace: WorkspaceViewModel, player: FakePlayback, analysis: Analysis
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    workspace.setDraftCategory(str(analysis.categories[0].id))

    workspace.setDraftCategory("")

    assert [row["selected"] for row in workspace.categoryModel.rows()] == [False, False]
    # The timeline draws an uncategorised range in its own fallback colour
    # rather than in one this seam invents.
    assert workspace.draftCategoryColor == ""


def test_an_existing_clips_category_is_the_one_shown_chosen(
    workspace: WorkspaceViewModel, clip: Clip
) -> None:
    workspace.refresh()

    workspace.editClip(str(clip.id))

    assert [row["selected"] for row in workspace.categoryModel.rows()] == [True, False]


# --- Saving -----------------------------------------------------------------


def test_saving_a_new_clip_writes_it_to_the_analysis_as_one_change(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    analysis: Analysis,
    document: AnalysisDocument,
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    workspace.setDraftName("Gegenstoss")
    workspace.setDraftNotes("Zweite Welle")
    workspace.setDraftCategory(str(analysis.categories[0].id))
    before = analysis.revision

    workspace.commitDraft()

    assert len(analysis.clips) == 1
    kept = analysis.clips[0]
    assert kept.name == "Gegenstoss"
    assert kept.notes == "Zweite Welle"
    assert kept.category_id == analysis.categories[0].id
    assert (kept.start_ms, kept.end_ms) == (600_000, 612_000)
    assert kept.source_video_id == analysis.source_videos[0].id
    assert analysis.revision == before + 1, "the Clip reached the Analysis in pieces"
    assert document.dirty is True


def test_saving_leaves_the_editing_state_and_selects_what_was_kept(
    workspace: WorkspaceViewModel, player: FakePlayback, analysis: Analysis
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.commitDraft()

    assert workspace.editing is False
    assert workspace.selectedClipId == str(analysis.clips[0].id)
    assert [row["clipId"] for row in workspace.rangeModel.rows()] == [
        str(analysis.clips[0].id)
    ]


def test_saving_an_edit_updates_the_clip_rather_than_adding_a_second_one(
    workspace: WorkspaceViewModel, clip: Clip, analysis: Analysis
) -> None:
    workspace.refresh()
    workspace.editClip(str(clip.id))
    workspace.setDraftName("Gegenstoss Kreis")
    workspace.setDraftEndText("00:10:18.400")
    before = analysis.revision

    workspace.commitDraft()

    assert len(analysis.clips) == 1
    kept = analysis.clip(clip.id)
    assert kept.name == "Gegenstoss Kreis"
    assert kept.end_ms == 618_400
    assert kept.notes == "Zweite Welle"
    assert analysis.revision == before + 1


def test_a_clip_that_cannot_be_kept_is_not_kept(
    workspace: WorkspaceViewModel, player: FakePlayback, analysis: Analysis
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    workspace.setDraftName("")

    workspace.commitDraft()

    assert analysis.clips == ()
    assert workspace.editing is True, "the analyst is still holding a broken Clip"


def test_a_saved_clip_appears_in_the_clip_list(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)
    workspace.setDraftName("Gegenstoss")

    workspace.commitDraft()

    assert "Gegenstoss" in [row["title"] for row in workspace.clipModel.rows()]


# --- Cancelling --------------------------------------------------------------


def test_cancelling_a_newly_marked_clip_leaves_nothing_behind(
    workspace: WorkspaceViewModel,
    player: FakePlayback,
    analysis: Analysis,
    document: AnalysisDocument,
) -> None:
    """The Pending Clip was never part of the Analysis, so there is no undo."""

    mark_a_clip(workspace, player, 600_000, 612_000)
    workspace.setDraftName("Gegenstoss")
    workspace.setDraftCategory(str(analysis.categories[0].id))

    workspace.cancelDraft()

    assert workspace.editing is False
    assert analysis.clips == ()
    assert document.dirty is False


def test_cancelling_an_edit_leaves_the_clip_exactly_as_it_was(
    workspace: WorkspaceViewModel, clip: Clip, analysis: Analysis
) -> None:
    workspace.refresh()
    before = analysis.revision
    workspace.editClip(str(clip.id))
    workspace.setDraftName("Etwas anderes")
    workspace.setDraftEndText("00:10:18.400")
    workspace.setDraftCategory("")

    workspace.cancelDraft()

    assert workspace.editing is False
    assert analysis.clip(clip.id) == clip
    assert analysis.revision == before


def test_cancelling_twice_over_is_still_just_cancelling(
    workspace: WorkspaceViewModel, player: FakePlayback, analysis: Analysis
) -> None:
    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.cancelDraft()
    workspace.cancelDraft()

    assert workspace.editing is False
    assert analysis.clips == ()


def test_the_draft_is_gone_once_the_editor_is_closed(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    """Nothing is left for a later binding to read out of a closed editor."""

    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.cancelDraft()

    assert workspace.draftName == ""
    assert workspace.draftStartText == ""
    assert workspace.draftDurationText == ""
    assert workspace.draftValid is False
    assert workspace.draftError == ""


def test_opening_a_different_analysis_closes_the_editor(
    workspace: WorkspaceViewModel, player: FakePlayback
) -> None:
    """Whatever was being edited belonged to the Analysis that is gone."""

    mark_a_clip(workspace, player, 600_000, 612_000)

    workspace.newAnalysis()

    assert workspace.editing is False
    assert workspace.pendingActive is False
