from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt

from playback import MediaPlayerPlayback, Playback


class VideoWidget(QWidget):
    """Hosts the video surface of the one player.

    It owns its own layout and never touches its parent's. All playback
    control lives in the Playback seam it renders for.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAcceptDrops(True)

        self.video_surface = QVideoWidget(self)
        self.video_surface.setAspectRatioMode(Qt.KeepAspectRatioByExpanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_surface)

        self._playback: Playback | None = None
        self.set_playback(MediaPlayerPlayback(self))

    @property
    def playback(self) -> Playback:
        assert self._playback is not None
        return self._playback

    def set_playback(self, playback: Playback) -> None:
        """Render for another Playback, so tests can supply a fake one."""
        previous = self._playback
        if previous is not None:
            previous.unload()
            previous.set_video_output(None)
            previous.deleteLater()

        self._playback = playback
        playback.set_video_output(self.video_surface)
