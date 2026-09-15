"""Timecode formatting, in Python.

Every string the interface shows for a time is produced here rather than in
QML. Formatting is a rule about the domain — a position is milliseconds, shown
to the second, in a fixed-width form so that a column of times lines up — and
the presentation layer is given the finished string.

Editable Clip boundaries use the precise form below, including milliseconds.
"""

from __future__ import annotations

_SECOND = 1_000
_MINUTE = 60 * _SECOND
_HOUR = 60 * _MINUTE


def clock(position_ms: int) -> str:
    """`HH:MM:SS` — the form the transport reads elapsed and total time in."""

    position_ms = max(0, int(position_ms))
    hours, rest = divmod(position_ms, _HOUR)
    minutes, rest = divmod(rest, _MINUTE)
    seconds = rest // _SECOND
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def ruler_label(position_ms: int) -> str:
    """`MM:SS` below the hour, `H:MM` past it — the ruler has room for two.

    A ruler label is read against its neighbours rather than on its own, so it
    names the two fields that are changing and drops the one that is not. A
    ninety-minute recording would otherwise label its second half with the same
    strings as its first.
    """

    position_ms = max(0, int(position_ms))
    hours, rest = divmod(position_ms, _HOUR)
    minutes, rest = divmod(rest, _MINUTE)
    if hours:
        return f"{hours}:{minutes:02d}"
    return f"{minutes:02d}:{rest // _SECOND:02d}"


def duration(length_ms: int) -> str:
    """`M:SS` — how long a Clip is, written so it cannot read as a position.

    A position in this application is always `HH:MM:SS`; a length drops the
    leading fields it does not need, so a column of starts and a column of
    lengths stay tellable apart at a glance in a 32px row. Lengths are shown
    to the second: a Clip list is read to find a moment, and the hundredths
    the Clip editor edits to would only make the column wider than the room
    the sidebar has for it.
    """

    length_ms = max(0, int(length_ms))
    minutes, rest = divmod(length_ms, _MINUTE)
    return f"{minutes}:{rest // _SECOND:02d}"


def precise(position_ms: int) -> str:
    """`HH:MM:SS.mmm` — a complete, editable Clip boundary."""

    position_ms = max(0, int(position_ms))
    hours, rest = divmod(position_ms, _HOUR)
    minutes, rest = divmod(rest, _MINUTE)
    seconds, milliseconds = divmod(rest, _SECOND)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def parse(value: str) -> int | None:
    """Read an editable Clip boundary, or reject text that is not one."""

    try:
        clock_part, milliseconds_part = value.strip().split(".")
        hours_part, minutes_part, seconds_part = clock_part.split(":")
        hours = int(hours_part)
        minutes = int(minutes_part)
        seconds = int(seconds_part)
        milliseconds = int(milliseconds_part)
    except (AttributeError, TypeError, ValueError):
        return None
    if (
        hours < 0
        or not 0 <= minutes < 60
        or not 0 <= seconds < 60
        or len(milliseconds_part) != 3
        or not 0 <= milliseconds < 1_000
    ):
        return None
    return hours * _HOUR + minutes * _MINUTE + seconds * _SECOND + milliseconds
