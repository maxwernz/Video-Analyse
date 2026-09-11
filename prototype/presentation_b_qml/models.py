"""Qt item models over the Analysis, so QML renders rows it does not compute.

Every model here is a projection of the real ``Analysis``. QML receives rows
that are already grouped, ordered and formatted; it decides where to put them
and what they look like. That split is the architectural claim this prototype
is testing, and item models are what make it enforceable — a ``ListView`` can
only read roles, so there is nowhere for a workflow rule to hide in a delegate.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Qt,
)

import timecode
from analysis import Analysis, Clip

UNCATEGORIZED_LABEL = "Ohne Kategorie"
UNCATEGORIZED_COLOR = "#5E646C"


def source_badge(display_name: str) -> str:
    """Shorten a Source-video name to something a 32px Clip row can carry.

    The row has to hold a title, a start and a duration, and at the 260px
    minimum sidebar width there is no room left for `halbzeit-1.mp4`. The
    badge keeps the leading letter and the trailing number — `halbzeit-1.mp4`
    becomes `H1` — which is enough to tell two halves apart at a glance while
    the full name stays one hover away.
    """
    stem = display_name.rsplit(".", 1)[0]
    letter = next((character for character in stem if character.isalpha()), "V")
    digits = ""
    for character in reversed(stem):
        if character.isdigit():
            digits = character + digits
        elif digits:
            break
    return f"{letter.upper()}{digits or ''}" or letter.upper()


def _roles(*names: str) -> dict[int, QByteArray]:
    return {
        Qt.ItemDataRole.UserRole + offset: QByteArray(name.encode())
        for offset, name in enumerate(names)
    }


class _RoleModel(QAbstractListModel):
    """A list model whose roles are named once and read by attribute name."""

    ROLES: tuple[str, ...] = ()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._role_names = _roles(*self.ROLES)
        self._rows: list[dict[str, object]] = []

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802 - Qt override
        return self._role_names

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        name = self._role_names.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(bytes(name).decode())

    def _replace(self, rows: list[dict[str, object]]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def row(self, index: int) -> dict[str, object] | None:
        return self._rows[index] if 0 <= index < len(self._rows) else None


@dataclass(frozen=True)
class ClipPresentation:
    """One Clip as the interface says it, with the Category already resolved."""

    clip: Clip
    category_name: str
    category_color: str
    source_name: str
    source_index: int


def present_clips(analysis: Analysis) -> list[ClipPresentation]:
    sources = {video.id: (index, video) for index, video in enumerate(analysis.source_videos)}
    categories = {category.id: category for category in analysis.categories}
    presentations = []
    for clip in analysis.clips:
        category = categories.get(clip.category_id) if clip.category_id else None
        source_index, source = sources[clip.source_video_id]
        presentations.append(
            ClipPresentation(
                clip=clip,
                category_name=category.name if category else UNCATEGORIZED_LABEL,
                category_color=category.color if category else UNCATEGORIZED_COLOR,
                source_name=source.display_name,
                source_index=source_index,
            )
        )
    return presentations


class ClipListModel(_RoleModel):
    """The Clip list, grouped by Category and flattened into rows.

    The grouping is done here rather than in a QML section delegate because the
    order is a rule about the Analysis — Categories keep the order the Analysis
    gives them, uncategorized Clips fall to the end, and within a Category
    Clips read in Source-video then time order. A section delegate would have
    put that rule in JavaScript sorting comparators.
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

    def refresh(
        self,
        analysis: Analysis,
        *,
        selected_clip_id: UUID | None,
    ) -> None:
        show_source_cue = len(analysis.source_videos) > 1
        by_category: dict[str | None, list[ClipPresentation]] = {}
        for presentation in present_clips(analysis):
            by_category.setdefault(presentation.category_name, []).append(presentation)

        ordered_names = [category.name for category in analysis.categories]
        if UNCATEGORIZED_LABEL in by_category:
            ordered_names.append(UNCATEGORIZED_LABEL)

        rows: list[dict[str, object]] = []
        for name in ordered_names:
            group = by_category.get(name)
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
            for presentation in group:
                clip = presentation.clip
                rows.append(
                    {
                        "kind": "clip",
                        "clipId": str(clip.id),
                        "title": clip.name,
                        "categoryName": presentation.category_name,
                        "categoryColor": presentation.category_color,
                        "startText": timecode.clock(clip.start_ms),
                        "durationText": timecode.duration(clip.end_ms - clip.start_ms),
                        "sourceCue": presentation.source_name if show_source_cue else "",
                        "sourceBadge": (
                            source_badge(presentation.source_name)
                            if show_source_cue
                            else ""
                        ),
                        "selected": clip.id == selected_clip_id,
                        "count": 0,
                    }
                )
        self._replace(rows)


class TimelineRangeModel(_RoleModel):
    """The Clip ranges of the Active Source video, in milliseconds.

    Positions stay in milliseconds. Turning them into pixels needs the width
    of the track, which only the running interface knows, so that one
    conversion is the timeline's own arithmetic and lives in QML.
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
        rows = [
            {
                "clipId": str(presentation.clip.id),
                "title": presentation.clip.name,
                "startMs": presentation.clip.start_ms,
                "endMs": presentation.clip.end_ms,
                "color": presentation.category_color,
                "selected": presentation.clip.id == selected_clip_id,
            }
            for presentation in present_clips(analysis)
            if presentation.clip.source_video_id == source_video_id
        ]
        rows.sort(key=lambda row: row["startMs"])
        self._replace(rows)


class RulerModel(_RoleModel):
    """The ruler's ticks, chosen for the width the track actually got.

    Which interval is legible at a given width is a real rule with an
    unpleasant amount of arithmetic in it, and it is the kind of thing that
    quietly grows into a JavaScript helper module. Keeping it in Python, driven
    by one slot the timeline calls on resize, is the honest test of whether
    that boundary survives contact.
    """

    ROLES = ("positionMs", "label", "major")

    #: Candidate label intervals in milliseconds, coarsest last.
    INTERVALS = (
        15_000, 30_000, 60_000, 2 * 60_000, 5 * 60_000,
        10_000 * 6 * 2, 15 * 60_000, 30 * 60_000, 60 * 60_000,
    )
    MINIMUM_LABEL_SPACING_PX = 62

    def layout(self, duration_ms: int, width_px: float) -> None:
        if duration_ms <= 0 or width_px <= 0:
            self._replace([])
            return
        interval = self._interval_for(duration_ms, width_px)
        minor = interval // (4 if interval >= 60_000 else 3)
        rows: list[dict[str, object]] = []
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
            position += minor if minor else interval
        self._replace(rows)

    def _interval_for(self, duration_ms: int, width_px: float) -> int:
        """The finest interval whose labels still clear each other."""
        pixels_per_ms = width_px / duration_ms
        for interval in self.INTERVALS:
            if interval * pixels_per_ms >= self.MINIMUM_LABEL_SPACING_PX:
                return interval
        return self.INTERVALS[-1]


class SourceVideoModel(_RoleModel):
    """The Videos tab: every Source video, with the active one marked."""

    ROLES = ("sourceId", "name", "durationText", "clipCount", "active", "missing")

    def refresh(self, analysis: Analysis, *, active_source_id: UUID | None) -> None:
        from pathlib import Path

        rows = []
        for video in analysis.source_videos:
            clips = analysis.clips_of_source_video(video.id)
            rows.append(
                {
                    "sourceId": str(video.id),
                    "name": video.display_name,
                    "durationText": (
                        timecode.clock(video.duration_ms)
                        if video.duration_ms is not None
                        else "--:--:--"
                    ),
                    "clipCount": len(clips),
                    "active": video.id == active_source_id,
                    "missing": not Path(video.location).is_file(),
                }
            )
        self._replace(rows)


class CategoryModel(_RoleModel):
    """The Analysis-wide Categories, for the Clip editor's chooser."""

    ROLES = ("categoryId", "name", "color", "selected")

    def refresh(self, analysis: Analysis, *, selected_category_id: UUID | None) -> None:
        self._replace(
            [
                {
                    "categoryId": str(category.id),
                    "name": category.name,
                    "color": category.color,
                    "selected": category.id == selected_category_id,
                }
                for category in analysis.categories
            ]
        )
