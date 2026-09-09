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

    def load(self, location: str, duration_ms: int = 0) -> None:
        self._location = location
        self._position = 0
        self.set_duration(duration_ms)

    def unload(self) -> None:
        self.pause()
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

    def seek(self, position_ms: int) -> None:
        self._position = self._within_video(position_ms)
        self.position_changed.emit(self._position)

    def playback_rate(self) -> float:
        return self._rate

    def set_playback_rate(self, rate: float) -> None:
        self._rate = rate

    def is_muted(self) -> bool:
        return self._muted

    def set_muted(self, muted: bool) -> None:
        self._muted = muted

    def _start_playing(self) -> None:
        return None

    def _stop_playing(self) -> None:
        return None
