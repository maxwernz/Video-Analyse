"""The Category manager's destructive control as a rendered QML surface."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMetaObject, QObject, QUrl  # noqa: E402
from PySide6.QtQuick import QQuickItem, QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from analysis import Analysis, AnalysisDocument  # noqa: E402
from playback import FakePlayback  # noqa: E402
from qml_icons import install_icon_provider  # noqa: E402
from workspace_view_model import WorkspaceViewModel  # noqa: E402


QML_ROOT = Path(__file__).parents[1] / "qml"


class _InertRecoveryScheduler:
    """A Recovery scheduler that never arms a real `QTimer`.

    Every QML test builds a `WorkspaceViewModel` and tears its window down
    well before a real debounce (`RECOVERY_DEBOUNCE_MS`) would fire — but the
    Qt event loop is shared for the whole test session, so a real
    `_TimerRecoveryScheduler`'s `QTimer` left ticking past that teardown is
    still live enough to fire into whatever the view and view model happen
    to have become by the time it does. Injecting this instead removes the
    only real Qt timer this test would otherwise leave behind.
    """

    def schedule(self, run: object) -> None:
        return None

    def cancel(self) -> None:
        return None


def _visual_child(item: QQuickItem, name: str) -> QQuickItem | None:
    """Delegates are visual children, not QObject children, in a ListView."""

    for child in item.childItems():
        if child.objectName() == name:
            return child
        found = _visual_child(child, name)
        if found is not None:
            return found
    return None


def test_category_removal_is_armed_in_the_row_and_states_its_clip_effect() -> None:
    application = QApplication.instance() or QApplication([])
    analysis = Analysis("Match")
    source = analysis.add_source_video("half.mp4", "/videos/half.mp4")
    category = analysis.add_category("Angriff", "#EF4444")
    clip = analysis.add_clip(
        source.id, "Fast break", 1_000, 2_000, category_id=category.id
    )
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis),
        FakePlayback(),
        recovery_scheduler=_InertRecoveryScheduler(),
    )
    workspace.showCategoryManagement()
    assert len(workspace.managedCategoryModel.rows()) == 1

    view = QQuickView()
    view.engine().addImportPath(str(QML_ROOT))
    install_icon_provider(view.engine())
    workspace.setParent(view)
    view.rootContext().setContextProperty("workspace", workspace)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(300, 600)
    view.setSource(QUrl.fromLocalFile(str(QML_ROOT / "CategoryManager.qml")))
    assert view.status() == QQuickView.Status.Ready, [
        error.toString() for error in view.errors()
    ]
    view.show()
    QTest.qWaitForWindowExposed(view)

    listed = view.rootObject().findChild(QObject, "managedCategoryList")
    assert listed is not None
    assert listed.property("count") == 1
    root = view.rootObject()
    assert isinstance(root, QQuickItem)
    remove = _visual_child(root, "managedCategoryRemove")
    assert remove is not None
    assert QMetaObject.invokeMethod(remove, "clicked")
    application.processEvents()

    warning = _visual_child(root, "categoryRemovalWarning")
    assert warning is not None
    assert "1 Clip bleibt ohne Kategorie." in warning.property("text")
    assert analysis.clip(clip.id).category_id == category.id
    row = _visual_child(root, "managedCategoryRow")
    assert row is not None and row.property("removeArmed") is True

    confirmed_remove = _visual_child(root, "managedCategoryRemove")
    assert confirmed_remove is not None
    assert QMetaObject.invokeMethod(confirmed_remove, "clicked")
    application.processEvents()

    assert analysis.clip(clip.id).category_id is None

    # Taken down rather than only closed and left to Python's garbage
    # collector: a window's C++ object left to a deferred, GC-timed
    # collection can stay alive — with everything parented to it, including
    # any real Qt timer — for an indeterminate stretch of later tests.
    view.close()
    view.setSource(QUrl())
    view.deleteLater()
    application.processEvents()
