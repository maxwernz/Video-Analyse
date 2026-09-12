"""THROWAWAY PROTOTYPE A -- the compact timeline, custom painted.

ADR 0006 anatomy: 60px total, a 16px ruler over a 44px track, Clip ranges as
filled bars, a 2px accent playhead with a grabbable handle, a hover cursor line
and a timecode tooltip.

The static content -- ruler, ticks, labels, ranges -- is painted once into a
cached layer and blitted; only the playhead and the hover cursor are painted per
frame. That split is deliberate: a naive implementation repaints twelve ranges
and a full ruler on every position tick, and the question this prototype has to
answer is what the visual bar actually costs in paint work.
"""

from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QToolTip, QWidget

from analysis.model import Analysis, Clip

from . import fixture, fonts, tokens

# Candidate labelled intervals, in seconds. The first one wide enough to carry
# a label without crowding wins, so a 45-minute video and a 4-minute one both
# get a legible ruler.
_INTERVALS = (10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600)
_MINIMUM_LABEL_SPACING = 88

_HANDLE_WIDTH = 9
_HANDLE_HEIGHT = 10


class Timeline(QWidget):
    """One seek surface for the Active Source video."""

    scrubbed = Signal(int)
    clip_selected = Signal(UUID)
    clip_activated = Signal(UUID)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(tokens.TIMELINE_HEIGHT)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        self._analysis: Analysis | None = None
        self._source_video_id: UUID | None = None
        self._duration_ms = 0
        self._position_ms = 0
        self._selected_clip_id: UUID | None = None

        self._ranges: list[tuple[QRect, UUID]] = []
        self._static_layer: QPixmap | None = None
        self._hover_x: int | None = None
        self._dragging = False

        self._ruler_font = fonts.mono(tokens.SIZE_RULER_LABEL, tokens.WEIGHT_REGULAR)

    # ---------- state ----------

    def show_source_video(
        self,
        analysis: Analysis,
        source_video_id: UUID,
        duration_ms: int,
    ) -> None:
        self._analysis = analysis
        self._source_video_id = source_video_id
        self._duration_ms = max(0, duration_ms)
        self._invalidate_static_layer()

    def set_position(self, position_ms: int) -> None:
        if position_ms == self._position_ms:
            return
        self._position_ms = position_ms
        # Only the playhead moved, so the cached layer still stands.
        self.update()

    def set_duration(self, duration_ms: int) -> None:
        if duration_ms == self._duration_ms:
            return
        self._duration_ms = max(0, duration_ms)
        self._invalidate_static_layer()

    def set_selected_clip(self, clip_id: UUID | None) -> None:
        if clip_id == self._selected_clip_id:
            return
        self._selected_clip_id = clip_id
        self._invalidate_static_layer()

    def refresh(self) -> None:
        self._invalidate_static_layer()

    def _invalidate_static_layer(self) -> None:
        self._static_layer = None
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._invalidate_static_layer()

    # ---------- geometry ----------

    def _ruler_rect(self) -> QRect:
        return QRect(0, 0, self.width(), tokens.TIMELINE_RULER_HEIGHT)

    def _track_rect(self) -> QRect:
        return QRect(
            0,
            tokens.TIMELINE_RULER_HEIGHT,
            self.width(),
            tokens.TIMELINE_TRACK_HEIGHT,
        )

    def _x_for(self, position_ms: int) -> int:
        if self._duration_ms <= 0:
            return 0
        fraction = min(1.0, max(0.0, position_ms / self._duration_ms))
        return int(round(fraction * max(0, self.width() - 1)))

    def _position_for(self, x: int) -> int:
        if self._duration_ms <= 0 or self.width() <= 1:
            return 0
        fraction = min(1.0, max(0.0, x / (self.width() - 1)))
        return int(round(fraction * self._duration_ms))

    def _clips(self) -> tuple[Clip, ...]:
        if self._analysis is None or self._source_video_id is None:
            return ()
        return self._analysis.clips_of_source_video(self._source_video_id)

    def _category_color(self, clip: Clip) -> QColor:
        if self._analysis is None or clip.category_id is None:
            return QColor(tokens.TEXT_FAINT)
        return QColor(self._analysis.category(clip.category_id).color)

    # ---------- painting ----------

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        if self._static_layer is None:
            self._static_layer = self._build_static_layer()
        painter.drawPixmap(0, 0, self._static_layer)
        self._paint_hover(painter)
        self._paint_playhead(painter)
        painter.end()

    def _build_static_layer(self) -> QPixmap:
        ratio = self.devicePixelRatioF()
        layer = QPixmap(int(self.width() * ratio), int(self.height() * ratio))
        layer.setDevicePixelRatio(ratio)
        layer.fill(QColor(tokens.APP))

        painter = QPainter(layer)
        painter.setRenderHint(QPainter.Antialiasing, False)
        self._paint_track_ground(painter)
        self._paint_ruler(painter)
        self._paint_ranges(painter)
        painter.end()
        return layer

    def _paint_track_ground(self, painter: QPainter) -> None:
        track = self._track_rect()
        painter.fillRect(track, QColor(tokens.STAGE))
        painter.setPen(QPen(QColor(tokens.RULE), tokens.BORDER))
        painter.drawLine(0, track.top(), self.width(), track.top())

    def _paint_ruler(self, painter: QPainter) -> None:
        """Labelled minute marks at an adaptive interval, plus minor ticks."""
        if self._duration_ms <= 0:
            return
        ruler = self._ruler_rect()
        interval = self._label_interval_seconds()
        minor = max(1, interval // 5)

        painter.setFont(self._ruler_font)
        metrics = QFontMetrics(self._ruler_font)
        baseline = ruler.bottom() - 4

        minor_pen = QPen(QColor(tokens.RULE), tokens.BORDER)
        major_pen = QPen(QColor(tokens.TEXT_FAINT), tokens.BORDER)

        second = 0
        total_seconds = self._duration_ms // 1000
        while second <= total_seconds:
            x = self._x_for(second * 1000)
            if second % interval == 0:
                painter.setPen(major_pen)
                painter.drawLine(x, ruler.bottom() - 3, x, ruler.bottom())
                label = self._ruler_label(second)
                width = metrics.horizontalAdvance(label)
                # Keep the first and last labels inside the widget rather than
                # letting them hang off the ends.
                left = min(max(0, x - width // 2), self.width() - width)
                painter.drawText(QPoint(left, baseline), label)
            else:
                painter.setPen(minor_pen)
                painter.drawLine(x, ruler.bottom() - 2, x, ruler.bottom())
            second += minor

    def _label_interval_seconds(self) -> int:
        for interval in _INTERVALS:
            spacing = self._x_for(interval * 1000) - self._x_for(0)
            if spacing >= _MINIMUM_LABEL_SPACING:
                return interval
        return _INTERVALS[-1]

    def _ruler_label(self, second: int) -> str:
        minutes, seconds = divmod(second, 60)
        return f"{minutes}:{seconds:02d}"

    def _paint_ranges(self, painter: QPainter) -> None:
        """Clip ranges: 40% alpha fill, 1px full-colour top edge."""
        track = self._track_rect()
        top = track.top() + 1
        height = track.height() - 2
        self._ranges = []

        for clip in self._clips():
            start_x = self._x_for(clip.start_ms)
            end_x = self._x_for(clip.end_ms)
            width = max(tokens.RANGE_MINIMUM_WIDTH, end_x - start_x)
            rect = QRect(start_x, top, width, height)
            self._ranges.append((rect, clip.id))

            color = self._category_color(clip)
            fill = QColor(color)
            fill.setAlphaF(tokens.RANGE_FILL_ALPHA)
            painter.fillRect(rect, fill)
            painter.fillRect(QRect(rect.left(), rect.top(), rect.width(), 1), color)

            if clip.id == self._selected_clip_id:
                self._paint_selected_range(painter, rect, color)

    def _paint_selected_range(
        self,
        painter: QPainter,
        rect: QRect,
        color: QColor,
    ) -> None:
        """Emphasis without relying on colour: brighter fill plus an outline."""
        brighter = QColor(color)
        brighter.setAlphaF(0.68)
        painter.fillRect(rect, brighter)
        painter.setPen(QPen(QColor(tokens.TEXT), tokens.BORDER))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

    def _paint_hover(self, painter: QPainter) -> None:
        if self._hover_x is None or self._dragging:
            return
        painter.setPen(QPen(QColor(tokens.TEXT_MUTED), tokens.BORDER))
        track = self._track_rect()
        painter.drawLine(self._hover_x, track.top(), self._hover_x, track.bottom())

    def _paint_playhead(self, painter: QPainter) -> None:
        if self._duration_ms <= 0:
            return
        x = self._x_for(self._position_ms)
        accent = QColor(tokens.ACCENT)

        painter.fillRect(
            QRect(
                x - tokens.PLAYHEAD_WIDTH // 2,
                0,
                tokens.PLAYHEAD_WIDTH,
                self.height(),
            ),
            accent,
        )
        # The grabbable handle sits at the ruler, where the pointer expects it.
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(self._handle_rect(x), 2, 2)
        painter.setRenderHint(QPainter.Antialiasing, False)

    def _handle_rect(self, x: int) -> QRect:
        return QRect(
            x - _HANDLE_WIDTH // 2,
            0,
            _HANDLE_WIDTH,
            _HANDLE_HEIGHT,
        )

    # ---------- interaction ----------

    def _clip_at(self, x: int, y: int) -> UUID | None:
        point = QPoint(x, y)
        for rect, clip_id in reversed(self._ranges):
            if rect.contains(point):
                return clip_id
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        if event.button() != Qt.LeftButton:
            return
        position = event.position().toPoint()
        self._dragging = True
        self._hover_x = None

        # Clicking a range selects that Clip; it still scrubs, because the
        # timeline is the one seek surface and a click on it always means "go
        # there" (ADR 0006).
        clip_id = self._clip_at(position.x(), position.y())
        if clip_id is not None:
            self.clip_selected.emit(clip_id)
        self.scrubbed.emit(self._position_for(position.x()))
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        position = event.position().toPoint()
        if self._dragging:
            self.scrubbed.emit(self._position_for(position.x()))
            self.update()
            return
        self._hover_x = position.x()
        QToolTip.showText(
            event.globalPosition().toPoint(),
            fixture.timecode(self._position_for(position.x())),
            self,
        )
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt naming
        self._dragging = False
        self._hover_x = event.position().toPoint().x()
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        position = event.position().toPoint()
        clip_id = self._clip_at(position.x(), position.y())
        if clip_id is not None:
            self.clip_activated.emit(clip_id)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._hover_x = None
        QToolTip.hideText()
        self.update()
