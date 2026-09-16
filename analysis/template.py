from __future__ import annotations

import json
import os
from collections.abc import Iterable, Sequence
from pathlib import Path
from uuid import UUID, uuid4

from .document import AnalysisDocument
from .errors import InvalidAnalysisDataError
from .model import Analysis, Category


#: The handball Categories an installation starts with until an analyst changes
#: its Category template.
DEFAULT_CATEGORY_TEMPLATE: tuple[tuple[str, str], ...] = (
    ("Abwehr", "#3B82F6"),
    ("Angriff", "#EF4444"),
    ("Tor", "#22C55E"),
)

class _Unchanged:
    pass


_UNCHANGED = _Unchanged()


class CategoryTemplateStore:
    """The editable, installation-local source for future Analysis Categories."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fallback_categories = _built_in_categories()

    @property
    def path(self) -> Path:
        return self._path

    def categories(self) -> tuple[Category, ...]:
        """Keep new Analyses usable when installation settings are damaged."""

        try:
            return self._read()
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, InvalidAnalysisDataError):
            return self._fallback_categories

    def category(self, category_id: UUID) -> Category:
        """Raise the same way an Analysis does when the identity is unknown."""

        return self._as_analysis().category(category_id)

    def add_category(self, name: str, color: str = "#808080") -> Category:
        template = self._as_analysis()
        category = template.add_category(name, color)
        self._write(template.categories)
        return category

    def update_category(
        self,
        category_id: UUID,
        *,
        name: str | object = _UNCHANGED,
        color: str | object = _UNCHANGED,
    ) -> Category:
        template = self._as_analysis()
        category = template.category(category_id)
        if name is not _UNCHANGED:
            if not isinstance(name, str):
                raise InvalidAnalysisDataError("Category name must be text")
            category = template.update_category(category_id, name=name)
        if color is not _UNCHANGED:
            if not isinstance(color, str):
                raise InvalidAnalysisDataError("Category color must be text")
            category = template.update_category(category_id, color=color)
        self._write(template.categories)
        return category

    def remove_category(self, category_id: UUID) -> None:
        template = self._as_analysis()
        template.remove_category(category_id)
        self._write(template.categories)

    def reorder_categories(self, category_ids: Sequence[UUID]) -> None:
        template = self._as_analysis()
        template.reorder_categories(category_ids)
        self._write(template.categories)

    def restore_builtin(self) -> None:
        """Replace only future-Analysis defaults with the handball starting set."""

        self._write(_built_in_categories())

    def _as_analysis(self) -> Analysis:
        template = Analysis("Category template")
        for category in self.categories():
            template.add_category(category.name, category.color, category_id=category.id)
        return template

    def _read(self) -> tuple[Category, ...]:
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"categories"}:
            raise InvalidAnalysisDataError("Category template must contain Categories")
        raw_categories = payload["categories"]
        if not isinstance(raw_categories, list):
            raise InvalidAnalysisDataError("Category template Categories must be a list")
        template = Analysis("Category template")
        for entry in raw_categories:
            if not isinstance(entry, dict) or set(entry) != {"id", "name", "color"}:
                raise InvalidAnalysisDataError("Category template entry is invalid")
            identity, name, color = entry["id"], entry["name"], entry["color"]
            if not isinstance(identity, str) or not isinstance(name, str) or not isinstance(color, str):
                raise InvalidAnalysisDataError("Category template entry is invalid")
            try:
                category_id = UUID(identity)
            except ValueError as error:
                raise InvalidAnalysisDataError("Category template identity is invalid") from error
            template.add_category(name, color, category_id=category_id)
        return template.categories

    def _write(self, categories: Iterable[Category]) -> None:
        rows = [
            {"id": str(category.id), "name": category.name, "color": category.color}
            for category in categories
        ]
        encoded = json.dumps({"categories": rows}, ensure_ascii=False, indent=2) + "\n"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            temporary.write_text(encoded, encoding="utf-8")
            os.replace(temporary, self._path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


def _built_in_categories() -> tuple[Category, ...]:
    return tuple(
        Category(uuid4(), name, color) for name, color in DEFAULT_CATEGORY_TEMPLATE
    )


def apply_category_template(
    analysis: Analysis,
    template: Iterable[tuple[str, str] | Category] = DEFAULT_CATEGORY_TEMPLATE,
) -> None:
    """Copy Category meanings, never template identities, into an Analysis."""

    for entry in template:
        name, color = (entry.name, entry.color) if isinstance(entry, Category) else entry
        if analysis.category_named(name) is None:
            analysis.add_category(name, color)


def new_analysis_document(
    title: str = "", *, template_store: CategoryTemplateStore | None = None
) -> AnalysisDocument:
    """Seed a new Analysis from the current template without sharing UUIDs."""

    analysis = Analysis(title)
    if template_store is None:
        apply_category_template(analysis)
    else:
        apply_category_template(analysis, template_store.categories())
    return AnalysisDocument(analysis)
