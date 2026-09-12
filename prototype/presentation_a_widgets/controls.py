"""THROWAWAY PROTOTYPE A -- the small controls the tokens ask for.

Notably the playback-speed control, which must not be a stock ``QComboBox``:
in the captured evidence that one widget signals "default Qt" more loudly than
anything else in the window.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from . import fonts, icons, tokens


class IconButton(QToolButton):
    """An icon-only chrome button. Recolours by state through the SVG family."""

    def __init__(
        self,
        name: str,
        *,
        size: int = tokens.ICON_SIZE_DEFAULT,
        tooltip: str = "",
        button: int = 28,
        color: str = tokens.TEXT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._size = size
        self._color = color
        self.setIcon(icons.icon(name, color, size))
        self.setIconSize(QSize(size, size))
        self.setFixedSize(button, button)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        if tooltip:
            self.setToolTip(tooltip)

    def set_icon_name(self, name: str) -> None:
        if name == self._name:
            return
        self._name = name
        self.setIcon(icons.icon(name, self._color, self._size))


class JumpButton(IconButton):
    """The five-second jumps: a rotate icon carrying its own numeral.

    Drawn rather than composed from two widgets so the numeral sits optically
    inside the arrow, the way the reference does it.
    """

    def __init__(self, name: str, seconds: int, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self._seconds = seconds
        self._numeral_font = fonts.mono(9, tokens.WEIGHT_MEDIUM)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setFont(self._numeral_font)
        painter.setPen(QColor(tokens.TEXT if self.isEnabled() else tokens.TEXT_FAINT))
        painter.drawText(self.rect().adjusted(0, 2, 0, 0), Qt.AlignCenter, str(self._seconds))
        painter.end()


class PlayButton(IconButton):
    """Play/pause, rendered larger than its neighbours."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "play",
            size=tokens.ICON_SIZE_TRANSPORT,
            tooltip="Wiedergabe (Leertaste)",
            button=36,
            parent=parent,
        )

    def set_playing(self, playing: bool) -> None:
        self.set_icon_name("pause" if playing else "play")
        self.setToolTip("Pause (Leertaste)" if playing else "Wiedergabe (Leertaste)")


class SegmentedControl(QWidget):
    """Clips / Videos, as a segmented control rather than web-style tabs."""

    changed = Signal(int)

    def __init__(self, options: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for position, label in enumerate(options):
            button = QPushButton(label, self)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.NoFocus)
            button.setProperty(
                "segment", "left" if position == 0 else "right"
            )
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._group.addButton(button, position)
            layout.addWidget(button)

        self._group.idClicked.connect(self.changed.emit)
        self._group.button(0).setChecked(True)

    def set_current(self, position: int) -> None:
        button = self._group.button(position)
        if button is not None and not button.isChecked():
            button.setChecked(True)
            self.changed.emit(position)


class SpeedButton(QToolButton):
    """Playback speed as a menu button. Explicitly not a stock QComboBox."""

    rate_changed = Signal(float)

    RATES = (0.25, 0.5, 1.0, 1.5, 2.0)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rate = 1.0
        self.setPopupMode(QToolButton.InstantPopup)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(tokens.CONTROL_HEIGHT)
        self.setToolTip("Wiedergabegeschwindigkeit")

        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for rate in self.RATES:
            action = QAction(_rate_text(rate), menu)
            action.setCheckable(True)
            action.setChecked(rate == self._rate)
            action.triggered.connect(lambda _checked, value=rate: self._choose(value))
            group.addAction(action)
            menu.addAction(action)
        self.setMenu(menu)
        self._label_font = fonts.mono(tokens.SIZE_TIMECODE, tokens.WEIGHT_MEDIUM)
        self._update_width()

    def _choose(self, rate: float) -> None:
        self._rate = rate
        self._update_width()
        self.update()
        self.rate_changed.emit(rate)

    def _update_width(self) -> None:
        metrics = QFontMetrics(self._label_font)
        self.setFixedWidth(metrics.horizontalAdvance(_rate_text(self._rate)) + 34)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(0, 0, -1, -1)

        ground = tokens.CONTROL_HOVER if self.underMouse() else tokens.CONTROL
        painter.setPen(QColor(tokens.CONTROL_BORDER))
        painter.setBrush(QColor(ground))
        painter.drawRoundedRect(rect, tokens.RADIUS, tokens.RADIUS)

        painter.setFont(self._label_font)
        painter.setPen(QColor(tokens.TEXT))
        painter.drawText(
            rect.adjusted(9, 0, -20, 0),
            Qt.AlignVCenter | Qt.AlignLeft,
            _rate_text(self._rate),
        )
        size = 12
        painter.drawPixmap(
            QRect(rect.right() - 17, rect.center().y() - size // 2, size, size),
            icons.tinted("chevron-down", tokens.TEXT_MUTED, size),
        )
        painter.end()


def _rate_text(rate: float) -> str:
    return f"{rate:g}x"


def section_label(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setProperty("role", "section")
    return label


def timecode_label(text: str = "", *, muted: bool = False) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "timecodeMuted" if muted else "timecode")
    return label
