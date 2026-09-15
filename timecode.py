"""Timecode formatting, in Python.

Every string the interface shows for a time is produced here rather than in
QML. Formatting is a rule about the domain — a position is milliseconds, shown
to the second, in a fixed-width form so that a column of times lines up — and
the presentation layer is given the finished string.

The forms the other surfaces need (an editable boundary to the millisecond, a
Clip length, a ruler label) arrive with the tickets that show them, each with
the test that pins it.
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
