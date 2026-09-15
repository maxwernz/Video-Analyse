"""The Clip editor as a form, driven by a real pointer and a real keyboard.

Everything the editor decides is tested headless in
`tests/test_workspace_clip_editor.py`. What cannot be tested there is what the
window owns: whether the form's bindings resolve against a draft that actually
exists, whether the Category chips — a delegate, and therefore the one thing an
empty-Analysis load test never instantiates — bind to roles that are really
there, and whether the buttons in the action row are wired to the slots they
claim to call. An unwired button is silent: it loads without complaint and does
nothing, which is exactly the failure this file exists to catch.

So this loads the real component over a real Analysis, in the editing state,
with engine warnings treated as failures for the whole interaction rather than
only for the load.
"""

from __future__ import annotations

import os
from pathlib import Path
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtQuick import QQuickItem, QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import timecode  # noqa: E402
from analysis import Analysis, AnalysisDocument, Clip  # noqa: E402
from playback import FakePlayback  # noqa: E402
from qml_icons import install_icon_provider  # noqa: E402
from workspace_view_model import WorkspaceViewModel  # noqa: E402


QML_ROOT = Path(__file__).parents[1] / "qml"

#: The editor's own width, and a window tall enough to hold the whole form.
EDITOR_WIDTH = 360
EDITOR_HEIGHT = 700

HALF_MS = 45 * 60_000

#: Long enough for a press to stop looking like the start of a drag.
SETTLE_MS = 60


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


class Scheduler:
    """The event loop, stood in for, so priming is not a wait.

    Priming ignores every position the player reports until it is over, so a
    form built while it is still in flight would mark its Clip at zero — a
    race rather than a behaviour, and one a test should not be holding its
    breath through.
    """

    def __init__(self) -> None:
        self.pending: list[tuple[int, object]] = []

    def __call__(self, delay_ms: int, run) -> None:  # type: ignore[no-untyped-def]
        self.pending.append((delay_ms, run))

    def elapse(self) -> None:
        due, self.pending = self.pending, []
        for _, run in due:
            run()  # type: ignore[operator]


@pytest.fixture
def analysis() -> Analysis:
    analysis = Analysis("SG Beispiel - TV Muster")
    analysis.add_source_video(
        "halbzeit-1.mp4", "/videos/halbzeit-1.mp4", duration_ms=HALF_MS
    )
    analysis.add_category("Tore", color="#E2564A")
    analysis.add_category("Abwehr", color="#4BA46A")
    return analysis


@pytest.fixture
def clip(analysis: Analysis) -> Clip:
    return analysis.add_clip(
        analysis.source_videos[0].id,
        "Gegenstoss",
        600_000,
        612_000,
        notes="Zweite Welle",
        category_id=analysis.categories[0].id,
    )


class Form:
    """The real `ClipEditor.qml`, in a window, with a pointer over it."""

    def __init__(
        self,
        view: QQuickView,
        workspace: WorkspaceViewModel,
        warnings: list[str],
    ) -> None:
        self.view = view
        self.workspace = workspace
        self.warnings = warnings
        self._clicked_at = 0.0

    def find(self, object_name: str) -> QQuickItem:
        found = self.every(object_name)
        assert found, f"the form has no {object_name}"
        return found[0]

    def every(self, object_name: str, inside: QQuickItem | None = None) -> list[QQuickItem]:
        """Every item of that name in the drawn form.

        The visual tree rather than `findChildren`: a `Repeater`'s delegates —
        the Category chips — are drawn inside the form but are not QObject
        children of its root, so the object-tree search walks straight past
        the very delegates this file exists to exercise.
        """

        found: list[QQuickItem] = []

        def walk(item: QQuickItem) -> None:
            for child in item.childItems():
                if child.objectName() == object_name:
                    found.append(child)
                walk(child)

        walk(self.view.rootObject() if inside is None else inside)
        return found

    def click(self, item: QQuickItem) -> None:
        """Press and release on an item, where it actually is on screen.

        Press and release rather than one click, because the form scrolls: a
        `Flickable` holds a press until it knows the pointer is not dragging,
        and a click delivered as one event never reaches the control inside.

        Two presses close together in time are a double-click as far as the
        window is concerned, and a `MouseArea` does not report the second of
        those as a click at all, so consecutive presses are spaced out.
        """

        since_ms = (time.monotonic() - self._clicked_at) * 1_000
        apart_ms = QApplication.doubleClickInterval() + SETTLE_MS
        if since_ms < apart_ms:
            QTest.qWait(round(apart_ms - since_ms))

        centre = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
        at = QPoint(round(centre.x()), round(centre.y()))
        QTest.mousePress(self.view, Qt.MouseButton.LeftButton, pos=at)
        QTest.qWait(SETTLE_MS)
        QTest.mouseRelease(self.view, Qt.MouseButton.LeftButton, pos=at)
        self._clicked_at = time.monotonic()
        QApplication.processEvents()

    def type_into(self, object_name: str, text: str) -> None:
        """Type a value the way an analyst does: focus, type, press Return."""

        self.click(self.find(object_name))
        QTest.keyClick(self.view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        for character in text:
            QTest.keyClick(self.view, character)
        QTest.keyClick(self.view, Qt.Key.Key_Return)
        QApplication.processEvents()

    def settle(self) -> None:
        """Let the scene lay itself out before anything is aimed at it.

        Positioners size themselves on the next frame, not on the change that
        caused them, so a chip clicked before that lands where the chip used
        to be — which reads exactly like a control that was never wired up.
        """

        QApplication.processEvents()
        QTest.qWait(SETTLE_MS)
        QApplication.processEvents()

    def text_of(self, object_name: str) -> str:
        return str(self.find(object_name).property("text"))

    def every_of_class(self, inside: QQuickItem, class_name: str) -> list[QQuickItem]:
        """Every item of one QML type drawn inside another."""

        found: list[QQuickItem] = []

        def walk(item: QQuickItem) -> None:
            for child in item.childItems():
                if child.metaObject().className().startswith(class_name):
                    found.append(child)
                walk(child)

        walk(inside)
        return found


@pytest.fixture
def form(application: QApplication, analysis: Analysis):
    """The editor, already editing, because that is the only state it has."""

    player = FakePlayback()
    scheduler = Scheduler()
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), player, schedule=scheduler
    )
    scheduler.elapse()
    # The media announcing its length, without which the player refuses every
    # position past zero and there is nothing to mark a Clip in.
    player.set_duration(HALF_MS)
    workspace.refresh()

    view = QQuickView()
    warnings: list[str] = []
    view.engine().warnings.connect(
        lambda reported: warnings.extend(warning.toString() for warning in reported)
    )
    view.engine().addImportPath(str(QML_ROOT))
    install_icon_provider(view.engine())
    workspace.setParent(view)  # the context holds no reference of its own
    view.rootContext().setContextProperty("workspace", workspace)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(EDITOR_WIDTH, EDITOR_HEIGHT)
    view.setSource(QUrl.fromLocalFile(str(QML_ROOT / "ClipEditor.qml")))
    assert view.status() == QQuickView.Status.Ready, [
        error.toString() for error in view.errors()
    ]
    view.show()
    QTest.qWaitForWindowExposed(view)

    yield Form(view, workspace, warnings)

    # Taken down rather than only hidden: a window left alive still takes the
    # pointer events the next test sends, and the failure that produces looks
    # like a control that is not wired up.
    view.close()
    view.setSource(QUrl())
    view.deleteLater()
    QApplication.processEvents()


def in_the_editing_state(form: Form) -> None:
    """Mark a Clip, which is how an analyst arrives at this form."""

    form.workspace.seek(600_000)
    form.workspace.markBoundary()
    form.workspace.seek(612_000)
    form.workspace.markBoundary()
    form.settle()


def test_the_form_draws_a_real_draft_without_an_engine_warning(form: Form) -> None:
    """The delegates an empty Analysis never instantiates, instantiated.

    An empty-Analysis load test creates no Category chip at all, so a chip
    bound to a role that does not exist would survive it. This one has real
    Categories in it.
    """

    in_the_editing_state(form)

    assert len(form.every("categoryChip")) == 2
    assert form.warnings == []


def test_the_boundaries_are_shown_whole_in_monospace(form: Form) -> None:
    in_the_editing_state(form)

    start = form.find("startField")
    assert start.property("value") == timecode.precise(600_000)

    # Wide enough for the whole timecode: the rejected interface clipped this
    # field to `:00.000`, and the fix is a field sized for what it holds. The
    # text is measured rather than the box, because what matters is that the
    # value fits in the room it was given, in the face it is set in.
    written = [
        item
        for item in form.every_of_class(start, "QQuickTextInput")
        if item.property("text") == timecode.precise(600_000)
    ]
    assert written, "the start field shows no timecode at all"
    assert written[0].property("contentWidth") <= written[0].width()
    assert "Mono" in str(written[0].property("font").family())


def test_the_duration_is_shown_and_follows_the_boundaries(form: Form) -> None:
    in_the_editing_state(form)
    assert form.text_of("durationReadout") == timecode.precise_duration(12_000)

    form.workspace.setDraftEndText("00:10:18.400")
    form.settle()

    assert form.text_of("durationReadout") == timecode.precise_duration(18_400)


def test_the_notes_field_says_what_it_is_for_while_it_is_empty(form: Form) -> None:
    in_the_editing_state(form)
    notes = form.find("notesField")

    assert notes.property("text") == ""
    placeholder = [
        child
        for child in notes.childItems()
        if child.property("text") not in (None, "")
    ]
    assert placeholder, "an empty notes box is a mystery"


def test_typing_a_title_reaches_the_draft(form: Form) -> None:
    in_the_editing_state(form)

    form.type_into("titleField", "Gegenstoss")

    assert form.workspace.draftName == "Gegenstoss"
    assert form.warnings == []


def test_pressing_a_category_chip_files_the_clip_under_it(form: Form) -> None:
    in_the_editing_state(form)

    form.click(form.every("categoryChip")[1])

    assert [row["selected"] for row in form.workspace.categoryModel.rows()] == [
        False,
        True,
    ]


def test_the_stepper_nudges_the_boundary_it_belongs_to(form: Form) -> None:
    in_the_editing_state(form)
    before = form.workspace.draftEndMs

    end_field = form.find("endField")
    # The upper half of the pair, which is the one that adds.
    up = [
        item
        for item in form.every_of_class(end_field, "Stepper")
        if item.property("up") is True
    ]
    assert up, "the boundary field has no steppers"
    form.click(up[0])

    assert form.workspace.draftEndMs > before
    assert end_field.property("value") == timecode.precise(
        form.workspace.draftEndMs
    )


def test_the_primary_writes_the_clip_to_the_analysis(
    form: Form, analysis: Analysis
) -> None:
    """The button the whole form exists for, pressed rather than simulated."""

    in_the_editing_state(form)
    form.type_into("titleField", "Gegenstoss")

    form.click(form.find("saveButton"))

    assert [clip.name for clip in analysis.clips] == ["Gegenstoss"]
    assert form.workspace.editing is False
    assert form.warnings == []


def test_the_secondary_leaves_the_analysis_alone(
    form: Form, analysis: Analysis
) -> None:
    in_the_editing_state(form)
    form.type_into("titleField", "Gegenstoss")

    form.click(form.find("cancelButton"))

    assert analysis.clips == ()
    assert form.workspace.editing is False


def test_the_refused_boundary_is_explained_in_the_action_row(form: Form) -> None:
    in_the_editing_state(form)
    assert form.find("draftError").property("visible") is False

    form.workspace.setDraftEndText("00:09:00.000")
    form.settle()

    assert form.find("draftError").property("visible") is True
    assert form.text_of("draftError") != ""
    assert form.find("saveButton").property("enabled") is False


def test_the_same_form_says_which_of_its_two_jobs_it_is_doing(
    form: Form, clip: Clip
) -> None:
    """One editor, two states of the same Analysis, two words of difference."""

    in_the_editing_state(form)
    marked = form.find("saveButton").property("label")
    form.click(form.find("cancelButton"))

    form.workspace.refresh()
    form.workspace.editClip(str(clip.id))
    form.settle()

    assert form.find("saveButton").property("label") != marked
    assert form.find("titleField").property("text") == "Gegenstoss"
    assert form.text_of("durationReadout") == timecode.precise_duration(12_000)
