"""The one compact timeline beneath the video.

ADR 0006 gives the workspace exactly one seek surface: a compact strip scoped
to the Active Source video, carrying the playhead and that video's Clip ranges
on its own time scale. This module is that strip. It knows nothing about the
Analysis: the controller hands it the ranges to show and listens to what the
person did with them, so nothing here can reach the model.

Every position it reports is transient presentation state, exactly like the
playback position it draws.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from visual_system import (
    ACCENT_BRIGHT,
    SURFACE_ACTIVE,
    TEXT,
    TEXT_MUTED,
    muted_category_color,
)

TIMELINE_HEIGHT = 26

MINIMUM_RANGE_WIDTH = 3
"""How narrow a Clip range may get before it stops being worth drawing.

A ninety-minute Source video across a twelve-hundred-pixel timeline is about
four and a half seconds per pixel, so without a floor a short Clip would be
neither visible nor clickable.
"""

RANGE_HEIGHT = 10
SELECTED_RANGE_HEIGHT = 18
PLAYHEAD_WIDTH = 2

TRACK = SURFACE_ACTIVE
UNCATEGORIZED_RANGE = TEXT_MUTED


@dataclass(frozen=True, slots=True)
class RangeAppearance:
    """How the timeline draws one Clip range."""

    fill: QColor
    outlined: bool
    height: int


@dataclass(frozen=True, slots=True)
class TimelineRange:
    """One Clip of the Active Source video, as the timeline needs to draw it."""

    clip_id: UUID
    start_ms: int
    end_ms: int
    color: str | None = None


class Timeline(QWidget):
    """The playhead and the Clip ranges of the Active Source video."""

    scrubbed = Signal(int)
    clip_selected = Signal(object)
    clip_activated = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(TIMELINE_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._duration_ms = 0
        self._position_ms = 0
        self._ranges: tuple[TimelineRange, ...] = ()
        self._selected_clip_id: UUID | None = None

    # --- What the controller tells the timeline ----------------------------

    def set_duration(self, duration_ms: int) -> None:
        self._duration_ms = max(0, duration_ms)
        self.update()

    def set_position(self, position_ms: int) -> None:
        self._position_ms = max(0, position_ms)
        self.update()

    def show_ranges(self, ranges: Iterable[TimelineRange]) -> None:
        """Show the Clip ranges of the Active Source video, and no others.

        A selection belongs to the Source video it was made on, so a different
        set of ranges arrives with nothing selected.
        """
        self._ranges = tuple(ranges)
        self._selected_clip_id = None
        self.update()

    def set_selected_clip(self, clip_id: UUID | None) -> None:
        self._selected_clip_id = clip_id
        self.update()

    def selected_clip(self) -> UUID | None:
        return self._selected_clip_id

    # --- Time and pixels ---------------------------------------------------

    def time_at(self, x: int) -> int:
        """The time the given pixel column stands for."""
        if self._duration_ms <= 0 or self.width() <= 0:
            return 0
        return _clamp(int(x * self._duration_ms / self.width()), 0, self._duration_ms)

    def x_at(self, position_ms: int) -> int:
        """The pixel column the given time falls in."""
        if self._duration_ms <= 0 or self.width() <= 0:
            return 0
        return _clamp(
            int(position_ms * self.width() / self._duration_ms),
            0,
            self.width() - 1,
        )

    def range_geometry(self, clip_range: TimelineRange) -> tuple[int, int]:
        """Where a Clip range is drawn, as a left edge and a width.

        The width never falls below ``MINIMUM_RANGE_WIDTH``, and hit-testing
        uses the same geometry, so a Clip is clickable wherever it is visible.
        """
        left = self.x_at(clip_range.start_ms)
        width = max(MINIMUM_RANGE_WIDTH, self.x_at(clip_range.end_ms) - left)
        left = min(left, max(0, self.width() - width))
        return left, width

    def range_at(self, x: int) -> TimelineRange | None:
        """The Clip range under a pixel column, latest drawn winning."""
        for clip_range in reversed(self._ranges):
            left, width = self.range_geometry(clip_range)
            if left <= x < left + width:
                return clip_range
        return None

    def range_appearance(self, clip_range: TimelineRange) -> RangeAppearance:
        """How one Clip range is drawn, selected or not.

        The selected range is emphasized by its shape — it fills the strip and
        gains an outline — so the emphasis survives a Clip that carries no
        Category color at all.
        """
        selected = clip_range.clip_id == self._selected_clip_id
        color = (
            muted_category_color(clip_range.color)
            if clip_range.color
            else QColor(UNCATEGORIZED_RANGE)
        )
        return RangeAppearance(
            fill=color,
            outlined=selected,
            height=SELECTED_RANGE_HEIGHT if selected else RANGE_HEIGHT,
        )

    # --- Drawing -----------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(TRACK))
        for clip_range in self._ranges:
            self._paint_range(painter, clip_range)
        self._paint_playhead(painter)
        painter.end()

    def _paint_range(self, painter: QPainter, clip_range: TimelineRange) -> None:
        left, width = self.range_geometry(clip_range)
        appearance = self.range_appearance(clip_range)
        top = (self.height() - appearance.height) // 2
        painter.fillRect(left, top, width, appearance.height, appearance.fill)
        if not appearance.outlined:
            return
        painter.setPen(QPen(QColor(TEXT), 1))
        painter.drawRect(left, top, width - 1, appearance.height - 1)

    def _paint_playhead(self, painter: QPainter) -> None:
        if self._duration_ms <= 0:
            return
        painter.fillRect(
            self.x_at(self._position_ms),
            0,
            PLAYHEAD_WIDTH,
            self.height(),
            QColor(ACCENT_BRIGHT),
        )

    # --- What the person does to it ----------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Scrub to the time pressed, and select a Clip range pressed on.

        Selecting never moves the playhead to the Clip start: the press is a
        seek to where the person pointed, and the selection comes on top.
        """
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        x = int(event.position().x())
        self._scrub_to(x)
        clip_range = self.range_at(x)
        if clip_range is None:
            return
        self.set_selected_clip(clip_range.clip_id)
        self.clip_selected.emit(clip_range.clip_id)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-clicking a Clip range navigates to the Clip start."""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        clip_range = self.range_at(int(event.position().x()))
        if clip_range is None:
            return
        self.clip_activated.emit(clip_range.clip_id)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Dragging scrubs continuously; the playhead follows the cursor."""
        if not event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)
            return
        self._scrub_to(event.position().x())

    def _scrub_to(self, x: float) -> None:
        if self._duration_ms <= 0:
            return
        self.scrubbed.emit(self.time_at(int(x)))


def _clamp(value: int, lowest: int, highest: int) -> int:
    return max(lowest, min(highest, value))
