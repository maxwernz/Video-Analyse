"""One interface for the two Category collections an analyst can edit."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from analysis import Analysis, Category, CategoryTemplateStore


class CategoryCollection(Protocol):
    """Keep manager actions independent of where future Categories live."""

    def categories(self) -> tuple[Category, ...]: ...

    def analysis(self) -> Analysis | None: ...

    def add_category(self, name: str, color: str) -> Category: ...

    def update_category(
        self, category_id: UUID, *, name: str | None = None, color: str | None = None
    ) -> Category: ...

    def remove_category(self, category_id: UUID) -> None: ...

    def reorder_categories(self, category_ids: Sequence[UUID]) -> None: ...


class AnalysisCategories:
    """Preserve Clip-impact counts while editing this Analysis's Categories."""

    def __init__(self, analysis: Analysis) -> None:
        self._analysis = analysis

    def categories(self) -> tuple[Category, ...]:
        return self._analysis.categories

    def analysis(self) -> Analysis:
        return self._analysis

    def add_category(self, name: str, color: str) -> Category:
        return self._analysis.add_category(name, color)

    def update_category(
        self, category_id: UUID, *, name: str | None = None, color: str | None = None
    ) -> Category:
        if name is not None:
            return self._analysis.update_category(category_id, name=name)
        if color is not None:
            return self._analysis.update_category(category_id, color=color)
        return self._analysis.category(category_id)

    def remove_category(self, category_id: UUID) -> None:
        self._analysis.remove_category(category_id)

    def reorder_categories(self, category_ids: Sequence[UUID]) -> None:
        self._analysis.reorder_categories(category_ids)


class TemplateCategories:
    """Keep template edits isolated from every Analysis already underway."""

    def __init__(self, store: CategoryTemplateStore) -> None:
        self._store = store

    def categories(self) -> tuple[Category, ...]:
        return self._store.categories()

    def analysis(self) -> None:
        return None

    def add_category(self, name: str, color: str) -> Category:
        return self._store.add_category(name, color)

    def update_category(
        self, category_id: UUID, *, name: str | None = None, color: str | None = None
    ) -> Category:
        if name is not None:
            return self._store.update_category(category_id, name=name)
        if color is not None:
            return self._store.update_category(category_id, color=color)
        return next(category for category in self.categories() if category.id == category_id)

    def remove_category(self, category_id: UUID) -> None:
        self._store.remove_category(category_id)

    def reorder_categories(self, category_ids: Sequence[UUID]) -> None:
        self._store.reorder_categories(category_ids)
