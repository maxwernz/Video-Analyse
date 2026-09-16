"""Where the installation-local Category template lives, and how it survives.

`CategoryTemplateStore` is durable, installation-local state — separate from
any Analysis file — resolved through `QStandardPaths` (`tests/conftest.py`
overrides that resolution for the whole suite, through the same env-var seam
`app_runtime.configure_local_logging` uses for its log directory). These
tests exercise the store directly: round-tripping, and the two ways it must
never fail startup — a missing file and a corrupt one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analysis.template import CategoryTemplate, DEFAULT_CATEGORY_TEMPLATE
from category_template_store import CategoryTemplateStore, template_store_path


def test_loading_a_missing_file_falls_back_to_the_built_in_template(
    tmp_path: Path,
) -> None:
    store = CategoryTemplateStore(tmp_path / "does-not-exist.json")

    template = store.load()

    assert [(entry.name, entry.color) for entry in template.entries] == list(
        DEFAULT_CATEGORY_TEMPLATE
    )


def test_saving_then_loading_round_trips_names_colors_and_order(
    tmp_path: Path,
) -> None:
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    template = CategoryTemplate()
    template.add("Kontertor", "#8FAE3C")
    template.add("Siebenmeter", "#DE8241")

    store.save(template)
    reloaded = store.load()

    assert [(entry.name, entry.color) for entry in reloaded.entries] == [
        ("Kontertor", "#8FAE3C"),
        ("Siebenmeter", "#DE8241"),
    ]


def test_saving_then_loading_preserves_entry_identity(tmp_path: Path) -> None:
    """A rename after a reload must still land on the entry it named.

    The template's own identity is what QML edits by; if a round trip lost it
    a rename would have nothing stable to address.
    """

    store = CategoryTemplateStore(tmp_path / "category-template.json")
    template = CategoryTemplate()
    entry = template.add("Kontertor", "#8FAE3C")
    store.save(template)

    reloaded = store.load()

    assert reloaded.entries[0].id == entry.id


@pytest.mark.parametrize(
    "contents",
    [
        "not json at all {{{",
        "[]",
        '{"categories": "not a list"}',
        '{"categories": [{"id": "not-a-uuid", "name": "x", "color": "#000"}]}',
        '{"categories": [{"name": "missing id and color"}]}',
    ],
)
def test_loading_a_corrupt_file_falls_back_to_the_built_in_template(
    tmp_path: Path, contents: str
) -> None:
    path = tmp_path / "category-template.json"
    path.write_text(contents, encoding="utf-8")
    store = CategoryTemplateStore(path)

    template = store.load()

    assert [(entry.name, entry.color) for entry in template.entries] == list(
        DEFAULT_CATEGORY_TEMPLATE
    )


def test_restoring_the_default_template_overwrites_customization(
    tmp_path: Path,
) -> None:
    store = CategoryTemplateStore(tmp_path / "category-template.json")
    customized = CategoryTemplate()
    customized.add("Nur meins", "#5B87D6")
    store.save(customized)

    restored = store.restore_default()

    assert [(entry.name, entry.color) for entry in restored.entries] == list(
        DEFAULT_CATEGORY_TEMPLATE
    )
    assert [(entry.name, entry.color) for entry in store.load().entries] == list(
        DEFAULT_CATEGORY_TEMPLATE
    )


def test_saving_creates_the_parent_directory(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "deeper" / "category-template.json"
    store = CategoryTemplateStore(nested)

    store.save(CategoryTemplate.default())

    assert nested.is_file()


# --- Path resolution: the env override, and QStandardPaths beneath it ------


def test_the_env_override_wins_over_standard_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / "override" / "category-template.json"
    monkeypatch.setenv("VIDEO_ANALYSE_CATEGORY_TEMPLATE_PATH", str(override))

    assert template_store_path() == override


def test_with_no_override_the_path_is_resolved_through_standard_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIDEO_ANALYSE_CATEGORY_TEMPLATE_PATH", raising=False)

    from PySide6.QtCore import QCoreApplication, QStandardPaths

    if not QCoreApplication.instance():
        QCoreApplication([])
    QCoreApplication.setOrganizationName("test-org")
    QCoreApplication.setApplicationName("test-app")

    expected = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    assert expected, "the test environment must offer an application-data location"

    resolved = template_store_path()

    assert resolved == Path(expected) / "category-template.json"
