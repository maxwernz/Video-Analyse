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

from analysis import ExternalChangeChoice, UnsavedChangesChoice
from application_workflow import ANALYSIS_FILE_FILTER, SOURCE_VIDEO_FILE_FILTER


UNSAVED_CHANGES_TITLE = "Ungespeicherte Änderungen"
UNSAVED_CHANGES_QUESTION = (
    "Es gibt ungespeicherte Änderungen. Möchten Sie speichern?"
)

OPEN_ANALYSIS_TITLE = "Analyse öffnen"
SAVE_ANALYSIS_TITLE = "Analyse speichern"
ADD_SOURCE_VIDEO_TITLE = "Video hinzufügen"
RELINK_SOURCE_VIDEO_TITLE = "Ersatzmedia auswählen"

EXTERNAL_CHANGE_TITLE = "Datei wurde extern geändert"
EXTERNAL_CHANGE_QUESTION = (
    "Diese Analyse-Datei wurde außerhalb der Anwendung geändert. Möchten Sie "
    "die geänderte Datei laden (eigene Änderungen gehen verloren) oder Ihre "
    "Änderungen unter einem anderen Namen speichern?"
)

REPLACEMENT_MISMATCH_TITLE = "Video stimmt nicht überein"
REPLACEMENT_MISMATCH_QUESTION = (
    "Die gewählte Datei stimmt nicht mit den gespeicherten Merkmalen von "
    "„{display_name}“ überein (Größe, Länge, Inhalt). Vorhandene Clip-"
    "Zeitstempel passen möglicherweise nicht mehr zum Ersatzmedium. Trotzdem "
    "verknüpfen?"
)

RECOVERY_OFFER_TITLE = "Nicht gespeicherte Änderungen gefunden"
RECOVERY_OFFER_QUESTION = (
    "Nach einem unerwarteten Beenden wurden nicht gespeicherte Änderungen "
    "gefunden. Möchten Sie diese wiederherstellen?"
)


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

    def ask_external_change_conflict(self) -> ExternalChangeChoice:
        """Ask how to resolve a Save whose file changed outside the app.

        There is no "overwrite anyway" button: only Reload and Save As are
        offered, so this question can never end in either version being
        silently destroyed. A dismissed question is Cancel, exactly as it is
        for unsaved changes: the Analysis stays open, stays dirty, and stays
        unsaved rather than guessing which version the analyst meant to keep.
        """

        question = QMessageBox()
        question.setIcon(QMessageBox.Icon.Warning)
        question.setWindowTitle(EXTERNAL_CHANGE_TITLE)
        question.setText(EXTERNAL_CHANGE_QUESTION)
        reload_button = question.addButton(
            "Neu laden", QMessageBox.ButtonRole.AcceptRole
        )
        save_as_button = question.addButton(
            "Speichern unter…", QMessageBox.ButtonRole.ActionRole
        )
        question.addButton(QMessageBox.StandardButton.Cancel)
        question.setDefaultButton(QMessageBox.StandardButton.Cancel)

        question.exec()
        clicked = question.clickedButton()
        if clicked is reload_button:
            return ExternalChangeChoice.RELOAD
        if clicked is save_as_button:
            return ExternalChangeChoice.SAVE_AS
        return ExternalChangeChoice.CANCEL

    def offer_recovered_analysis(self) -> bool:
        """Ask whether to restore Recovery data found after abnormal termination.

        A dismissed question is read as declining it, the same reasoning as
        every other question here: it is the reading that cannot surprise
        anybody, even though — unlike unsaved changes — declining here
        discards the offered snapshot rather than keeping something open.
        """

        question = QMessageBox()
        question.setIcon(QMessageBox.Icon.Question)
        question.setWindowTitle(RECOVERY_OFFER_TITLE)
        question.setText(RECOVERY_OFFER_QUESTION)
        question.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        question.setDefaultButton(QMessageBox.StandardButton.Yes)
        return question.exec() == QMessageBox.StandardButton.Yes

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

    def choose_replacement_media(self, display_name: str) -> str | None:
        chosen, _ = QFileDialog.getOpenFileName(
            None,
            RELINK_SOURCE_VIDEO_TITLE,
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.MoviesLocation
            ),
            SOURCE_VIDEO_FILE_FILTER,
        )
        return chosen or None

    def confirm_source_video_replacement(self, display_name: str) -> bool:
        """Ask before adopting media that does not verify against `display_name`.

        A real, consequential question — like `ask_unsaved_changes` and
        `ask_external_change_conflict` — so it is a native `QMessageBox`
        rather than anything drawn in QML, and a dismissed dialog reads as
        No exactly as those two do: the Source video stays unavailable
        rather than silently adopting unverified media.
        """
        question = QMessageBox()
        question.setIcon(QMessageBox.Icon.Warning)
        question.setWindowTitle(REPLACEMENT_MISMATCH_TITLE)
        question.setText(
            REPLACEMENT_MISMATCH_QUESTION.format(display_name=display_name)
        )
        question.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        question.setDefaultButton(QMessageBox.StandardButton.No)
        return question.exec() == QMessageBox.StandardButton.Yes

    def report_failure(self, title: str, message: str) -> None:
        QMessageBox.critical(None, title, message)


def _documents_directory() -> str:
    return QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
