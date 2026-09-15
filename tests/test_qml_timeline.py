"""The interaction grammar of the one seek surface, driven by a real pointer.

Everything the timeline computes is tested headless through the view model.
What cannot be tested there is the part the scene graph owns: whether a Clip
drawn at its three-pixel minimum is a *hit target* rather than only a drawing,
and whether pressing, dragging and double-clicking the surface mean what
ADR 0006 says they mean. So these tests load the real component into a window
and send it real mouse events.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from analysis import Analysis, AnalysisDocument, Clip  # noqa: E402
from playback import FakePlayback  # noqa: E402
from workspace_view_model import WorkspaceViewModel  # noqa: E402


QML_ROOT = Path(__file__).parents[1] / "qml"

#: A ninety-minute half, the length ADR 0006 records its limitation against.
MATCH_MS = 90 * 60_000

#: The width the track gets in a designed window, near enough.
TRACK_WIDTH = 1_200

#: Roughly four and a half seconds per pixel, so this Clip is under two pixels
#: wide and is drawn at the three-pixel minimum.
SHORT_CLIP_START_MS = 100_000
SHORT_CLIP_END_MS = 106_800

TRACK_Y = 40


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


def x_of(position_ms: int) -> int:
    return round(position_ms / MATCH_MS * TRACK_WIDTH)


def ms_at(x: int) -> int:
    return round(x / TRACK_WIDTH * MATCH_MS)


class Surface:
    """The real `Timeline.qml`, in a window, with a pointer over it."""

    def __init__(self, view: QQuickView, workspace: WorkspaceViewModel) -> None:
        self.view = view
        self.workspace = workspace

    def click(self, x: int) -> None:
        # Long enough that two clicks in a row are two clicks rather than one
        # double-click, which the window would deliver as a different event.
        QTest.qWait(QApplication.doubleClickInterval() + 50)
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=QPoint(x, TRACK_Y))

    def double_click(self, x: int) -> None:
        QTest.qWait(QApplication.doubleClickInterval() + 50)
        QTest.mouseDClick(self.view, Qt.MouseButton.LeftButton, pos=QPoint(x, TRACK_Y))

    def drag(self, from_x: int, to_x: int) -> None:
        QTest.mousePress(self.view, Qt.MouseButton.LeftButton, pos=QPoint(from_x, TRACK_Y))
        steps = 8
        for step in range(1, steps + 1):
            moved = from_x + round((to_x - from_x) * step / steps)
            QTest.mouseMove(self.view, QPoint(moved, TRACK_Y))
        QTest.mouseRelease(self.view, Qt.MouseButton.LeftButton, pos=QPoint(to_x, TRACK_Y))


@pytest.fixture
def analysis() -> Analysis:
    analysis = Analysis("Spiel gegen Kiel")
    analysis.add_source_video(
        "Halbzeit 1", "/videos/halbzeit-1.mp4", duration_ms=MATCH_MS
    )
    return analysis


@pytest.fixture
def short_clip(analysis: Analysis) -> Clip:
    """A seven-second counter-attack in a ninety-minute half."""

    return analysis.add_clip(
        analysis.source_videos[0].id,
        "Gegenstoss",
        SHORT_CLIP_START_MS,
        SHORT_CLIP_END_MS,
    )


@pytest.fixture
def surface(application: QApplication, analysis: Analysis, short_clip: Clip):
    workspace = WorkspaceViewModel(AnalysisDocument(analysis), FakePlayback())
    workspace.refresh()

    view = QQuickView()
    view.engine().addImportPath(str(QML_ROOT))
    workspace.setParent(view)  # the context holds no reference of its own
    view.rootContext().setContextProperty("workspace", workspace)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setSource(QUrl.fromLocalFile(str(QML_ROOT / "Timeline.qml")))
    assert view.status() == QQuickView.Status.Ready, [
        error.toString() for error in view.errors()
    ]
    view.resize(TRACK_WIDTH, 60)
    view.show()
    QTest.qWaitForWindowExposed(view, 2_000)
    QGuiApplication.processEvents()

    yield Surface(view, workspace)

    view.close()


# --- The grammar (ADR 0006) --------------------------------------------------


def test_clicking_the_track_scrubs_the_playhead_to_that_time(
    surface: Surface,
) -> None:
    surface.click(x_of(30 * 60_000))

    assert surface.workspace.positionMs == pytest.approx(30 * 60_000, abs=10_000)


def test_dragging_across_the_track_scrubs_with_the_pointer(
    surface: Surface,
) -> None:
    surface.drag(x_of(10 * 60_000), x_of(70 * 60_000))

    assert surface.workspace.positionMs == pytest.approx(70 * 60_000, abs=10_000)


def test_a_clip_narrower_than_the_minimum_is_still_selectable_with_one_click(
    surface: Surface, short_clip: Clip
) -> None:
    """The three-pixel minimum is a hit target, not only a drawing.

    Four and a half seconds to the pixel, this Clip is under two pixels of
    real width. It is drawn three wide, and the scene graph hit-tests what is
    drawn — which is the whole reason ranges are Items rather than painting.
    """

    surface.click(x_of(SHORT_CLIP_START_MS) + 1)

    assert surface.workspace.selectedClipId == str(short_clip.id)


def test_clicking_a_range_does_not_move_the_playhead_to_the_clips_start(
    surface: Surface,
) -> None:
    """Selection and seeking are separate acts on the same click."""

    x = x_of(SHORT_CLIP_START_MS) + 1
    surface.click(x)

    assert surface.workspace.positionMs == pytest.approx(ms_at(x), abs=5_000)
    assert surface.workspace.positionMs != SHORT_CLIP_START_MS


def test_dragging_over_a_range_scrubs_rather_than_selecting_nothing(
    surface: Surface,
) -> None:
    """A range is not a hole in the seek surface."""

    surface.drag(x_of(SHORT_CLIP_START_MS) - 20, x_of(SHORT_CLIP_START_MS) + 20)

    assert surface.workspace.positionMs == pytest.approx(
        ms_at(x_of(SHORT_CLIP_START_MS) + 20), abs=5_000
    )


def test_double_clicking_a_range_seeks_to_the_clip_start(
    surface: Surface, short_clip: Clip
) -> None:
    surface.double_click(x_of(SHORT_CLIP_START_MS) + 1)

    assert surface.workspace.positionMs == short_clip.start_ms


def test_double_clicking_empty_track_seeks_no_further_than_the_pointer(
    surface: Surface,
) -> None:
    x = x_of(45 * 60_000)
    surface.double_click(x)

    assert surface.workspace.positionMs == pytest.approx(ms_at(x), abs=10_000)


def test_a_scrub_elsewhere_leaves_the_selected_clip_selected(
    surface: Surface, short_clip: Clip
) -> None:
    """Scrubbing is navigation; it is not a change of what is being worked on."""

    surface.click(x_of(SHORT_CLIP_START_MS) + 1)

    surface.click(x_of(45 * 60_000))

    assert surface.workspace.selectedClipId == str(short_clip.id)
