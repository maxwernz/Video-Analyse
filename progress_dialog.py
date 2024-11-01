from PySide6.QtWidgets import QDialog, QProgressBar, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer

class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Progress")
        self.setFixedSize(300, 100)
        self.setGeometry(100, 100, 300, 100)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(10, 10, 280, 50)
        self.progress_bar.setValue(0)

        self.progress_bar.setStyleSheet("""
    QProgressBar {
        border: 2px solid #d3d3d3;
        border-radius: 10px;
        background-color: #e0e0e0;
        height: 20px;
        text-align: center;
        font: bold 12px;
        color: black;
    }

    QProgressBar::chunk {
        background-color: #007AFF;
        border-radius: 10px;
    }
""")

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

    def center_on_main_window(self, main_window):
        # Die Mitte des Hauptfensters berechnen
        main_window_rect = main_window.frameGeometry()
        center_point = main_window_rect.center()

        # Die Mitte des Dialogfensters berechnen
        dialog_rect = self.frameGeometry()
        dialog_rect.moveCenter(center_point)

        # Den Dialog in die Mitte des Hauptfensters verschieben
        self.move(dialog_rect.topLeft())

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}%")

        if value == 100:
            self.raise_()
            self.close_timer.start(2000)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = ProgressDialog()
    dialog.show()
    sys.exit(app.exec())
