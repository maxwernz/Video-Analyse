from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from PySide6.QtWidgets import QTreeWidgetItem

from analysis import Clip
from util import milliseconds_to_hhmmss


@dataclass(frozen=True)
class ClipItem:
    """Read-only snapshot of a Clip, used for rendering and Combined exports.

    The canonical Clip lives in the Analysis; this carries just enough of it for
    the tree and the export to work without owning or mutating that state.
    """

    name: str
    start_position: int
    end_position: int
    notes: str
    category: str | None = None
    clip_id: UUID | None = None

    @classmethod
    def from_clip(cls, clip: Clip, category_name: str | None) -> "ClipItem":
        return cls(
            name=clip.name,
            start_position=clip.start_ms,
            end_position=clip.end_ms,
            notes=clip.notes,
            category=category_name,
            clip_id=clip.id,
        )

    def clip_times(self) -> tuple[int, int]:
        return self.start_position, self.end_position

    def clip_times_s(self) -> tuple[float, float]:
        return self.start_position / 1000, self.end_position / 1000

    def tree_values(self) -> tuple[str, str, str]:
        return (
            self.name,
            milliseconds_to_hhmmss(self.start_position),
            milliseconds_to_hhmmss(self.end_position),
        )


class TreeItem(QTreeWidgetItem):

    def __init__(self, parent=None):
        QTreeWidgetItem.__init__(self, parent)

    def children(self):
        return [self.child(i) for i in range(self.childCount())]


class CategoryTreeItem(TreeItem):
    """Top-level item rendering one Analysis Category."""

    def __init__(self, category_id: UUID | None, name: str, parent=None):
        TreeItem.__init__(self, parent)
        self.category_id = category_id
        self.setText(0, name)


class ClipTreeItem(TreeItem):

    def __init__(self, clip_item: ClipItem, parent=None):
        TreeItem.__init__(self, parent)
        self.clip_item = clip_item
        for i, val in enumerate(self.clip_item.tree_values()):
            self.setText(i, val)

    @property
    def clip_id(self) -> UUID | None:
        return self.clip_item.clip_id
