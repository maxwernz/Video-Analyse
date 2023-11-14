from PyQt5.QtWidgets import QTreeWidget, QMenu, QAction
from PyQt5.QtCore import Qt
from clip_handler import ClipHandler, EditClip
from treewidget_item import TreeItem, ClipTreeItem

class TreeWidget(QTreeWidget):

    tree_item_list = []

    def __init__(self, parent=None):
        super().__init__(parent)

        self.sortByColumn(1, 0)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.itemDoubleClicked.connect(self.edit_item)

    def context_menu(self, event):
        item = self.itemAt(event)
        if item:
            menu = QMenu(self)

            remove_action = QAction("Remove", self)
            remove_action.triggered.connect(lambda: self.remove_item(item))
            menu.addAction(remove_action)

            menu.exec(self.mapToGlobal(event))

    def add_clips(self, clip_list):
        for clip in clip_list:
            self.add_clip(clip)

    def add_clip(self, clip):
        TreeWidget.tree_item_list.append(clip)
        category = clip.category
        parent = self
        if category is not None:
            if category in ClipHandler.categories:
                category_item = self.get_category_item(category)
            else:
                category_item = TreeItem(parent)
                category_item.setText(0, category)
                ClipHandler.categories[category] = category_item
            parent = category_item
        
        ClipTreeItem(clip, parent=parent)

    def edit_item(self, item, _):
        if item is None:
            return
        
        if item.parent() is None: # TopLevelItem
            return
        
        dialog = EditClip(item.clip())
        if dialog.exec():
            clip_item = dialog.clip_item
            item.edit_item(clip_item.clip_name())
            category = clip_item.category
            if item.parent() != ClipHandler.categories[category]:
                old_parent = item.parent()
                old_parent.removeChild(item)
                new_parent = self.get_category_item(category)
                new_parent.addChild(item)

                self.check_empty_parent(old_parent)

        self.fit_tree()

    def get_category_item(self, category):
        category_item = ClipHandler.categories[category]
        if category_item is None:
            category_item = TreeItem(self)
            category_item.setText(0, category)
            ClipHandler.categories[category] = category_item
        
        return category_item

    def remove_item(self, item):
        parent = item.parent()
        if parent is None:
            index = self.indexOfTopLevelItem(item)
            self.takeTopLevelItem(index)
            for child in item.children():
                self.remove_clip_from_list(child)
        else:
            parent.removeChild(item)
            self.remove_clip_from_list(item)


            self.check_empty_parent(parent)

    def check_empty_parent(self, parent):
        if parent.childCount() == 0:
            index = self.indexOfTopLevelItem(parent)
            self.takeTopLevelItem(index)
            category = parent.text(0)
            ClipHandler.categories[category] = None

    def remove_analysis(self):
        self.clear()
        TreeWidget.tree_item_list = []
        ClipHandler.categories = {"Abwehr": None, "Angriff": None, "Tor": None}

    def remove_clip_from_list(self, item):
        clip_item = item.clip()
        TreeWidget.tree_item_list.remove(clip_item)

    def fit_tree(self):
        self.expandAll()
        for col in range(self.columnCount()):
            self.resizeColumnToContents(col)
    
