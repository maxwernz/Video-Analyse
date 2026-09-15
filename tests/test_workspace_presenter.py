"""The questions the workflow asks, put to a person as the platform's dialogs.

The workflow decides what a command means; this is the one place that turns its
questions into windows. The dialogs themselves are the platform's own — ADR
0007 owns the appearance and keeps the behaviour — so what is tested here is
that the platform's dialog is the one asked for, and that each answer it can
give is read as the right decision.

No dialog is ever shown: the Qt entry points are stood in for, which is exactly
what an answer the analyst cannot give would otherwise cost.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

from analysis import UnsavedChangesChoice  # noqa: E402
from application_workflow import (  # noqa: E402
    ANALYSIS_FILE_FILTER,
    SOURCE_VIDEO_FILE_FILTER,
    WorkflowPresenter,
)
from workspace_presenter import WorkspacePresenter  # noqa: E402


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def presenter(application: QApplication) -> WorkspacePresenter:
    return WorkspacePresenter()


class DialogCall:
    """What a stood-in dialog was asked for, and what it answers."""

    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.arguments: tuple[Any, ...] = ()
        self.keywords: dict[str, Any] = {}
        self.calls = 0

    def __call__(self, *arguments: Any, **keywords: Any) -> Any:
        self.calls += 1
        self.arguments = arguments
        self.keywords = keywords
        return self.answer

    @property
    def everything_passed(self) -> list[Any]:
        return [*self.arguments, *self.keywords.values()]


def _stand_in_for(
    monkeypatch: pytest.MonkeyPatch, name: str, answer: Any
) -> DialogCall:
    call = DialogCall(answer)
    monkeypatch.setattr(QFileDialog, name, staticmethod(call))
    return call


# --- The unsaved-changes question ------------------------------------------


@pytest.mark.parametrize(
    ("button", "choice"),
    [
        (QMessageBox.StandardButton.Save, UnsavedChangesChoice.SAVE),
        (QMessageBox.StandardButton.Discard, UnsavedChangesChoice.DISCARD),
        (QMessageBox.StandardButton.Cancel, UnsavedChangesChoice.CANCEL),
    ],
)
def test_every_answer_the_question_offers_is_read_as_a_decision(
    presenter: WorkspacePresenter,
    monkeypatch: pytest.MonkeyPatch,
    button: QMessageBox.StandardButton,
    choice: UnsavedChangesChoice,
) -> None:
    monkeypatch.setattr(QMessageBox, "exec", lambda _self: int(button))

    assert presenter.ask_unsaved_changes() is choice


def test_a_dismissed_question_keeps_the_unsaved_work(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Closing the window is not choosing to discard anything."""

    monkeypatch.setattr(
        QMessageBox, "exec", lambda _self: int(QMessageBox.StandardButton.NoButton)
    )

    assert presenter.ask_unsaved_changes() is UnsavedChangesChoice.CANCEL


def test_the_question_offers_all_three_decisions(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch
) -> None:
    offered: list[QMessageBox] = []
    monkeypatch.setattr(
        QMessageBox,
        "exec",
        lambda self: offered.append(self)
        or int(QMessageBox.StandardButton.Cancel),
    )

    presenter.ask_unsaved_changes()

    buttons = offered[0].standardButtons()
    assert buttons & QMessageBox.StandardButton.Save
    assert buttons & QMessageBox.StandardButton.Discard
    assert buttons & QMessageBox.StandardButton.Cancel
    assert offered[0].text()


# --- Choosing files --------------------------------------------------------


def test_the_analysis_to_open_is_chosen_from_the_platforms_dialog(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    chosen = tmp_path / "spiel.analysis"
    dialog = _stand_in_for(
        monkeypatch, "getOpenFileName", (str(chosen), ANALYSIS_FILE_FILTER)
    )

    assert presenter.choose_analysis_to_open() == str(chosen)
    assert ANALYSIS_FILE_FILTER in dialog.everything_passed


def test_a_dismissed_open_dialog_means_no_file(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stand_in_for(monkeypatch, "getOpenFileName", ("", ""))

    assert presenter.choose_analysis_to_open() is None


def test_the_destination_dialog_offers_the_name_the_workflow_suggests(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    destination = tmp_path / "spiel.analysis"
    dialog = _stand_in_for(
        monkeypatch, "getSaveFileName", (str(destination), ANALYSIS_FILE_FILTER)
    )

    assert presenter.choose_analysis_destination("Spiel gegen Kiel.analysis") == str(
        destination
    )
    offered = [value for value in dialog.everything_passed if isinstance(value, str)]
    assert any(
        value.endswith("Spiel gegen Kiel.analysis") for value in offered
    ), offered
    assert ANALYSIS_FILE_FILTER in dialog.everything_passed


def test_a_dismissed_destination_dialog_means_no_file(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stand_in_for(monkeypatch, "getSaveFileName", ("", ""))

    assert presenter.choose_analysis_destination("Analyse.analysis") is None


def test_a_source_video_is_chosen_with_the_video_filter(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The dialog is ready before the action that opens it lands in #48."""

    video = tmp_path / "halbzeit-1.mp4"
    dialog = _stand_in_for(
        monkeypatch, "getOpenFileName", (str(video), SOURCE_VIDEO_FILE_FILTER)
    )

    assert presenter.choose_source_video() == str(video)
    assert SOURCE_VIDEO_FILE_FILTER in dialog.everything_passed


@pytest.mark.parametrize(
    ("chooser", "request_file"),
    [
        ("getOpenFileName", lambda p: p.choose_analysis_to_open()),
        ("getOpenFileName", lambda p: p.choose_source_video()),
        (
            "getSaveFileName",
            lambda p: p.choose_analysis_destination("Analyse.analysis"),
        ),
    ],
    ids=["open-analysis", "add-video", "save-analysis"],
)
def test_no_file_dialog_asks_qt_to_draw_its_own(
    presenter: WorkspacePresenter,
    monkeypatch: pytest.MonkeyPatch,
    chooser: str,
    request_file: Any,
) -> None:
    """Native dialogs, per ADR 0007: appearance is owned, behaviour is not."""

    dialog = _stand_in_for(monkeypatch, chooser, ("", ""))

    request_file(presenter)

    assert dialog.calls == 1
    assert not any(
        isinstance(value, QFileDialog.Option)
        and value & QFileDialog.Option.DontUseNativeDialog
        for value in dialog.everything_passed
    )


# --- Reporting a failure ---------------------------------------------------


def test_a_failure_is_reported_where_the_analyst_will_see_it(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch
) -> None:
    reported: list[tuple[str, str]] = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        staticmethod(
            lambda _parent, title, text, *args, **kwargs: reported.append((title, text))
            or QMessageBox.StandardButton.Ok
        ),
    )

    presenter.report_failure("Analysis could not be saved", "the disk is full")

    assert reported == [("Analysis could not be saved", "the disk is full")]


def test_the_presenter_answers_everything_the_workflow_can_ask() -> None:
    """A question with no answer is a crash at the worst possible moment."""

    questions = [
        name for name in vars(WorkflowPresenter) if not name.startswith("_")
    ]
    assert questions
    for question in questions:
        assert callable(getattr(WorkspacePresenter, question, None)), question
