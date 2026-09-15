"""The menu bar, which is the one part of this interface Qt Quick never draws.

A real parentless `QMenuBar` created in Python is the system menu bar on macOS,
which is the whole point: ADR 0007 owns the appearance and keeps the behaviour,
and a menu strip drawn inside the window would be the wordmark strip again with
different words in it. Qt Quick's own `MenuBar` is deliberately not evaluated.

What is tested here is that every document command and the established Add
Source video command is in it, that each carries its intended shortcut, and
that triggering an entry runs the command.
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QAction, QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QMenuBar  # noqa: E402

from menu_bar import ADD_SOURCE_VIDEO_TEXT, FILE_MENU_TITLE, build_menu_bar  # noqa: E402


class RecordingCommands:
    """Stands in for the view model: the commands, written down."""

    def __init__(self) -> None:
        self.ran: list[str] = []

    def newAnalysis(self) -> bool:
        self.ran.append("new")
        return True

    def openAnalysis(self) -> bool:
        self.ran.append("open")
        return True

    def saveAnalysis(self) -> bool:
        self.ran.append("save")
        return True

    def saveAnalysisAs(self) -> bool:
        self.ran.append("save as")
        return True

    def addSourceVideo(self) -> bool:
        self.ran.append("add video")
        return True


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def commands() -> RecordingCommands:
    return RecordingCommands()


@pytest.fixture
def closed() -> list[str]:
    return []


@pytest.fixture
def menu_bar(
    application: QApplication, commands: RecordingCommands, closed: list[str]
) -> QMenuBar:
    return build_menu_bar(commands, close_window=lambda: closed.append("closed"))


def _file_menu(menu_bar: QMenuBar) -> QMenu:
    menu = menu_bar.findChild(QMenu)
    assert isinstance(menu, QMenu)
    return menu


def _entries(menu_bar: QMenuBar) -> list[QAction]:
    return [
        action for action in _file_menu(menu_bar).actions() if not action.isSeparator()
    ]


def _entry(menu_bar: QMenuBar, shortcut: QKeySequence.StandardKey) -> QAction:
    for action in _entries(menu_bar):
        if action.shortcut() == QKeySequence(shortcut):
            return action
    raise AssertionError(f"no menu entry carries {shortcut}")


def test_the_menu_bar_belongs_to_no_window(menu_bar: QMenuBar) -> None:
    """Parentless is what makes it the system menu bar on macOS."""

    assert menu_bar.parent() is None
    assert _file_menu(menu_bar).title() == FILE_MENU_TITLE


def test_on_macos_it_really_is_the_system_menu_bar(
    menu_bar: QMenuBar, application: QApplication
) -> None:
    """The claim ADR 0007 rests on, checked rather than assumed.

    The prototype only ever ran on macOS, so "the system menu bar" is a claim
    about *there*. It is also only true under the real platform plugin: the
    offscreen plugin continuous integration uses has no menu bar to hand a
    menu to, which is why this skips rather than fails.
    """

    if sys.platform != "darwin" or application.platformName() != "cocoa":
        pytest.skip("only the real macOS platform plugin has a system menu bar")

    assert menu_bar.isNativeMenuBar()


def test_every_document_command_has_an_entry_and_its_platform_shortcut(
    menu_bar: QMenuBar,
) -> None:
    commanded = {
        QKeySequence.StandardKey.New,
        QKeySequence.StandardKey.Open,
        QKeySequence.StandardKey.Save,
        QKeySequence.StandardKey.SaveAs,
        QKeySequence.StandardKey.Close,
    }
    carried = {action.shortcut() for action in _entries(menu_bar)}

    for standard_key in commanded:
        assert QKeySequence(standard_key) in carried, standard_key

    for action in _entries(menu_bar):
        assert action.text(), "a menu entry with no text"
        assert not action.shortcut().isEmpty()


def test_the_add_source_video_command_keeps_its_existing_shortcut(
    menu_bar: QMenuBar, commands: RecordingCommands
) -> None:
    shortcut = QKeySequence("Ctrl+Shift+O")
    add_video = next(
        action for action in _entries(menu_bar) if action.text() == ADD_SOURCE_VIDEO_TEXT
    )

    assert add_video.shortcut() == shortcut
    add_video.trigger()
    assert commands.ran == ["add video"]


def test_the_commands_read_in_the_order_they_are_used(menu_bar: QMenuBar) -> None:
    ordered = [
        QKeySequence(action.shortcut()) for action in _entries(menu_bar)
    ]
    assert ordered == [
        QKeySequence(QKeySequence.StandardKey.New),
        QKeySequence(QKeySequence.StandardKey.Open),
        QKeySequence(QKeySequence.StandardKey.Save),
        QKeySequence(QKeySequence.StandardKey.SaveAs),
        QKeySequence("Ctrl+Shift+O"),
        QKeySequence(QKeySequence.StandardKey.Close),
    ]


@pytest.mark.parametrize(
    ("standard_key", "command"),
    [
        (QKeySequence.StandardKey.New, "new"),
        (QKeySequence.StandardKey.Open, "open"),
        (QKeySequence.StandardKey.Save, "save"),
        (QKeySequence.StandardKey.SaveAs, "save as"),
    ],
)
def test_choosing_an_entry_runs_the_command_it_names(
    menu_bar: QMenuBar,
    commands: RecordingCommands,
    standard_key: QKeySequence.StandardKey,
    command: str,
) -> None:
    _entry(menu_bar, standard_key).trigger()

    assert commands.ran == [command]


def test_close_asks_the_window_to_close_rather_than_the_document(
    menu_bar: QMenuBar, commands: RecordingCommands, closed: list[str]
) -> None:
    """Closing goes through the window, so one gate asks about unsaved work.

    The window's own close — the red button, Cmd+Q, the menu entry — all end up
    in the same place, and that place is where the question is asked.
    """

    _entry(menu_bar, QKeySequence.StandardKey.Close).trigger()

    assert closed == ["closed"]
    assert commands.ran == []


def test_the_menu_bar_carries_no_entry_that_does_nothing(
    menu_bar: QMenuBar, commands: RecordingCommands, closed: list[str]
) -> None:
    """An inert menu entry is worse than a missing one.

    The prototype's menu bar was inert throughout, which is the gap this
    ticket closes. Entries for the surfaces that do not exist yet arrive with
    the tickets that own them.
    """

    for action in _entries(menu_bar):
        commands.ran.clear()
        closed.clear()
        action.trigger()
        assert commands.ran or closed, f"{action.text()} does nothing"
