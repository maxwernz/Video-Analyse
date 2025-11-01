import sys
from PySide6.QtWidgets import QApplication
from mainwindow import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.load_video("/Volumes/T7/Handball/Videos/Handschuhsheim/TSV vs Hockenheim.mp4")
    window.load_video("/Volumes/T7/Handball/Videos/Handschuhsheim/TSV vs. Dossenheim.mp4")
    window.show()
    sys.exit(app.exec())