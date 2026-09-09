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

        self._player: Playback | None = None

    @property
    def player(self) -> Playback:
        """The one player, backed by real media unless one was supplied."""
        if self._player is None:
            self.set_player(MediaPlayerPlayback(self))
        assert self._player is not None
        return self._player

    def set_player(self, player: Playback) -> None:
        """Render for a given Playback, so tests can supply a fake one."""
        self._player = player
        player.set_video_output(self.video_surface)
