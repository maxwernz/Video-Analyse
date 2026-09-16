from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from analysis import Analysis, AnalysisDocument, CategoryTemplateStore
from playback import FakePlayback
from workspace_view_model import WorkspaceViewModel


def test_category_management_keeps_analysis_and_template_edits_separate(tmp_path) -> None:
    analysis = Analysis("Match")
    attack = analysis.add_category("Angriff", "#EF4444")
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), FakePlayback(), template_store=store
    )

    workspace.showCategoryManagement()
    workspace.addManagedCategory()
    workspace.setManagedCategoryName(str(attack.id), "Angriff Mitte")

    assert [category.name for category in analysis.categories] == [
        "Angriff Mitte",
        "Neue Kategorie",
    ]

    workspace.setCategoryManagementScope("template")
    workspace.addManagedCategory()
    workspace.restoreCategoryTemplate()

    assert [category.name for category in analysis.categories] == [
        "Angriff Mitte",
        "Neue Kategorie",
    ]
    assert [row["name"] for row in workspace.managedCategoryModel.rows()] == [
        "Abwehr",
        "Angriff",
        "Tor",
    ]
