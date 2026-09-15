"""The presentation state QML reads, and the only place it can change it.

QML gets properties, signals and slots. It never sees an `Analysis`, a `Clip`
or the `Playback`, so a delegate cannot reach past the interface into the
domain, and every rule about what an action means — which playback rate is
selected, how a position is written down, what pressing play does while the
video surface is still being primed — stays here in Python where a test can
reach it without a window.

What this carries today is the transport and the video surface. The Clip list,
the timeline and the Clip editor arrive with the tickets that own them, each
extending this same seam.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

import timecode
from analysis import AnalysisDocument
from playback import Playback


#: The speeds the segmented control offers, in the order it draws them.
PLAYBACK_RATES = (0.5, 1.0, 1.5, 2.0)

#: The speed a Source video opens at, and the one an unrecognised rate reads as.
NORMAL_RATE = 1.0

#: How long the video surface is played for before being put back.
#:
#: Long enough that Qt's FFmpeg backend has decoded and presented a frame,
#: short enough that nobody sees the picture move. The prototype measured this
#: on macOS; it is a decoder warm-up rather than a wall-clock guarantee, and a
#: backend that needs longer shows its first frame late rather than never.
PRIMING_MS = 140

#: Schedules work for later. Injectable so that priming is testable as
#: behaviour rather than as a wait.
Schedule = Callable[[int, Callable[[], None]], None]


def _after(delay_ms: int, run: Callable[[], None]) -> None:
    QTimer.singleShot(delay_ms, run)


class WorkspaceViewModel(QObject):
    """One facade over the Analysis document and the playback of its video."""

    documentChanged = Signal()
    playbackChanged = Signal()

    def __init__(
        self,
        document: AnalysisDocument,
        playback: Playback,
        parent: QObject | None = None,
        *,
        schedule: Schedule = _after,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._playback = playback
        self._playback.setParent(self)
        self._schedule = schedule

        self._active_source_id: UUID | None = None
        self._position_ms = 0
        self._duration_ms = 0
        self._priming = False
        self._muted_before_priming = False

        self._playback.position_changed.connect(self._position_reported)
        self._playback.duration_changed.connect(self._duration_reported)
        self._playback.playing_changed.connect(self._playing_reported)

        sources = self._document.analysis.source_videos
        if sources:
            self._activate_source(sources[0].id)

    # --- What QML is allowed to see ---------------------------------------

    @Property(bool, notify=documentChanged)
    def hasVideo(self) -> bool:
        """Whether there is an Active Source video to act on at all."""

        return self._active_source_id is not None

    @Property(int, notify=playbackChanged)
    def positionMs(self) -> int:
        return self._position_ms

    @Property(int, notify=playbackChanged)
    def durationMs(self) -> int:
        return self._duration_ms

    @Property(str, notify=playbackChanged)
    def positionText(self) -> str:
        return timecode.clock(self._position_ms)

    @Property(str, notify=playbackChanged)
    def durationText(self) -> str:
        return timecode.clock(self._duration_ms)

    @Property(bool, notify=playbackChanged)
    def playing(self) -> bool:
        # Priming is a decoder detail. Reporting it would flicker the play
        # control on every newly opened Analysis.
        return False if self._priming else self._playback.is_playing()

    @Property(bool, notify=playbackChanged)
    def muted(self) -> bool:
        return self._muted_before_priming if self._priming else self._playback.is_muted()

    @Property(float, notify=playbackChanged)
    def volume(self) -> float:
        return self._playback.volume()

    @Property(float, notify=playbackChanged)
    def playbackRate(self) -> float:
        return self._playback.playback_rate()

    @Property(list, constant=True)
    def playbackRates(self) -> list:
        return [f"{rate:g}x" for rate in PLAYBACK_RATES]

    @Property(int, notify=playbackChanged)
    def playbackRateIndex(self) -> int:
        """Which speed is selected.

        Deciding that is not the segmented control's business: it draws
        whichever option this names.
        """

        rate = self._playback.playback_rate()
        for index, candidate in enumerate(PLAYBACK_RATES):
            if abs(candidate - rate) < 0.001:
                return index
        return PLAYBACK_RATES.index(NORMAL_RATE)

    # --- What QML is allowed to do ----------------------------------------

    @Slot(QObject)
    def attachVideoOutput(self, video_output: QObject) -> None:
        """Hand the Qt Quick video item to the existing playback seam.

        `Playback.set_video_output` already takes a plain `QObject`, and a
        `VideoOutput` carries the `videoSink` property `QMediaPlayer` looks
        for, so the Qt Quick surface attaches through the seam unmodified.
        """

        self._playback.set_video_output(video_output)

    @Slot()
    def playPause(self) -> None:
        if self._priming:
            # The analyst got there first. Keep the play that priming started
            # rather than pausing something they never saw start.
            self._end_priming()
            return
        self._playback.play_pause()

    @Slot()
    def stepForward(self) -> None:
        self._playback.step_forward()

    @Slot()
    def stepBackward(self) -> None:
        self._playback.step_backward()

    @Slot()
    def jumpForward(self) -> None:
        self._playback.jump_forward()

    @Slot()
    def jumpBackward(self) -> None:
        self._playback.jump_backward()

    @Slot(int)
    def seek(self, position_ms: int) -> None:
        self._playback.seek(int(position_ms))

    @Slot()
    def toggleMuted(self) -> None:
        self._playback.toggle_muted()
        self.playbackChanged.emit()

    @Slot(float)
    def setVolume(self, volume: float) -> None:
        """Set the level. Turning the bench audio down is not muting it."""

        self._playback.set_volume(float(volume))
        self.playbackChanged.emit()

    @Slot(int)
    def setRateIndex(self, index: int) -> None:
        if 0 <= index < len(PLAYBACK_RATES):
            self._playback.set_playback_rate(PLAYBACK_RATES[index])
            self.playbackChanged.emit()

    # --- The Active Source video ------------------------------------------

    def _activate_source(self, source_id: UUID) -> None:
        self._active_source_id = source_id
        video = self._document.analysis.source_video(source_id)
        self._playback.load(video.location)
        if video.duration_ms is not None:
            self._duration_reported(video.duration_ms)
        self._prime_video_surface()
        self.documentChanged.emit()

    def _prime_video_surface(self) -> None:
        """Make a newly loaded Source video show a frame instead of black.

        Qt's FFmpeg backend hands the video sink nothing until playback has
        actually started once: seeking a stopped player moves the position and
        decodes no frame, so an Analysis opens black until somebody presses
        play. The surface is therefore primed with a very short play and then
        put back exactly where it was — muted, because a blip of match audio
        is not a first frame, and without telling the interface, because a
        transport that flickered would be a second defect in place of the
        first.

        This is a property of `QMediaPlayer` rather than of QML — Qt Widgets
        meets it too — and it is done entirely through the public seam.
        """

        if self._priming or not self._playback.is_loaded():
            return
        self._priming = True
        self._muted_before_priming = self._playback.is_muted()
        self._playback.set_muted(True)
        self._playback.play()
        self._schedule(PRIMING_MS, self._finish_priming)

    def _finish_priming(self) -> None:
        if not self._priming:
            return
        resume_at = self._position_ms
        self._playback.pause()
        self._end_priming()
        self._playback.seek(resume_at)

    def _end_priming(self) -> None:
        """Stop priming and give the analyst back the sound they chose."""

        self._priming = False
        self._playback.set_muted(self._muted_before_priming)
        self.playbackChanged.emit()

    # --- What the player reports ------------------------------------------

    def _position_reported(self, position_ms: int) -> None:
        if self._priming:
            # The playhead does not move for a play nobody asked for.
            return
        self._position_ms = int(position_ms)
        self.playbackChanged.emit()

    def _duration_reported(self, duration_ms: int) -> None:
        """Trust the Analysis until the media reports something better."""

        if duration_ms <= 0:
            return
        self._duration_ms = int(duration_ms)
        self.playbackChanged.emit()

    def _playing_reported(self, _playing: bool) -> None:
        if self._priming:
            return
        self.playbackChanged.emit()
