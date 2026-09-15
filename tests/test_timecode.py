"""Every time the interface shows is formatted in Python, not in QML.

Formatting is a rule about the domain — a position is milliseconds, shown in a
fixed-width clock form — and keeping it here is what stops it being reinvented
in JavaScript in each surface that needs it.
"""

from __future__ import annotations

import timecode


def test_a_position_reads_as_a_fixed_width_clock() -> None:
    assert timecode.clock(0) == "00:00:00"
    assert timecode.clock(1_000) == "00:00:01"
    assert timecode.clock(61_000) == "00:01:01"
    assert timecode.clock(3_723_000) == "01:02:03"


def test_every_position_is_the_same_width_so_columns_of_times_line_up() -> None:
    widths = {len(timecode.clock(position)) for position in (0, 59_999, 3_600_000)}
    assert widths == {8}


def test_a_position_is_truncated_to_the_second_it_is_inside() -> None:
    """A clock that rounded up would name a second the video is not in yet."""

    assert timecode.clock(1_999) == "00:00:01"


def test_a_position_before_the_start_of_the_video_reads_as_the_start() -> None:
    """Nothing shows a negative time; a player that reports one is clamped."""

    assert timecode.clock(-5_000) == "00:00:00"


def test_a_video_longer_than_a_day_keeps_counting_in_hours() -> None:
    assert timecode.clock(25 * 3_600_000) == "25:00:00"
