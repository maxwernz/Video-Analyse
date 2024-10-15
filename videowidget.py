from PySide6.QtWidgets import QSlider, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QSignalBlocker, Signal, QUrl

from util import milliseconds_to_hhmmss

class VideoWidget(QWidget):

    video_paused = Signal()

    def __init__(self, parent=None):
        super().__init__()

        self.setWindowTitle("Video Player App")
        self.setGeometry(100, 100, 800, 600)

        self.is_playing = False
        self.video_loaded = False
        self.current_speed = 1.0

        self.content = None
        self.setAcceptDrops(True)

        self.init_ui()

    def init_ui(self):
        # Create a media player and video widget
        self.media_player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Create labels for time information
        # self.position_label = QLabel("00:00:00")
        # self.position_label.setFixedWidth(65)
        # spacer_label = QLabel("/")
        # self.duration_label = QLabel("00:00:00")
        # self.duration_label.setFixedWidth(65)

        # Create a progress bar for video position
        # self.position_slider = QSlider(Qt.Orientation.Horizontal)  # Horizontal orientation
        # self.position_slider.sliderMoved.connect(self.set_position)

        # Create a layout for time label and position slider
        # time_layout = QHBoxLayout()
        # time_layout.addWidget(self.position_label)
        # time_layout.addWidget(spacer_label)
        # time_layout.addWidget(self.duration_label)
        # time_layout.addWidget(self.position_slider)

        # Create the main layout for the central widget
        main_layout = QVBoxLayout(self.parent())
        main_layout.addWidget(self.video_widget)
        # main_layout.addLayout(time_layout)
        self.setLayout(main_layout)

    def get_position(self):
        return self.media_player.position()

    def play_pause_video(self):
        if not self.video_loaded:
            return
        if not self.is_playing:
            self.media_player.play()
            self.is_playing = True
        else:
            self.is_playing = False
            self.media_player.pause()

    def videoIsPlaying(self):
        return self.is_playing

    def pause_video(self):
        self.is_playing = False
        self.media_player.pause()
        self.video_paused.emit()

    def play_video(self):
        self.media_player.play()
        self.is_playing = True

    def change_sound(self):
        self.audio_output.setMuted(not self.audio_output.isMuted())

    def change_speed(self, speed_text):
        if speed_text == "0.25x":
            self.current_speed = 0.25
        elif speed_text == "0.5x":
            self.current_speed = 0.5
        elif speed_text == "1x":
            self.current_speed = 1.0
        elif speed_text == "2x":
            self.current_speed = 2.0

        self.media_player.setPlaybackRate(self.current_speed)

    def load_video(self, url):
        self.content = QUrl(url)
        self.media_player.setSource(self.content)  # Updated for PySide6
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.video_loaded = True

    def new_content(self):
        self.media_player.setSource(self.content)  # Updated for PySide6
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.video_loaded = True

    def set_position(self, position):
        self.media_player.setPosition(position)

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

    def move_backward(self):
        if self.is_playing:
            self.pause_video()
        current_position = self.media_player.position()
        new_position = int(current_position - 100 * self.current_speed)
        if new_position <= 0:
            new_position = 0
        self.set_position(new_position)

    def move_forward(self):
        if self.is_playing:
            self.pause_video()
        current_position = self.media_player.position()
        new_position = int(current_position + 100 * self.current_speed)
        if new_position >= self.media_player.duration():
            new_position = self.media_player.duration()
        self.set_position(new_position)

    def jump_forward(self):
        current_position = self.media_player.position()
        new_position = int(current_position + 5000 * self.current_speed)
        if new_position >= self.media_player.duration():
            new_position = self.media_player.duration()

        self.set_position(new_position)
        

    def jump_backward(self):
        current_position = self.media_player.position()
        new_position = int(current_position - 5000 * self.current_speed)
        if new_position <= 0:
            new_position = 0
        
        self.set_position(new_position)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    from PySide6.QtCore import QUrl

    app = QApplication(sys.argv)

    main_window = QMainWindow()
    video_widget = VideoWidget()

    # Load a video from a URL (replace with a valid file URL for testing)
    # video_url = QUrl.fromLocalFile("/path/to/video.mp4")
    # video_widget.load_video(video_url)

    main_window.setCentralWidget(video_widget)
    main_window.resize(800, 600)
    main_window.show()

    sys.exit(app.exec())
