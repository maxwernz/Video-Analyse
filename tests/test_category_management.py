from __future__ import annotations

import os
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from analysis import Analysis, AnalysisDocument, CategoryTemplateStore, UnknownEntityError
from analysis.category_palette import CATEGORY_PALETTE
from category_management import AnalysisCategories, TemplateCategories
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


def test_managed_categories_can_be_recoloured_in_either_scope(tmp_path) -> None:
    analysis = Analysis("Match")
    attack = analysis.add_category("Angriff", "#EF4444")
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), FakePlayback(), template_store=store
    )
    workspace.showCategoryManagement()

    workspace.setManagedCategoryColor(str(attack.id), CATEGORY_PALETTE[3])
    assert analysis.category(attack.id).color == CATEGORY_PALETTE[3]

    workspace.cycleManagedCategoryColor(str(attack.id))
    assert analysis.category(attack.id).color == CATEGORY_PALETTE[4]

    workspace.setCategoryManagementScope("template")
    template_row = workspace.managedCategoryModel.rows()[0]
    workspace.setManagedCategoryColor(str(template_row["categoryId"]), CATEGORY_PALETTE[7])

    assert store.categories()[0].color == CATEGORY_PALETTE[7]
    # The Analysis's own Category is untouched by a template recolour.
    assert analysis.category(attack.id).color == CATEGORY_PALETTE[4]


def test_managed_categories_can_be_reordered_in_either_scope(tmp_path) -> None:
    analysis = Analysis("Match")
    defence = analysis.add_category("Abwehr", "#3B82F6")
    attack = analysis.add_category("Angriff", "#EF4444")
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), FakePlayback(), template_store=store
    )
    workspace.showCategoryManagement()

    workspace.moveManagedCategoryLater(str(defence.id))

    assert [category.id for category in analysis.categories] == [attack.id, defence.id]

    workspace.setCategoryManagementScope("template")
    before = [category.name for category in store.categories()]
    workspace.moveManagedCategoryEarlier(
        str(next(row for row in workspace.managedCategoryModel.rows() if row["name"] == "Tor")[
            "categoryId"
        ])
    )
    after = [category.name for category in store.categories()]

    assert after != before
    # The Analysis's own order is untouched by a template reorder.
    assert [category.id for category in analysis.categories] == [attack.id, defence.id]


def test_updating_a_managed_category_s_name_and_colour_together_applies_both(
    tmp_path,
) -> None:
    analysis = Analysis("Match")
    attack = analysis.add_category("Angriff", "#EF4444")
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), FakePlayback(), template_store=store
    )
    workspace.showCategoryManagement()

    updated = AnalysisCategories(analysis).update_category(
        attack.id, name="Angriff links", color=CATEGORY_PALETTE[5]
    )

    assert updated.name == "Angriff links"
    assert updated.color == CATEGORY_PALETTE[5]
    assert analysis.category(attack.id).name == "Angriff links"
    assert analysis.category(attack.id).color == CATEGORY_PALETTE[5]


def test_a_duplicate_managed_category_name_is_refused_and_reported(tmp_path) -> None:
    """The refusal analysts correct is surfaced, not raised through QML."""

    analysis = Analysis("Match")
    attack = analysis.add_category("Angriff", "#EF4444")
    analysis.add_category("Abwehr", "#3B82F6")
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), FakePlayback(), template_store=store
    )
    workspace.showCategoryManagement()

    workspace.setManagedCategoryName(str(attack.id), "  abwehr ")

    assert workspace.categoryError != ""
    assert analysis.category(attack.id).name == "Angriff"

    # A later successful edit clears the earlier refusal.
    workspace.setManagedCategoryName(str(attack.id), "Angriff Mitte")

    assert workspace.categoryError == ""
    assert analysis.category(attack.id).name == "Angriff Mitte"


def test_a_stale_category_id_is_reported_rather_than_raised_from_every_managed_slot(
    tmp_path,
) -> None:
    """Every mutating managed-Category slot must fail the way the UI expects.

    A QML delegate's `categoryId` can go stale (another edit removed the row
    just before this click is dispatched); every slot that can hit
    `Analysis.category()`'s `UnknownEntityError` must catch it into
    `categoryError`, the same as `addManagedCategory` and
    `setManagedCategoryName` already did, rather than let it escape a Qt
    slot unhandled.
    """

    analysis = Analysis("Match")
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), FakePlayback(), template_store=store
    )
    workspace.showCategoryManagement()
    stale_id = str(uuid4())

    workspace.setManagedCategoryColor(stale_id, CATEGORY_PALETTE[0])
    assert workspace.categoryError != ""

    workspace.removeManagedCategory(stale_id)
    assert workspace.categoryError != ""


def test_an_unknown_template_category_id_raises_an_analysis_error(tmp_path) -> None:
    """The template scope must fail the same way the Analysis scope does.

    `AnalysisCategories` already raises through `Analysis.category`, which is
    an `AnalysisError`; a caller's `except AnalysisError` (as
    `workspace_view_model.py` uses) must not be bypassed by a bare
    `StopIteration` from the template scope's collection.
    """

    store = CategoryTemplateStore(tmp_path / "category-template.json")

    with pytest.raises(UnknownEntityError):
        TemplateCategories(store).update_category(uuid4())


def test_managing_template_categories_leaves_the_open_clip_editor_untouched(
    tmp_path,
) -> None:
    """A template-scope edit must not disturb an Analysis-scope Clip draft.

    The Category manager's two scopes are unrelated collections; a
    template-only edit changing the Clip editor's own Category selection
    was the earlier bug this guards against.
    """

    analysis = Analysis("Match")
    analysis.add_source_video("half.mp4", "/videos/half.mp4", duration_ms=3_000)
    attack = analysis.add_category("Angriff", "#EF4444")
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    player = FakePlayback()
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), player, template_store=store
    )
    player.set_duration(3_000)
    workspace.seek(0)
    workspace.markBoundary()
    workspace.seek(1_000)
    workspace.markBoundary()
    workspace.setDraftCategory(str(attack.id))
    assert workspace.draftCategoryColor == attack.color

    workspace.showCategoryManagement()
    workspace.setCategoryManagementScope("template")
    workspace.addManagedCategory()

    assert workspace.draftCategoryColor == attack.color


def test_removing_a_managed_template_category_never_touches_an_open_analysis(
    tmp_path,
) -> None:
    analysis = Analysis("Match")
    attack = analysis.add_category("Angriff", "#EF4444")
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    workspace = WorkspaceViewModel(
        AnalysisDocument(analysis), FakePlayback(), template_store=store
    )
    workspace.showCategoryManagement()
    workspace.setCategoryManagementScope("template")

    goal_row = next(
        row for row in workspace.managedCategoryModel.rows() if row["name"] == "Tor"
    )
    workspace.removeManagedCategory(str(goal_row["categoryId"]))

    assert [category.name for category in store.categories()] == ["Abwehr", "Angriff"]
    assert [category.name for category in analysis.categories] == ["Angriff"]
    assert analysis.category(attack.id).name == "Angriff"
