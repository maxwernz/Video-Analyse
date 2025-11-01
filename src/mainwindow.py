import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QLabel
from PySide6 import QtCore, QtGui
from PySide6.QtCore import QUrl, Qt, QSignalBlocker, Signal, Property, QTranslator, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QDesktopServices
from Ui_main_window import Ui_MainWindow
from clip_handler import CreateClip
from treewidget_item import ClipTreeItem
import pickle
from treewidget import TreeWidget
from video_creator import VideoCreator, ProgressLogger
from util import milliseconds_to_hhmmss

basedir = os.path.dirname(__file__)

class MainWindow(QMainWindow, Ui_MainWindow):

    file_changed = Signal(str)
    file_changes_made = Signal(bool)

    def __init__(self, parent=None):
        super().__init__()
        # self.set_language('de')
        self.setupUi(self)
        self.treeWidget.header().setVisible(True)
        self.videoStack.setCurrentIndex(1)

        self.actionLoad_Video.triggered.connect(self.open_video)
        self.actionAnalyse_speichern.triggered.connect(self.save_analysis)
        self.actionAnalyse_laden.triggered.connect(self.open_analysis)
        self.actionClips_Exportieren.triggered.connect(self.export)
        self.actionVideo_Exportieren.triggered.connect(lambda: self.export(full_video=True))
        self.actionAnalyse_entfernen.triggered.connect(self.remove_analysis)
        self.position_slider.sliderMoved.connect(self.videoWidget.set_position)

        self.loadVideoButton.clicked.connect(self.open_video)

        self.export_timer = QTimer()
        
        self.setup_connections()
        self.setup_shortcuts()

        self.progressBar.setVisible(False)
        self.openExportButton.setVisible(False)
        self.exportFinishedLabel.setVisible(False)
        self.clipHandler.setVisible(False)
        self.editHandler.setVisible(False)

        self.treeWidget.set_edit_handler(self.editHandler)


        self.setAcceptDrops(True)

        self.clip_start = None
        self.file_name = None
        self._current_file = None
        self.file_changed.emit(None)
        self._is_saved = True

    def set_language(self, lang_code):
        translator = QTranslator()
        translator.load('qtbase_' + lang_code, ':/translations')
        QApplication.instance().installTranslator(translator)

    def setup_connections(self):
        self.playPauseButton.clicked.connect(self.videoWidget.play_pause_video)
        self.videoWidget.video_paused.connect(self.toggle_play_button)
        self.soundButton.clicked.connect(self.videoWidget.change_sound)
        self.forwardButton.clicked.connect(self.videoWidget.jump_forward)
        self.backwardButton.clicked.connect(self.videoWidget.jump_backward)
        self.clipButton.toggled.connect(lambda recording: self.clip_started() if recording else self.clip_stopped())
        self.speedBox.currentIndexChanged.connect(lambda: self.videoWidget.change_speed(self.speedBox.currentText()))
        self.treeWidget.itemClicked.connect(self.jump_to_clip)
        self.treeWidget.export_clips.connect(self.export)
        self.treeWidget.item_changed.connect(self.set_saved_status)
        self.treeWidget.clip_handler_opened.connect(self.disable_clip_handler)
        self.export_timer.timeout.connect(lambda: self.exportFinishedLabel.setVisible(False))
        self.export_timer.timeout.connect(lambda: self.openExportButton.setVisible(False))
        self.export_timer.timeout.connect(self.openExportButton.clicked.disconnect)


    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(self.videoWidget.move_forward)
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(self.videoWidget.move_backward)
        QShortcut(QKeySequence(Qt.Key_Up), self).activated.connect(self.change_speed_up)
        QShortcut(QKeySequence(Qt.Key_Down), self).activated.connect(self.change_speed_down)
        QShortcut(QKeySequence.Close, self).activated.connect(self.close)

    def closeEvent(self, event):
        if self.is_saved or self.confirm_close():
            event.accept()
        else:
            event.ignore()

    def confirm_close(self):
        message_box = QMessageBox()
        message_box.setWindowTitle("Ungespeicherte Änderungen")
        message_box.setText("Es gibt ungespeicherte Änderungen. Möchten sie speichern?")
        message_box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        message_box.setStyleSheet("""
    QMessageBox {
        background-color: rgb(31, 31, 31); /* Dark background for the message box */
        border: 2px solid rgb(65, 65, 65); /* Border around the message box */
        border-radius: 10px; /* Rounded corners */
        color: white; /* Text color */
    }

    /* Style the QLabel (main text in the box) */
    QMessageBox QLabel {
        color: white; /* Main text color */
        font: 14px "Segoe UI", sans-serif;
    }

    /* Style for the QPushButton within the QMessageBox */
    QMessageBox QPushButton {
        background-color: rgb(45, 45, 45); /* Button background */
        color: white; /* Button text color */
        border: 2px solid rgb(65, 65, 65); /* Button border */
        border-radius: 5px;
        padding: 5px 10px;
        font: 14px "Segoe UI", sans-serif;
    }

    QMessageBox QPushButton:hover {
        background-color: rgb(66, 65, 64); /* Background color on hover */
    }

    QMessageBox QPushButton:pressed {
        background-color: rgb(80, 80, 80); /* Darker color when pressed */
    }
""")
        reply = message_box.exec()
        
        if reply == QMessageBox.Save:
            self.save_analysis()
            return True
        elif reply == QMessageBox.Discard:
            return True
        else:
            return False

    @Property(str, notify=file_changed)
    def current_file(self):
        return self._current_file
    
    @current_file.setter
    def current_file(self, value):
        if self._current_file != value:
            self._current_file = value
            self.file_changed.emit(value)

    @Property(bool, notify=file_changes_made)
    def is_saved(self):
        return self._is_saved
    
    @is_saved.setter
    def is_saved(self, value):
        if self._is_saved != value:
            self._is_saved = value
            self.file_changes_made.emit(value)

    def set_saved_status(self, value):
        self.is_saved = value

    def toggle_play_button(self):
        with QSignalBlocker(self.playPauseButton): 
            self.playPauseButton.click()

    def open_video(self):
        file_name = QFileDialog.getOpenFileName(self, "Open file", "${HOME}", "Video files (*.mp4 *.mov)")[0]
        self.load_video(file_name)

    def load_video(self, file_name):
        if file_name:
            self.file_name = file_name
            self.remove_analysis()
            self.videoWidget.media_player.positionChanged.connect(self.position_changed)
            self.videoWidget.media_player.durationChanged.connect(self.duration_changed)
            self.videoWidget.load_video(QUrl.fromLocalFile(self.file_name))
            self.titleLabel.setText(os.path.basename(file_name).removesuffix('.mp4'))

            self.videoThumbnailsWidget.add_video(file_name)
            self.videoStack.setCurrentIndex(0)

    def save_analysis(self):

        if self.current_file is None:
            file_name = QFileDialog.getSaveFileName(self, "Save file", self.titleLabel.text(), "Analyse Dateien (*.analysis)")[0]
            if not file_name:
                return
            self.current_file = file_name
        else:
            file_name = self.current_file

        pickle.dump((self.file_name, TreeWidget.tree_item_list), open(file_name, 'wb'))
        self.is_saved = True

    def open_analysis(self):
        file_name = QFileDialog.getOpenFileName(self, "Open file", "${HOME}", "Analyse Dateien (*.analysis)")[0]
        self.load_analysis(file_name)

    def load_analysis(self, file_name):
        
        if not file_name:
            return

        video_file, tree_list = pickle.load(open(file_name, 'rb'))

        if os.path.exists(video_file):
            self.file_name = video_file
        else:
            QMessageBox.critical(self, "Error", f"Video URL not found")
            return
        
        self.load_video(self.file_name)

        self.current_file = file_name
        
        self.treeWidget.add_clips(tree_list)
        
        self.treeWidget.fit_tree()

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

        self.clipHandler.new_clip(self.clip_start, clip_stop)
        self.treeWidget.disable_clip_handler()
        self.clipHandler.setVisible(True)
        self.clipHandler.acceptButton.clicked.connect(lambda: self.add_clip(clip=self.clipHandler.clip))
        self.clipHandler.cancelButton.clicked.connect(self.disable_clip_handler)


    def add_clip(self, clip):
        self.treeWidget.add_clip(clip)
        self.treeWidget.fit_tree()
        self.is_saved = False
        self.disable_clip_handler()


    def disable_clip_handler(self):
        self.clipHandler.setVisible(False)
        self.clipHandler.acceptButton.clicked.disconnect()
        self.clipHandler.cancelButton.clicked.disconnect()

    def jump_to_clip(self):
        selected_item = self.treeWidget.currentItem()
        if not isinstance(selected_item, ClipTreeItem):
            return
        
        self.videoWidget.set_position(selected_item.clip_item.jump_point())

    def export(self, full_video=False):

        if full_video:
            selected_clips = self.treeWidget.get_top_level_items()
        else:
            selected_clips = self.treeWidget.selectedItems()
        if not selected_clips:
            QMessageBox.information(self, "Info", f"No Clips selected")
            return

        file_name = file_name = QFileDialog.getSaveFileName(self, "Save file", "Clips", "Video Datei (*.mp4)")[0]
        if not file_name:
            return

        clips = []

        for item in selected_clips:
            if item.is_category_item():
                for child in item.children():
                    clip = child.clip_item
                    if clip not in clips:
                        clips.append(clip)
            else:
                clip = item.clip_item
                if clip not in clips:
                    clips.append(clip)

        

        logger = ProgressLogger()
        video_creator = VideoCreator(clips, self.file_name, file_name, full_video, logger=logger)
        self.progressBar.setVisible(True)
        logger.progress_changed.connect(self.progressBar.setValue)
        logger.export_finished.connect(lambda: self.export_finished(file_name))

        try:
            video_creator.start()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    
    def export_finished(self, file_name):
        self.progressBar.setVisible(False)
        self.exportFinishedLabel.setVisible(True)
        self.openExportButton.setVisible(True)
        self.openExportButton.clicked.connect(lambda: self.open_file_explorer(file_name))
        self.export_timer.start(10000)


    def remove_analysis(self):
        self.treeWidget.remove_analysis()
        self.current_file = None

    def open_file_explorer(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            
            url = str(event.mimeData().urls()[0].toLocalFile()).lower()

            if url.endswith(".mp4") or url.endswith(".mov"):
                self.load_video(url)
            elif url.endswith(".analysis"):
                self.load_analysis(url)
        else:
            event.ignore()

    def position_changed(self, position):
        with QSignalBlocker(self.position_slider):
            self.position_slider.setTracking(True)
            self.position_slider.setSliderPosition(position)
            self.position_slider.update()
            self.position_slider.repaint()
        self.set_position_label(position)

    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)
        self.set_duration_label(duration)

    def set_position_label(self, position):
        self.position_label.setText(f"{milliseconds_to_hhmmss(position)}")
    
    def set_duration_label(self, duration):
        self.duration_label.setText(f"{milliseconds_to_hhmmss(duration)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

