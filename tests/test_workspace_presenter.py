"""The questions the workflow asks, put to a person as QML's own dialogs.

The workflow decides what a command means; this is the one place that turns its
questions into dialog requests `qml/Dialogs.qml` draws. What is tested here is
that the right kind of dialog is asked for with the right content, and that
each answer QML can report back is read as the right decision — all without a
QML engine or a window, exactly as the Widgets-era version of this suite
needed neither a real `QFileDialog` nor a real `QMessageBox`.

Every method on `WorkspacePresenter` is continuation-based now (issue #69):
`QtQuick.Dialogs.FileDialog`, the one dialog technology immune to the
hover-tracking self-cancel this issue is about, is asynchronous by
construction, and every synchronous `QMessageBox`-backed question shares its
seam with the file choosers. A test drives that seam exactly the way QML
does — request a dialog, read what `WorkspacePresenter` published for it,
then call the same slot QML calls to report an answer — and captures the
completion's result in a list rather than a return value.
"""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from analysis import ExternalChangeChoice, UnsavedChangesChoice  # noqa: E402
from application_workflow import WorkflowPresenter  # noqa: E402
from workspace_presenter import (  # noqa: E402
    WorkspacePresenter,
    _existing_start_directory,
)


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def presenter(application: QApplication) -> WorkspacePresenter:
    return WorkspacePresenter()


def _capture() -> tuple[list[Any], Callable[[Any], None]]:
    results: list[Any] = []
    return results, results.append


# --- The unsaved-changes question -------------------------------------------


def test_every_answer_the_question_offers_is_read_as_a_decision(
    presenter: WorkspacePresenter,
) -> None:
    for button_id, choice in (
        ("save", UnsavedChangesChoice.SAVE),
        ("discard", UnsavedChangesChoice.DISCARD),
        ("cancel", UnsavedChangesChoice.CANCEL),
    ):
        results, on_result = _capture()
        presenter.ask_unsaved_changes(on_result)
        presenter.questionAnswered(button_id)
        assert results == [choice]


def test_a_dismissed_question_keeps_the_unsaved_work(
    presenter: WorkspacePresenter,
) -> None:
    """Closing the dialog is not choosing to discard anything."""

    results, on_result = _capture()
    presenter.ask_unsaved_changes(on_result)
    presenter.questionAnswered("")

    assert results == [UnsavedChangesChoice.CANCEL]


def test_the_question_offers_all_three_decisions(presenter: WorkspacePresenter) -> None:
    presenter.ask_unsaved_changes(lambda choice: None)

    ids = {button["id"] for button in presenter.questionButtons}
    assert ids == {"save", "discard", "cancel"}
    assert presenter.questionText


# --- Choosing files ----------------------------------------------------------


def test_the_analysis_to_open_is_chosen_from_a_file_dialog(
    presenter: WorkspacePresenter, tmp_path: Path
) -> None:
    chosen = tmp_path / "spiel.analysis"
    results, on_result = _capture()

    presenter.choose_analysis_to_open(on_result)
    presenter.fileDialogAccepted(QUrl.fromLocalFile(str(chosen)))

    assert results == [str(chosen)]
    assert ".analysis" in presenter.fileDialogFilter


def test_a_dismissed_open_dialog_means_no_file(presenter: WorkspacePresenter) -> None:
    results, on_result = _capture()

    presenter.choose_analysis_to_open(on_result)
    presenter.fileDialogCancelled()

    assert results == [None]


def test_the_destination_dialog_offers_the_name_the_workflow_suggests(
    presenter: WorkspacePresenter, tmp_path: Path
) -> None:
    destination = tmp_path / "spiel.analysis"
    results, on_result = _capture()

    presenter.choose_analysis_destination("Spiel gegen Kiel.analysis", on_result)

    assert presenter.fileDialogSuggestedName == "Spiel gegen Kiel.analysis"
    assert presenter.fileDialogMode == "save"

    presenter.fileDialogAccepted(QUrl.fromLocalFile(str(destination)))
    assert results == [str(destination)]


def test_a_dismissed_destination_dialog_means_no_file(
    presenter: WorkspacePresenter,
) -> None:
    results, on_result = _capture()

    presenter.choose_analysis_destination("Analyse.analysis", on_result)
    presenter.fileDialogCancelled()

    assert results == [None]


def test_a_source_video_is_chosen_with_the_video_filter(
    presenter: WorkspacePresenter, tmp_path: Path
) -> None:
    video = tmp_path / "halbzeit-1.mp4"
    results, on_result = _capture()

    presenter.choose_source_video(on_result)

    assert ".mp4" in presenter.fileDialogFilter
    assert presenter.fileDialogMode == "open"

    presenter.fileDialogAccepted(QUrl.fromLocalFile(str(video)))
    assert results == [str(video)]


def test_replacement_media_is_chosen_with_the_video_filter(
    presenter: WorkspacePresenter, tmp_path: Path
) -> None:
    video = tmp_path / "halbzeit-1-ersatz.mp4"
    results, on_result = _capture()

    presenter.choose_replacement_media("Halbzeit 1", on_result)

    assert ".mp4" in presenter.fileDialogFilter

    presenter.fileDialogAccepted(QUrl.fromLocalFile(str(video)))
    assert results == [str(video)]


def test_a_dismissed_replacement_media_dialog_means_no_file(
    presenter: WorkspacePresenter,
) -> None:
    results, on_result = _capture()

    presenter.choose_replacement_media("Halbzeit 1", on_result)
    presenter.fileDialogCancelled()

    assert results == [None]


def test_a_non_local_file_dialog_answer_means_no_file(
    presenter: WorkspacePresenter,
) -> None:
    """`QUrl.toLocalFile` is empty for anything that is not a real local path."""

    results, on_result = _capture()

    presenter.choose_analysis_to_open(on_result)
    presenter.fileDialogAccepted(QUrl("https://example.invalid/not-local"))

    assert results == [None]


def test_a_missing_start_directory_is_never_handed_to_a_file_dialog(
    tmp_path: Path,
) -> None:
    """An unavailable iCloud Documents/Movies location falls back safely."""

    assert _existing_start_directory(str(tmp_path / "not-mounted")) == ""
    assert _existing_start_directory(str(tmp_path)) == str(tmp_path)


def test_a_second_dialog_request_cannot_replace_the_first_pending_answer(
    presenter: WorkspacePresenter,
) -> None:
    """A native menu shortcut cannot strand the QML question it interrupted."""

    original, original_done = _capture()
    interrupted, interrupted_done = _capture()
    presenter.ask_unsaved_changes(original_done)

    presenter.choose_analysis_to_open(interrupted_done)
    assert interrupted == [None]
    assert original == []

    presenter.questionAnswered("discard")
    assert original == [UnsavedChangesChoice.DISCARD]


# --- Confirming a mismatched replacement ------------------------------------


def test_confirming_the_replacement_reads_yes_as_confirmed(
    presenter: WorkspacePresenter,
) -> None:
    results, on_result = _capture()

    presenter.confirm_source_video_replacement("Halbzeit 1", on_result)
    presenter.questionAnswered("yes")

    assert results == [True]


@pytest.mark.parametrize("button_id", ["no", ""], ids=["declined", "dismissed"])
def test_declining_or_dismissing_the_replacement_confirmation_reads_as_no(
    presenter: WorkspacePresenter, button_id: str
) -> None:
    results, on_result = _capture()

    presenter.confirm_source_video_replacement("Halbzeit 1", on_result)
    presenter.questionAnswered(button_id)

    assert results == [False]


def test_the_replacement_confirmation_names_the_source_video(
    presenter: WorkspacePresenter,
) -> None:
    presenter.confirm_source_video_replacement("Halbzeit 1", lambda choice: None)

    assert "Halbzeit 1" in presenter.questionText


# --- The external-change conflict -------------------------------------------


def test_every_answer_the_external_change_question_offers_is_read_as_a_decision(
    presenter: WorkspacePresenter,
) -> None:
    for button_id, choice in (
        ("reload", ExternalChangeChoice.RELOAD),
        ("saveAs", ExternalChangeChoice.SAVE_AS),
        ("cancel", ExternalChangeChoice.CANCEL),
    ):
        results, on_result = _capture()
        presenter.ask_external_change_conflict(on_result)
        presenter.questionAnswered(button_id)
        assert results == [choice]


def test_the_external_change_question_offers_no_overwrite_option(
    presenter: WorkspacePresenter,
) -> None:
    """No "overwrite anyway" button: neither version may be silently destroyed."""

    presenter.ask_external_change_conflict(lambda choice: None)

    ids = {button["id"] for button in presenter.questionButtons}
    assert ids == {"reload", "saveAs", "cancel"}


def test_a_dismissed_external_change_question_is_cancel(
    presenter: WorkspacePresenter,
) -> None:
    results, on_result = _capture()

    presenter.ask_external_change_conflict(on_result)
    presenter.questionAnswered("")

    assert results == [ExternalChangeChoice.CANCEL]


# --- Offering recovered work -------------------------------------------------


def test_accepting_the_recovery_offer_reads_as_yes(presenter: WorkspacePresenter) -> None:
    results, on_result = _capture()

    presenter.offer_recovered_analysis(on_result)
    presenter.questionAnswered("yes")

    assert results == [True]


@pytest.mark.parametrize("button_id", ["no", ""], ids=["declined", "dismissed"])
def test_declining_or_dismissing_the_recovery_offer_reads_as_no(
    presenter: WorkspacePresenter, button_id: str
) -> None:
    results, on_result = _capture()

    presenter.offer_recovered_analysis(on_result)
    presenter.questionAnswered(button_id)

    assert results == [False]


# --- Reporting a failure -----------------------------------------------------


def test_a_failure_is_reported_where_the_analyst_will_see_it(
    presenter: WorkspacePresenter,
) -> None:
    presenter.report_failure("Analysis could not be saved", "the disk is full")

    assert presenter.failureTitle == "Analysis could not be saved"
    assert presenter.failureMessage == "the disk is full"


def test_reporting_a_failure_needs_nobody_to_dismiss_it_first() -> None:
    """Nothing downstream of `report_failure` waits on an answer."""

    import inspect

    signature = inspect.signature(WorkspacePresenter.report_failure)
    assert list(signature.parameters) == ["self", "title", "message"]


def test_a_second_failure_is_queued_rather_than_overwriting_the_first(
    presenter: WorkspacePresenter,
) -> None:
    """Neither of two failures reported before either is dismissed is lost.

    `QMessageBox.critical` used to block until dismissed, so a Save
    failing over a full disk and an unrelated relink failing right after
    could never race for the same title and message. `report_failure`
    replaced that with fields set and a signal emitted, unguarded, so a
    second call used to overwrite the first outright before the analyst
    had read it. Report two, and check that both are still readable, one
    at a time, rather than the second silently replacing the first.
    """

    presenter.report_failure("Analysis could not be saved", "the disk is full")
    presenter.report_failure(
        "Source video could not be relinked", "the file no longer exists"
    )

    # The first failure is still what is showing — not overwritten by the
    # second, and not dropped in favour of it either.
    assert presenter.failurePending is True
    assert presenter.failureTitle == "Analysis could not be saved"
    assert presenter.failureMessage == "the disk is full"

    presenter.failureDismissed()

    # The second failure now shows in its turn, not lost.
    assert presenter.failurePending is True
    assert presenter.failureTitle == "Source video could not be relinked"
    assert presenter.failureMessage == "the file no longer exists"

    presenter.failureDismissed()

    assert presenter.failurePending is False


# --- Every question the workflow can ask has an answer ----------------------


def test_the_presenter_answers_everything_the_workflow_can_ask() -> None:
    """A question with no answer is a crash at the worst possible moment."""

    questions = [
        name for name in vars(WorkflowPresenter) if not name.startswith("_")
    ]
    assert questions
    for question in questions:
        assert callable(getattr(WorkspacePresenter, question, None)), question
