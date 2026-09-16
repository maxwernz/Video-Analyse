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
    workspace = WorkspaceViewModel(AnalysisDocument(analysis), FakePlayback())
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
    view.close()
