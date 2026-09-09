from __future__ import annotations

from pathlib import Path

import pytest

from analysis import (
    Analysis,
    AnalysisDocument,
    UnsavedChangesChoice,
    new_analysis_document,
)
from application_workflow import ApplicationWorkflow


class FakePresenter:
    """Stands in for every decision the workflow asks a person to make."""

    def __init__(self) -> None:
        self.unsaved_choice = UnsavedChangesChoice.DISCARD
        self.analysis_to_open: str | None = None
        self.analysis_destination: str | None = None
        self.source_video: str | None = None
        self.unsaved_prompts = 0
        self.suggested_names: list[str] = []
        self.failures: list[tuple[str, str]] = []

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        self.unsaved_prompts += 1
        return self.unsaved_choice

    def choose_analysis_to_open(self) -> str | None:
        return self.analysis_to_open

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        self.suggested_names.append(suggested_name)
        return self.analysis_destination

    def choose_source_video(self) -> str | None:
        return self.source_video

    def report_failure(self, title: str, message: str) -> None:
        self.failures.append((title, message))


class RecordedEvents:
    def __init__(self) -> None:
        self.replacements = 0
        self.changes = 0


@pytest.fixture
def presenter() -> FakePresenter:
    return FakePresenter()


@pytest.fixture
def events() -> RecordedEvents:
    return RecordedEvents()


@pytest.fixture
def workflow(presenter: FakePresenter, events: RecordedEvents) -> ApplicationWorkflow:
    def analysis_replaced() -> None:
        events.replacements += 1

    def document_changed() -> None:
        events.changes += 1

    return ApplicationWorkflow(
        presenter,
        on_analysis_replaced=analysis_replaced,
        on_document_changed=document_changed,
    )


def _video(tmp_path: Path, name: str = "first-half.mp4") -> Path:
    video_path = tmp_path / name
    video_path.write_bytes(b"not a real video")
    return video_path


def _analysis_with_work(workflow: ApplicationWorkflow, tmp_path: Path) -> None:
    source_video = workflow.add_source_video_file(_video(tmp_path))
    assert source_video is not None
    workflow.analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)


# --- New ------------------------------------------------------------------


def test_a_new_workflow_starts_on_a_clean_templated_analysis(
    workflow: ApplicationWorkflow,
) -> None:
    assert workflow.analysis.source_videos == ()
    assert [category.name for category in workflow.analysis.categories] == [
        "Abwehr",
        "Angriff",
        "Tor",
    ]
    assert workflow.document.dirty is False


def test_new_analysis_replaces_the_current_one_after_discarding(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD

    assert workflow.new_analysis() is True

    assert presenter.unsaved_prompts == 1
    assert workflow.analysis.clips == ()
    assert workflow.analysis.source_videos == ()
    assert workflow.document.dirty is False
    assert events.replacements == 1


def test_cancelling_the_unsaved_prompt_keeps_the_current_analysis(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    analysis = workflow.analysis
    presenter.unsaved_choice = UnsavedChangesChoice.CANCEL

    assert workflow.new_analysis() is False

    assert workflow.analysis is analysis
    assert len(workflow.analysis.clips) == 1
    assert events.replacements == 0


def test_a_clean_analysis_is_replaced_without_asking(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
) -> None:
    assert workflow.new_analysis() is True
    assert presenter.unsaved_prompts == 0


# --- Save and Save As -----------------------------------------------------


def test_saving_an_unsaved_analysis_asks_for_a_destination_once(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    destination = tmp_path / "match.analysis"
    presenter.analysis_destination = str(destination)

    assert workflow.save() is True
    assert destination.is_file()
    assert workflow.document.dirty is False
    assert presenter.suggested_names == ["first-half.analysis"]

    workflow.analysis.add_clip(
        workflow.analysis.source_videos[0].id, "Second", 3_000, 4_000
    )
    assert workflow.save() is True
    assert presenter.suggested_names == ["first-half.analysis"]


def test_save_as_always_asks_for_a_destination(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.analysis_destination = str(tmp_path / "match.analysis")
    assert workflow.save() is True

    presenter.analysis_destination = str(tmp_path / "copy.analysis")
    assert workflow.save_as() is True

    assert (tmp_path / "copy.analysis").is_file()
    assert workflow.document.path == tmp_path / "copy.analysis"
    assert len(presenter.suggested_names) == 2


def test_a_cancelled_destination_leaves_the_analysis_dirty(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.analysis_destination = None

    assert workflow.save() is False
    assert workflow.document.dirty is True
    assert presenter.failures == []


def test_a_failed_save_is_reported_and_leaves_the_analysis_dirty(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    workflow.analysis.set_title("Leer")
    presenter.analysis_destination = str(tmp_path / "empty.analysis")

    assert workflow.save() is False
    assert workflow.document.dirty is True
    assert len(presenter.failures) == 1
    assert not (tmp_path / "empty.analysis").exists()


def test_a_cancelled_save_prevents_replacing_the_analysis(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.SAVE
    presenter.analysis_destination = None

    assert workflow.new_analysis() is False
    assert workflow.document.dirty is True
    assert len(workflow.analysis.clips) == 1


def test_a_failed_save_prevents_replacing_the_analysis(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    workflow.analysis.set_title("Leer")
    presenter.unsaved_choice = UnsavedChangesChoice.SAVE
    presenter.analysis_destination = str(tmp_path / "empty.analysis")

    assert workflow.new_analysis() is False
    assert workflow.document.dirty is True


def test_saving_before_replacing_lets_the_analysis_go(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.SAVE
    presenter.analysis_destination = str(tmp_path / "match.analysis")

    assert workflow.new_analysis() is True
    assert (tmp_path / "match.analysis").is_file()
    assert workflow.analysis.clips == ()


# --- Open -----------------------------------------------------------------


def _saved_analysis_file(tmp_path: Path) -> Path:
    document = new_analysis_document("Gespeichert")
    source_video = document.analysis.add_source_video(
        "second-half.mp4",
        str(tmp_path / "second-half.mp4"),
    )
    document.analysis.add_clip(source_video.id, "Tor", 5_000, 6_000)
    return document.save_as(tmp_path / "saved.analysis")


def test_opening_an_analysis_replaces_the_current_one(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    saved = _saved_analysis_file(tmp_path)
    presenter.analysis_to_open = str(saved)

    assert workflow.open_analysis() is True

    assert workflow.analysis.title == "Gespeichert"
    assert [clip.name for clip in workflow.analysis.clips] == ["Tor"]
    assert workflow.document.path == saved
    assert workflow.document.dirty is False
    assert events.replacements == 1


def test_unsaved_changes_are_settled_before_a_file_is_chosen(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    """Nobody should pick a file only to be asked whether they meant to."""
    _analysis_with_work(workflow, tmp_path)
    asked: list[str] = []
    presenter.unsaved_choice = UnsavedChangesChoice.CANCEL
    presenter.analysis_to_open = str(_saved_analysis_file(tmp_path))

    def record_prompt() -> UnsavedChangesChoice:
        asked.append("unsaved")
        return UnsavedChangesChoice.CANCEL

    def record_chooser() -> str | None:
        asked.append("chooser")
        return presenter.analysis_to_open

    presenter.ask_unsaved_changes = record_prompt  # type: ignore[method-assign]
    presenter.choose_analysis_to_open = record_chooser  # type: ignore[method-assign]

    assert workflow.open_analysis() is False

    assert asked == ["unsaved"]


def test_cancelling_the_open_dialog_changes_nothing(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    events: RecordedEvents,
) -> None:
    presenter.analysis_to_open = None

    assert workflow.open_analysis() is False
    assert events.replacements == 0
    assert presenter.unsaved_prompts == 0


def test_a_failed_load_leaves_the_open_analysis_untouched(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    analysis = workflow.analysis
    broken = tmp_path / "broken.analysis"
    broken.write_text("{ not json", encoding="utf-8")
    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD

    assert workflow.open_analysis_file(broken) is False

    assert workflow.analysis is analysis
    assert len(workflow.analysis.clips) == 1
    assert len(presenter.failures) == 1
    assert events.replacements == 0


def test_a_rejected_load_leaves_the_open_analysis_untouched(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    analysis = workflow.analysis
    presenter.unsaved_choice = UnsavedChangesChoice.CANCEL

    assert workflow.open_analysis_file(_saved_analysis_file(tmp_path)) is False

    assert workflow.analysis is analysis
    assert len(workflow.analysis.clips) == 1


def test_a_missing_analysis_file_is_reported(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    assert workflow.open_analysis_file(tmp_path / "absent.analysis") is False
    assert len(presenter.failures) == 1


# --- Adding Source videos -------------------------------------------------


def test_adding_a_video_is_additive_and_keeps_existing_work(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
    presenter: FakePresenter,
    events: RecordedEvents,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    changes_before = events.changes

    second = workflow.add_source_video_file(_video(tmp_path, "second-half.mp4"))

    assert second is not None
    assert [source.display_name for source in workflow.analysis.source_videos] == [
        "first-half.mp4",
        "second-half.mp4",
    ]
    assert len(workflow.analysis.clips) == 1
    assert presenter.unsaved_prompts == 0
    assert events.replacements == 0
    assert events.changes == changes_before + 1


def test_only_the_first_video_titles_an_untitled_analysis(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    workflow.add_source_video_file(_video(tmp_path))
    workflow.add_source_video_file(_video(tmp_path, "second-half.mp4"))

    assert workflow.analysis.title == "first-half"


def test_adding_a_video_through_the_dialog_uses_the_chosen_file(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    presenter.source_video = str(_video(tmp_path))

    added = workflow.add_source_video()

    assert added is not None
    assert workflow.analysis.source_videos[0].location == presenter.source_video


def test_cancelling_the_video_dialog_adds_nothing(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
) -> None:
    presenter.source_video = None

    assert workflow.add_source_video() is None
    assert workflow.analysis.source_videos == ()


def test_a_rejected_video_is_reported_and_leaves_the_analysis_as_it_was(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    video_path = _video(tmp_path)
    workflow.add_source_video_file(video_path)
    revision = workflow.analysis.revision

    assert workflow.add_source_video_file(video_path) is None

    assert len(workflow.analysis.source_videos) == 1
    assert workflow.analysis.revision == revision
    assert len(presenter.failures) == 1


def test_a_rejected_first_video_does_not_leave_a_title_behind(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    assert workflow.add_source_video_file(tmp_path / "   ") is None

    assert workflow.analysis.title == ""
    assert workflow.analysis.source_videos == ()
    assert workflow.document.dirty is False


def test_starting_a_new_analysis_is_not_the_same_as_adding_a_video(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD

    workflow.new_analysis()

    assert workflow.analysis.source_videos == ()
    assert workflow.analysis.clips == ()


# --- Dropped files --------------------------------------------------------


def test_a_dropped_video_is_added_to_the_current_analysis(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)

    assert workflow.open_dropped_file(_video(tmp_path, "second-half.MOV")) is True

    assert len(workflow.analysis.source_videos) == 2
    assert len(workflow.analysis.clips) == 1


def test_a_dropped_analysis_file_replaces_the_current_analysis(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.DISCARD

    assert workflow.open_dropped_file(_saved_analysis_file(tmp_path)) is True

    assert workflow.analysis.title == "Gespeichert"


def test_an_unsupported_dropped_file_is_ignored(
    workflow: ApplicationWorkflow,
    tmp_path: Path,
) -> None:
    note = tmp_path / "notes.txt"
    note.write_text("nothing to see", encoding="utf-8")

    assert workflow.open_dropped_file(note) is False
    assert workflow.analysis.source_videos == ()


# --- Window title ---------------------------------------------------------


def test_the_window_title_reports_an_untitled_clean_analysis(
    workflow: ApplicationWorkflow,
) -> None:
    assert workflow.window_title == "Unbenannte Analyse — Video Analyse"


def test_the_window_title_reports_the_title_and_dirty_state(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    assert workflow.window_title == "• first-half — Video Analyse"

    workflow.analysis.set_title("Spiel gegen Musterstadt")
    assert workflow.window_title == "• Spiel gegen Musterstadt — Video Analyse"

    presenter.analysis_destination = str(tmp_path / "match.analysis")
    assert workflow.save() is True
    assert workflow.window_title == "Spiel gegen Musterstadt — Video Analyse"


# --- Closing --------------------------------------------------------------


def test_closing_a_clean_analysis_is_allowed_without_asking(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
) -> None:
    assert workflow.may_replace_analysis() is True
    assert presenter.unsaved_prompts == 0


def test_closing_a_dirty_analysis_asks_and_can_be_refused(
    workflow: ApplicationWorkflow,
    presenter: FakePresenter,
    tmp_path: Path,
) -> None:
    _analysis_with_work(workflow, tmp_path)
    presenter.unsaved_choice = UnsavedChangesChoice.CANCEL

    assert workflow.may_replace_analysis() is False
    assert workflow.document.dirty is True


def test_an_explicitly_supplied_document_is_adopted(
    presenter: FakePresenter,
) -> None:
    document = AnalysisDocument(Analysis("Vorhanden"))

    workflow = ApplicationWorkflow(presenter, document=document)

    assert workflow.document is document
    assert workflow.analysis.title == "Vorhanden"
