"""Where the installation-local Category template lives on disk.

The Category template (CONTEXT.md) is durable state that outlives any single
Analysis: an analyst who reshapes it — renames "Tor" to "Treffer", drops a
Category their club never uses — expects every future Analysis on that
machine to start from what they set, including after the application
restarts. It is not part of any Analysis file: it never touches
`analysis/document.py` or `AnalysisFileCodec`, and its path is resolved
through `QStandardPaths` the way `app_runtime.configure_local_logging`
resolves the log directory, rather than hardcoded.

Kept independent of `analysis/` for the same reason `media_probe.py` is: it
reads and writes a real file rather than deciding what a Category template
is, and it is the one module on this call path that needs `QStandardPaths`
(`analysis/template.py` imports it lazily and only when it needs the
installed template — see that module's docstring).

A missing file is what every fresh install has. A corrupt one — hand-edited,
half-written by a crash, from some future version this one cannot read — is
treated exactly the same: `load` never raises and always returns a usable
template, because a broken template file must not block startup.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import QStandardPaths

from analysis.template import CategoryTemplate, CategoryTemplateEntry

_STORE_FILE_NAME = "category-template.json"

#: Overrides `template_store_path`'s own resolution, the same way
#: `VIDEO_ANALYSE_LOG_DIR` overrides `app_runtime.configure_local_logging`'s.
#: A test suite that let every test resolve through `QStandardPaths`
#: unmodified would depend on whatever this machine's real application-data
#: directory happens to hold, including a file this same suite wrote on a
#: previous run; `tests/conftest.py` sets this for every test instead.
_PATH_OVERRIDE_ENV_VAR = "VIDEO_ANALYSE_CATEGORY_TEMPLATE_PATH"

logger = logging.getLogger(__name__)


def template_store_path() -> Path:
    """Where the durable Category template is read from and written to."""

    configured_path = os.environ.get(_PATH_OVERRIDE_ENV_VAR)
    if configured_path:
        return Path(configured_path)
    application_data = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not application_data:
        raise RuntimeError(
            "The operating system did not provide an application-data location"
        )
    return Path(application_data) / _STORE_FILE_NAME


class CategoryTemplateStore:
    """Reads and writes the durable Category template, tolerating a bad file."""

    def __init__(self, path: Path | None = None) -> None:
        # `path` is the test seam: a test gives its own `tmp_path` rather than
        # this depending on `QStandardPaths`, which needs a live application
        # identity to answer at all.
        self._path = path

    def _resolved_path(self) -> Path:
        return self._path if self._path is not None else template_store_path()

    def load(self) -> CategoryTemplate:
        """The durable template, or the built-in one for every way this can fail."""

        try:
            path = self._resolved_path()
        except RuntimeError:
            logger.warning(
                "Category template location unavailable; using the built-in template"
            )
            return CategoryTemplate.default()
        if not path.is_file():
            return CategoryTemplate.default()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entries = [
                CategoryTemplateEntry(
                    id=UUID(str(item["id"])),
                    name=str(item["name"]),
                    color=str(item["color"]),
                )
                for item in raw["categories"]
            ]
            return CategoryTemplate(entries)
        except Exception:
            logger.warning(
                "Category template file is unreadable; using the built-in template",
                exc_info=True,
            )
            return CategoryTemplate.default()

    def save(self, template: CategoryTemplate) -> None:
        path = self._resolved_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "categories": [
                {"id": str(entry.id), "name": entry.name, "color": entry.color}
                for entry in template.entries
            ]
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def restore_default(self) -> CategoryTemplate:
        """Write the built-in handball template back, and report it."""

        default = CategoryTemplate.default()
        self.save(default)
        return default


__all__ = ["CategoryTemplateStore", "template_store_path"]
