from __future__ import annotations

from PySide6.QtCore import QObject, Signal

STEP_INTERVAL_MS = 100
"""Fine stepping distance; deliberately independent of the playback rate."""

JUMP_INTERVAL_MS = 5_000
"""Coarse jump distance, likewise independent of the playback rate."""


class Playback(QObject):
    """Controls the one player showing the Active Source video.

    Playback is transient presentation state: nothing here ever reaches an
    Analysis file or marks an Analysis document dirty. Implementations supply
    the device operations; the shared state machine here keeps every entry
    point reporting the same way.
    """

    position_changed = Signal(int)
    duration_changed = Signal(int)
    playing_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._playing = False
        self._pending_seek: int | None = None

    # Implemented by concrete playback

    def load(self, location: str) -> None:
        raise NotImplementedError

    def unload(self) -> None:
        raise NotImplementedError

    def is_loaded(self) -> bool:
        raise NotImplementedError

    def location(self) -> str | None:
        """Where the Active Source video is being played from, if any."""
        raise NotImplementedError

    def set_video_output(self, video_output: QObject | None) -> None:
        """Render into a surface the host owns. Ignored where there is none."""
        return None

    def position(self) -> int:
        raise NotImplementedError

    def duration(self) -> int:
        raise NotImplementedError

    def playback_rate(self) -> float:
        raise NotImplementedError

    def set_playback_rate(self, rate: float) -> None:
        raise NotImplementedError

    def _seek_to(self, position_ms: int) -> None:
        raise NotImplementedError

    def _can_seek(self) -> bool:
        """Whether the media will accept a position right now."""
        return True

    def _start_playing(self) -> None:
        raise NotImplementedError

    def _stop_playing(self) -> None:
        raise NotImplementedError

    # Shared playback control

    def is_playing(self) -> bool:
        return self._playing

    def play(self) -> None:
        if self._playing or not self.is_loaded():
            return
        self._start_playing()
        self._set_playing(True)

    def pause(self) -> None:
        if not self._playing:
            return
        self._stop_playing()
        self._set_playing(False)

    def play_pause(self) -> None:
        self.pause() if self._playing else self.play()

    def seek(self, position_ms: int) -> None:
        """Move the playhead, holding the seek until the media can take it.

        Media that is still loading discards a position, so navigating to a
        Clip straight after its Source video is activated would otherwise be
        lost.
        """
        position = self._within_video(position_ms)
        if self._can_seek():
            self._pending_seek = None
            self._seek_to(position)
        else:
            self._pending_seek = position

    def step_forward(self) -> None:
        self._step_by(STEP_INTERVAL_MS)

    def step_backward(self) -> None:
        self._step_by(-STEP_INTERVAL_MS)

    def jump_forward(self) -> None:
        self.seek(self.position() + JUMP_INTERVAL_MS)

    def jump_backward(self) -> None:
        self.seek(self.position() - JUMP_INTERVAL_MS)

    def _step_by(self, interval_ms: int) -> None:
        """Step a fixed distance, so precision does not depend on the rate."""
        self.pause()
        self.seek(self.position() + interval_ms)

    def _apply_pending_seek(self) -> None:
        """Make the held seek once the media became able to take it."""
        if self._pending_seek is None or not self._can_seek():
            return
        position = self._pending_seek
        self._pending_seek = None
        self._seek_to(self._within_video(position))

    def _forget_pending_seek(self) -> None:
        """A seek belongs to the Source video it was made against."""
        self._pending_seek = None

    def _within_video(self, position_ms: int) -> int:
        """Clamp to the Source video, tolerating a duration not yet known."""
        duration = self.duration()
        if duration > 0:
            position_ms = min(position_ms, duration)
        return max(0, position_ms)

    def is_muted(self) -> bool:
        raise NotImplementedError

    def set_muted(self, muted: bool) -> None:
        raise NotImplementedError

    def toggle_muted(self) -> None:
        self.set_muted(not self.is_muted())

    def _set_playing(self, playing: bool) -> None:
        if self._playing != playing:
            self._playing = playing
            self.playing_changed.emit(playing)
