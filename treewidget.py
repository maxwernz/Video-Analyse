from __future__ import annotations

from uuid import UUID

from PySide6.QtWidgets import QTreeWidget, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal

from analysis import Analysis
from treewidget_item import CategoryTreeItem, ClipItem, ClipTreeItem

MENU_STYLE_SHEET = """
        QMenu {
            background-color: rgb(178, 178, 178); /* Background color of the menu */
            border: 1px solid #C0C0C0; /* Light gray border */
            padding: 5px; /* Padding around menu */
            border-radius: 8px; /* Large border radius */
            font: 14px;
        }

        QMenu::item {
            padding: 2px 4px; /* Padding for menu items */
            color: #333; /* Text color */
        }

        QMenu::item:selected {
            background-color: #007AFF; /* Selected item background color */
            color: white; /* Selected item text color */
            border-radius: 4px; /* Large border radius for selected items */
        }

        QMenu::separator {
            height: 1px; /* Height of the separator */
            background-color: #C0C0C0; /* Color of the separator */
            margin: 5px 0; /* Margin around separator */
        }

    """


class TreeWidget(QTreeWidget):
    """Renders the Clips and Categories of an Analysis.

    The widget owns no durable state: it renders whatever Analysis it is given
    and reports requested changes by identity, leaving the mutation to the
    Analysis operations.
    """

    export_clips = Signal()
    clip_edit_requested = Signal(object)
    clip_remove_requested = Signal(object)
    category_edit_requested = Signal(object)
    category_remove_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.sortByColumn(1, Qt.AscendingOrder)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.itemDoubleClicked.connect(self.request_edit)

    def render_analysis(self, analysis: Analysis) -> None:
        """Rebuild the tree from the Analysis, keeping the selected Clip selected."""
        selected_clip_ids = {
            item.clip_id for item in self._clip_tree_items() if item.isSelected()
        }
        self.clear()

        category_names = {category.id: category.name for category in analysis.categories}
        category_items: dict[UUID, CategoryTreeItem] = {}
        for clip in analysis.clips:
            parent: QTreeWidget | CategoryTreeItem = self
            if clip.category_id is not None:
                category_item = category_items.get(clip.category_id)
                if category_item is None:
                    category_item = CategoryTreeItem(
                        clip.category_id,
                        category_names[clip.category_id],
                        parent=self,
                    )
                    category_items[clip.category_id] = category_item
                parent = category_item
            clip_item = ClipItem.from_clip(
                clip,
                None if clip.category_id is None else category_names[clip.category_id],
            )
            item = ClipTreeItem(clip_item, parent=parent)
            if clip.id in selected_clip_ids:
                item.setSelected(True)

        self.fit_tree()

    def context_menu(self, event):
        item = self.itemAt(event)
        if item is None:
            return

        menu = QMenu(self)

        remove_action = QAction("Löschen", self)
        remove_action.triggered.connect(lambda: self.request_remove(item))
        menu.addAction(remove_action)

        edit_action = QAction("Bearbeiten", self)
        edit_action.triggered.connect(lambda: self.request_edit(item))
        menu.addAction(edit_action)

        export_action = QAction("Clips exportieren", self)
        export_action.triggered.connect(lambda: self.export_clips.emit())
        menu.addAction(export_action)
        menu.setStyleSheet(MENU_STYLE_SHEET)

        menu.exec(self.mapToGlobal(event))

    def request_edit(self, item, _=None) -> None:
        if isinstance(item, ClipTreeItem):
            self.clip_edit_requested.emit(item.clip_id)
        elif isinstance(item, CategoryTreeItem):
            self.category_edit_requested.emit(item.category_id)

    def request_remove(self, item) -> None:
        if isinstance(item, ClipTreeItem):
            self.clip_remove_requested.emit(item.clip_id)
        elif isinstance(item, CategoryTreeItem):
            self.category_remove_requested.emit(item.category_id)

    def selected_clip_items(self) -> list[ClipItem]:
        """The Clips covered by the selection, Category items included."""
        return self._clip_items_of(self.selectedItems())

    def all_clip_items(self) -> list[ClipItem]:
        return self._clip_items_of(self.get_top_level_items())

    def fit_tree(self) -> None:
        self.expandAll()
        for col in range(self.columnCount()):
            self.resizeColumnToContents(col)

    def get_top_level_items(self):
        return [self.topLevelItem(index) for index in range(self.topLevelItemCount())]

    def _clip_items_of(self, items) -> list[ClipItem]:
        clip_items: list[ClipItem] = []
        for item in items:
            candidates = item.children() if item.is_category_item() else [item]
            for candidate in candidates:
                clip_item = candidate.clip()
                if clip_item not in clip_items:
                    clip_items.append(clip_item)
        return clip_items

    def _clip_tree_items(self) -> list[ClipTreeItem]:
        clip_items: list[ClipTreeItem] = []
        for item in self.get_top_level_items():
            if isinstance(item, ClipTreeItem):
                clip_items.append(item)
            else:
                clip_items.extend(item.children())
        return clip_items
