"""The menu bar Windows and Linux draw inside the window.

There are two menu bars and there is one definition. macOS gets a real
parentless `QMenuBar`, which is the system menu bar (`tests/test_menu_bar.py`);
every other platform has nowhere to put a widget, so `qml/MenuBar.qml` draws
the same commands from the same `menu_bar.MENUS`. A second, hand-maintained
list is the failure this ticket exists to prevent, so the first tests here are
about the two bars being unable to differ.

The rest press the real menu. A QML delegate that binds to a property which
does not exist loads without complaint and draws nothing, and a menu nobody
ever opened instantiates no delegate at all — so these open it, look at what it
drew, and click the entries rather than calling the slots behind them.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent  # noqa: E402
from PySide6.QtQuick import QQuickItem  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QMenuBar  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402

import menu_bar  # noqa: E402
from analysis import AnalysisDocument, UnsavedChangesChoice  # noqa: E402
from app_runtime import register_bundled_fonts  # noqa: E402
from application_workflow import UNTITLED_ANALYSIS_TITLE  # noqa: E402
from playback import FakePlayback  # noqa: E402
from qml_runtime import build_engine  # noqa: E402
from workspace_view_model import WorkspaceViewModel  # noqa: E402


PROJECT_ROOT = Path(__file__).parents[1]
QML_ROOT = PROJECT_ROOT / "qml"
MENU_BAR_QML = QML_ROOT / "MenuBar.qml"
MAIN_QML = QML_ROOT / "Main.qml"


@pytest.fixture(scope="session")
def application() -> QApplication:
    instance = QApplication.instance() or QApplication([])
    register_bundled_fonts()
    assert isinstance(instance, QApplication)
    return instance


# --- One definition, two menu bars -----------------------------------------


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


def _widget_entries(bar: QMenuBar) -> list[tuple[str, str, str, str]]:
    """The `QMenuBar`, read back as title, text, sequence and command."""

    read: list[tuple[str, str, str, str]] = []
    for menu in bar.findChildren(QMenu):
        for action in menu.actions():
            if action.isSeparator():
                read.append((menu.title(), "", "", ""))
                continue
            read.append(
                (
                    menu.title(),
                    action.text(),
                    action.shortcut().toString(
                        QKeySequence.SequenceFormat.NativeText
                    ),
                    str(action.data()),
                )
            )
    return read


def _drawn_entries(model: list[dict[str, object]]) -> list[tuple[str, str, str, str]]:
    """The QML menu bar's data, read back the same way."""

    read: list[tuple[str, str, str, str]] = []
    for menu in model:
        title = str(menu["title"])
        for entry in menu["entries"]:  # type: ignore[attr-defined]
            if entry["separator"]:
                read.append((title, "", "", ""))
                continue
            read.append(
                (title, str(entry["text"]), str(entry["shortcut"]), str(entry["command"]))
            )
    return read


def test_the_two_menu_bars_cannot_carry_different_commands(
    application: QApplication,
) -> None:
    """The whole point of this ticket, as a test rather than as a promise.

    Both bars are generated from `menu_bar.MENUS`, so this can only fail if
    somebody builds one of them from something else.
    """

    built = menu_bar.build_menu_bar(RecordingCommands(), close_window=lambda: None)

    assert _widget_entries(built) == _drawn_entries(menu_bar.menu_model())


def test_the_drawn_menu_carries_every_command_and_its_platform_sequence(
    application: QApplication,
) -> None:
    drawn = [
        entry
        for menu in menu_bar.menu_model()
        for entry in menu["entries"]  # type: ignore[attr-defined]
        if not entry["separator"]
    ]

    assert [entry["command"] for entry in drawn] == [
        menu_bar.NEW,
        menu_bar.OPEN,
        menu_bar.SAVE,
        menu_bar.SAVE_AS,
        menu_bar.ADD_SOURCE_VIDEO,
        menu_bar.CLOSE,
    ]
    for entry, defined in zip(drawn, menu_bar.entries_of(), strict=True):
        assert entry["text"] == defined.text
        assert entry["shortcut"] == QKeySequence(defined.shortcut).toString(
            QKeySequence.SequenceFormat.NativeText
        )
        assert entry["shortcut"], f"{defined.text} shows no key sequence"


def test_every_command_in_the_definition_has_something_to_run(
    application: QApplication,
) -> None:
    """Neither bar may carry an entry that does nothing, or one nothing names."""

    runners = menu_bar.command_runners(
        RecordingCommands(), close_window=lambda: None
    )

    assert set(runners) == {entry.command for entry in menu_bar.entries_of()}


def test_the_drawn_menu_declares_no_key_sequence_of_its_own() -> None:
    """The sequences are listened for once per platform, not twice.

    A menu entry that declared its own `Shortcut` would be the second listener
    #47 found and removed, and an ambiguous sequence activates nothing at all.
    """

    source = MENU_BAR_QML.read_text(encoding="utf-8")
    assert "StandardKey" not in source
    # The one sequence the menu does own is Escape, and it holds it only while
    # a menu is open — the window's own Escape stands down for exactly that.
    assert "enabled: root.opened" in source
    assert "enabled: !menuBar.opened" in MAIN_QML.read_text(encoding="utf-8")


def test_python_and_the_window_agree_on_which_platform_has_a_native_menu_bar(
    application: QApplication,
) -> None:
    """Two spellings of one question; a disagreement is two bars or none."""

    view_model = WorkspaceViewModel(AnalysisDocument.new(), FakePlayback())
    engine, component, window = _shell(view_model)

    assert window.property("nativeMenuBar") is menu_bar.native_menu_bar_available()
    assert menu_bar.native_menu_bar_available() is (sys.platform == "darwin")

    _put_away(application, window)
    del engine, component


# --- The view model's half of it -------------------------------------------


class _AnswersEverything:
    """A person who always answers, so an entry reaches the Analysis."""

    def __init__(
        self,
        to_open: str | None = None,
        destination: str | None = None,
        source_video: str | None = "/videos/menu.mp4",
    ) -> None:
        self.to_open = to_open
        self.destination = destination
        self.source_video = source_video

    def ask_unsaved_changes(self) -> UnsavedChangesChoice:
        return UnsavedChangesChoice.DISCARD

    def choose_analysis_to_open(self) -> str | None:
        return self.to_open

    def choose_analysis_destination(self, suggested_name: str) -> str | None:
        return self.destination

    def choose_source_video(self) -> str | None:
        return self.source_video

    def report_failure(self, title: str, message: str) -> None:
        raise AssertionError(f"{title}: {message}")


def _an_analysis(title: str) -> AnalysisDocument:
    """An Analysis with a Source video, because an empty one cannot be saved."""

    document = AnalysisDocument.new(title)
    document.analysis.add_source_video("Halbzeit 1", "/videos/halbzeit-1.mp4")
    return document


def test_the_view_model_offers_the_menu_the_definition_describes(
    application: QApplication,
) -> None:
    view_model = WorkspaceViewModel(AnalysisDocument.new(), FakePlayback())

    assert view_model.menus == menu_bar.menu_model()


def test_running_a_menu_command_does_what_the_widgets_bar_does(
    application: QApplication, tmp_path: Path
) -> None:
    destination = tmp_path / "spiel.analysis"
    view_model = WorkspaceViewModel(
        _an_analysis("Spiel gegen Flensburg"),
        FakePlayback(),
        presenter=_AnswersEverything(destination=str(destination)),
    )

    assert view_model.runMenuCommand(menu_bar.SAVE) is True
    assert destination.is_file()

    assert view_model.runMenuCommand(menu_bar.NEW) is True
    assert view_model.analysisTitle == UNTITLED_ANALYSIS_TITLE


def test_the_close_command_asks_the_window_rather_than_the_document(
    application: QApplication,
) -> None:
    view_model = WorkspaceViewModel(
        _an_analysis("Spiel gegen Kiel"), FakePlayback(), presenter=_AnswersEverything()
    )
    asked: list[str] = []
    view_model.closeRequested.connect(lambda: asked.append("close"))

    assert view_model.runMenuCommand(menu_bar.CLOSE) is True

    assert asked == ["close"]
    assert view_model.analysisTitle == "Spiel gegen Kiel"


def test_a_command_nothing_names_is_refused(application: QApplication) -> None:
    view_model = WorkspaceViewModel(AnalysisDocument.new(), FakePlayback())

    assert view_model.runMenuCommand("burn-the-analysis") is False


# --- The menu as an analyst meets it ---------------------------------------


def _shell(
    view_model: QObject,
) -> tuple[QQmlApplicationEngine, QQmlComponent, QObject]:
    """The real window, over a workspace a test can look at afterwards."""

    engine = build_engine(QML_ROOT, context_objects={"workspace": view_model})
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(MAIN_QML)))
    assert component.status() == QQmlComponent.Status.Ready, [
        error.toString() for error in component.errors()
    ]
    window = component.create()
    assert window is not None, [error.toString() for error in component.errors()]
    return engine, component, window


def _item_named(root: QObject, name: str) -> QQuickItem | None:
    """Find a drawn item by name, delegates included.

    A Repeater's delegate is a visual child of the item it was drawn in but
    not a `QObject` child of it, so `findChild` cannot see one — and every
    menu title and every menu entry is a delegate.
    """

    for item in root.childItems():  # type: ignore[attr-defined]
        if item.objectName() == name:
            return item
        found = _item_named(item, name)
        if found is not None:
            return found
    return None


def _put_away(application: QApplication, window: QObject) -> None:
    """Take a window off the screen and let it go.

    A window left open outlives the test that made it, and the next test's
    clicks are then aimed into a scene with two windows in it.
    """

    window.setProperty("visible", False)
    window.deleteLater()
    application.processEvents()


def _drawn(application: QApplication, window: QObject) -> None:
    """Make the window draw, so an item is where it will be clicked.

    Positioners lay their children out on the way to a frame. A window that
    has never produced one — and offscreen, only the first one does by itself
    — leaves every entry stacked at the origin, and a click aimed at one of
    them lands on whichever entry happens to be underneath.
    """

    window.grabWindow()  # type: ignore[attr-defined]
    application.processEvents()


def _in_window(window: QObject, item: QQuickItem) -> QPoint:
    """The middle of an item, in the window's own coordinates."""

    centre = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    return QPoint(int(centre.x()), int(centre.y()))


def _click(application: QApplication, window: QObject, item: QQuickItem) -> None:
    _drawn(application, window)
    QTest.mouseClick(
        window,  # type: ignore[arg-type]
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        _in_window(window, item),
    )
    application.processEvents()


def _drawing_the_menu(
    application: QApplication, view_model: QObject
) -> tuple[
    QQmlApplicationEngine, QQmlComponent, QObject, QObject
]:
    """The window as Windows and Linux see it, whichever machine this is.

    The platform decision is one property, so a Mac can be asked what a
    Windows analyst would be looking at. What it cannot be asked is how the
    result looks, which is why #51 is a real-hardware gate.
    """

    engine, component, window = _shell(view_model)
    window.setProperty("nativeMenuBar", False)
    application.processEvents()
    bar = window.findChild(QObject, "menuBar")
    assert bar is not None, "the window draws no menu bar"
    return engine, component, window, bar


def test_the_window_draws_a_menu_bar_where_the_platform_has_no_native_one(
    application: QApplication,
) -> None:
    view_model = WorkspaceViewModel(AnalysisDocument.new(), FakePlayback())
    engine, component, window, bar = _drawing_the_menu(application, view_model)
    application.processEvents()

    assert bar.property("visible") is True
    assert bar.property("height") > 0

    toolbar = window.findChild(QObject, "toolbar")
    assert toolbar.property("y") == bar.property("height"), (
        "the toolbar does not sit below the menu bar"
    )

    _put_away(application, window)
    del engine, component


def test_a_platform_with_a_system_menu_bar_draws_none_in_the_window(
    application: QApplication,
) -> None:
    """macOS keeps what it has, and loses no room to a second menu bar."""

    view_model = WorkspaceViewModel(AnalysisDocument.new(), FakePlayback())
    engine, component, window = _shell(view_model)
    window.setProperty("nativeMenuBar", True)
    application.processEvents()

    bar = window.findChild(QObject, "menuBar")
    assert bar.property("visible") is False
    assert bar.property("height") == 0
    assert window.findChild(QObject, "toolbar").property("y") == 0

    _put_away(application, window)
    del engine, component


def _open_the_file_menu(
    application: QApplication, window: QObject, bar: QObject
) -> QObject:
    title = _item_named(bar, f"menuTitle:{menu_bar.FILE_MENU_TITLE}")
    assert title is not None, "the menu bar draws no File menu"
    _click(application, window, title)

    assert bar.property("opened") is True, "clicking the menu opened nothing"
    _drawn(application, window)
    panel = window.findChild(QObject, "openMenu")
    assert panel.property("visible") is True
    return panel


def _texts_of(root: QObject) -> set[str]:
    """Every string this surface actually put on the screen."""

    drawn: set[str] = set()
    for item in root.childItems():  # type: ignore[attr-defined]
        text = item.property("text")
        if isinstance(text, str) and text:
            drawn.add(text)
        drawn |= _texts_of(item)
    return drawn


def test_opening_the_menu_draws_every_entry_with_its_sequence(
    application: QApplication,
) -> None:
    """The entries are drawn, not merely defined.

    A Repeater whose menu nobody opened creates no delegate, so a broken
    binding in one would survive the load test untouched. This opens the menu
    and reads what it put on the screen.
    """

    view_model = WorkspaceViewModel(AnalysisDocument.new(), FakePlayback())
    engine, component, window, bar = _drawing_the_menu(application, view_model)
    # The shell's load test creates no menu delegate, because nobody opened a
    # menu in it; a binding that is wrong in one of them is reported here or
    # nowhere.
    warnings: list[str] = []
    engine.warnings.connect(
        lambda reported: warnings.extend(warning.toString() for warning in reported)
    )
    panel = _open_the_file_menu(application, window, bar)

    drawn = _texts_of(panel)
    for entry in menu_bar.entries_of():
        assert entry.text in drawn, f"{entry.text} was not drawn"
        assert QKeySequence(entry.shortcut).toString(
            QKeySequence.SequenceFormat.NativeText
        ) in drawn, f"{entry.text} was drawn without its key sequence"

    assert panel.property("width") > 0 and panel.property("height") > 0
    assert warnings == [], "the open menu loaded with engine warnings"

    _put_away(application, window)
    del engine, component


def test_choosing_save_from_the_menu_saves_the_analysis(
    application: QApplication, tmp_path: Path
) -> None:
    """One entry, pressed the way an analyst presses it."""

    destination = tmp_path / "spiel.analysis"
    view_model = WorkspaceViewModel(
        _an_analysis("Spiel gegen Flensburg"),
        FakePlayback(),
        presenter=_AnswersEverything(destination=str(destination)),
    )
    engine, component, window, bar = _drawing_the_menu(application, view_model)
    _open_the_file_menu(application, window, bar)

    save = _item_named(bar, f"menuEntry:{menu_bar.SAVE}")
    assert save is not None, "the menu drew no Save entry"
    _click(application, window, save)

    assert destination.is_file(), "choosing Save saved nothing"
    assert bar.property("opened") is False, "the menu stayed open after a choice"

    _put_away(application, window)
    del engine, component


def test_no_entry_in_the_drawn_menu_does_nothing(
    application: QApplication, tmp_path: Path
) -> None:
    """An inert entry is worse than a missing one, and inertness is silent."""

    for entry in menu_bar.entries_of():
        destination = tmp_path / f"{entry.command}.analysis"
        opened = tmp_path / "kiel.analysis"
        _an_analysis("Spiel gegen Kiel").save_as(opened)
        added_video = tmp_path / f"{entry.command}.mp4"
        added_video.write_bytes(f"not real media: {entry.command}".encode())
        view_model = WorkspaceViewModel(
            _an_analysis("Spiel gegen Flensburg"),
            FakePlayback(),
            presenter=_AnswersEverything(
                to_open=str(opened),
                destination=str(destination),
                source_video=str(added_video),
            ),
        )
        ran: list[str] = []
        for signal, name in (
            (view_model.documentChanged, "document"),
            (view_model.closeRequested, "close"),
        ):
            signal.connect(lambda name=name: ran.append(name))

        engine, component, window, bar = _drawing_the_menu(application, view_model)
        _open_the_file_menu(application, window, bar)
        item = _item_named(bar, f"menuEntry:{entry.command}")
        assert item is not None, f"the menu drew no entry for {entry.text}"
        _click(application, window, item)

        assert ran, f"{entry.text} does nothing"

        _put_away(application, window)
        del engine, component


def test_pressing_elsewhere_closes_the_menu(application: QApplication) -> None:
    view_model = WorkspaceViewModel(AnalysisDocument.new(), FakePlayback())
    engine, component, window, bar = _drawing_the_menu(application, view_model)
    _open_the_file_menu(application, window, bar)

    QTest.mouseClick(
        window,  # type: ignore[arg-type]
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(int(window.property("width")) - 40, int(window.property("height")) - 40),
    )
    application.processEvents()

    assert bar.property("opened") is False

    _put_away(application, window)
    del engine, component


def test_escape_closes_the_open_menu_rather_than_the_window_s_own_state(
    application: QApplication,
) -> None:
    """The proof that the two Escapes are never both listening.

    Two enabled `Shortcut` items on one sequence are ambiguous, and an
    ambiguous sequence activates neither of them — so the menu closing here is
    the evidence that exactly one of them was listening.
    """

    view_model = WorkspaceViewModel(
        _an_analysis("Spiel gegen Kiel"), FakePlayback(), presenter=_AnswersEverything()
    )
    engine, component, window, bar = _drawing_the_menu(application, view_model)
    view_model.markBoundary()
    application.processEvents()
    assert view_model.pendingActive is True

    _open_the_file_menu(application, window, bar)
    QTest.keyClick(window, Qt.Key.Key_Escape)  # type: ignore[arg-type]
    application.processEvents()

    assert bar.property("opened") is False, "Escape did not close the menu"
    assert view_model.pendingActive is True, (
        "Escape reached the window's own state while a menu was open"
    )

    # And with the menu closed, the window's own Escape is listening again.
    QTest.keyClick(window, Qt.Key.Key_Escape)  # type: ignore[arg-type]
    application.processEvents()
    assert view_model.pendingActive is False

    _put_away(application, window)
    del engine, component


def test_the_document_sequences_still_reach_the_window_where_it_draws_the_menu(
    application: QApplication, tmp_path: Path
) -> None:
    """The drawn menu adds no second listener, so the sequence still works.

    An ambiguous sequence activates nothing, which is exactly what this would
    catch if a menu entry ever declared one of its own.
    """

    destination = tmp_path / "spiel.analysis"
    view_model = WorkspaceViewModel(
        _an_analysis("Spiel gegen Flensburg"),
        FakePlayback(),
        presenter=_AnswersEverything(destination=str(destination)),
    )
    engine, component, window, bar = _drawing_the_menu(application, view_model)
    application.processEvents()

    combination = QKeySequence(QKeySequence.StandardKey.Save)[0]
    QTest.keyClick(  # type: ignore[arg-type]
        window,
        combination.key(),
        combination.keyboardModifiers(),
    )
    application.processEvents()

    assert destination.is_file(), "the Save sequence reached nothing"

    _put_away(application, window)
    del engine, component
