from __future__ import annotations

from .player import Playback


class FakePlayback(Playback):
    """In-memory Playback so controller tests never need real media."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._location: str | None = None
        self._position = 0
        self._duration = 0
        self._rate = 1.0
        self._muted = False
        self._seekable = True

    def load(self, location: str) -> None:
        self._forget_pending_seek()
        self._location = location
        self._position = 0
        self.set_duration(0)

    def unload(self) -> None:
        self.pause()
        self._forget_pending_seek()
        self._location = None
        self._position = 0
        self.set_duration(0)

    def is_loaded(self) -> bool:
        return self._location is not None

    def location(self) -> str | None:
        return self._location

    def position(self) -> int:
        return self._position

    def duration(self) -> int:
        return self._duration

    def set_duration(self, duration_ms: int) -> None:
        """Stand in for the media announcing its duration once it is ready."""
        self._duration = duration_ms
        self.duration_changed.emit(duration_ms)

    def set_seekable(self, seekable: bool) -> None:
        """Stand in for media that cannot take a position until it loads."""
        self._seekable = seekable
        if seekable:
            self._apply_pending_seek()

    def playback_rate(self) -> float:
        return self._rate

    def set_playback_rate(self, rate: float) -> None:
        self._rate = rate

    def is_muted(self) -> bool:
        return self._muted

    def set_muted(self, muted: bool) -> None:
        self._muted = muted

    def _seek_to(self, position_ms: int) -> None:
        self._position = position_ms
        self.position_changed.emit(self._position)

    def _can_seek(self) -> bool:
        return self._seekable

    def _start_playing(self) -> None:
        return None

    def _stop_playing(self) -> None:
        return None
