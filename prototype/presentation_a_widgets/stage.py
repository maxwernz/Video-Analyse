"""THROWAWAY PROTOTYPE A -- the video stage and the designed empty state.

The stage is the darkest surface in the window so the frame is the brightest
thing on screen. The empty state is a designed drop target rather than the flat
black rectangle the shipped interface shows.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import fonts, icons, tokens


class StageView(QWidget):
    """Shows the Active Source video, or a decoded poster frame when faked."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StageHost")
        self.setAutoFillBackground(True)
        self._poster: QPixmap | None = None
        self._surface: QWidget | None = None

    def set_poster(self, path: Path | None) -> None:
        if path is not None and path.exists():
            self._poster = QPixmap(str(path))
        else:
            self._poster = None
        self.update()

    def set_surface(self, surface: QWidget | None) -> None:
        """Host a real video surface, which then owns the whole stage."""
        self._surface = surface
        if surface is not None:
            surface.setParent(self)
            surface.setGeometry(self.rect())
            surface.show()
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        if self._surface is not None:
            self._surface.setGeometry(self.rect())

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(tokens.STAGE))
        if self._surface is not None or self._poster is None:
            painter.end()
            return
        # Letterbox the frame; the stage ground shows through the bars.
        scaled = self._poster.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        painter.drawPixmap(
            (self.width() - scaled.width()) // 2,
            (self.height() - scaled.height()) // 2,
            scaled,
        )
        painter.end()


class EmptyStage(QWidget):
    """The designed drop target for an Analysis with no Source videos."""

    add_requested = Signal()

    ZONE_WIDTH = 520
    ZONE_HEIGHT = 260

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StageHost")
        self.setAcceptDrops(True)

        icon = QLabel(self)
        icon.setPixmap(icons.tinted("film", tokens.TEXT_FAINT, 40))
        icon.setAlignment(Qt.AlignCenter)

        heading = QLabel("Video hinzufügen", self)
        heading.setFont(fonts.ui(tokens.SIZE_DOCUMENT_TITLE, tokens.WEIGHT_MEDIUM))
        heading.setAlignment(Qt.AlignCenter)

        hint = QLabel("Video hierher ziehen oder auswählen", self)
        hint.setProperty("role", "muted")
        hint.setAlignment(Qt.AlignCenter)

        button = QPushButton("Video auswählen", self)
        button.setProperty("kind", "primary")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self.add_requested.emit)

        shortcut = QLabel("⌘O", self)
        shortcut.setProperty("role", "faint")
        shortcut.setFont(fonts.mono(tokens.SIZE_SECTION_LABEL, tokens.WEIGHT_REGULAR))
        shortcut.setAlignment(Qt.AlignCenter)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(button)
        buttons.addStretch(1)

        column = QVBoxLayout()
        column.setSpacing(0)
        column.addWidget(icon)
        column.addSpacing(18)
        column.addWidget(heading)
        column.addSpacing(6)
        column.addWidget(hint)
        column.addSpacing(20)
        column.addLayout(buttons)
        column.addSpacing(12)
        column.addWidget(shortcut)

        outer = QVBoxLayout(self)
        outer.addStretch(1)
        outer.addLayout(column)
        outer.addStretch(1)

    def _zone(self) -> QRect:
        return QRect(
            (self.width() - self.ZONE_WIDTH) // 2,
            (self.height() - self.ZONE_HEIGHT) // 2,
            self.ZONE_WIDTH,
            self.ZONE_HEIGHT,
        )

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(tokens.STAGE))
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(tokens.CONTROL_BORDER), tokens.BORDER)
        pen.setStyle(Qt.DashLine)
        pen.setDashPattern([4, 4])
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self._zone(), tokens.RADIUS, tokens.RADIUS)
        painter.end()
