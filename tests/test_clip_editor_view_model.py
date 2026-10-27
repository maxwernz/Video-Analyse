"""Clip editing through the public QML view-model seam."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from analysis import Analysis, AnalysisDocument  # noqa: E402
from playback import FakePlayback  # noqa: E402
from workspace_view_model import WorkspaceViewModel  # noqa: E402


VIDEO = "/videos/halbzeit-1.mp4"
DURATION_MS = 90 * 60_000


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def document() -> AnalysisDocument:
    analysis = Analysis("Spiel gegen Kiel")
    analysis.add_source_video("Halbzeit 1", VIDEO, duration_ms=DURATION_MS)
    analysis.add_category("Angriff", "#E2564A")
    return AnalysisDocument(analysis)


@pytest.fixture
def player(application: QApplication) -> FakePlayback:
    return FakePlayback()


@pytest.fixture
def workspace(
    document: AnalysisDocument, player: FakePlayback
) -> WorkspaceViewModel:
    pending: list[object] = []
    model = WorkspaceViewModel(
        document, player, schedule=lambda _delay, run: pending.append(run)
    )
    for run in pending:
        run()  # type: ignore[operator]
    return model


def test_completing_a_pending_clip_pauses_and_opens_the_editor(
    workspace: WorkspaceViewModel,
    document: AnalysisDocument,
    player: FakePlayback,
) -> None:
    player.seek(12_000)
    player.play()
    workspace.markBoundary()
    player.seek(18_500)
    workspace.markBoundary()

    assert workspace.mode == "editing"
    assert workspace.pendingActive is False
    assert workspace.draftStartText == "00:00:12.000"
    assert workspace.draftEndText == "00:00:18.500"
    assert player.is_playing() is False
    assert document.analysis.clips == ()


def test_saving_a_new_clip_is_one_analysis_change(
    workspace: WorkspaceViewModel, document: AnalysisDocument, player: FakePlayback
) -> None:
    player.seek(12_000)
    workspace.markBoundary()
    player.seek(18_500)
    workspace.markBoundary()
    before = document.analysis.revision
    workspace.setDraftName("Tempo-Gegenstoss")
    category = document.analysis.categories[0]
    workspace.setDraftCategory(str(category.id))
    workspace.setDraftNotes("Rueckraum bindet beide Halbverteidiger")

    workspace.commitDraft()

    assert document.analysis.revision == before + 1
    assert document.dirty is True
    assert workspace.mode == "workspace"
    assert workspace.selectedClipId == str(document.analysis.clips[0].id)
    clip = document.analysis.clips[0]
    assert (clip.name, clip.start_ms, clip.end_ms, clip.notes, clip.category_id) == (
        "Tempo-Gegenstoss",
        12_000,
        18_500,
        "Rueckraum bindet beide Halbverteidiger",
        category.id,
    )


def test_cancelling_a_new_clip_leaves_the_analysis_unchanged(
    workspace: WorkspaceViewModel, document: AnalysisDocument, player: FakePlayback
) -> None:
    player.seek(12_000)
    workspace.markBoundary()
    player.seek(18_500)
    workspace.markBoundary()
    before = document.analysis.revision

    workspace.cancelDraft()

    assert document.analysis.revision == before
    assert document.analysis.clips == ()
    assert workspace.mode == "workspace"


def test_a_pending_clip_cannot_move_to_another_source_video(
    workspace: WorkspaceViewModel, document: AnalysisDocument, player: FakePlayback
) -> None:
    other = document.analysis.add_source_video(
        "Halbzeit 2", "/videos/halbzeit-2.mp4", duration_ms=DURATION_MS
    )
    workspace.refresh()
    player.seek(12_000)
    workspace.markBoundary()

    workspace.selectSourceVideo(str(other.id))

    assert workspace.pendingActive is False
    player.seek(18_000)
    workspace.markBoundary()
    assert workspace.pendingActive is True
    assert document.analysis.clips == ()


def test_the_same_editor_updates_an_existing_clip_as_one_change(
    workspace: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    source = document.analysis.source_videos[0]
    clip = document.analysis.add_clip(source.id, "Alter Name", 5_000, 8_000)
    workspace.refresh()
    before = document.analysis.revision

    workspace.editClip(str(clip.id))
    workspace.setDraftName("Neuer Name")
    workspace.setDraftStartText("00:00:05.500")
    workspace.setDraftEndText("00:00:09.000")
    workspace.commitDraft()

    assert document.analysis.revision == before + 1
    assert document.analysis.clip(clip.id).name == "Neuer Name"
    assert document.analysis.clip(clip.id).start_ms == 5_500
    assert document.analysis.clip(clip.id).end_ms == 9_000


def test_cancelling_an_existing_clip_leaves_it_exactly_as_it_was(
    workspace: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    source = document.analysis.source_videos[0]
    original = document.analysis.add_clip(source.id, "Original", 5_000, 8_000)
    workspace.refresh()
    before = document.analysis.revision

    workspace.editClip(str(original.id))
    workspace.setDraftName("Nicht speichern")
    workspace.setDraftEndText("00:00:12.000")
    workspace.cancelDraft()

    assert document.analysis.revision == before
    assert document.analysis.clip(original.id) == original


def test_adjusting_a_boundary_seeks_to_it_and_updates_duration_live(
    workspace: WorkspaceViewModel, document: AnalysisDocument, player: FakePlayback
) -> None:
    source = document.analysis.source_videos[0]
    clip = document.analysis.add_clip(source.id, "Tor", 5_000, 8_000)
    workspace.refresh()
    workspace.editClip(str(clip.id))

    workspace.setDraftEndText("00:00:10.250")

    assert player.position() == 10_250
    assert workspace.draftDurationText == "0:05"


def test_an_end_before_the_start_is_rejected_with_an_explanation(
    workspace: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    source = document.analysis.source_videos[0]
    clip = document.analysis.add_clip(source.id, "Tor", 5_000, 8_000)
    workspace.refresh()
    workspace.editClip(str(clip.id))

    workspace.setDraftEndText("00:00:04.000")

    assert workspace.draftValid is False
    assert "Ende" in workspace.draftError
    before = document.analysis.revision
    workspace.commitDraft()
    assert document.analysis.revision == before
    assert document.analysis.clip(clip.id) == clip


def test_categories_are_exposed_as_rows_with_the_draft_selection(
    workspace: WorkspaceViewModel, document: AnalysisDocument
) -> None:
    category = document.analysis.categories[0]
    source = document.analysis.source_videos[0]
    clip = document.analysis.add_clip(
        source.id, "Tor", 5_000, 8_000, category_id=category.id
    )
    workspace.refresh()

    workspace.editClip(str(clip.id))

    assert workspace.categoryModel.rows() == (
        {
            "categoryId": str(category.id),
            "name": "Angriff",
            "color": "#E2564A",
            "selected": True,
        },
    )
