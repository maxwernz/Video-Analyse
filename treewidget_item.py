from PyQt5.QtWidgets import QTreeWidgetItem
from util import milliseconds_to_hhmmss

class TreeItem(QTreeWidgetItem):

    def __init__(self, parent=None):
        QTreeWidgetItem.__init__(self, parent)

class ClipTreeItem(TreeItem):

    def __init__(self, clip_item, parent=None):

        TreeItem.__init__(self, parent)
        self.clip_item = clip_item
        for i, val in enumerate(self.clip_item.tree_values()):
            self.setText(i, val)

class ClipItem:

    def __init__(self, name, start_position, end_position, notes):
        self.start_position = start_position
        self.end_position = end_position
        self.notes = notes
        self.name = name


    def tree_values(self):
        return self.name, milliseconds_to_hhmmss(self.start_position), milliseconds_to_hhmmss(self.end_position)
    
    def jump_point(self):
        return self.start_position