from __future__ import annotations

from analysis import CategoryTemplateStore, DEFAULT_CATEGORY_TEMPLATE, new_analysis_document
from application_workflow import ApplicationWorkflow


def test_missing_or_invalid_template_falls_back_to_the_handball_categories(
    tmp_path,
) -> None:
    template_path = tmp_path / "category-template.json"
    store = CategoryTemplateStore(template_path)

    assert [(category.name, category.color) for category in store.categories()] == list(
        DEFAULT_CATEGORY_TEMPLATE
    )

    template_path.write_text("not JSON", encoding="utf-8")

    assert [(category.name, category.color) for category in store.categories()] == list(
        DEFAULT_CATEGORY_TEMPLATE
    )


def test_template_customization_does_not_reach_existing_analyses(
    tmp_path,
) -> None:
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    counter = store.add_category("Konter", "#F59E0B")
    store.update_category(counter.id, name="Schneller Konter", color="#DE8241")
    store.reorder_categories([counter.id, *[category.id for category in store.categories() if category.id != counter.id]])

    first = new_analysis_document(template_store=store).analysis
    first_categories = tuple(first.categories)

    # The template changes again after the first Analysis was made from it.
    store.remove_category(counter.id)
    second = new_analysis_document(template_store=store).analysis

    assert [category.name for category in first.categories] == [
        "Schneller Konter",
        "Abwehr",
        "Angriff",
        "Tor",
    ]
    assert tuple(first.categories) == first_categories
    assert [category.name for category in second.categories] == [
        "Abwehr",
        "Angriff",
        "Tor",
    ]
    assert {category.id for category in first.categories}.isdisjoint(
        category.id for category in second.categories
    )


def test_two_new_analyses_never_share_category_identities(tmp_path) -> None:
    """Fresh Category UUIDs per Analysis, even from the same, unstored default.

    A shared UUID between two Analyses would let saving or editing one leak
    a Category identity into the other; only independent deep copies rule
    that out.
    """

    first = new_analysis_document("First").analysis
    second = new_analysis_document("Second").analysis

    assert {category.id for category in first.categories}.isdisjoint(
        category.id for category in second.categories
    )
    assert [category.name for category in first.categories] == [
        category.name for category in second.categories
    ]


def test_editing_an_analysis_category_never_mutates_the_template_store(tmp_path) -> None:
    """The copy handed to an Analysis must be independent, not a shared reference."""

    store = CategoryTemplateStore(tmp_path / "category-template.json")
    original_template_categories = store.categories()

    analysis = new_analysis_document("Match", template_store=store).analysis
    defence = next(category for category in analysis.categories if category.name == "Abwehr")
    analysis.update_category(defence.id, name="Abwehr rechts", color="#000000")
    analysis.remove_category(
        next(category for category in analysis.categories if category.name == "Tor").id
    )

    assert store.categories() == original_template_categories
    assert [category.name for category in store.categories()] == ["Abwehr", "Angriff", "Tor"]


def test_a_template_can_be_emptied_without_becoming_corrupt(tmp_path) -> None:
    store = CategoryTemplateStore(tmp_path / "category-template.json")

    for category in store.categories():
        store.remove_category(category.id)

    assert store.categories() == ()
    assert new_analysis_document(template_store=store).analysis.categories == ()


def test_an_unreadable_template_uses_the_handball_fallback(tmp_path) -> None:
    template_directory = tmp_path / "category-template.json"
    template_directory.mkdir()

    store = CategoryTemplateStore(template_directory)

    assert [category.name for category in store.categories()] == [
        "Abwehr",
        "Angriff",
        "Tor",
    ]


def test_workflow_uses_its_installation_template_for_new_analyses(tmp_path) -> None:
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    store.add_category("Konter", "#F59E0B")
    workflow = ApplicationWorkflow(_Presenter(), template_store=store)

    assert workflow.new_analysis() is True

    assert [category.name for category in workflow.analysis.categories] == [
        "Abwehr",
        "Angriff",
        "Tor",
        "Konter",
    ]


class _Presenter:
    def ask_unsaved_changes(self):  # type: ignore[no-untyped-def]
        raise AssertionError("a clean Analysis must not ask")

    def choose_analysis_to_open(self):  # type: ignore[no-untyped-def]
        return None

    def choose_analysis_destination(self, suggested_name):  # type: ignore[no-untyped-def]
        return None

    def choose_source_video(self):  # type: ignore[no-untyped-def]
        return None

    def report_failure(self, title, message):  # type: ignore[no-untyped-def]
        raise AssertionError(f"unexpected failure: {title}: {message}")
