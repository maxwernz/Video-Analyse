from PyQt5.QtWidgets import QSlider, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt

from util import milliseconds_to_hhmmss

class VideoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.setWindowTitle("Video Player App")
        self.setGeometry(100, 100, 800, 600)

        self.is_playing = False
        self.video_loaded = False
        self.current_speed = 1.0

        self.init_ui()

    def init_ui(self):
        # # Create a media player and video widget
        self.media_player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.media_player.setVideoOutput(self.video_widget)

        # # Create labels for time information
        self.time_label = QLabel("00:00:00 / 00:00:00")

        # # Create a progress bar for video position
        self.position_slider = QSlider(Qt.Orientation.Horizontal)  # Horizontal orientation
        self.position_slider.sliderMoved.connect(self.set_position)

        # # Create a layout for time label and position slider
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.position_slider)

        # # Create the main layout for the central widget
        main_layout = QVBoxLayout(self.parent())
        main_layout.addWidget(self.video_widget)
        main_layout.addLayout(time_layout)
        self.setLayout(main_layout)

    def get_position(self):
        return self.media_player.position()

    def play_pause_video(self):
        if not self.video_loaded:
            return
        if not self.is_playing:
            self.media_player.play()
            self.is_playing = True
            # self.timer.start(1000)  # Update every second
        else:
            self.is_playing = False
            self.media_player.pause()
            # self.timer.stop()

    def videoIsPlaying(self):
        return self.is_playing

    def pause_video(self):
        self.media_player.pause()
        self.is_playing = False

    def change_sound(self):
        self.media_player.setMuted(not self.media_player.isMuted())

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
        self.media_player.setMedia(QMediaContent(url))
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.video_loaded = True

    def set_position(self, position):
        self.media_player.setPosition(position)

    def position_changed(self, position):
        self.position_slider.setValue(position)
        self.set_time_label(position=position)

    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)
        self.set_time_label(duration=duration)

    def set_time_label(self, position=None, duration=None):
        if duration is None:
            duration = self.media_player.duration()
        str_duration = milliseconds_to_hhmmss(duration)
        if position is None:
            position = self.media_player.position()
        str_position = milliseconds_to_hhmmss(position)

        self.time_label.setText(f"{str_position} / {str_duration}")

    def move_backward(self):
        current_position = self.media_player.position()
        new_position = current_position - 100 * self.current_speed
        if new_position <= 0:
            new_position = 0
        self.set_position(new_position)

    def move_forward(self):
        current_position = self.media_player.position()
        new_position = current_position + 100 * self.current_speed
        if new_position >= self.media_player.duration():
            new_position = self.media_player.duration()
        self.set_position(new_position)

    def jump_forward(self):
        current_position = self.media_player.position()
        new_position = current_position + 5000 * self.current_speed
        if new_position >= self.media_player.duration():
            new_position = self.media_player.duration()
        
        self.set_position(new_position)

    def jump_backward(self):
        current_position = self.media_player.position()
        new_position = current_position - 5000 * self.current_speed
        if new_position <= 0:
            new_position = 0
        
        self.set_position(new_position)