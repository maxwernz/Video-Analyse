import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtCore import QUrl
from Ui_main_window import Ui_MainWindow

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.menuFile.triggered.connect(self.load_video)
        self.setup_connections()

    def setup_connections(self):
        self.playPauseButton.clicked.connect(self.videoWidget.play_pause_video)

    def load_video(self):
        file_name = QFileDialog.getOpenFileName(self, "Open file", "${HOME}", "Video files (*.mp4 *.mov)")[0]
        if file_name:
            url = QUrl.fromLocalFile(file_name)
            self.videoWidget.load_video(url)
        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.videoWidget.load_video(QUrl.fromLocalFile("/Users/max/Downloads/Buchen.mp4"))
    sys.exit(app.exec())

