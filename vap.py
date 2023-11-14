import sys
import os
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QShortcut, QMessageBox
from PyQt5.QtCore import QUrl, Qt, QSignalBlocker
from PyQt5.QtGui import QKeySequence
from Ui_main_window import Ui_MainWindow
from clip_handler import CreateClip
from treewidget_item import ClipTreeItem
import pickle
import threading
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
from treewidget import TreeWidget

basedir = os.path.dirname(__file__)

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.add_icons()

        self.actionLoad_Video.triggered.connect(self.open_video)
        self.actionAnalyse_speichern.triggered.connect(self.save_analysis)
        self.actionAnalyse_laden.triggered.connect(self.open_analysis)
        self.actionClips_Exportieren.triggered.connect(self.export_selected_clips)
        self.actionAnalyse_entfernen.triggered.connect(self.remove_analysis)
        
        self.setup_connections()
        self.setup_shortcuts()

        self.setAcceptDrops(True)

        self.clip_start = None
        self.file_name = None

    def add_icons(self):
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(os.path.join(basedir, "icons/mute.svg")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon.addPixmap(QtGui.QPixmap(os.path.join(basedir, "icons/sound.svg")), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.soundButton.setIcon(icon)
        self.soundButton.setIconSize(QtCore.QSize(20, 20))

        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(os.path.join(basedir, "icons/backward.svg")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.backwardButton.setIcon(icon1)
        self.backwardButton.setIconSize(QtCore.QSize(20, 20))

        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(os.path.join(basedir, "icons/play.svg")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon2.addPixmap(QtGui.QPixmap(os.path.join(basedir, "icons/pause.svg")), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.playPauseButton.setIcon(icon2)
        self.playPauseButton.setIconSize(QtCore.QSize(20, 20))

        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(os.path.join(basedir, "icons/forward.svg")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.forwardButton.setIcon(icon3)
        self.forwardButton.setIconSize(QtCore.QSize(20, 20))

        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(os.path.join(basedir, "icons/record.svg")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon4.addPixmap(QtGui.QPixmap(os.path.join(basedir, "icons/record_action.svg")), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.clipButton.setIcon(icon4)
        self.clipButton.setIconSize(QtCore.QSize(20, 20))

    def setup_connections(self):
        self.playPauseButton.clicked.connect(self.videoWidget.play_pause_video)
        self.videoWidget.video_paused.connect(self.toggle_play_button)
        self.soundButton.clicked.connect(self.videoWidget.change_sound)
        self.forwardButton.clicked.connect(self.videoWidget.jump_forward)
        self.backwardButton.clicked.connect(self.videoWidget.jump_backward)
        self.clipButton.toggled.connect(lambda recording: self.clip_started() if recording else self.clip_stopped())
        self.speedBox.currentIndexChanged.connect(lambda: self.videoWidget.change_speed(self.speedBox.currentText()))
        self.treeWidget.itemClicked.connect(self.jump_to_clip)
        self.treeWidget.export_clips.connect(self.export_selected_clips)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(self.videoWidget.move_forward)
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(self.videoWidget.move_backward)
        QShortcut(QKeySequence(Qt.Key_Up), self).activated.connect(self.change_speed_up)
        QShortcut(QKeySequence(Qt.Key_Down), self).activated.connect(self.change_speed_down)
        QShortcut(QKeySequence.Close, self).activated.connect(self.close)

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
            self.videoWidget.load_video(QUrl.fromLocalFile(self.file_name))
            self.titleLabel.setText(os.path.basename(file_name).removesuffix('.mp4'))

    def save_analysis(self):

        file_name = QFileDialog.getSaveFileName(self, "Save file", "Spielanalyse", "Analyse Dateien (*.analysis)")[0]
        if not file_name:
            return
        pickle.dump((self.file_name, TreeWidget.tree_item_list), open(file_name, 'wb'))

    def open_analysis(self):
        file_name = QFileDialog.getOpenFileName(self, "Open file", "${HOME}", "Analyse Dateien (*.analysis)")[0]
        self.load_analysis(file_name)

    def load_analysis(self, file_name):
        
        if not file_name:
            return

        file_name, tree_list = pickle.load(open(file_name, 'rb'))

        if os.path.exists(file_name):
            self.file_name = file_name
        else:
            QMessageBox.critical(self, "Error", f"Video URL not found")
            return
        
        self.load_video(self.file_name)
        
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
        clip_handler = CreateClip(self.clip_start, clip_stop)
        try:
            if clip_handler.exec():
                clip = clip_handler.clip
                self.treeWidget.add_clip(clip)
                self.treeWidget.fit_tree()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def jump_to_clip(self):
        selected_item = self.treeWidget.currentItem()
        if not isinstance(selected_item, ClipTreeItem):
            return
        
        self.videoWidget.set_position(selected_item.clip_item.jump_point())

    def export_selected_clips(self):

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

        def create_category_clip(category, size=(640, 480)):
            text_clip = TextClip(category, fontsize=150, color="white", size=size).set_duration(1.5)
            return CompositeVideoClip([text_clip])

        # Funktion, um die Videoverarbeitung in einem separaten Thread auszuführen
        def process_video():
            video = VideoFileClip(self.file_name)
            # clip_segments.sort(key=lambda t: t[0])
            size = video.size

            category = clips[0].category
            subclips = [create_category_clip(category, size)]
            for i, clip in enumerate(clips):
                clip_category = clip.category
                if clip_category != category:
                    category = clip_category
                    subclips.append(create_category_clip(category, size))
                
                start_time, end_time = clip.clip_times_s()
                video_clip = video.subclip(start_time, end_time)
                text_clip = TextClip(f"{i+1}", fontsize=100, color="white").set_position((50, 50)).set_duration(end_time - start_time)
                subclips.append(CompositeVideoClip([video_clip, text_clip]))

            combined_video = concatenate_videoclips(subclips)
            combined_video.write_videofile(file_name, logger=None, audio=False, threads=4)

        # Einen separaten Thread erstellen und starten
        video_thread = threading.Thread(target=process_video)
        video_thread.start()

    def export_video(self):
        

    def remove_analysis(self):
        self.treeWidget.remove_analysis()

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
            
            url = str(event.mimeData().urls()[0].toLocalFile())

            if url.endswith(".mp4"):
                self.load_video(url)
            elif url.endswith(".analysis"):
                self.load_analysis(url)
        else:
            event.ignore()

        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # window.load_video("/Users/max/Downloads/Buchen.mp4")
    window.load_analysis("/Users/max/Downloads/Buchen.analysis")
    app.exec()



