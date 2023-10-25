
from PyQt5.QtWidgets import QDialog
from Ui_clip_handler import Ui_Dialog
from treewidget_item import ClipItem
from util import milliseconds_to_hhmmss

class ClipHandler(QDialog, Ui_Dialog):

    categories = {}

    def __init__(self, clip_start, clip_stop, parent=None):

        QDialog.__init__(self, parent)

        self.setupUi(self)

        self.start_time = clip_start
        self.stop_time = clip_stop

        self.clip = None
        self.category = None

        label_start = milliseconds_to_hhmmss(self.start_time)
        label_stop = milliseconds_to_hhmmss(self.stop_time)
        self.clipDuration.setText(f"{label_start} / {label_stop}")

        self.acceptButton.setDisabled(True)
        self.categoryBox.addItems(ClipHandler.categories)

        self.clipNameLine.textChanged.connect(lambda text: self.acceptButton.setEnabled(text != ""))
        self.cancelButton.clicked.connect(self.close)
        self.acceptButton.clicked.connect(self.save_entry)

    def save_entry(self):
        category = self.categoryBox.currentText()
        if category != "":
            self.category = category
            if category not in ClipHandler.categories:
                ClipHandler.categories.update({category: None})
        
        self.clip = ClipItem(self.clipNameLine.text(), self.start_time, self.stop_time, self.notesText.toPlainText())
        self.accept()


