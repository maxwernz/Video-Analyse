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
        # Applied as two independent calls, never an early return after just
        # one: a caller naming both a new name and colour must get both, not
        # have the colour silently dropped because the name branch returned
        # first.
        if name is not None:
            self._analysis.update_category(category_id, name=name)
        if color is not None:
            self._analysis.update_category(category_id, color=color)
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
        # Same two-independent-calls shape as AnalysisCategories, so naming
        # both a new name and colour changes both, and the unknown-identity
        # error matches the Analysis scope's (an AnalysisError, not a bare
        # StopIteration a caller's `except AnalysisError` would miss).
        if name is not None:
            self._store.update_category(category_id, name=name)
        if color is not None:
            self._store.update_category(category_id, color=color)
        return self._store.category(category_id)

    def remove_category(self, category_id: UUID) -> None:
        self._store.remove_category(category_id)

    def reorder_categories(self, category_ids: Sequence[UUID]) -> None:
        self._store.reorder_categories(category_ids)
