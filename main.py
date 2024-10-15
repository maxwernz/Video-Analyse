import sys
from PySide6.QtWidgets import QApplication
from mainwindow import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.load_video("/Volumes/T7/Handball/Videos/Handschuhsheim/TSV vs. S3L.mp4")
    window.videoWidget.set_position(1000)
    window.show()
    sys.exit(app.exec())