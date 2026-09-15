"""The rows the timeline draws, computed where a test can reach them.

Two item models, both projections of the real `Analysis` and of the Active
Source video's length: the ruler's marks and the Clip ranges. QML receives
rows it does not compute, and a `Repeater` can only read roles, so there is
nowhere for a rule about the Analysis to hide inside a delegate.

Positions stay in milliseconds. Turning a millisecond into a pixel needs the
width of the track, which only the running interface knows, so that one
conversion is the timeline's own arithmetic and lives in QML. Which interval
is legible at that width is the opposite kind of thing — a rule with an
unpleasant amount of arithmetic in it — and it lives here.
"""

from __future__ import annotations

from uuid import UUID

import timecode
from analysis import Analysis
from item_models import RoleModel, Row


class RulerModel(RoleModel):
    """The ruler's marks, chosen for the width the track actually got.

    An interval is legible when its labels clear each other at the current
    scale, which is why the width is an input: the same ninety minutes needs
    five-minute labels across a wide window and hourly ones in a narrow one.
    Keeping the decision here is the boundary #37 draws — the alternative is a
    JavaScript helper module growing inside the delegate that draws the marks.
    """

    ROLES = ("positionMs", "label", "major")

    #: Candidate label intervals in milliseconds, finest first.
    INTERVALS = (
        15_000,
        30_000,
        60_000,
        2 * 60_000,
        5 * 60_000,
        10 * 60_000,
        15 * 60_000,
        30 * 60_000,
        60 * 60_000,
    )

    #: How much room a ruler label needs before the next one may start.
    #:
    #: A `MM:SS` label at 10px JetBrains Mono is about 30px wide; the rest is
    #: the air that keeps two labels from reading as one number.
    MINIMUM_LABEL_SPACING_PX = 62

    def layout(self, duration_ms: int, width_px: float) -> None:
        """Rule a track of `width_px` for a Source video of `duration_ms`."""

        if duration_ms <= 0 or width_px <= 0:
            self._replace([])
            return
        interval = self.interval_for(duration_ms, width_px)
        minor = interval // (4 if interval >= 60_000 else 3)
        rows: list[Row] = []
        position = 0
        while position <= duration_ms:
            major = position % interval == 0
            rows.append(
                {
                    "positionMs": position,
                    "label": timecode.ruler_label(position) if major else "",
                    "major": major,
                }
            )
            position += minor or interval
        self._replace(rows)

    @classmethod
    def interval_for(cls, duration_ms: int, width_px: float) -> int:
        """The finest labelling interval whose labels still clear each other."""

        pixels_per_ms = width_px / duration_ms
        for interval in cls.INTERVALS:
            if interval * pixels_per_ms >= cls.MINIMUM_LABEL_SPACING_PX:
                return interval
        return cls.INTERVALS[-1]


class TimelineRangeModel(RoleModel):
    """The Clip ranges of the Active Source video, in milliseconds.

    A Clip with no Category carries no colour rather than a grey of its own:
    the timeline draws it in the theme's faint text colour, so the one place
    colour is written down stays `Theme.qml`.
    """

    ROLES = ("clipId", "title", "startMs", "endMs", "color", "selected")

    def refresh(
        self,
        analysis: Analysis,
        *,
        source_video_id: UUID | None,
        selected_clip_id: UUID | None,
    ) -> None:
        if source_video_id is None:
            self._replace([])
            return
        colours = {category.id: category.color for category in analysis.categories}
        # The ranges read in the order they happen, whatever order the Clips
        # were marked in.
        clips = sorted(
            analysis.clips_of_source_video(source_video_id),
            key=lambda clip: (clip.start_ms, clip.end_ms),
        )
        rows: list[Row] = [
            {
                "clipId": str(clip.id),
                "title": clip.name,
                "startMs": clip.start_ms,
                "endMs": clip.end_ms,
                "color": colours.get(clip.category_id, "") if clip.category_id else "",
                "selected": clip.id == selected_clip_id,
            }
            for clip in clips
        ]
        self._replace(rows)
