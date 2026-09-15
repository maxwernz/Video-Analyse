"""The application's menu bar: real, parentless, and made in Python.

Everything else this interface draws is Qt Quick. The menu bar is not, and that
is deliberate. A parentless `QMenuBar` is the *system* menu bar on macOS, which
is where a Mac user looks for New, Open and Save, and Qt Quick's own `MenuBar`
would have drawn a menu strip inside the window instead — the wordmark strip
mistake with different words in it (ADR 0007, which keeps native behaviour and
owns only the appearance). Qt Quick's `MenuBar` is deliberately not evaluated.

The entries carry `QKeySequence.StandardKey` rather than spelled-out sequences,
so Save is Cmd+S on macOS and Ctrl+S everywhere else without this module
knowing which platform it is on.

Only the document commands live here. The prototype's menu bar was inert from
end to end, and an entry that does nothing is worse than one that is missing,
so Clip and view entries arrive with the tickets that own those surfaces.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenuBar


FILE_MENU_TITLE = "Datei"

NEW_ANALYSIS_TEXT = "Neue Analyse"
OPEN_ANALYSIS_TEXT = "Analyse öffnen …"
SAVE_ANALYSIS_TEXT = "Analyse speichern"
SAVE_ANALYSIS_AS_TEXT = "Analyse speichern unter …"
CLOSE_TEXT = "Schließen"


class DocumentCommands(Protocol):
    """What the menu bar needs of the workspace, and nothing more."""

    def newAnalysis(self) -> bool: ...

    def openAnalysis(self) -> bool: ...

    def saveAnalysis(self) -> bool: ...

    def saveAnalysisAs(self) -> bool: ...


def build_menu_bar(
    commands: DocumentCommands,
    *,
    close_window: Callable[[], None],
) -> QMenuBar:
    """The File menu, wired to the commands the workspace already carries.

    Closing goes through the window rather than through a command of its own:
    the red button, the platform's quit and this entry then all arrive at the
    same gate, and the unsaved-changes question is asked exactly once, in one
    place.

    The menu bar has no parent and nothing else holds it, so the caller keeps
    the returned object alive for as long as the application runs.
    """

    menu_bar = QMenuBar()
    file_menu = menu_bar.addMenu(FILE_MENU_TITLE)

    file_menu.addAction(
        _command(
            menu_bar,
            NEW_ANALYSIS_TEXT,
            QKeySequence.StandardKey.New,
            commands.newAnalysis,
        )
    )
    file_menu.addAction(
        _command(
            menu_bar,
            OPEN_ANALYSIS_TEXT,
            QKeySequence.StandardKey.Open,
            commands.openAnalysis,
        )
    )
    file_menu.addSeparator()
    file_menu.addAction(
        _command(
            menu_bar,
            SAVE_ANALYSIS_TEXT,
            QKeySequence.StandardKey.Save,
            commands.saveAnalysis,
        )
    )
    file_menu.addAction(
        _command(
            menu_bar,
            SAVE_ANALYSIS_AS_TEXT,
            QKeySequence.StandardKey.SaveAs,
            commands.saveAnalysisAs,
        )
    )
    file_menu.addSeparator()
    file_menu.addAction(
        _command(
            menu_bar,
            CLOSE_TEXT,
            QKeySequence.StandardKey.Close,
            close_window,
        )
    )
    return menu_bar


def _command(
    menu_bar: QMenuBar,
    text: str,
    shortcut: QKeySequence.StandardKey,
    run: Callable[[], object],
) -> QAction:
    action = QAction(text, menu_bar)
    action.setShortcut(QKeySequence(shortcut))
    # A command reports whether it happened; a menu entry has nowhere to say
    # so, and what it could not do has already been reported to the analyst.
    action.triggered.connect(lambda _checked=False: run())
    return action
