import sys
from PyQt5.QtWidgets import QApplication, QFileDialog, QPushButton, QSlider, QComboBox, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtCore import Qt

class VideoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.setWindowTitle("Video Player App")
        self.setGeometry(100, 100, 800, 600)

        self.is_playing = False
        self.video_loaded = False

        self.init_ui()

    def init_ui(self):
        # # Create a media player and video widget
        self.media_player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.media_player.setVideoOutput(self.video_widget)

        # # Create buttons for play, pause, forward, and backward
        # self.play_button = QPushButton("Play")
        # self.play_button.clicked.connect(self.play_video)
        # self.pause_button = QPushButton("Pause")
        # self.pause_button.clicked.connect(self.pause_video)
        # self.forward_button = QPushButton("Forward")
        # self.forward_button.clicked.connect(self.forward_video)
        # self.backward_button = QPushButton("Backward")
        # self.backward_button.clicked.connect(self.backward_video)

        # # Create a combo box for adjusting playback speed
        # self.speed_combobox = QComboBox()
        # self.speed_combobox.addItems(["0.5x", "1x", "2x", "4x", "8x"])
        # self.speed_combobox.setCurrentText("1x")
        # self.speed_combobox.activated.connect(self.change_speed)

        # # Create a "Load Video" button
        # self.load_button = QPushButton("Load Video")
        # self.load_button.clicked.connect(self.load_video)

        # # Create labels for time information
        # self.time_label = QLabel("Time: 00:00 / 00:00")

        # # Create a progress bar for video position
        self.position_slider = QSlider(Qt.Orientation.Horizontal)  # Horizontal orientation
        self.position_slider.sliderMoved.connect(self.set_position)

        # # Create a layout for buttons and combo box
        # control_layout = QHBoxLayout()
        # control_layout.addWidget(self.load_button)
        # control_layout.addWidget(self.play_button)
        # control_layout.addWidget(self.pause_button)
        # control_layout.addWidget(self.forward_button)
        # control_layout.addWidget(self.backward_button)
        # control_layout.addWidget(self.speed_combobox)

        # # Create a layout for time label and position slider
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.position_slider)

        # # Create a central widget and set the video widget as the central widget
        # central_widget = QWidget(self)
        # self.setCentralWidget(central_widget)

        # # Create the main layout for the central widget
        main_layout = QVBoxLayout(self.parent())
        main_layout.addWidget(self.video_widget)
        # main_layout.addLayout(control_layout)
        main_layout.addLayout(time_layout)
        self.setLayout(main_layout)

        # # Create a timer to update position and time label
        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self.update_position_and_time)

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

    # def forward_video(self):
    #     self.media_player.setPosition(self.media_player.position() + 1000)  # Advance 1 second

    # def backward_video(self):
    #     self.media_player.setPosition(self.media_player.position() - 1000)  # Rewind 1 second

    # def change_speed(self):
    #     speed_text = self.speed_combobox.currentText()
    #     if speed_text == "0.5x":
    #         speed = 0.5
    #     elif speed_text == "1x":
    #         speed = 1.0
    #     elif speed_text == "2x":
    #         speed = 2.0
    #     elif speed_text == "4x":
    #         speed = 4.0
    #     elif speed_text == "8x":
    #         speed = 8.0

    #     self.media_player.setPlaybackRate(speed)

    # def update_position_and_time(self):
    #     position = self.media_player.position()
    #     duration = self.media_player.duration()
    #     print(duration)
    #     position_str = self.format_time(position)
    #     duration_str = self.format_time(duration)
        # time_info = f"Time: {position_str} / {duration_str}"
        # self.time_label.setText(time_info)
    #     if duration > 0:
    #         self.position_slider.setValue((position / duration) * 1000)

    # def format_time(self, milliseconds):
    #     seconds = int((milliseconds / 1000) % 60)
    #     minutes = int((milliseconds / (1000 * 60)) % 60)
    #     return f"{minutes:02d}:{seconds:02d}"

    def load_video(self, url):
        self.media_player.setMedia(QMediaContent(url))
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.video_loaded = True

    def set_position(self, position):
        # position = self.position_slider.value()
        # duration = self.media_player.duration()
        # position_ms = (position / 1000) * duration
        self.media_player.setPosition(position)

    def position_changed(self, position):
        self.position_slider.setValue(position)

    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)