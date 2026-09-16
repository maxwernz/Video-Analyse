"""Qt-owned location of the installation Category template."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths

from analysis import CategoryTemplateStore


def installation_category_template_store() -> CategoryTemplateStore:
    """Keep template state with application settings on every supported OS."""

    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    if not location:
        raise OSError("Qt did not provide an application configuration location")
    return CategoryTemplateStore(Path(location) / "category-template.json")
