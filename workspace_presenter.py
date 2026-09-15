"""The questions the workflow asks, put to a person as the platform's dialogs.

`application_workflow` holds every rule about what New, Open, Save, Save As and
Close mean, and asks a `WorkflowPresenter` whenever a decision is a person's to
make. This module is that presenter for the Qt Quick workspace, and it is the
only place in the presentation layer that opens a window of its own.

The dialogs are the platform's own — ADR 0007 owns this application's
appearance and keeps native *behaviour*, and a file dialog is behaviour: it is
where sidebar favourites, network volumes and iCloud live. Nothing here asks Qt
to draw a dialog itself.

They are parentless, because the workspace's window is a `QQuickWindow` rather
than a `QWidget` and cannot parent one. Qt gives a parentless dialog to the
active window, which in a single-window application is the workspace.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QMessageBox

from analysis import UnsavedChangesChoice
from application_workflow import ANALYSIS_FILE_FILTER, SOURCE_VIDEO_FILE_FILTER


UNSAVED_CHANGES_TITLE = "Ungespeicherte Änderungen"
UNSAVED_CHANGES_QUESTION = (
    "Es gibt ungespeicherte Änderungen. Möchten Sie speichern?"
)

OPEN_ANALYSIS_TITLE = "Analyse öffnen"
SAVE_ANALYSIS_TITLE = "Analyse speichern"
ADD_SOURCE_VIDEO_TITLE = "Video hinzufügen"


class WorkspacePresenter:
    """Every decision the workflow needs a person for, and every report."""

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        """Ask whether unsaved work should be saved, discarded or kept.

        A dismissed question is not an answer, so it is read as Cancel: the
        Analysis stays open and stays dirty, which is the only reading that
        cannot lose anybody's morning.
        """

        question = QMessageBox()
        question.setIcon(QMessageBox.Icon.Warning)
        question.setWindowTitle(UNSAVED_CHANGES_TITLE)
        question.setText(UNSAVED_CHANGES_QUESTION)
        question.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        question.setDefaultButton(QMessageBox.StandardButton.Save)

        answer = question.exec()
        if answer == QMessageBox.StandardButton.Save:
            return UnsavedChangesChoice.SAVE
        if answer == QMessageBox.StandardButton.Discard:
            return UnsavedChangesChoice.DISCARD
        return UnsavedChangesChoice.CANCEL

    def choose_analysis_to_open(self) -> str | None:
        chosen, _ = QFileDialog.getOpenFileName(
            None,
            OPEN_ANALYSIS_TITLE,
            _documents_directory(),
            ANALYSIS_FILE_FILTER,
        )
        return chosen or None

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        chosen, _ = QFileDialog.getSaveFileName(
            None,
            SAVE_ANALYSIS_TITLE,
            os.path.join(_documents_directory(), suggested_name),
            ANALYSIS_FILE_FILTER,
        )
        return chosen or None

    def choose_source_video(self) -> str | None:
        chosen, _ = QFileDialog.getOpenFileName(
            None,
            ADD_SOURCE_VIDEO_TITLE,
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.MoviesLocation
            ),
            SOURCE_VIDEO_FILE_FILTER,
        )
        return chosen or None

    def report_failure(self, title: str, message: str) -> None:
        QMessageBox.critical(None, title, message)


def _documents_directory() -> str:
    return QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
