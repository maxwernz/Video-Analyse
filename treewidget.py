from PyQt5.QtWidgets import QTreeWidget, QMenu, QAction
from PyQt5.QtCore import Qt
from clip_handler import ClipHandler

class TreeWidget(QTreeWidget):

    tree_item_list = []

    def __init__(self, parent=None):
        super().__init__(parent)

        self.sortByColumn(1, 0)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def context_menu(self, event):
        item = self.itemAt(event)
        if item:
            menu = QMenu(self)

            remove_action = QAction("Remove", self)
            remove_action.triggered.connect(lambda: self.remove_item(item))
            menu.addAction(remove_action)

            menu.exec(self.mapToGlobal(event))

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
    
