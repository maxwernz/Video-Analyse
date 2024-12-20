from PySide6.QtWidgets import QTreeWidgetItem
from util import milliseconds_to_hhmmss

class TreeItem(QTreeWidgetItem):

    def __init__(self, parent=None):
        QTreeWidgetItem.__init__(self, parent)

    def children(self):
        return [self.child(i) for i in range(self.childCount())]
    
    def is_category_item(self):
        return self.parent() is None
            

class ClipTreeItem(TreeItem):

    def __init__(self, clip_item, parent=None):

        TreeItem.__init__(self, parent)
        self.clip_item = clip_item
        for i, val in enumerate(self.clip_item.tree_values()):
            self.setText(i, val)

    def clip(self):
        return self.clip_item

    def edit_item(self, name):
        self.setText(0, name)

class ClipItem:

    def __init__(self, name, start_position, end_position, notes, category=None):
        self.start_position = start_position
        self.end_position = end_position
        self.notes = notes
        self.name = name
        self.category = category

    def clip_times(self):
        return self.start_position, self.end_position

    def clip_times_s(self):
        return self.start_position/1000, self.end_position/1000

    def tree_values(self):
        return self.name, milliseconds_to_hhmmss(self.start_position), milliseconds_to_hhmmss(self.end_position)
    
    def jump_point(self):
        return self.start_position
    
    def clip_name(self):
        return self.name
    
    def clip_notes(self):
        return self.notes
    
    def edit_item(self, name, notes, category):
        self.name = name
        self.notes = notes
        self.category = category