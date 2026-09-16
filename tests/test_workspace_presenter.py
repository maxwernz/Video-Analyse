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
import workspace_presenter  # noqa: E402
from workspace_presenter import WorkspacePresenter  # noqa: E402


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def presenter(application: QApplication) -> WorkspacePresenter:
    return WorkspacePresenter()


class DialogCall:
    """A native dialog stand-in that records what it was configured with.

    `WorkspacePresenter` builds a real `QFileDialog` instance rather than
    calling the static convenience functions, so the stand-in mirrors the
    instance API instead of intercepting a single class method.
    """

    def __init__(self, answer: str | None) -> None:
        self.answer = answer
        self.title = ""
        self.accept_mode: QFileDialog.AcceptMode | None = None
        self.file_mode: QFileDialog.FileMode | None = None
        self.name_filter = ""
        self.directory: str | None = None
        self.selected_name = ""
        self.options_set: list[QFileDialog.Option] = []
        self.calls = 0

    def setWindowTitle(self, title: str) -> None:
        self.title = title

    def setAcceptMode(self, mode: QFileDialog.AcceptMode) -> None:
        self.accept_mode = mode

    def setFileMode(self, mode: QFileDialog.FileMode) -> None:
        self.file_mode = mode

    def setNameFilter(self, name_filter: str) -> None:
        self.name_filter = name_filter

    def setDirectory(self, directory: str) -> None:
        self.directory = directory

    def selectFile(self, name: str) -> None:
        self.selected_name = name

    def setOption(self, option: QFileDialog.Option, *_args: Any) -> None:
        self.options_set.append(option)

    def exec(self) -> int:
        self.calls += 1
        return int(bool(self.answer))

    def selectedFiles(self) -> list[str]:
        return [self.answer] if self.answer else []


def _stand_in_for(
    monkeypatch: pytest.MonkeyPatch, answer: str | None
) -> DialogCall:
    """Replace the `QFileDialog` the presenter builds with a recording stub.

    A single stand-in serves every chooser: the presenter always goes through
    one instance-building seam (`_choose_file`) regardless of which document
    command asked for a file.
    """

    dialog = DialogCall(answer)

    class _StandInDialogClass:
        """A stand-in for the `QFileDialog` class, not just one instance.

        The presenter reads `QFileDialog.AcceptMode`/`FileMode`/`Option` off
        the class itself, so the stand-in has to be a class-like object too,
        not merely a factory function.
        """

        AcceptMode = QFileDialog.AcceptMode
        FileMode = QFileDialog.FileMode
        Option = QFileDialog.Option

        def __new__(cls) -> DialogCall:  # type: ignore[misc]
            return dialog

    monkeypatch.setattr(workspace_presenter, "QFileDialog", _StandInDialogClass)
    return dialog


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
    assert dialog.accept_mode == QFileDialog.AcceptMode.AcceptOpen


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
    assert dialog.accept_mode == QFileDialog.AcceptMode.AcceptSave


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
    assert dialog.accept_mode == QFileDialog.AcceptMode.AcceptOpen


@pytest.mark.parametrize(
    "request_file",
    [
        lambda p: p.choose_analysis_to_open(),
        lambda p: p.choose_source_video(),
        lambda p: p.choose_analysis_destination("Analyse.analysis"),
    ],
    ids=["open-analysis", "add-video", "save-analysis"],
)
def test_no_file_dialog_asks_qt_to_draw_its_own(
    presenter: WorkspacePresenter,
    monkeypatch: pytest.MonkeyPatch,
    request_file: Any,
) -> None:
    """Native dialogs, per ADR 0007: appearance is owned, behaviour is not."""

    dialog = _stand_in_for(monkeypatch, None)

    request_file(presenter)

    assert dialog.calls == 1
    assert QFileDialog.Option.DontUseNativeDialog not in dialog.options_set


# --- The start directory ----------------------------------------------------
#
# iCloud Drive can leave a stale Documents or Movies path in
# `QStandardPaths`; a native panel given one refuses to open at all. This is
# not #69's self-closing dialog — that cause is a `QQuickItem`'s hover/cursor
# tracking during the panel's modal loop (see `workspace_presenter`'s
# `_choose_file` docstring), which is not assertable under the offscreen
# platform this suite runs under. This is the one piece of #69's
# investigation that *is* a Python-level seam: the presenter must not hand
# the panel a start directory that cannot be opened.


def test_a_missing_start_directory_is_left_to_the_panels_own_default(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(
        workspace_presenter, "_documents_directory", lambda: str(missing)
    )
    dialog = _stand_in_for(monkeypatch, None)

    presenter.choose_analysis_to_open()

    assert dialog.directory is None


def test_an_existing_start_directory_is_still_offered(
    presenter: WorkspacePresenter, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        workspace_presenter, "_documents_directory", lambda: str(tmp_path)
    )
    dialog = _stand_in_for(monkeypatch, None)

    presenter.choose_analysis_to_open()

    assert dialog.directory == str(tmp_path)


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
