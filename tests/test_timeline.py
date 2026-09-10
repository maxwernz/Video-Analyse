from __future__ import annotations

import os
from uuid import uuid4

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from timeline import MINIMUM_RANGE_WIDTH, Timeline, TimelineRange  # noqa: E402
from visual_system import muted_category_color  # noqa: E402

TIMELINE_WIDTH = 600
"""A round width, so a worked example maps pixels to time without rounding."""

VIDEO_DURATION_MS = 60_000


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def timeline(application: QApplication) -> Timeline:
    """One timeline at a known width, so pixels mean the same on both platforms."""
    widget = Timeline()
    widget.resize(TIMELINE_WIDTH, widget.height())
    widget.set_duration(VIDEO_DURATION_MS)
    return widget


def _point(timeline: Timeline, x: int) -> QPoint:
    return QPoint(x, timeline.height() // 2)


def _click(timeline: Timeline, x: int) -> None:
    QTest.mouseClick(timeline, Qt.MouseButton.LeftButton, pos=_point(timeline, x))


def _range(start_ms: int, end_ms: int, color: str | None = "#EF4444") -> TimelineRange:
    return TimelineRange(uuid4(), start_ms, end_ms, color)


def test_clicking_the_timeline_scrubs_to_the_time_under_the_cursor(
    timeline: Timeline,
) -> None:
    scrubbed: list[int] = []
    timeline.scrubbed.connect(scrubbed.append)

    _click(timeline, TIMELINE_WIDTH // 2)

    assert scrubbed == [VIDEO_DURATION_MS // 2]


def _drag_to(timeline: Timeline, x: int) -> None:
    """One move of a held drag; ``QTest.mouseMove`` carries no button state."""
    QApplication.sendEvent(
        timeline,
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(_point(timeline, x)),
            QPointF(timeline.mapToGlobal(_point(timeline, x))),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )


def test_dragging_along_the_timeline_scrubs_continuously(timeline: Timeline) -> None:
    scrubbed: list[int] = []
    timeline.scrubbed.connect(scrubbed.append)

    QTest.mousePress(timeline, Qt.MouseButton.LeftButton, pos=_point(timeline, 60))
    _drag_to(timeline, 180)
    _drag_to(timeline, 300)
    QTest.mouseRelease(timeline, Qt.MouseButton.LeftButton, pos=_point(timeline, 300))

    assert scrubbed == [6_000, 18_000, 30_000]


def test_a_timeline_without_a_duration_scrubs_nowhere(
    application: QApplication,
) -> None:
    """A Source video that has not announced its duration has no time scale."""
    timeline = Timeline()
    timeline.resize(TIMELINE_WIDTH, timeline.height())
    scrubbed: list[int] = []
    timeline.scrubbed.connect(scrubbed.append)

    _click(timeline, TIMELINE_WIDTH // 2)

    assert scrubbed == []


def test_clicking_on_top_of_a_clip_range_still_scrubs_to_that_time(
    timeline: Timeline,
) -> None:
    timeline.show_ranges([_range(0, VIDEO_DURATION_MS)])
    scrubbed: list[int] = []
    timeline.scrubbed.connect(scrubbed.append)

    _click(timeline, TIMELINE_WIDTH // 4)

    assert scrubbed == [VIDEO_DURATION_MS // 4]


def test_clicking_a_clip_range_selects_that_clip(timeline: Timeline) -> None:
    clip_range = _range(30_000, 40_000)
    timeline.show_ranges([clip_range])
    selected: list[object] = []
    timeline.clip_selected.connect(selected.append)

    _click(timeline, 350)

    assert selected == [clip_range.clip_id]
    assert timeline.selected_clip_id() == clip_range.clip_id


def test_clicking_beside_every_clip_range_selects_nothing(
    timeline: Timeline,
) -> None:
    timeline.show_ranges([_range(30_000, 40_000)])
    selected: list[object] = []
    timeline.clip_selected.connect(selected.append)

    _click(timeline, 100)

    assert selected == []
    assert timeline.selected_clip_id() is None


def test_double_clicking_a_clip_range_reports_it_for_navigation(
    timeline: Timeline,
) -> None:
    clip_range = _range(30_000, 40_000)
    timeline.show_ranges([clip_range])
    activated: list[object] = []
    timeline.clip_activated.connect(activated.append)

    QTest.mouseDClick(timeline, Qt.MouseButton.LeftButton, pos=_point(timeline, 350))

    assert activated == [clip_range.clip_id]


def test_a_short_clip_stays_wide_enough_to_see_and_to_click(
    timeline: Timeline,
) -> None:
    """One second of a ninety-minute Source video is a fraction of a pixel."""
    timeline.set_duration(5_400_000)
    clip_range = _range(2_700_000, 2_701_000)
    timeline.show_ranges([clip_range])
    selected: list[object] = []
    timeline.clip_selected.connect(selected.append)

    left, width = timeline.range_geometry(clip_range)
    assert width >= MINIMUM_RANGE_WIDTH

    _click(timeline, left + width - 1)

    assert selected == [clip_range.clip_id]


def test_showing_the_ranges_of_another_source_video_drops_the_selection(
    timeline: Timeline,
) -> None:
    clip_range = _range(30_000, 40_000)
    timeline.show_ranges([clip_range])
    timeline.set_selected_clip(clip_range.clip_id)

    timeline.show_ranges([_range(1_000, 2_000)])

    assert timeline.selected_clip_id() is None


def test_the_selected_range_is_emphasized_beyond_its_category_color(
    timeline: Timeline,
) -> None:
    """Color informs; the shape of the selected range carries the meaning."""
    clip_range = _range(10_000, 20_000, "#EF4444")
    timeline.show_ranges([clip_range])
    unselected = timeline.range_appearance(clip_range)

    timeline.set_selected_clip(clip_range.clip_id)
    selected = timeline.range_appearance(clip_range)

    assert selected.fill == muted_category_color("#EF4444")
    assert selected.fill.saturation() < QColor("#EF4444").saturation()
    assert selected.outlined is True
    assert unselected.outlined is False
    assert selected.height > unselected.height


def test_a_clip_without_a_category_is_still_drawn(timeline: Timeline) -> None:
    clip_range = _range(10_000, 20_000, color=None)
    timeline.show_ranges([clip_range])

    appearance = timeline.range_appearance(clip_range)

    assert appearance.fill.isValid() is True


def test_the_timeline_paints_its_ranges_and_its_playhead(
    timeline: Timeline,
) -> None:
    """A rendering smoke test: the strip is painted, not left blank."""
    timeline.show_ranges([_range(10_000, 20_000)])
    timeline.set_position(30_000)
    image = QImage(timeline.size(), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    timeline.render(image)

    painted = {image.pixelColor(x, timeline.height() // 2).name() for x in range(0, TIMELINE_WIDTH, 5)}
    assert len(painted) > 1
