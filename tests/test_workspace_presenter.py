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

from PySide6.QtGui import QWindow  # noqa: E402
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


class DialogHandle:
    """The visible dialog window, reduced to its ownership relationship."""

    def __init__(self) -> None:
        self.transient_parent: QWindow | None = None

    def setTransientParent(self, parent: QWindow) -> None:
        self.transient_parent = parent


class DialogCall:
    """A native dialog stand-in that records the choices it is configured with."""

    def __init__(self, answer: str | None) -> None:
        self.answer = answer
        self.window_handle = DialogHandle()
        self.title = ""
        self.name_filter = ""
        self.directory: str | None = None
        self.selected_name = ""
        self.calls = 0
        self.native_handle_requested = False

    def setWindowTitle(self, title: str) -> None:
        self.title = title

    def setAcceptMode(self, _mode: QFileDialog.AcceptMode) -> None:
        pass

    def setFileMode(self, _mode: QFileDialog.FileMode) -> None:
        pass

    def setNameFilter(self, name_filter: str) -> None:
        self.name_filter = name_filter

    def setDirectory(self, directory: str) -> None:
        self.directory = directory

    def selectFile(self, name: str) -> None:
        self.selected_name = name

    def winId(self) -> int:
        self.native_handle_requested = True
        return 0

    def windowHandle(self) -> DialogHandle:
        return self.window_handle

    def exec(self) -> int:
        self.calls += 1
        return int(bool(self.answer))

    def selectedFiles(self) -> list[str]:
        return [self.answer] if self.answer else []


def _stand_in_for(
    monkeypatch: pytest.MonkeyPatch, answer: str | None
) -> DialogCall:
    call = DialogCall(answer)

    class StandInFileDialog:
        AcceptMode = QFileDialog.AcceptMode
        FileMode = QFileDialog.FileMode

        def __new__(cls) -> DialogCall:
            return call

    monkeypatch.setattr("workspace_presenter.QFileDialog", StandInFileDialog)
    return call


FILE_CHOOSERS = [
    lambda presenter: presenter.choose_analysis_to_open(),
    lambda presenter: presenter.choose_source_video(),
    lambda presenter: presenter.choose_analysis_destination("Analyse.analysis"),
]


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
    dialog = _stand_in_for(monkeypatch, str(chosen))

    assert presenter.choose_analysis_to_open() == str(chosen)
    assert dialog.name_filter == ANALYSIS_FILE_FILTER


def test_a_dismissed_open_dialog_means_no_file(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stand_in_for(monkeypatch, None)

    assert presenter.choose_analysis_to_open() is None


def test_the_destination_dialog_offers_the_name_the_workflow_suggests(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    destination = tmp_path / "spiel.analysis"
    dialog = _stand_in_for(monkeypatch, str(destination))

    assert presenter.choose_analysis_destination("Spiel gegen Kiel.analysis") == str(
        destination
    )
    assert dialog.selected_name == "Spiel gegen Kiel.analysis"
    assert dialog.name_filter == ANALYSIS_FILE_FILTER


def test_a_dismissed_destination_dialog_means_no_file(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stand_in_for(monkeypatch, None)

    assert presenter.choose_analysis_destination("Analyse.analysis") is None


def test_a_source_video_is_chosen_with_the_video_filter(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The dialog is ready before the action that opens it lands in #48."""

    video = tmp_path / "halbzeit-1.mp4"
    dialog = _stand_in_for(monkeypatch, str(video))

    assert presenter.choose_source_video() == str(video)
    assert dialog.name_filter == SOURCE_VIDEO_FILE_FILTER


@pytest.mark.parametrize(
    "request_file",
    FILE_CHOOSERS,
    ids=["open-analysis", "add-video", "save-analysis"],
)
def test_every_file_dialog_has_the_shown_scene_as_its_transient_parent(
    presenter: WorkspacePresenter,
    monkeypatch: pytest.MonkeyPatch,
    request_file: Any,
) -> None:
    """The offscreen seam covers ownership; Cocoa input delivery needs live proof."""

    scene_window = QWindow()
    presenter.set_scene_window(scene_window)
    dialog = _stand_in_for(monkeypatch, None)

    request_file(presenter)

    assert dialog.calls == 1
    assert dialog.native_handle_requested
    assert dialog.window_handle.transient_parent is scene_window


@pytest.mark.parametrize(
    "request_file",
    FILE_CHOOSERS,
    ids=["open-analysis", "add-video", "save-analysis"],
)
def test_a_missing_start_directory_is_not_given_to_the_native_dialog(
    presenter: WorkspacePresenter,
    monkeypatch: pytest.MonkeyPatch,
    request_file: Any,
) -> None:
    """A stale iCloud location must leave Qt to choose a directory it can open."""

    missing_directory = "/not-a-real-video-analyse-directory"
    monkeypatch.setattr(
        "workspace_presenter.QStandardPaths.writableLocation",
        lambda _location: missing_directory,
    )
    dialog = _stand_in_for(monkeypatch, None)

    request_file(presenter)

    assert dialog.directory is None


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
