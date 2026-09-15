"""The document commands, driven with no window, no dialog and no media.

New, Open, Save, Save As and Close are what an analyst does to an Analysis
rather than to a video, and every one of them can lose a morning's work if it
skips the unsaved-changes question. The view model is where that question is
asked, so it is where these tests drive: the person who would stand in front of
a dialog is a recording stand-in, which is what makes the decision flow — the
cancel, the discard, the save that fails — testable at all.

The rules themselves stay in `application_workflow`, which this ticket does not
touch. What is tested here is that the interface asks it, in the right order,
and shows what it reports.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from analysis import (  # noqa: E402
    Analysis,
    AnalysisDocument,
    UnsavedChangesChoice,
)
from application_workflow import (  # noqa: E402
    APPLICATION_TITLE,
    UNSAVED_CHANGES_MARKER,
    UNTITLED_ANALYSIS_TITLE,
)
from playback import FakePlayback  # noqa: E402
from workspace_view_model import WorkspaceViewModel  # noqa: E402


VIDEO = "/videos/halbzeit-1.mp4"


class RecordingPresenter:
    """The person the workflow asks, written down instead of shown a dialog."""

    def __init__(self) -> None:
        self.choice = UnsavedChangesChoice.CANCEL
        self.analysis_to_open: str | None = None
        self.destination: str | None = None
        self.source_video: str | None = None
        self.questions = 0
        self.suggested_names: list[str] = []
        self.failures: list[tuple[str, str]] = []

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        self.questions += 1
        return self.choice

    def choose_analysis_to_open(self) -> str | None:
        return self.analysis_to_open

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        self.suggested_names.append(suggested_name)
        return self.destination

    def choose_source_video(self) -> str | None:
        return self.source_video

    def report_failure(self, title: str, message: str) -> None:
        self.failures.append((title, message))


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def presenter() -> RecordingPresenter:
    return RecordingPresenter()


@pytest.fixture
def player(application: QApplication) -> FakePlayback:
    return FakePlayback()


def _document_with_a_video(title: str = "Spiel gegen Kiel") -> AnalysisDocument:
    analysis = Analysis(title)
    analysis.add_source_video("Halbzeit 1", VIDEO, duration_ms=2_700_000)
    return AnalysisDocument(analysis)


def _saved_analysis(path: Path, title: str = "Spiel gegen Kiel") -> Path:
    document = _document_with_a_video(title)
    document.save_as(path)
    return path


def _workspace(
    document: AnalysisDocument,
    player: FakePlayback,
    presenter: RecordingPresenter,
) -> WorkspaceViewModel:
    return WorkspaceViewModel(document, player, presenter=presenter)


# --- What the analyst can see ---------------------------------------------


def test_an_untitled_analysis_still_has_something_to_call_itself(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    workspace = _workspace(AnalysisDocument.new(), player, presenter)

    assert workspace.analysisTitle == UNTITLED_ANALYSIS_TITLE
    assert workspace.dirty is False


def test_the_workspace_shows_the_analysis_and_whether_it_is_saved(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)

    assert workspace.analysisTitle == "Spiel gegen Kiel"
    assert workspace.dirty is False
    assert workspace.windowTitle == f"Spiel gegen Kiel — {APPLICATION_TITLE}"

    document.analysis.set_title("Spiel gegen Flensburg")

    assert workspace.dirty is True
    assert workspace.windowTitle == (
        f"{UNSAVED_CHANGES_MARKER} Spiel gegen Flensburg — {APPLICATION_TITLE}"
    )


def test_saving_clears_the_dirty_marker(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.destination = str(tmp_path / "spiel.analysis")

    assert workspace.saveAnalysis() is True

    assert workspace.dirty is False
    assert workspace.windowTitle == f"Spiel gegen Flensburg — {APPLICATION_TITLE}"


def test_the_interface_is_told_when_the_document_changes(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    """A binding that is never notified shows yesterday's Analysis."""

    workspace = _workspace(_document_with_a_video(), player, presenter)
    reports: list[int] = []
    workspace.documentChanged.connect(lambda: reports.append(1))

    presenter.destination = str(tmp_path / "spiel.analysis")
    workspace.saveAnalysis()
    assert reports, "saving told the interface nothing"

    reports.clear()
    workspace.newAnalysis()
    assert reports, "a new Analysis told the interface nothing"


# --- New -------------------------------------------------------------------


def test_a_new_analysis_replaces_a_saved_one_without_a_question(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    workspace = _workspace(_document_with_a_video(), player, presenter)

    assert workspace.newAnalysis() is True

    assert presenter.questions == 0
    assert workspace.analysisTitle == UNTITLED_ANALYSIS_TITLE
    assert workspace.hasVideo is False


def test_a_cancelled_question_keeps_the_analysis_and_its_unsaved_work(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.choice = UnsavedChangesChoice.CANCEL

    assert workspace.newAnalysis() is False

    assert presenter.questions == 1
    assert workspace.analysisTitle == "Spiel gegen Flensburg"
    assert workspace.dirty is True


def test_discarding_unsaved_work_lets_the_new_analysis_through(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.choice = UnsavedChangesChoice.DISCARD

    assert workspace.newAnalysis() is True

    assert workspace.analysisTitle == UNTITLED_ANALYSIS_TITLE


def test_choosing_to_save_first_writes_the_analysis_before_replacing_it(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.choice = UnsavedChangesChoice.SAVE
    destination = tmp_path / "spiel.analysis"
    presenter.destination = str(destination)

    assert workspace.newAnalysis() is True

    assert destination.is_file()
    assert workspace.analysisTitle == UNTITLED_ANALYSIS_TITLE


def test_a_cancelled_save_refuses_to_let_the_analysis_go(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    """Dismissing the destination dialog is not agreeing to lose the work."""

    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.choice = UnsavedChangesChoice.SAVE
    presenter.destination = None

    assert workspace.newAnalysis() is False

    assert workspace.analysisTitle == "Spiel gegen Flensburg"
    assert workspace.dirty is True


def test_a_new_analysis_stops_playing_the_old_ones_video(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    workspace = _workspace(_document_with_a_video(), player, presenter)
    assert workspace.hasVideo is True

    workspace.newAnalysis()

    assert player.is_loaded() is False
    assert player.is_playing() is False
    assert workspace.positionMs == 0
    assert workspace.durationMs == 0


# --- Open ------------------------------------------------------------------


def test_opening_an_analysis_asks_about_unsaved_work_before_the_file(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    """Nobody picks a file only to be told their work is about to go."""

    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.choice = UnsavedChangesChoice.CANCEL
    presenter.analysis_to_open = str(_saved_analysis(tmp_path / "kiel.analysis"))

    assert workspace.openAnalysis() is False

    assert presenter.questions == 1
    assert workspace.analysisTitle == "Spiel gegen Flensburg"


def test_a_dismissed_file_dialog_leaves_the_analysis_alone(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    workspace = _workspace(_document_with_a_video(), player, presenter)
    presenter.analysis_to_open = None

    assert workspace.openAnalysis() is False

    assert workspace.analysisTitle == "Spiel gegen Kiel"


def test_an_opened_analysis_becomes_the_one_the_workspace_is_about(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    workspace = _workspace(AnalysisDocument.new(), player, presenter)
    presenter.analysis_to_open = str(
        _saved_analysis(tmp_path / "kiel.analysis", "Spiel gegen Kiel")
    )

    assert workspace.openAnalysis() is True

    assert workspace.analysisTitle == "Spiel gegen Kiel"
    assert workspace.dirty is False
    assert workspace.hasVideo is True
    assert player.location() == VIDEO


def test_a_file_that_cannot_be_read_is_reported_and_changes_nothing(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    workspace = _workspace(_document_with_a_video(), player, presenter)
    broken = tmp_path / "broken.analysis"
    broken.write_text("this is not an Analysis", encoding="utf-8")
    presenter.analysis_to_open = str(broken)

    assert workspace.openAnalysis() is False

    assert presenter.failures, "an unreadable file was opened in silence"
    assert workspace.analysisTitle == "Spiel gegen Kiel"


# --- Save and Save As ------------------------------------------------------


def test_saving_an_analysis_that_has_no_file_yet_asks_where_to_put_it(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    workspace = _workspace(_document_with_a_video(), player, presenter)
    destination = tmp_path / "spiel.analysis"
    presenter.destination = str(destination)

    assert workspace.saveAnalysis() is True

    assert destination.is_file()
    assert presenter.suggested_names == ["Spiel gegen Kiel.analysis"]


def test_saving_an_analysis_that_has_a_file_asks_nothing(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    document = _document_with_a_video()
    document.save_as(tmp_path / "spiel.analysis")
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")

    assert workspace.saveAnalysis() is True

    assert presenter.suggested_names == []
    assert workspace.dirty is False


def test_save_as_always_asks_and_writes_the_second_file(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    document = _document_with_a_video()
    first = tmp_path / "spiel.analysis"
    document.save_as(first)
    workspace = _workspace(document, player, presenter)
    second = tmp_path / "kopie.analysis"
    presenter.destination = str(second)

    assert workspace.saveAnalysisAs() is True

    assert first.is_file()
    assert second.is_file()


def test_a_save_that_cannot_be_written_is_reported_and_stays_dirty(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    # A destination inside something that is not a directory: the write fails
    # where an analyst's full disk or read-only volume would fail it.
    not_a_directory = tmp_path / "nowhere"
    not_a_directory.write_text("", encoding="utf-8")
    presenter.destination = str(not_a_directory / "spiel.analysis")

    assert workspace.saveAnalysis() is False

    assert presenter.failures, "a failed save was reported to nobody"
    assert workspace.dirty is True


# --- Close -----------------------------------------------------------------


def test_a_saved_analysis_closes_without_a_question(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    workspace = _workspace(_document_with_a_video(), player, presenter)

    assert workspace.requestClose() is True
    assert presenter.questions == 0


def test_closing_with_unsaved_work_asks_first_and_can_be_cancelled(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.choice = UnsavedChangesChoice.CANCEL

    assert workspace.requestClose() is False

    assert presenter.questions == 1
    assert workspace.dirty is True


def test_closing_with_unsaved_work_can_discard_it(
    player: FakePlayback, presenter: RecordingPresenter
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.choice = UnsavedChangesChoice.DISCARD

    assert workspace.requestClose() is True


def test_closing_with_unsaved_work_can_save_it_first(
    player: FakePlayback, presenter: RecordingPresenter, tmp_path: Path
) -> None:
    document = _document_with_a_video()
    workspace = _workspace(document, player, presenter)
    document.analysis.set_title("Spiel gegen Flensburg")
    presenter.choice = UnsavedChangesChoice.SAVE
    destination = tmp_path / "spiel.analysis"
    presenter.destination = str(destination)

    assert workspace.requestClose() is True

    assert destination.is_file()


# --- A workspace with nobody to ask ----------------------------------------


def test_a_workspace_built_without_a_person_to_ask_refuses_to_lose_work(
    player: FakePlayback,
) -> None:
    """The transport's own tests build a workspace with nobody to ask.

    Such a workspace can still play a video; what it must never do is discard
    an Analysis because there was no one to ask about it.
    """

    document = _document_with_a_video()
    workspace = WorkspaceViewModel(document, player)
    document.analysis.set_title("Spiel gegen Flensburg")

    assert workspace.newAnalysis() is False
    assert workspace.requestClose() is False
    assert workspace.analysisTitle == "Spiel gegen Flensburg"
