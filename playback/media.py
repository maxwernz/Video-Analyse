from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from .player import Playback


class MediaPlayerPlayback(Playback):
    """Playback backed by QMediaPlayer.

    It owns the media objects only. The video surface belongs to whichever
    widget hosts it, so this constructs no layout and never reaches into the
    host's parent.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._media_player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.positionChanged.connect(
            lambda position: self.position_changed.emit(int(position))
        )
        self._media_player.durationChanged.connect(
            lambda duration: self.duration_changed.emit(int(duration))
        )
        self._media_player.playbackStateChanged.connect(self._playback_state_changed)
        self._media_player.seekableChanged.connect(
            lambda _seekable: self._apply_pending_seek()
        )

    def set_video_output(self, video_output: QObject | None) -> None:
        self._media_player.setVideoOutput(video_output)

    def load(self, location: str) -> None:
        self._forget_pending_seek()
        self._media_player.setSource(QUrl.fromLocalFile(location))

    def unload(self) -> None:
        self.pause()
        self._forget_pending_seek()
        self._media_player.stop()
        self._media_player.setSource(QUrl())

    def is_loaded(self) -> bool:
        return not self._media_player.source().isEmpty()

    def location(self) -> str | None:
        """Report where the media is in the platform's own path form.

        QUrl hands back forward slashes on every platform, which would make
        this disagree with FakePlayback about the same Source video.
        """
        source = self._media_player.source()
        return None if source.isEmpty() else str(Path(source.toLocalFile()))

    def position(self) -> int:
        return self._media_player.position()

    def duration(self) -> int:
        return self._media_player.duration()

    def _seek_to(self, position_ms: int) -> None:
        self._media_player.setPosition(position_ms)

    def _can_seek(self) -> bool:
        return self._media_player.isSeekable()

    def playback_rate(self) -> float:
        return self._media_player.playbackRate()

    def set_playback_rate(self, rate: float) -> None:
        self._media_player.setPlaybackRate(rate)

    def is_muted(self) -> bool:
        return self._audio_output.isMuted()

    def set_muted(self, muted: bool) -> None:
        self._audio_output.setMuted(muted)

    def _start_playing(self) -> None:
        self._media_player.play()

    def _stop_playing(self) -> None:
        self._media_player.pause()

    def _playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """Keep the reported state honest when the media stops on its own."""
        self._set_playing(state == QMediaPlayer.PlaybackState.PlayingState)
