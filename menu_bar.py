"""The application's menu bar: one definition, two platforms' worth of menu.

Every document command an analyst can reach through a menu is written down
exactly once, in `MENUS`, and both menu bars are built from it:

- macOS gets a real parentless `QMenuBar`, which Cocoa turns into the *system*
  menu bar. That is where a Mac user looks for New, Open and Save, and drawing
  a menu strip inside the window instead would be the wordmark strip mistake
  with different words in it (ADR 0007, which keeps native behaviour and owns
  only the appearance).
- Windows and Linux put the menu bar inside the window, where a `QMenuBar`
  cannot go because a `QQuickWindow` is not a widget. There the same `MENUS`
  are handed to QML as data — `menu_model()` — and `qml/MenuBar.qml` draws
  them from the same primitives as every other surface.

A second, hand-maintained list for the second platform is the failure this
module exists to prevent, so neither menu bar knows what the commands are: the
entries, their order, their separators and their key sequences all come from
`MENUS`, and what an entry *does* comes from `command_runners`.

The entries carry `QKeySequence.StandardKey` rather than spelled-out sequences,
so Save is Cmd+S on macOS and Ctrl+S everywhere else without this module
knowing which platform it is on.

Only the document commands live here. The prototype's menu bar was inert from
end to end, and an entry that does nothing is worse than one that is missing,
so Clip and view entries arrive with the tickets that own those surfaces.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import sys
from typing import Protocol

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenuBar


FILE_MENU_TITLE = "Datei"

NEW_ANALYSIS_TEXT = "Neue Analyse"
OPEN_ANALYSIS_TEXT = "Analyse öffnen …"
SAVE_ANALYSIS_TEXT = "Analyse speichern"
SAVE_ANALYSIS_AS_TEXT = "Analyse speichern unter …"
CLOSE_TEXT = "Schließen"

#: What an entry names. A command is a name rather than a callable because the
#: QML menu bar receives its entries as data over the view model boundary, and
#: a callable is not something QML may be handed.
NEW = "new"
OPEN = "open"
SAVE = "save"
SAVE_AS = "saveAs"
CLOSE = "close"


class DocumentCommands(Protocol):
    """What the menu bar needs of the workspace, and nothing more."""

    def newAnalysis(self) -> bool: ...

    def openAnalysis(self) -> bool: ...

    def saveAnalysis(self) -> bool: ...

    def saveAnalysisAs(self) -> bool: ...


@dataclass(frozen=True)
class MenuEntry:
    """One command, as both menu bars draw it."""

    command: str
    text: str
    shortcut: QKeySequence.StandardKey


@dataclass(frozen=True)
class MenuSeparator:
    """The rule between two groups of commands."""


SEPARATOR = MenuSeparator()


@dataclass(frozen=True)
class Menu:
    """One menu in the bar, in the order its entries are read."""

    title: str
    entries: tuple[MenuEntry | MenuSeparator, ...]


#: The menu bar, defined once for every platform that has one.
MENUS: tuple[Menu, ...] = (
    Menu(
        FILE_MENU_TITLE,
        (
            MenuEntry(NEW, NEW_ANALYSIS_TEXT, QKeySequence.StandardKey.New),
            MenuEntry(OPEN, OPEN_ANALYSIS_TEXT, QKeySequence.StandardKey.Open),
            SEPARATOR,
            MenuEntry(SAVE, SAVE_ANALYSIS_TEXT, QKeySequence.StandardKey.Save),
            MenuEntry(SAVE_AS, SAVE_ANALYSIS_AS_TEXT, QKeySequence.StandardKey.SaveAs),
            SEPARATOR,
            MenuEntry(CLOSE, CLOSE_TEXT, QKeySequence.StandardKey.Close),
        ),
    ),
)


def entries_of(menus: tuple[Menu, ...] = MENUS) -> list[MenuEntry]:
    """Every command in the bar, in the order it is read."""

    return [
        entry
        for menu in menus
        for entry in menu.entries
        if isinstance(entry, MenuEntry)
    ]


def native_menu_bar_available() -> bool:
    """Whether this platform puts the menu bar outside the window.

    macOS does, and a parentless `QMenuBar` becomes it. Everywhere else the
    menu bar belongs inside the window, where only QML can draw it. The same
    question is asked in `qml/Main.qml`, and a test holds the two answers
    together.
    """

    return sys.platform == "darwin"


def command_runners(
    commands: DocumentCommands,
    *,
    close_window: Callable[[], None],
) -> dict[str, Callable[[], object]]:
    """What each command does, for whichever menu bar is asking.

    Closing goes through the window rather than through a command of its own:
    the red button, the platform's quit and this entry then all arrive at the
    same gate, and the unsaved-changes question is asked exactly once, in one
    place.
    """

    return {
        NEW: commands.newAnalysis,
        OPEN: commands.openAnalysis,
        SAVE: commands.saveAnalysis,
        SAVE_AS: commands.saveAnalysisAs,
        CLOSE: close_window,
    }


def menu_model(menus: tuple[Menu, ...] = MENUS) -> list[dict[str, object]]:
    """`MENUS` as the plain data the QML menu bar draws.

    The key sequence is written out here rather than in QML, in the platform's
    own notation, because `StandardKey` is what names the command and only Qt
    knows what that is on the machine this is running on.

    Nothing in this model declares a shortcut. The sequences are *listened* for
    once per platform — by the system menu bar on macOS, by the window's own
    `Shortcut` items everywhere else — and a menu entry that declared them a
    second time would make every one of them ambiguous.
    """

    return [
        {
            "title": menu.title,
            "entries": [_entry_model(entry) for entry in menu.entries],
        }
        for menu in menus
    ]


def _entry_model(entry: MenuEntry | MenuSeparator) -> dict[str, object]:
    if isinstance(entry, MenuSeparator):
        return {"separator": True}
    return {
        "separator": False,
        "command": entry.command,
        "text": entry.text,
        "shortcut": QKeySequence(entry.shortcut).toString(
            QKeySequence.SequenceFormat.NativeText
        ),
    }


def build_menu_bar(
    commands: DocumentCommands,
    *,
    close_window: Callable[[], None],
) -> QMenuBar:
    """`MENUS` as a real `QMenuBar`, wired to the commands the workspace carries.

    The menu bar has no parent and nothing else holds it, so the caller keeps
    the returned object alive for as long as the application runs.
    """

    runners = command_runners(commands, close_window=close_window)
    menu_bar = QMenuBar()
    for menu in MENUS:
        built = menu_bar.addMenu(menu.title)
        for entry in menu.entries:
            if isinstance(entry, MenuSeparator):
                built.addSeparator()
                continue
            built.addAction(_command(menu_bar, entry, runners[entry.command]))
    return menu_bar


def _command(
    menu_bar: QMenuBar,
    entry: MenuEntry,
    run: Callable[[], object],
) -> QAction:
    action = QAction(entry.text, menu_bar)
    # QML gets this same identifier in `menu_model()`. Keeping it on the
    # widget action makes the shared-definition contract observable too: a
    # test can read both bars back including what each entry actually runs.
    action.setData(entry.command)
    action.setShortcut(QKeySequence(entry.shortcut))
    # A command reports whether it happened; a menu entry has nowhere to say
    # so, and what it could not do has already been reported to the analyst.
    action.triggered.connect(lambda _checked=False: run())
    return action
