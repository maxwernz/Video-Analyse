"""Which field a 32px Clip row gives up when the sidebar is narrow.

#37 left one question open: a Clip row carries a title, a Source-video cue, a
start and a length, and at the 300px default sidebar width they do not all
fit. The Widgets prototype elided the title, which is the truncation failure
this migration exists to fix; the Quick prototype shortened the cue to a
two-character badge and kept all four, which still elides the title.

This file is the measurement the decision was made on, kept as a test so that
a changed token, a changed metric or a changed typeface has to face it again.
It measures the real bundled faces at the real token sizes against real German
Source-video names and Clip titles, and the geometry it measures is the
geometry `Sidebar.qml` lays out.

The decision: the **length** is the field that goes. It is the only one of the
four an analyst does not need in order to find a moment — the start is the
address, the cue says which half, and the title is what is being looked for —
and it comes back whole as soon as the sidebar is wide enough for all four.
"""

from __future__ import annotations

import os
from pathlib import Path
import re

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont, QFontMetricsF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import timecode  # noqa: E402
from app_runtime import (  # noqa: E402
    TIMECODE_FONT_FAMILY,
    UI_FONT_FAMILY,
    register_bundled_fonts,
)
from sidebar_models import source_badges  # noqa: E402


THEME = Path(__file__).parents[1] / "qml" / "Theme.qml"
SIDEBAR = Path(__file__).parents[1] / "qml" / "Sidebar.qml"

#: Clip titles out of real handball analyses, in the language they are written
#: in. Nothing here is longer than a coach would actually type.
TITLES = (
    "Tor von rechts aussen",
    "Tor nach Kreuzbewegung",
    "Gegenstoss ueber links",
    "Doppelpass Rückraum Mitte",
    "Kreisläufer Anspiel",
    "Abwehrfehler Mitte",
    "Fehlwurf Halbrechts",
    "7m nach Zeitspiel",
    "Zeitstrafe Nr. 7",
    "Tempogegenstoss",
)

#: A title long enough that no layout can hold it in a 300px sidebar beside a
#: timecode. It elides, and that is accepted: the row is 300px, not the title.
VERY_LONG_TITLE = "Technischer Fehler Rueckraum"

#: Real Source-video names, as they come off a camera or a club's file server.
SOURCE_NAMES = (
    "halbzeit-1.mp4",
    "halbzeit-2.mp4",
)

#: The longest start a Source video can show, and the longest length a Clip
#: list will ever put in the column beside it.
LONGEST_START = timecode.clock(99 * 3_600_000)
LONGEST_LENGTH = timecode.duration(99 * 60_000 + 59_000)


@pytest.fixture(scope="session")
def application() -> QApplication:
    instance = QApplication.instance() or QApplication([])
    register_bundled_fonts()
    return instance  # type: ignore[return-value]


def _metrics(family: str, pixel_size: int, weight: QFont.Weight) -> QFontMetricsF:
    font = QFont(family)
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return QFontMetricsF(font)


def _token(name: str) -> int:
    """One metric, read from the theme rather than repeated here."""

    found = re.search(
        rf"readonly property (?:int|real) {name}:\s*([0-9.]+)",
        THEME.read_text(encoding="utf-8"),
    )
    assert found is not None, f"Theme.qml no longer declares {name}"
    return int(float(found.group(1)))


class Row:
    """The Clip row's geometry, as `Sidebar.qml` anchors it."""

    def __init__(self) -> None:
        self.title = _metrics(UI_FONT_FAMILY, _token("sizeRow"), QFont.Weight.Medium)
        self.timecode = _metrics(
            TIMECODE_FONT_FAMILY, _token("sizeTimecode"), QFont.Weight.Medium
        )
        self.badge = _metrics(
            UI_FONT_FAMILY, _token("sizeRuler"), QFont.Weight.Medium
        )

    def badge_block(self, names: tuple[str, ...]) -> float:
        """What the cue costs the row, badge and its gap together."""

        if len(names) < 2:
            return 0.0
        widest = max(
            self.badge.horizontalAdvance(badge) for badge in source_badges(list(names))
        )
        return widest + _token("badgePadding") + _token("badgeGap")

    def room_for_the_title(
        self, sidebar_width: int, *, names: tuple[str, ...], length: bool
    ) -> float:
        """How much of the row is left for the Clip's own name."""

        room = (
            sidebar_width
            - _token("clipTitleInset")
            - _token("clipTitleGap")
            - _token("gutter")
            - self.timecode.horizontalAdvance(LONGEST_START)
            - self.badge_block(names)
        )
        if length:
            room -= _token("timecodeColumnSpacing") + _token("durationColumnWidth")
        return room

    def elided(self, titles: tuple[str, ...], room: float) -> list[str]:
        return [title for title in titles if self.title.horizontalAdvance(title) > room]


@pytest.fixture
def row(application: QApplication) -> Row:
    return Row()


# --- The decision -----------------------------------------------------------


def test_the_row_carries_real_titles_and_the_cue_at_the_default_width(
    row: Row,
) -> None:
    """The acceptance criterion: the cue costs the title nothing at 300px."""

    room = row.room_for_the_title(_token("sidebarWidth"), names=SOURCE_NAMES, length=False)

    assert row.elided(TITLES, room) == []


def test_carrying_the_length_as_well_would_elide_real_titles(row: Row) -> None:
    """Why a field had to go at all, rather than the four being squeezed.

    This is the measurement that decides the ticket: at the default width, all
    four fields together leave the title too little room for titles a coach
    actually types — which is the Quick prototype's row, and the failure the
    Widgets prototype made explicit by eliding the title on purpose.
    """

    room = row.room_for_the_title(_token("sidebarWidth"), names=SOURCE_NAMES, length=True)

    assert row.elided(TITLES, room) != []


def test_the_length_is_the_field_that_goes_and_it_comes_back(row: Row) -> None:
    """`clipDurationMinimumWidth` is a width at which all four fit again.

    Not *the smallest* such width, and this is the interesting part. Bundling
    Inter and JetBrains Mono gives both platforms the same typeface, not the
    same metrics: Qt rasterises them through DirectWrite on Windows and
    CoreText on macOS, and the two disagree in opposite directions — the mono
    comes out narrower on Windows, the sans wider. So the exact pixel at which
    the fourth field starts to fit is platform-dependent, and a token cannot be
    the smallest such width everywhere at once.

    The token is therefore the macOS measurement, asserted here to be
    *sufficient* on whichever platform is running rather than minimal. The
    decision it encodes — that the length is the field that goes — is what this
    file is really pinning, and that holds on both.
    """

    threshold = _token("clipDurationMinimumWidth")
    room = row.room_for_the_title(threshold, names=SOURCE_NAMES, length=True)

    assert row.elided(TITLES, room) == []


def test_only_the_length_is_ever_dropped_for_want_of_room() -> None:
    """One width-conditional field in the row, and it is not the title."""

    source = SIDEBAR.read_text(encoding="utf-8")
    assert source.count("root.width >=") == 1
    assert source.count("Theme.clipDurationMinimumWidth") == 1


def test_the_title_keeps_the_largest_share_of_the_narrowest_row(row: Row) -> None:
    """At the 260px minimum the title still has more room than any other field.

    Some elision is unavoidable when an analyst drags the sidebar to its
    minimum; what must not happen is the title being the field that is
    sacrificed for the others. The exact title that starts eliding differs
    between DirectWrite and CoreText, so the contract here is the allocation,
    while the default-width test above protects the real-title corpus.
    """

    minimum = _token("sidebarMinimum")
    room = row.room_for_the_title(minimum, names=SOURCE_NAMES, length=False)

    assert room > row.timecode.horizontalAdvance(LONGEST_START) + row.badge_block(
        SOURCE_NAMES
    )


# --- The columns themselves -------------------------------------------------


def test_the_length_column_holds_the_longest_length_it_can_show(row: Row) -> None:
    """The prototype's column was 38px around a value 43px wide.

    It declared `M:SS.m` — `0:18.4` — in a 38px column, so every Clip in the
    reference screenshot was showing a clipped length. The production form is
    `M:SS`, which fits the column it is given.
    """

    assert row.timecode.horizontalAdvance(LONGEST_LENGTH) <= _token(
        "durationColumnWidth"
    )


def test_a_row_with_no_cue_gives_the_whole_saving_to_the_title(row: Row) -> None:
    """A single-video Analysis has nothing to disambiguate, so it pays nothing."""

    one_video = row.room_for_the_title(
        _token("sidebarWidth"), names=("halbzeit-1.mp4",), length=False
    )
    two_videos = row.room_for_the_title(
        _token("sidebarWidth"), names=SOURCE_NAMES, length=False
    )

    assert one_video > two_videos
    assert row.elided(TITLES + (VERY_LONG_TITLE,), one_video) == []
