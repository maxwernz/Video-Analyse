"""The questions the workflow asks, put to a person as the platform's dialogs.

`application_workflow` holds every rule about what New, Open, Save, Save As and
Close mean, and asks a `WorkflowPresenter` whenever a decision is a person's to
make. This module is that presenter for the Qt Quick workspace, and it is the
only place in the presentation layer that opens a window of its own.

The dialogs are the platform's own — ADR 0007 owns this application's
appearance and keeps native *behaviour*, and a file dialog is behaviour: it is
where sidebar favourites, network volumes and iCloud live. Nothing here asks Qt
to draw a dialog itself.

Each dialog is transient to the shown `QQuickWindow`. That keeps the platform
panel associated with the QML window that opened it without needing a QWidget.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QWindow
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

    def __init__(self) -> None:
        self._scene_window: QWindow | None = None

    def set_scene_window(self, window: QWindow) -> None:
        """Remember the shown workspace window that owns native file panels.

        A QQuickWindow cannot be a QWidget parent, but macOS needs the native
        panel to have this window as its transient parent when QML input opens
        it. The window is supplied only after the scene is shown, when Qt has
        made it a real platform window.
        """

        self._scene_window = window

    def _choose_file(
        self,
        *,
        title: str,
        directory: str,
        name_filter: str,
        accept_mode: QFileDialog.AcceptMode,
        file_mode: QFileDialog.FileMode,
        suggested_name: str | None = None,
    ) -> str | None:
        """Present one native file panel while preserving the workflow contract."""

        dialog = QFileDialog()
        dialog.setWindowTitle(title)
        dialog.setAcceptMode(accept_mode)
        dialog.setFileMode(file_mode)
        dialog.setNameFilter(name_filter)
        if _existing_directory(directory):
            dialog.setDirectory(directory)
        if suggested_name:
            dialog.selectFile(suggested_name)

        if self._scene_window is not None:
            dialog.winId()
            window_handle = dialog.windowHandle()
            if window_handle is not None:
                window_handle.setTransientParent(self._scene_window)

        if not dialog.exec():
            return None
        selected = dialog.selectedFiles()
        return selected[0] if selected else None

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
        return self._choose_file(
            title=OPEN_ANALYSIS_TITLE,
            directory=_documents_directory(),
            name_filter=ANALYSIS_FILE_FILTER,
            accept_mode=QFileDialog.AcceptMode.AcceptOpen,
            file_mode=QFileDialog.FileMode.ExistingFile,
        )

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        return self._choose_file(
            title=SAVE_ANALYSIS_TITLE,
            directory=_documents_directory(),
            name_filter=ANALYSIS_FILE_FILTER,
            accept_mode=QFileDialog.AcceptMode.AcceptSave,
            file_mode=QFileDialog.FileMode.AnyFile,
            suggested_name=suggested_name,
        )

    def choose_source_video(self) -> str | None:
        return self._choose_file(
            title=ADD_SOURCE_VIDEO_TITLE,
            directory=QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.MoviesLocation
            ),
            name_filter=SOURCE_VIDEO_FILE_FILTER,
            accept_mode=QFileDialog.AcceptMode.AcceptOpen,
            file_mode=QFileDialog.FileMode.ExistingFile,
        )

    def report_failure(self, title: str, message: str) -> None:
        QMessageBox.critical(None, title, message)


def _documents_directory() -> str:
    return QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )


def _existing_directory(directory: str) -> bool:
    """Only give native panels a start location the file system can open.

    iCloud Drive can leave a stale Documents or Movies path in QStandardPaths.
    Omitting an invalid directory lets the native panel choose its own valid
    default instead of attempting to open a location that no longer exists.
    """

    return os.path.isdir(directory)
