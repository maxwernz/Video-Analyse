"""Which ruler interval is legible at a given width, decided in Python.

The ruler is the one piece of the timeline that is a function of its inputs
rather than a seam: given a duration and the width the track actually got, the
marks it should carry are arithmetic. It gets a plain unit test for the same
reason `timecode` does — the alternative is the arithmetic quietly growing
into a JavaScript helper module inside the delegate that draws it.

The ranges are tested through the view model, with the rest of the timeline's
behaviour.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

import timecode  # noqa: E402
from timeline_models import RulerModel  # noqa: E402


FOUR_MINUTES_MS = 4 * 60_000
NINETY_MINUTES_MS = 90 * 60_000
TRACK_WIDTH_PX = 1_200


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ruler(application: QApplication) -> RulerModel:
    return RulerModel()


def labels(ruler: RulerModel) -> list[str]:
    return [str(row["label"]) for row in ruler.rows() if row["label"]]


def label_positions(ruler: RulerModel) -> list[int]:
    return [int(row["positionMs"]) for row in ruler.rows() if row["label"]]


# --- The interval -----------------------------------------------------------


def test_a_short_recording_is_labelled_finely_enough_to_be_useful(
    ruler: RulerModel,
) -> None:
    """Four minutes over a full-width track: a label every fifteen seconds."""

    ruler.layout(FOUR_MINUTES_MS, TRACK_WIDTH_PX)

    assert labels(ruler)[:3] == ["00:00", "00:15", "00:30"]


def test_a_full_match_is_labelled_coarsely_enough_to_stay_legible(
    ruler: RulerModel,
) -> None:
    """Ninety minutes over the same width: minutes would collide, so five."""

    ruler.layout(NINETY_MINUTES_MS, TRACK_WIDTH_PX)

    assert labels(ruler)[:3] == ["00:00", "05:00", "10:00"]
    assert labels(ruler)[-1] == "1:30"


def test_no_two_labels_are_drawn_closer_than_a_label_is_wide(
    ruler: RulerModel,
) -> None:
    """The rule the interval exists to keep, checked at every plausible size."""

    for duration_ms in (
        60_000,
        FOUR_MINUTES_MS,
        20 * 60_000,
        NINETY_MINUTES_MS,
        3 * 60 * 60_000,
    ):
        for width_px in (420, 700, TRACK_WIDTH_PX, 1_900):
            ruler.layout(duration_ms, width_px)
            positions = label_positions(ruler)
            gaps = [
                (later - earlier) / duration_ms * width_px
                for earlier, later in zip(positions, positions[1:])
            ]
            assert all(
                gap >= RulerModel.MINIMUM_LABEL_SPACING_PX for gap in gaps
            ), f"{duration_ms}ms over {width_px}px labels every {min(gaps)}px"


def test_a_narrow_track_still_carries_the_marks_it_can_fit(
    ruler: RulerModel,
) -> None:
    """A sidebar dragged wide leaves the timeline little room; it still rules."""

    ruler.layout(NINETY_MINUTES_MS, 300)

    assert labels(ruler) != []


def test_a_recording_longer_than_the_coarsest_interval_is_still_labelled(
    ruler: RulerModel,
) -> None:
    ruler.layout(6 * 60 * 60_000, 400)

    assert labels(ruler)[:2] == ["00:00", "1:00"]


# --- The marks themselves ---------------------------------------------------


def test_the_ruler_carries_unlabelled_minor_ticks_between_the_labels(
    ruler: RulerModel,
) -> None:
    ruler.layout(FOUR_MINUTES_MS, TRACK_WIDTH_PX)
    rows = ruler.rows()

    assert [row["major"] for row in rows[:4]] == [True, False, False, True]
    assert [row["label"] for row in rows[1:3]] == ["", ""]


def test_every_label_is_the_one_timecode_would_write(ruler: RulerModel) -> None:
    """No surface formats a time of its own, the ruler included."""

    ruler.layout(NINETY_MINUTES_MS, TRACK_WIDTH_PX)

    assert labels(ruler) == [
        timecode.ruler_label(position) for position in label_positions(ruler)
    ]


def test_the_ruler_stops_at_the_end_of_the_source_video(ruler: RulerModel) -> None:
    ruler.layout(FOUR_MINUTES_MS, TRACK_WIDTH_PX)

    assert max(int(row["positionMs"]) for row in ruler.rows()) <= FOUR_MINUTES_MS


def test_a_video_whose_length_is_not_known_yet_rules_nothing(
    ruler: RulerModel,
) -> None:
    """A duration arrives from the media; until it does there is no scale."""

    ruler.layout(FOUR_MINUTES_MS, TRACK_WIDTH_PX)
    ruler.layout(0, TRACK_WIDTH_PX)

    assert ruler.rows() == ()
    assert ruler.rowCount() == 0


def test_a_track_with_no_width_rules_nothing(ruler: RulerModel) -> None:
    ruler.layout(FOUR_MINUTES_MS, 0)

    assert ruler.rows() == ()


def test_the_marks_are_readable_through_the_roles_qml_binds_to(
    ruler: RulerModel,
) -> None:
    """A renamed role is a blank ruler, so the names are pinned here."""

    ruler.layout(FOUR_MINUTES_MS, TRACK_WIDTH_PX)
    names = {bytes(name).decode() for name in ruler.roleNames().values()}

    assert names == {"positionMs", "label", "major"}
    first = ruler.index(0, 0)
    values = {
        bytes(name).decode(): ruler.data(first, role)
        for role, name in ruler.roleNames().items()
    }
    assert values == {"positionMs": 0, "label": "00:00", "major": True}
