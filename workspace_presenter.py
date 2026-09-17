"""The questions the workflow asks, put to a person as QML's own dialogs.

`application_workflow` holds every rule about what New, Open, Save, Save As and
Close mean, and asks a `WorkflowPresenter` whenever a decision is a person's to
make. This module is that presenter for the Qt Quick workspace, and it is the
only place in the presentation layer that opens a dialog of its own.

Every dialog here used to be a `QFileDialog` or `QMessageBox`, opened with
`exec()`. Issue #69 found that self-cancelling: any `exec()`'d Qt Widgets
dialog — file chooser or message box alike — closes itself within a few
seconds of `exec()` starting if the OS mouse cursor is resting over a
hover-tracked `QQuickItem` at that moment, which on this application's own
toolbar is not a corner case but the ordinary way an analyst reaches Open,
Save As or Add Source video. `QFileDialog.open()` does not dodge it either:
transient-parented, it self-cancels in both cursor conditions; parentless, it
never becomes visible at all. The one dialog technology issue #69 measured
immune to this is `QtQuick.Dialogs.FileDialog`, which is still native on
macOS — so ADR 0007's native-*behaviour* promise holds — but is asynchronous
by construction. That is why every method below hands back its answer
through a completion instead of a return value, and it is why the file
choosers and the yes/no/report questions are QML items now rather than
anything from `QtWidgets`.

This class is the seam between that QML and `ApplicationWorkflow`. It is a
`QObject`, published to the QML engine as the `presenter` context object
alongside `workspace`: QML drives the dialog items from the properties and
signals below, and reports an answer back through a slot, which is the only
part of any of this the Python side of the workflow ever sees. Only one
question is ever outstanding at a time — every caller in `ApplicationWorkflow`
waits for the previous one to settle before asking the next — so one pending
completion per dialog *kind* (a file dialog, a question, a report) is
enough; nothing here needs to track which specific request is in flight.

QML never sees an `Analysis`, a `Clip` or a `SourceVideo` (ADR 0008): every
piece of text a dialog shows is a plain string or a small list of button
descriptions, decided here in Python.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QStandardPaths, QUrl, Signal, Slot

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

#: The button identities a question can offer, and how QML reads them back.
#: `default` marks the button Enter should choose; `cancel` marks the one
#: Escape, or dismissing the dialog outright, should be read as.
_SAVE_BUTTON = {"id": "save", "text": "Speichern", "default": True, "cancel": False}
_DISCARD_BUTTON = {
    "id": "discard",
    "text": "Verwerfen",
    "default": False,
    "cancel": False,
}
_CANCEL_BUTTON = {
    "id": "cancel",
    "text": "Abbrechen",
    "default": False,
    "cancel": True,
}
_RELOAD_BUTTON = {
    "id": "reload",
    "text": "Neu laden",
    "default": False,
    "cancel": False,
}
_SAVE_AS_BUTTON = {
    "id": "saveAs",
    "text": "Speichern unter…",
    "default": False,
    "cancel": False,
}
_YES_BUTTON = {"id": "yes", "text": "Ja", "default": True, "cancel": False}
_YES_BUTTON_NOT_DEFAULT = {"id": "yes", "text": "Ja", "default": False, "cancel": False}
_NO_BUTTON_DEFAULT = {"id": "no", "text": "Nein", "default": True, "cancel": True}
_NO_BUTTON = {"id": "no", "text": "Nein", "default": False, "cancel": True}


class WorkspacePresenter(QObject):
    """Every decision the workflow needs a person for, and every report.

    Answers a real analyst never gives back — a dialog this presenter opened
    that nothing ever answers — are simply never delivered. That is
    intentional: the workflow already treats a completion as "the command is
    still pending" rather than as a promise it will be called within any
    particular time, exactly as a real dialog left open indefinitely behaves
    today.
    """

    #: A file chooser is wanted. QML reads the four properties below to
    #: configure a `QtQuick.Dialogs.FileDialog` and opens it; the mode
    #: property tells it whether to open for reading or for writing.
    fileDialogRequested = Signal()

    #: A yes/no/report-shaped question is wanted. QML reads `questionTitle`,
    #: `questionText` and `questionButtons` to draw its own dialog.
    questionRequested = Signal()

    #: A non-blocking failure notice is wanted, read from `failureTitle` and
    #: `failureMessage`. Nothing waits for it to be dismissed.
    failureRequested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._file_dialog_title = ""
        self._file_dialog_folder = ""
        self._file_dialog_filter = ""
        self._file_dialog_mode = "open"
        self._file_dialog_suggested_name = ""
        self._file_dialog_callback: Callable[[str | None], None] | None = None

        self._question_title = ""
        self._question_text = ""
        self._question_buttons: list[dict[str, Any]] = []
        self._question_callback: Callable[[str | None], None] | None = None

        self._failure_title = ""
        self._failure_message = ""

    # --- What QML reads to draw a file dialog -------------------------------

    @Property(str, notify=fileDialogRequested)
    def fileDialogTitle(self) -> str:
        return self._file_dialog_title

    @Property(str, notify=fileDialogRequested)
    def fileDialogFolder(self) -> str:
        return self._file_dialog_folder

    @Property(str, notify=fileDialogRequested)
    def fileDialogFilter(self) -> str:
        return self._file_dialog_filter

    @Property(str, notify=fileDialogRequested)
    def fileDialogMode(self) -> str:
        """``"open"`` or ``"save"`` — which `FileDialog.fileMode` QML sets."""

        return self._file_dialog_mode

    @Property(str, notify=fileDialogRequested)
    def fileDialogSuggestedName(self) -> str:
        """The file name a Save dialog pre-fills; empty for every open dialog."""

        return self._file_dialog_suggested_name

    @Slot(QUrl)
    def fileDialogAccepted(self, url: QUrl) -> None:
        """QML reports the chosen file here.

        Not a plain string: a `FileDialog.selectedFile` is a `url`, and only
        a `QUrl` can be asked whether it is actually a local file before
        anything treats it as a path.
        """

        callback, self._file_dialog_callback = self._file_dialog_callback, None
        if callback is not None:
            callback(url.toLocalFile() if url.isLocalFile() else None)

    @Slot()
    def fileDialogCancelled(self) -> None:
        """QML reports a dismissed or cancelled file dialog here."""

        callback, self._file_dialog_callback = self._file_dialog_callback, None
        if callback is not None:
            callback(None)

    def _request_file_dialog(
        self,
        *,
        title: str,
        folder: str,
        file_filter: str,
        mode: str,
        suggested_name: str = "",
        on_result: Callable[[str | None], None],
    ) -> None:
        # A native menu shortcut can still arrive while the in-window QML
        # question is modal. Do not replace that question's completion: the
        # later command simply reads as cancelled, which is the one outcome
        # that cannot lose work or strand the original command.
        if self._file_dialog_callback is not None or self._question_callback is not None:
            on_result(None)
            return
        self._file_dialog_title = title
        self._file_dialog_folder = folder
        self._file_dialog_filter = file_filter
        self._file_dialog_mode = mode
        self._file_dialog_suggested_name = suggested_name
        self._file_dialog_callback = on_result
        self.fileDialogRequested.emit()

    # --- What QML reads to draw a question ----------------------------------

    @Property(str, notify=questionRequested)
    def questionTitle(self) -> str:
        return self._question_title

    @Property(str, notify=questionRequested)
    def questionText(self) -> str:
        return self._question_text

    @Property(list, notify=questionRequested)
    def questionButtons(self) -> list[dict[str, Any]]:
        return self._question_buttons

    @Slot(str)
    def questionAnswered(self, button_id: str) -> None:
        """QML reports which button was chosen, or an empty string when dismissed."""

        callback, self._question_callback = self._question_callback, None
        if callback is not None:
            callback(button_id or None)

    def _ask_question(
        self,
        *,
        title: str,
        text: str,
        buttons: list[dict[str, Any]],
        on_answer: Callable[[str | None], None],
    ) -> None:
        # See `_request_file_dialog`: QML blocks pointer input while a
        # question is visible, but a native menu command can bypass that
        # layer. Keep the first decision authoritative rather than replacing
        # its callback with the second command's question.
        if self._file_dialog_callback is not None or self._question_callback is not None:
            on_answer(None)
            return
        self._question_title = title
        self._question_text = text
        self._question_buttons = buttons
        self._question_callback = on_answer
        self.questionRequested.emit()

    # --- What QML reads to draw a failure notice ----------------------------

    @Property(str, notify=failureRequested)
    def failureTitle(self) -> str:
        return self._failure_title

    @Property(str, notify=failureRequested)
    def failureMessage(self) -> str:
        return self._failure_message

    # --- The `WorkflowPresenter` contract -----------------------------------

    def ask_unsaved_changes(
        self, on_result: Callable[[UnsavedChangesChoice], None]
    ) -> None:
        """Ask whether unsaved work should be saved, discarded or kept.

        A dismissed question is not an answer, so it is read as Cancel: the
        Analysis stays open and stays dirty, which is the only reading that
        cannot lose anybody's morning.
        """

        def after(button_id: str | None) -> None:
            if button_id == "save":
                on_result(UnsavedChangesChoice.SAVE)
            elif button_id == "discard":
                on_result(UnsavedChangesChoice.DISCARD)
            else:
                on_result(UnsavedChangesChoice.CANCEL)

        self._ask_question(
            title=UNSAVED_CHANGES_TITLE,
            text=UNSAVED_CHANGES_QUESTION,
            buttons=[_SAVE_BUTTON, _DISCARD_BUTTON, _CANCEL_BUTTON],
            on_answer=after,
        )

    def ask_external_change_conflict(
        self, on_result: Callable[[ExternalChangeChoice], None]
    ) -> None:
        """Ask how to resolve a Save whose file changed outside the app.

        There is no "overwrite anyway" button: only Reload and Save As are
        offered, so this question can never end in either version being
        silently destroyed. A dismissed question is Cancel, exactly as it is
        for unsaved changes: the Analysis stays open, stays dirty, and stays
        unsaved rather than guessing which version the analyst meant to keep.
        """

        def after(button_id: str | None) -> None:
            if button_id == "reload":
                on_result(ExternalChangeChoice.RELOAD)
            elif button_id == "saveAs":
                on_result(ExternalChangeChoice.SAVE_AS)
            else:
                on_result(ExternalChangeChoice.CANCEL)

        self._ask_question(
            title=EXTERNAL_CHANGE_TITLE,
            text=EXTERNAL_CHANGE_QUESTION,
            buttons=[_RELOAD_BUTTON, _SAVE_AS_BUTTON, _CANCEL_BUTTON],
            on_answer=after,
        )

    def offer_recovered_analysis(self, on_result: Callable[[bool], None]) -> None:
        """Ask whether to restore Recovery data found after abnormal termination.

        A dismissed question is read as declining it, the same reasoning as
        every other question here: it is the reading that cannot surprise
        anybody, even though — unlike unsaved changes — declining here
        discards the offered snapshot rather than keeping something open.
        """

        def after(button_id: str | None) -> None:
            on_result(button_id == "yes")

        self._ask_question(
            title=RECOVERY_OFFER_TITLE,
            text=RECOVERY_OFFER_QUESTION,
            buttons=[_YES_BUTTON, _NO_BUTTON_DEFAULT],
            on_answer=after,
        )

    def choose_analysis_to_open(
        self, on_result: Callable[[str | None], None]
    ) -> None:
        self._request_file_dialog(
            title=OPEN_ANALYSIS_TITLE,
            folder=_documents_directory(),
            file_filter=ANALYSIS_FILE_FILTER,
            mode="open",
            on_result=on_result,
        )

    def choose_analysis_destination(
        self, suggested_name: str, on_result: Callable[[str | None], None]
    ) -> None:
        self._request_file_dialog(
            title=SAVE_ANALYSIS_TITLE,
            folder=_documents_directory(),
            file_filter=ANALYSIS_FILE_FILTER,
            mode="save",
            suggested_name=suggested_name,
            on_result=on_result,
        )

    def choose_source_video(self, on_result: Callable[[str | None], None]) -> None:
        self._request_file_dialog(
            title=ADD_SOURCE_VIDEO_TITLE,
            folder=_movies_directory(),
            file_filter=SOURCE_VIDEO_FILE_FILTER,
            mode="open",
            on_result=on_result,
        )

    def choose_replacement_media(
        self, display_name: str, on_result: Callable[[str | None], None]
    ) -> None:
        self._request_file_dialog(
            title=RELINK_SOURCE_VIDEO_TITLE,
            folder=_movies_directory(),
            file_filter=SOURCE_VIDEO_FILE_FILTER,
            mode="open",
            on_result=on_result,
        )

    def confirm_source_video_replacement(
        self, display_name: str, on_result: Callable[[bool], None]
    ) -> None:
        """Ask before adopting media that does not verify against `display_name`.

        A real, consequential question — like `ask_unsaved_changes` and
        `ask_external_change_conflict` — and a dismissed dialog reads as No
        exactly as those two do: the Source video stays unavailable rather
        than silently adopting unverified media.
        """

        def after(button_id: str | None) -> None:
            on_result(button_id == "yes")

        self._ask_question(
            title=REPLACEMENT_MISMATCH_TITLE,
            text=REPLACEMENT_MISMATCH_QUESTION.format(display_name=display_name),
            buttons=[_YES_BUTTON_NOT_DEFAULT, _NO_BUTTON],
            on_answer=after,
        )

    def report_failure(self, title: str, message: str) -> None:
        self._failure_title = title
        self._failure_message = message
        self.failureRequested.emit()


def _documents_directory() -> str:
    return _existing_start_directory(
        QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
    )


def _movies_directory() -> str:
    return _existing_start_directory(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation)
    )


def _existing_start_directory(directory: str) -> str:
    """Return only a directory a native file panel can safely enter.

    macOS may report an iCloud Documents/Movies location before it is mounted
    locally. Passing that missing location to a file panel is not the cause
    of #69's hover bug, but a chooser must never be asked to enter a path that
    is not there. An empty folder leaves `FileDialog` at the platform default.
    """

    return directory if directory and Path(directory).is_dir() else ""
