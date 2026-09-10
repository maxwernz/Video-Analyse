"""THROWAWAY PROTOTYPE A -- the 56px transport.

One row: volume left, a single centred cluster with play/pause rendered larger
than its neighbours, and speed, the one accent primary action and the timecode
pinned right. Elapsed and total live here rather than in the timeline's ends,
because the ruler now carries time.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from . import controls, fixture, fonts, icons, tokens


class Transport(QWidget):
    play_pause_requested = Signal()
    step_back_requested = Signal()
    step_forward_requested = Signal()
    jump_back_requested = Signal()
    jump_forward_requested = Signal()
    mute_toggled = Signal()
    rate_changed = Signal(float)
    mark_clip_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Transport")
        self.setFixedHeight(tokens.TRANSPORT_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(tokens.CONTROL_GAP, 0, tokens.GUTTER, 0)
        layout.setSpacing(tokens.CONTROL_GAP)

        self._volume = controls.IconButton("volume", tooltip="Ton stummschalten", parent=self)
        self._volume.clicked.connect(self.mute_toggled.emit)
        layout.addWidget(self._volume)
        layout.addStretch(1)

        cluster = QWidget(self)
        cluster_layout = QHBoxLayout(cluster)
        cluster_layout.setContentsMargins(0, 0, 0, 0)
        cluster_layout.setSpacing(6)

        step_back = controls.IconButton(
            "step-back", tooltip="Ein Stück zurück", parent=cluster
        )
        step_back.clicked.connect(self.step_back_requested.emit)

        jump_back = controls.JumpButton(
            "rotate-ccw", 5, tooltip="Fünf Sekunden zurück", parent=cluster
        )
        jump_back.clicked.connect(self.jump_back_requested.emit)

        self._play = controls.PlayButton(cluster)
        self._play.clicked.connect(self.play_pause_requested.emit)

        jump_forward = controls.JumpButton(
            "rotate-cw", 5, tooltip="Fünf Sekunden vor", parent=cluster
        )
        jump_forward.clicked.connect(self.jump_forward_requested.emit)

        step_forward = controls.IconButton(
            "step-forward", tooltip="Ein Stück vor", parent=cluster
        )
        step_forward.clicked.connect(self.step_forward_requested.emit)

        for widget in (step_back, jump_back, self._play, jump_forward, step_forward):
            cluster_layout.addWidget(widget)
        layout.addWidget(cluster)

        layout.addStretch(1)

        self._speed = controls.SpeedButton(self)
        self._speed.rate_changed.connect(self.rate_changed.emit)
        layout.addWidget(self._speed)

        mark = QPushButton("Clip markieren", self)
        mark.setProperty("kind", "primary")
        mark.setIcon(icons.icon("scissors", tokens.ACCENT_ON, tokens.ICON_SIZE_DEFAULT))
        mark.setCursor(Qt.PointingHandCursor)
        mark.setToolTip("Clip markieren (R)")
        mark.clicked.connect(self.mark_clip_requested.emit)
        layout.addWidget(mark)
        self._mark = mark

        self._elapsed = controls.timecode_label("00:00:00")
        self._separator = controls.timecode_label("/", muted=True)
        self._total = controls.timecode_label("00:00:00", muted=True)
        for widget in (self._elapsed, self._separator, self._total):
            layout.addWidget(widget)
        layout.setSpacing(tokens.CONTROL_GAP)

    def set_position(self, position_ms: int) -> None:
        self._elapsed.setText(fixture.timecode(position_ms))

    def set_duration(self, duration_ms: int) -> None:
        self._total.setText(fixture.timecode(duration_ms))

    def set_playing(self, playing: bool) -> None:
        self._play.set_playing(playing)

    def set_muted(self, muted: bool) -> None:
        self._volume.set_icon_name("volume-x" if muted else "volume")

    def set_mark_visible(self, visible: bool) -> None:
        """Hidden while a Clip is being edited.

        The accent is reserved for one primary action, and in the editing
        state that action is 'Clip sichern' in the form.
        """
        self._mark.setVisible(visible)
