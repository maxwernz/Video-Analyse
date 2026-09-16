"""Confirm the template file resolves through Qt's settings location.

The template path must never be hardcoded: it has to move with the platform's
own application-configuration directory, and a missing directory must not
stop the installation from starting.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QStandardPaths  # noqa: E402

from analysis import CategoryTemplateStore, DEFAULT_CATEGORY_TEMPLATE  # noqa: E402
from category_template_settings import installation_category_template_store  # noqa: E402


def test_the_store_lives_under_qts_application_configuration_location(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        lambda location: str(tmp_path) if location == QStandardPaths.StandardLocation.AppConfigLocation else "",
    )

    store = installation_category_template_store()

    assert isinstance(store, CategoryTemplateStore)
    assert store.path == tmp_path / "category-template.json"
    # The location has never been created yet; a fresh installation still
    # gets a usable template rather than a startup failure.
    assert [(category.name, category.color) for category in store.categories()] == list(
        DEFAULT_CATEGORY_TEMPLATE
    )


def test_a_missing_configuration_location_is_reported_rather_than_guessed(
    monkeypatch,
) -> None:
    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda location: "")

    with pytest.raises(OSError):
        installation_category_template_store()
