"""Timecode formatting, in Python.

Every string the interface shows for a time is produced here rather than in
QML. Formatting is a rule about the domain — a position is milliseconds, shown
to the second, in a fixed-width form so that a column of times lines up — and
the presentation layer is given the finished string.

There are four forms, and which one a surface uses is a decision about what is
being read rather than about the surface: a position is `HH:MM:SS`, a ruler
label drops the field that is not changing, a Clip's length is shorter than a
position so the two never read alike, and a Clip boundary is editable to the
millisecond. `parse` reads that last one back.
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
    """`HH:MM:SS.mmm` — the editable form of a Clip boundary.

    Boundaries are edited to the millisecond, because a Clip's start is the
    frame a coach wants to see. The form is fixed-width for the same reason
    the clock is: the field in the Clip editor is sized for a whole timecode,
    and the captured evidence of the rejected interface is a boundary clipped
    to `:00.000`.
    """

    position_ms = max(0, int(position_ms))
    hours, rest = divmod(position_ms, _HOUR)
    minutes, rest = divmod(rest, _MINUTE)
    seconds, milliseconds = divmod(rest, _SECOND)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def precise_duration(length_ms: int) -> str:
    """`M:SS.mm` — how long the Clip being edited is, as its boundaries move.

    The Clip list writes `M:SS`, because a list is read to find a moment and
    a wider column costs the title its room. The editor is where the
    hundredths belong: the boundaries either side of this number are being
    edited to the millisecond, and a readout rounded to the second would sit
    still while they moved.
    """

    length_ms = max(0, int(length_ms))
    minutes, rest = divmod(length_ms, _MINUTE)
    seconds, milliseconds = divmod(rest, _SECOND)
    return f"{minutes}:{seconds:02d}.{milliseconds // 10:02d}"


def parse(text: str) -> int | None:
    """Read an edited boundary back, or report that it is not a time at all.

    Accepts `SS`, `MM:SS` and `HH:MM:SS`, each with optional fractional
    seconds, so a boundary can be corrected by typing `14:07.5` without
    spelling out an hour that is zero. Anything else is not a time: it is
    reported as such rather than read as a position, because a field that
    quietly understood `Halbzeit` as zero would move the video to the start
    of the match.
    """

    text = str(text).strip()
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
    return round((hours * _HOUR + minutes * _MINUTE + seconds * _SECOND))
