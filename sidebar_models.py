"""The rows the sidebar draws: every Clip, and every Source video.

Two projections of the same `Analysis`. The Clip list is grouped by Category
and flattened into rows, because the grouping is a rule about the Analysis —
Categories keep the order the Analysis gives them, uncategorized Clips fall to
the end, and inside a Category the Clips read in Source-video then time order.
A QML section delegate would have put that rule in JavaScript comparators.

No colour is written here that the Analysis does not carry. A Clip with no
Category hands QML an empty colour rather than a grey of its own, so the one
place a colour is written down stays `Theme.qml`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import timecode
from analysis import Analysis, Clip
from item_models import RoleModel, Row


#: What the Clips nobody has filed yet are grouped under.
UNCATEGORIZED_LABEL = "Ohne Kategorie"

#: What a Source video of unknown length shows instead of a guess.
UNKNOWN_DURATION_TEXT = "--:--:--"


def source_badges(display_names: Sequence[str]) -> list[str]:
    """Shorten each Source-video name to something a 32px Clip row can carry.

    The row has to hold a title, a start and a length as well, and at the
    260px minimum sidebar width there is no room for `halbzeit-1.mp4`. The
    badge keeps the leading letter and the trailing number — `halbzeit-1.mp4`
    becomes `H1` — which tells two halves apart at a glance while the full
    name stays one hover away.

    Badges are computed for the whole Analysis at once rather than one name at
    a time, because a cue that cannot tell two Source videos apart is not a
    cue: an Analysis of `Angriff.mp4` and `Abwehr.mp4` would otherwise badge
    both of them `A`. Where two names shorten to the same badge, every badge in
    the Analysis falls back to the video's position — `V1`, `V2` — which is
    always distinct and is still true of the list the analyst is reading.
    """

    shortened = [_badge(name) for name in display_names]
    counted = Counter(shortened)
    if any(counted[badge] > 1 for badge in shortened):
        return [f"V{position}" for position in range(1, len(shortened) + 1)]
    return shortened


def _badge(display_name: str) -> str:
    """One name, shortened: its first letter and its last run of digits."""

    stem = display_name.rsplit(".", 1)[0]
    letter = next((character for character in stem if character.isalpha()), "V")
    digits = ""
    for character in reversed(stem):
        if character.isdigit():
            digits = character + digits
        elif digits:
            break
    return f"{letter.upper()}{digits}"


@dataclass(frozen=True)
class _Presented:
    """One Clip as the sidebar says it, with everything already resolved."""

    clip: Clip
    category_name: str
    category_color: str
    source_name: str
    source_badge: str
    source_index: int


def _present(analysis: Analysis) -> list[_Presented]:
    badges = source_badges([video.display_name for video in analysis.source_videos])
    sources = {
        video.id: (index, video.display_name, badges[index])
        for index, video in enumerate(analysis.source_videos)
    }
    categories = {category.id: category for category in analysis.categories}
    presented = []
    for clip in analysis.clips:
        category = categories.get(clip.category_id) if clip.category_id else None
        index, name, badge = sources[clip.source_video_id]
        presented.append(
            _Presented(
                clip=clip,
                category_name=category.name if category else UNCATEGORIZED_LABEL,
                category_color=category.color if category else "",
                source_name=name,
                source_badge=badge,
                source_index=index,
            )
        )
    return presented


def _clip_count_text(count: int) -> str:
    """How many Clips a Source video holds, in the language it says it in.

    Written here rather than assembled in a delegate, because `1 Clips` is a
    sentence about the Analysis being wrong, not a layout mistake.
    """

    return f"{count} Clip" if count == 1 else f"{count} Clips"


class ClipListModel(RoleModel):
    """Every Clip in the Analysis, grouped by Category, ready to draw.

    One model carries both kinds of row — a Category heading and a Clip —
    because they are one scrolling list with one order, and `kind` says which
    shape a row is. The alternative, a model per group, would have made the
    order of the groups a second decision made somewhere else.
    """

    ROLES = (
        "kind",
        "clipId",
        "title",
        "categoryName",
        "categoryColor",
        "startText",
        "durationText",
        "sourceCue",
        "sourceBadge",
        "selected",
        "count",
    )

    def refresh(self, analysis: Analysis, *, selected_clip_id: UUID | None) -> None:
        # The cue is worth a row's width only when there is more than one
        # Source video to tell apart.
        cue_wanted = len(analysis.source_videos) > 1

        grouped: dict[str, list[_Presented]] = {}
        for presented in _present(analysis):
            grouped.setdefault(presented.category_name, []).append(presented)

        ordered = [category.name for category in analysis.categories]
        if UNCATEGORIZED_LABEL in grouped:
            # The Clips nobody has filed yet read last, under a heading of
            # their own, rather than being scattered through the Categories.
            ordered.append(UNCATEGORIZED_LABEL)

        rows: list[Row] = []
        for name in ordered:
            group = grouped.get(name)
            if not group:
                continue
            group.sort(key=lambda item: (item.source_index, item.clip.start_ms))
            rows.append(
                {
                    "kind": "category",
                    "clipId": "",
                    "title": name,
                    "categoryName": name,
                    "categoryColor": group[0].category_color,
                    "startText": "",
                    "durationText": "",
                    "sourceCue": "",
                    "sourceBadge": "",
                    "selected": False,
                    "count": len(group),
                }
            )
            rows.extend(
                self._clip_row(presented, cue_wanted, selected_clip_id)
                for presented in group
            )
        self._replace(rows)

    @staticmethod
    def _clip_row(
        presented: _Presented, cue_wanted: bool, selected_clip_id: UUID | None
    ) -> Row:
        clip = presented.clip
        return {
            "kind": "clip",
            "clipId": str(clip.id),
            "title": clip.name,
            "categoryName": presented.category_name,
            "categoryColor": presented.category_color,
            "startText": timecode.clock(clip.start_ms),
            "durationText": timecode.duration(clip.end_ms - clip.start_ms),
            "sourceCue": presented.source_name if cue_wanted else "",
            "sourceBadge": presented.source_badge if cue_wanted else "",
            "selected": clip.id == selected_clip_id,
            "count": 0,
        }


class SourceVideoModel(RoleModel):
    """Every Source video in the Analysis, with the active one marked."""

    ROLES = ("sourceId", "name", "badge", "durationText", "clipCountText", "active")

    def refresh(self, analysis: Analysis, *, active_source_id: UUID | None) -> None:
        badges = source_badges([video.display_name for video in analysis.source_videos])
        self._replace(
            [
                {
                    "sourceId": str(video.id),
                    "name": video.display_name,
                    "badge": badges[index],
                    "durationText": (
                        timecode.clock(video.duration_ms)
                        if video.duration_ms is not None
                        else UNKNOWN_DURATION_TEXT
                    ),
                    "clipCountText": _clip_count_text(
                        len(analysis.clips_of_source_video(video.id))
                    ),
                    "active": video.id == active_source_id,
                }
                for index, video in enumerate(analysis.source_videos)
            ]
        )
