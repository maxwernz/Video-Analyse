
from PySide6.QtWidgets import QDialog
from Ui_clip_handler import Ui_Dialog
from treewidget_item import ClipItem
from util import milliseconds_to_hhmmss

class ClipHandler(QDialog, Ui_Dialog):

    categories = {"Abwehr": None, "Angriff": None, "Tor": None}

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.categoryBox.addItems(ClipHandler.categories)

class CreateClip(ClipHandler):

    def __init__(self, clip_start, clip_stop, parent=None):

        ClipHandler.__init__(self, parent)

        self.start_time = clip_start
        self.stop_time = clip_stop

        self.clip = None
        self.category = None

        label_start = milliseconds_to_hhmmss(self.start_time)
        label_stop = milliseconds_to_hhmmss(self.stop_time)
        self.clipDuration.setText(f"{label_start} / {label_stop}")

        self.acceptButton.setDisabled(True)

        self.clipNameLine.textChanged.connect(lambda text: self.acceptButton.setEnabled(text != ""))
        self.cancelButton.clicked.connect(self.close)
        self.acceptButton.clicked.connect(self.save_entry)

    def save_entry(self):
        category = self.categoryBox.currentText()
        if category == "":
            category = None
        
        self.clip = ClipItem(self.clipNameLine.text(), self.start_time, self.stop_time, self.notesText.toPlainText(), category)
        self.accept()

class EditClip(ClipHandler):

    def __init__(self, clip_item: ClipItem, parent=None):

        ClipHandler.__init__(self, parent)

        self.clip_item = clip_item
        start_time, stop_time = clip_item.clip_times()

        label_start = milliseconds_to_hhmmss(start_time)
        label_stop = milliseconds_to_hhmmss(stop_time)
        self.clipDuration.setText(f"{label_start} / {label_stop}")

        self.clipNameLine.textChanged.connect(lambda text: self.acceptButton.setEnabled(text != ""))
        self.cancelButton.clicked.connect(self.close)
        self.acceptButton.clicked.connect(self.save_entry)

        self.clipNameLine.setText(clip_item.clip_name())
        self.notesText.setText(clip_item.clip_notes())

        category = clip_item.category
        self.categoryBox.setCurrentText(category)

    def save_entry(self):
        category = self.categoryBox.currentText()
        if category == "":
            category = None

        self.clip_item.edit_item(self.clipNameLine.text(), self.notesText.toPlainText(), category)
        self.accept()




