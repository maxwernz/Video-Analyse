from PySide6.QtWidgets import QTreeWidget, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal
from clip_handler import ClipHandler, EditClip
from treewidget_item import TreeItem, ClipTreeItem

class TreeWidget(QTreeWidget):

    tree_item_list = []
    export_clips = Signal()
    item_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.sortByColumn(1, Qt.AscendingOrder)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.itemDoubleClicked.connect(self.edit_item)

    def context_menu(self, event):
        item = self.itemAt(event)
        if item:
            menu = QMenu(self)

            remove_action = QAction("Löschen", self)
            remove_action.triggered.connect(lambda: self.remove_item(item))
            menu.addAction(remove_action)
            
            if item.parent() is not None:
                edit_action = QAction("Bearbeiten", self)
                edit_action.triggered.connect(lambda: self.edit_item(item))
                menu.addAction(edit_action)

            export_action = QAction("Clips exportieren", self)
            export_action.triggered.connect(lambda: self.export_clips.emit())
            menu.addAction(export_action)
            menu.setStyleSheet("""
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
        
    """)

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

    def edit_item(self, item, _=None):
        if item is None:
            return
        
        if item.parent() is None:  # TopLevelItem
            return
        
        dialog = EditClip(item.clip())
        if dialog.exec():
            clip_item = dialog.clip_item
            item.edit_item(clip_item.clip_name())
            category = clip_item.category
            if category not in ClipHandler.categories:
                parent = self
                category_item = TreeItem(parent)
                category_item.setText(0, category)
                ClipHandler.categories[category] = category_item
            if item.parent() != ClipHandler.categories[category]:
                old_parent = item.parent()
                old_parent.removeChild(item)
                new_parent = self.get_category_item(category)
                new_parent.addChild(item)

                self.check_empty_parent(old_parent)

            self.fit_tree()
            self.item_changed.emit(False)

    def get_category_item(self, category):
        category_item = ClipHandler.categories.get(category)
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
        self.item_changed.emit(False)

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

    def get_top_level_items(self):
        top_level_items = []
        for i in range(self.topLevelItemCount()):
            top_level_items.append(self.topLevelItem(i))
        return top_level_items


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    
    main_window = QMainWindow()
    tree_widget = TreeWidget()
    
    # Add some example items for testing
    # example_clips = [
    #     ClipHandler.create_clip("Clip 1", "Category A"),
    #     ClipHandler.create_clip("Clip 2", "Category B"),
    #     ClipHandler.create_clip("Clip 3", "Category A")
    # ]
    
    # tree_widget.add_clips(example_clips)
    
    main_window.setCentralWidget(tree_widget)
    main_window.resize(400, 300)
    main_window.show()

    sys.exit(app.exec())
