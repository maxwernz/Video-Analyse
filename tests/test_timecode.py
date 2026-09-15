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


# --- The ruler's own labels -------------------------------------------------


def test_a_ruler_label_below_an_hour_reads_as_minutes_and_seconds() -> None:
    """The ruler has room for two fields, not three."""

    assert timecode.ruler_label(0) == "00:00"
    assert timecode.ruler_label(90_000) == "01:30"
    assert timecode.ruler_label(45 * 60_000) == "45:00"


def test_a_ruler_label_past_the_hour_counts_hours_and_minutes() -> None:
    """A ninety-minute recording must not label its second half `30:00`."""

    assert timecode.ruler_label(3_600_000) == "1:00"
    assert timecode.ruler_label(90 * 60_000) == "1:30"
    assert timecode.ruler_label(2 * 3_600_000 + 5 * 60_000) == "2:05"


def test_a_ruler_label_never_reads_as_a_negative_time() -> None:
    assert timecode.ruler_label(-1) == "00:00"


# --- How long a Clip is -----------------------------------------------------


def test_a_length_is_written_in_minutes_and_seconds() -> None:
    assert timecode.duration(18_000) == "0:18"
    assert timecode.duration(65_000) == "1:05"
    assert timecode.duration(12 * 60_000 + 30_000) == "12:30"


def test_a_length_never_reads_like_a_position() -> None:
    """The Clip list carries both in one row, in the same monospaced face."""

    assert timecode.duration(18_000) != timecode.clock(18_000)
    assert len(timecode.duration(18_000)) < len(timecode.clock(18_000))


def test_a_length_is_truncated_to_the_second_it_has_reached() -> None:
    assert timecode.duration(18_999) == "0:18"


def test_a_length_past_an_hour_keeps_counting_in_minutes() -> None:
    """An hour-long Clip is not a Clip, but a column that shifted would lie."""

    assert timecode.duration(90 * 60_000) == "90:00"


def test_a_negative_length_reads_as_nothing_at_all() -> None:
    assert timecode.duration(-1) == "0:00"


# --- The Clip editor's two forms -------------------------------------------


def test_a_boundary_is_edited_to_the_millisecond() -> None:
    """The editable form of a Clip boundary, whole so the field cannot clip."""

    assert timecode.precise(0) == "00:00:00.000"
    assert timecode.precise(3_723_456) == "01:02:03.456"


def test_every_boundary_is_the_same_width_so_the_field_can_be_sized_for_it() -> None:
    widths = {len(timecode.precise(position)) for position in (0, 59_999, 3_600_000)}
    assert widths == {12}


def test_a_boundary_before_the_start_of_the_video_reads_as_the_start() -> None:
    assert timecode.precise(-5_000) == "00:00:00.000"


def test_the_editors_duration_carries_the_hundredths_the_clip_list_drops() -> None:
    """The token spec: the Clip list writes `M:SS`, the editor the hundredths."""

    assert timecode.precise_duration(18_400) == "0:18.40"
    assert timecode.precise_duration(0) == "0:00.00"
    assert timecode.precise_duration(90 * 60_000) == "90:00.00"


def test_the_editors_duration_never_reads_like_a_position() -> None:
    assert timecode.precise_duration(18_000) != timecode.precise(18_000)


def test_a_negative_length_reads_as_nothing_at_all_in_the_editor_too() -> None:
    assert timecode.precise_duration(-1) == "0:00.00"


def test_an_edited_boundary_is_read_back_in_the_form_it_is_shown_in() -> None:
    assert timecode.parse("01:02:03.456") == 3_723_456


def test_a_boundary_may_be_typed_without_the_fields_that_are_zero() -> None:
    """Nobody types the hour of a first-half Clip to nudge it by a second."""

    assert timecode.parse("14:07") == 14 * 60_000 + 7_000
    assert timecode.parse("7") == 7_000
    assert timecode.parse("14:07.5") == 14 * 60_000 + 7_500
    assert timecode.parse(" 14:07 ") == 14 * 60_000 + 7_000


def test_a_boundary_that_is_not_a_time_is_reported_as_no_time_at_all() -> None:
    """A field that silently read `Halbzeit` as zero would move the video."""

    for text in ("", "   ", "Halbzeit", "1:2:3:4", "-5", "01:70:00", "01:02:70"):
        assert timecode.parse(text) is None, text
