"""The rows the Category-management surfaces draw.

Two projections, one shape each: the Analysis-wide Categories `WorkspaceViewModel`
manages (with how many Clips each one carries, for the removal confirmation),
and the installation-local Category template's own entries. They are separate
models rather than one model with a "which scope" role, for the same reason
`ApplicationWorkflow` keeps the two operations separate: an Analysis Category
and a template entry are different data with different lifetimes, and
QML never has to ask which one a row is.
"""

from __future__ import annotations

from collections.abc import Iterable

from analysis import Analysis
from analysis.template import CategoryTemplateEntry
from item_models import RoleModel


class AnalysisCategoryModel(RoleModel):
    """This Analysis's Categories, in their durable order."""

    ROLES = ("categoryId", "name", "color", "clipCountText")

    def refresh(self, analysis: Analysis) -> None:
        self._replace(
            [
                {
                    "categoryId": str(category.id),
                    "name": category.name,
                    "color": category.color,
                    "clipCountText": _clip_count_text(
                        sum(
                            1
                            for clip in analysis.clips
                            if clip.category_id == category.id
                        )
                    ),
                }
                for category in analysis.categories
            ]
        )


class CategoryTemplateModel(RoleModel):
    """The installation-local Category template's own entries, in order."""

    ROLES = ("categoryId", "name", "color")

    def refresh(self, entries: Iterable[CategoryTemplateEntry]) -> None:
        self._replace(
            [
                {
                    "categoryId": str(entry.id),
                    "name": entry.name,
                    "color": entry.color,
                }
                for entry in entries
            ]
        )


def _clip_count_text(count: int) -> str:
    return f"{count} Clip" if count == 1 else f"{count} Clips"


__all__ = ["AnalysisCategoryModel", "CategoryTemplateModel"]
