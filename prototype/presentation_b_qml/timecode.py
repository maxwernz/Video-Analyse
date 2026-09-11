"""Timecode formatting, in Python.

Every string the interface shows for a time is produced here rather than in
QML. Formatting is a rule about the domain (a Clip boundary is milliseconds,
shown to hundredths, in a fixed-width form) and the prototype's architectural
question is how much of that has to move into JavaScript. The answer is
"none", and this module is where that is kept true.
"""

from __future__ import annotations

_MS = 1_000
_SECOND = _MS
_MINUTE = 60 * _SECOND
_HOUR = 60 * _MINUTE


def clock(position_ms: int) -> str:
    """`HH:MM:SS`, the form used in the Clip list, ruler and transport."""
    position_ms = max(0, int(position_ms))
    hours, rest = divmod(position_ms, _HOUR)
    minutes, rest = divmod(rest, _MINUTE)
    seconds = rest // _SECOND
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def precise(position_ms: int) -> str:
    """`HH:MM:SS.mmm`, the editable form of a Clip boundary.

    Boundaries are edited to the millisecond because a Clip's start is the
    frame a coach wants to see, and the previous interface clipped this field
    rather than sizing it for the value it holds.
    """
    position_ms = max(0, int(position_ms))
    hours, rest = divmod(position_ms, _HOUR)
    minutes, rest = divmod(rest, _MINUTE)
    seconds, milliseconds = divmod(rest, _SECOND)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def duration(length_ms: int) -> str:
    """`M:SS.m`, deliberately shorter than a position so the two never read alike."""
    length_ms = max(0, int(length_ms))
    minutes, rest = divmod(length_ms, _MINUTE)
    seconds, milliseconds = divmod(rest, _SECOND)
    return f"{minutes}:{seconds:02d}.{milliseconds // 100}"


def ruler_label(position_ms: int) -> str:
    """`H:MM` past the hour, `MM:SS` below it — the ruler has no room for both."""
    position_ms = max(0, int(position_ms))
    hours, rest = divmod(position_ms, _HOUR)
    minutes, rest = divmod(rest, _MINUTE)
    if hours:
        return f"{hours}:{minutes:02d}"
    return f"{minutes:02d}:{rest // _SECOND:02d}"


def parse(text: str) -> int | None:
    """Read an edited boundary back, or report that it is not a time.

    Accepts `SS`, `MM:SS`, `HH:MM:SS`, each with optional fractional seconds,
    so a boundary can be nudged by typing `14:07.5` without spelling out the
    hour.
    """
    text = text.strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) > 3:
        return None
    try:
        seconds = float(parts[-1])
        minutes = int(parts[-2]) if len(parts) > 1 else 0
        hours = int(parts[-3]) if len(parts) > 2 else 0
    except ValueError:
        return None
    if seconds < 0 or minutes < 0 or hours < 0:
        return None
    if len(parts) > 1 and seconds >= 60:
        return None
    if len(parts) > 2 and minutes >= 60:
        return None
    return round((hours * 3600 + minutes * 60 + seconds) * _MS)
