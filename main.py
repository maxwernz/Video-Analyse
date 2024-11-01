import sys
from PySide6.QtWidgets import QApplication
from mainwindow import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.load_analysis("/Users/max/Downloads/TSV vs. S3L.analysis")
    # window.load_video("/Users/max/Downloads/IMG_0024.MOV")
    window.show()
    sys.exit(app.exec())