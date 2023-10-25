import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QShortcut, QMessageBox
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QKeySequence
from Ui_main_window import Ui_MainWindow
from clip_handler import ClipHandler
from treewidget_item import TreeItem, ClipTreeItem

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.menuFile.triggered.connect(self.load_video)
        
        self.setup_connections()
        self.setup_shortcuts()

        self.clip_start = None

    def setup_connections(self):
        self.playPauseButton.clicked.connect(self.videoWidget.play_pause_video)
        self.soundButton.clicked.connect(self.videoWidget.change_sound)
        self.forwardButton.clicked.connect(self.videoWidget.jump_forward)
        self.backwardButton.clicked.connect(self.videoWidget.jump_backward)
        self.clipButton.toggled.connect(lambda recording: self.clip_started() if recording else self.clip_stopped())
        self.speedBox.currentIndexChanged.connect(lambda: self.videoWidget.change_speed(self.speedBox.currentText()))
        self.treeWidget.itemSelectionChanged.connect(self.jump_to_clip)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(self.videoWidget.move_forward)
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(self.videoWidget.move_backward)
        QShortcut(QKeySequence(Qt.Key_Up), self).activated.connect(self.change_speed_up)
        QShortcut(QKeySequence(Qt.Key_Down), self).activated.connect(self.change_speed_down)

    def load_video(self):
        file_name = QFileDialog.getOpenFileName(self, "Open file", "${HOME}", "Video files (*.mp4 *.mov)")[0]
        if file_name:
            url = QUrl.fromLocalFile(file_name)
            self.videoWidget.load_video(url)

    def change_speed_up(self):
        current_index = self.speedBox.currentIndex()
        if current_index == self.speedBox.count() - 1:
            return

        self.speedBox.setCurrentIndex(current_index + 1)

    def change_speed_down(self):
        current_index = self.speedBox.currentIndex()
        if current_index == 0:
            return 
        self.speedBox.setCurrentIndex(current_index - 1)

    def clip_started(self):
        self.clip_start = self.videoWidget.get_position()

    def clip_stopped(self):
        if self.videoWidget.videoIsPlaying():
            self.playPauseButton.click()
        clip_stop = self.videoWidget.get_position()
        clip_handler = ClipHandler(self.clip_start, clip_stop)
        try:
            if clip_handler.exec():
                clip = clip_handler.clip
                category = clip_handler.category
                parent = self.treeWidget
                if category is not None:
                    if category in ClipHandler.categories:
                        category_item = ClipHandler.categories[category]
                        if category_item is None:
                            category_item = TreeItem(parent)
                            category_item.setText(0, category)
                            ClipHandler.categories[category] = category_item
                    parent = category_item

                ClipTreeItem(clip, parent=parent)
                self.fit_tree()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def fit_tree(self):
        self.treeWidget.expandAll()
        for col in range(self.treeWidget.columnCount()):
            self.treeWidget.resizeColumnToContents(col)

    
    def jump_to_clip(self):
        selected_item = self.treeWidget.currentItem()
        if not isinstance(selected_item, ClipTreeItem):
            return
        
        self.videoWidget.set_position(selected_item.clip_item.jump_point())

        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.videoWidget.load_video(QUrl.fromLocalFile("/Users/max/Downloads/Buchen.mp4"))
    sys.exit(app.exec())

