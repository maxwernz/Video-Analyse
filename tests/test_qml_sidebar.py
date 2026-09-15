"""The sidebar as a real surface: rows that are drawn, and rows that are hit.

`tests/test_workspace_sidebar.py` covers what the lists say. This covers what
only a window can: that a 32px row is a hit target, that clicking one goes to
the Clip, that the segmented control switches the list, and that a delegate
full of real rows evaluates every one of its bindings without an engine
warning — a load test over an empty Analysis instantiates no delegate at all,
so a misspelled role inside one would render nothing and say nothing.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt, QUrl  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from analysis import Analysis, AnalysisDocument  # noqa: E402
from playback import FakePlayback  # noqa: E402
from qml_icons import install_icon_provider  # noqa: E402
from workspace_view_model import WorkspaceViewModel  # noqa: E402


QML_ROOT = Path(__file__).parents[1] / "qml"

FIRST_HALF = "/videos/halbzeit-1.mp4"
SECOND_HALF = "/videos/halbzeit-2.mp4"

#: The sidebar at its default width, and tall enough for every row.
SIDEBAR_WIDTH = 300
SIDEBAR_HEIGHT = 600

#: Where the first rows land: the tabs (16 + 28), their hairline (16 - 4 + 1),
#: then a 30px Category heading and the 32px Clip rows under it.
FIRST_ROW_Y = 16 + 28 + 12 + 1
CATEGORY_ROW_HEIGHT = 30
CLIP_ROW_HEIGHT = 32


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def analysis() -> Analysis:
    analysis = Analysis("SG Beispiel - TV Muster")
    first = analysis.add_source_video(
        "halbzeit-1.mp4", FIRST_HALF, duration_ms=45 * 60_000
    )
    second = analysis.add_source_video(
        "halbzeit-2.mp4", SECOND_HALF, duration_ms=42 * 60_000
    )
    tore = analysis.add_category("Tore", color="#E2564A")
    analysis.add_clip(
        first.id, "Tor von rechts aussen", 843_000, 861_000, category_id=tore.id
    )
    analysis.add_clip(
        second.id, "Tor nach Kreuzbewegung", 120_000, 138_000, category_id=tore.id
    )
    analysis.add_clip(first.id, "Noch unsortiert", 300_000, 312_000)
    return analysis


class Sidebar:
    """The real `Sidebar.qml`, in a window, with a pointer over it."""

    def __init__(self, view: QQuickView, workspace: WorkspaceViewModel) -> None:
        self.view = view
        self.workspace = workspace
        self.warnings: list[str] = []

    def click(self, x: int, y: int) -> None:
        QTest.qWait(QApplication.doubleClickInterval() + 50)
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=QPoint(x, y))
        QApplication.processEvents()

    def click_row(self, index: int, *, kind_heights: list[int]) -> None:
        """Click the row at `index`, given the heights of the ones above it."""

        top = FIRST_ROW_Y + sum(kind_heights[:index])
        self.click(SIDEBAR_WIDTH // 2, top + kind_heights[index] // 2)


@pytest.fixture
def sidebar(application: QApplication, analysis: Analysis):
    workspace = WorkspaceViewModel(AnalysisDocument(analysis), FakePlayback())
    workspace.refresh()

    view = QQuickView()
    view.engine().addImportPath(str(QML_ROOT))
    install_icon_provider(view.engine())
    workspace.setParent(view)  # the context holds no reference of its own
    view.rootContext().setContextProperty("workspace", workspace)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(SIDEBAR_WIDTH, SIDEBAR_HEIGHT)

    surface = Sidebar(view, workspace)
    view.engine().warnings.connect(
        lambda reported: surface.warnings.extend(
            warning.toString() for warning in reported
        )
    )

    view.setSource(QUrl.fromLocalFile(str(QML_ROOT / "Sidebar.qml")))
    assert view.status() == QQuickView.Status.Ready, [
        error.toString() for error in view.errors()
    ]
    view.show()
    QTest.qWaitForWindowExposed(view)

    yield surface

    view.close()
    view.setSource(QUrl())


#: The rows the fixture's Analysis produces, top to bottom.
ROW_HEIGHTS = [
    CATEGORY_ROW_HEIGHT,  # Tore
    CLIP_ROW_HEIGHT,  # Tor von rechts aussen
    CLIP_ROW_HEIGHT,  # Tor nach Kreuzbewegung
    CATEGORY_ROW_HEIGHT,  # Ohne Kategorie
    CLIP_ROW_HEIGHT,  # Noch unsortiert
]


def test_a_list_full_of_real_rows_draws_without_an_engine_warning(
    sidebar: Sidebar,
) -> None:
    """Every binding in both delegates, evaluated against real rows."""

    sidebar.workspace.setSidebarTab("videos")
    QApplication.processEvents()

    assert sidebar.warnings == []


def test_clicking_a_clip_goes_to_it(sidebar: Sidebar) -> None:
    sidebar.click_row(1, kind_heights=ROW_HEIGHTS)

    assert sidebar.workspace.selectedClipId != ""
    assert sidebar.workspace.positionMs == 843_000


def test_clicking_a_clip_of_the_other_half_activates_that_half(
    sidebar: Sidebar,
) -> None:
    sidebar.click_row(2, kind_heights=ROW_HEIGHTS)

    assert [row["active"] for row in sidebar.workspace.sourceModel.rows()] == [
        False,
        True,
    ]


def test_clicking_a_category_heading_selects_nothing(sidebar: Sidebar) -> None:
    """A heading is a label, not a row with something behind it."""

    sidebar.click_row(0, kind_heights=ROW_HEIGHTS)

    assert sidebar.workspace.selectedClipId == ""


def test_the_segmented_control_switches_to_the_videos_and_back(
    sidebar: Sidebar,
) -> None:
    tab_centre_y = 16 + 28 // 2
    videos_x = 16 + (SIDEBAR_WIDTH - 32) * 3 // 4
    clips_x = 16 + (SIDEBAR_WIDTH - 32) // 4

    sidebar.click(videos_x, tab_centre_y)
    assert sidebar.workspace.sidebarTab == "videos"

    sidebar.click(clips_x, tab_centre_y)
    assert sidebar.workspace.sidebarTab == "clips"


def test_choosing_a_source_video_in_the_videos_tab_activates_it(
    sidebar: Sidebar,
) -> None:
    sidebar.workspace.setSidebarTab("videos")
    QApplication.processEvents()

    sidebar.click(SIDEBAR_WIDTH // 2, FIRST_ROW_Y + 52 + 26)

    assert [row["active"] for row in sidebar.workspace.sourceModel.rows()] == [
        False,
        True,
    ]


def test_moving_through_the_videos_by_keyboard_activates_the_next_one(
    sidebar: Sidebar,
) -> None:
    """The replacement for the Widgets Videos-list keyboard contract."""

    sidebar.workspace.setSidebarTab("videos")
    QApplication.processEvents()

    QTest.keyClick(sidebar.view, Qt.Key.Key_Down)
    QApplication.processEvents()

    assert [row["active"] for row in sidebar.workspace.sourceModel.rows()] == [
        False,
        True,
    ]


def test_the_clip_list_has_no_column_header(sidebar: Sidebar) -> None:
    """The header strip is what truncated the Source-video column before.

    The first thing under the tabs is a Category heading — the list itself —
    rather than a strip of column names above it.
    """

    assert sidebar.workspace.clipModel.rows()[0]["kind"] == "category"
