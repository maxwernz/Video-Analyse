"""QML rows for managing Categories without handing it domain objects."""

from __future__ import annotations

from analysis import Analysis, Category
from item_models import RoleModel


class ManagedCategoryModel(RoleModel):
    """Keep QML from deriving durable Category consequences for itself."""

    ROLES = ("categoryId", "name", "color", "clipCount")

    def refresh(self, categories: tuple[Category, ...], analysis: Analysis | None) -> None:
        self._replace(
            [
                {
                    "categoryId": str(category.id),
                    "name": category.name,
                    "color": category.color,
                    "clipCount": (
                        sum(clip.category_id == category.id for clip in analysis.clips)
                        if analysis is not None
                        else 0
                    ),
                }
                for category in categories
            ]
        )
