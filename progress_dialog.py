from PyQt5.QtWidgets import QDialog, QProgressBar, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer

class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Progress")
        self.setFixedSize(300, 100)
        self.setGeometry(100, 100, 300, 100)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(10, 10, 280, 50)
        self.progress_bar.setValue(0)

        self.progress_label = QLabel("0%", self)  # QLabel für die Prozentzahl
        self.progress_label.setGeometry(10, 60, 280, 20)
        self.progress_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        self.setLayout(layout)

        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.close)

        self.setModal(False)

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}%")

        if value == 100:
            self.raise_()
            self.close_timer.start(2000)
