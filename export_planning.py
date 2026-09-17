"""Planning a Combined export: the Export list, its order, and its preflight.

A Combined export (`CONTEXT.md`) assembles selected Clips from one or more
Source videos into a single presentation video. The Export list that names
which Clips and in what order (also `CONTEXT.md`) is transient: it is built
from an Analysis, never written back into it, and rearranging it must never
touch `Analysis.revision` -- ADR 0003 says a Combined export's ordering is
"independent of the ordering stored in the Analysis", and #19 made Recovery
snapshots fire on exactly that revision moving, so an Export list that ever
bumped it would arm a Recovery snapshot for a change nobody made to their
Analysis.

That transience is also why everything here is a pure function over
`Analysis` read-only state plus `AnalysisDocument.resolve_source_video`: no
method on `Analysis` or `AnalysisDocument` is called that could change
either one. `video_creator.py` stays the only place that touches an encoder;
this module decides what it renders and in what order, never how.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from analysis import Analysis, AnalysisDocument, Clip, UnknownEntityError
from video_creator import RenderClip, VideoCreator

#: What an export Clip with no Category is labeled under, in its own final
#: group. Mirrors `sidebar_models.UNCATEGORIZED_LABEL` -- the same Analysis
#: rule, read by a different projection -- rather than importing a
#: presentation module's constant into a planning module that has no other
#: reason to depend on it.
UNCATEGORIZED_LABEL = "Ohne Kategorie"


@dataclass(frozen=True, slots=True)
class ExportListEntry:
    """One row of a temporary Export list: a Clip, not yet resolved to media.

    Everything a rendered Clip needs to be *identified and captioned* lives
    here, already read out of the Analysis; everything it needs to be
    *resolved to real media* is deliberately absent -- `preflight_export`
    resolves `source_video_id` through `AnalysisDocument.resolve_source_video`
    only when a render is actually about to happen, never here, so building
    or rearranging a list never touches the filesystem.
    """

    clip_id: UUID
    source_video_id: UUID
    name: str
    start_ms: int
    end_ms: int
    notes: str
    category_id: UUID | None
    category_name: str


def build_export_list(
    analysis: Analysis, clip_ids: Sequence[UUID]
) -> tuple[ExportListEntry, ...]:
    """The initial Export list for a set of selected Clips.

    Deterministic and read-only, per ADR 0003: Analysis-defined Category
    order first, then within each Category, Source-video order and then
    Clip start time; Clips with no Category form one final group in the same
    Source-video/start-time order. A `clip_id` that does not name a Clip in
    `analysis`, or repeats one already selected, is silently dropped rather
    than raised -- the caller's selection may have been made against a
    Clip list that changed a moment later, and an Export list is exactly the
    kind of thing that should degrade rather than fail an analyst's build.
    """

    clips_by_id = {clip.id: clip for clip in analysis.clips}
    selected = []
    seen: set[UUID] = set()
    for clip_id in clip_ids:
        clip = clips_by_id.get(clip_id)
        if clip is None or clip.id in seen:
            continue
        seen.add(clip.id)
        selected.append(clip)

    category_order = {
        category.id: index for index, category in enumerate(analysis.categories)
    }
    source_order = {
        source.id: index for index, source in enumerate(analysis.source_videos)
    }
    categories_by_id = {category.id: category for category in analysis.categories}
    #: One rank past every real Category, so uncategorized Clips always sort
    #: into the final group regardless of how many Categories exist.
    uncategorized_rank = len(category_order)

    def sort_key(clip: Clip) -> tuple[int, int, int]:
        category_rank = (
            category_order.get(clip.category_id, uncategorized_rank)
            if clip.category_id is not None
            else uncategorized_rank
        )
        source_rank = source_order.get(clip.source_video_id, len(source_order))
        return (category_rank, source_rank, clip.start_ms)

    ordered = sorted(selected, key=sort_key)
    return tuple(
        ExportListEntry(
            clip_id=clip.id,
            source_video_id=clip.source_video_id,
            name=clip.name,
            start_ms=clip.start_ms,
            end_ms=clip.end_ms,
            notes=clip.notes,
            category_id=clip.category_id,
            category_name=(
                categories_by_id[clip.category_id].name
                if clip.category_id is not None and clip.category_id in categories_by_id
                else UNCATEGORIZED_LABEL
            ),
        )
        for clip in ordered
    )


def reorder_export_list(
    entries: Sequence[ExportListEntry], clip_ids: Sequence[UUID]
) -> tuple[ExportListEntry, ...]:
    """Rearrange an existing Export list to a new Clip order.

    Purely a reordering of `entries`: every identity in `clip_ids` must name
    exactly one existing entry, or the whole reorder is refused rather than
    silently dropping or duplicating a row. This is what makes rearranging
    the Export list independent of durable Source-video, Category, and Clip
    creation order -- nothing here reads or writes an Analysis at all.
    """

    by_id = {entry.clip_id: entry for entry in entries}
    if len(clip_ids) != len(entries) or set(clip_ids) != set(by_id):
        raise ValueError(
            "Export-list reorder must name every existing entry exactly once"
        )
    return tuple(by_id[clip_id] for clip_id in clip_ids)


@dataclass(frozen=True, slots=True)
class UnavailableSourceVideo:
    """One Source video a Combined export needs that cannot be resolved."""

    source_video_id: UUID
    display_name: str


@dataclass(frozen=True, slots=True)
class ExportPreflight:
    """The complete verdict on whether an Export list is ready to render.

    `unavailable` names *every* required Source video that cannot currently
    be resolved, not the first one found -- an analyst relinking media
    before a render needs the whole list in one pass, not one failure at a
    time discovered across repeated attempts. `resolved_paths` carries the
    on-disk location for every required Source video when `ready` is true;
    it is empty-per-source for the ones named in `unavailable`.
    """

    unavailable: tuple[UnavailableSourceVideo, ...]
    resolved_paths: dict[UUID, Path]

    @property
    def ready(self) -> bool:
        """Whether rendering may begin: every required Source video resolved."""

        return not self.unavailable


def preflight_export(
    document: AnalysisDocument, entries: Sequence[ExportListEntry]
) -> ExportPreflight:
    """Resolve every Source video an Export list needs before any rendering.

    Resolution goes through `AnalysisDocument.resolve_source_video`
    exclusively -- the same stable-identity lookup `#17` gave manual
    relinking, trying only the recorded location and the location relative
    to the Analysis file -- never a fresh probe of whatever happens to be
    the Active Source video's current path. That is what lets every export
    Clip resolve its media through its own Source-video identity, even one
    that is not currently loaded in the player, and it never mutates the
    Analysis or the document.
    """

    analysis = document.analysis
    source_order = {
        source.id: index for index, source in enumerate(analysis.source_videos)
    }
    required_ids = sorted(
        {entry.source_video_id for entry in entries},
        key=lambda source_id: source_order.get(source_id, len(source_order)),
    )

    unavailable: list[UnavailableSourceVideo] = []
    resolved_paths: dict[UUID, Path] = {}
    for source_id in required_ids:
        try:
            path = document.resolve_source_video(source_id)
        except UnknownEntityError:
            # The Export list is transient and can outlive a Source video
            # named by a Clip picked into it earlier: an analyst may remove
            # that Source video (and its Clips) from the Analysis while the
            # Export list is still open. Treated the same as unresolved
            # media rather than left to raise out of preflight, so it is
            # reported alongside every other unavailable Source video
            # instead of crashing the one pass meant to find them all.
            unavailable.append(UnavailableSourceVideo(source_id, str(source_id)))
            continue
        if path is None:
            unavailable.append(
                UnavailableSourceVideo(source_id, _display_name(analysis, source_id))
            )
            continue
        resolved_paths[source_id] = path
    return ExportPreflight(tuple(unavailable), resolved_paths)


def _display_name(analysis: Analysis, source_id: UUID) -> str:
    try:
        return analysis.source_video(source_id).display_name
    except UnknownEntityError:  # pragma: no cover - defensive; see the removal case above
        return str(source_id)


class ExportUnavailableError(Exception):
    """Raised when a Combined export is asked to render with missing media.

    Carries the complete unavailable set so a caller can report every
    Source video that needs relinking in one message, matching
    `ExportPreflight.unavailable` rather than surfacing only the first.
    """

    def __init__(self, unavailable: Sequence[UnavailableSourceVideo]) -> None:
        self.unavailable = tuple(unavailable)
        names = ", ".join(source.display_name for source in self.unavailable)
        super().__init__(f"Source video media unavailable: {names}")


def render_clips_for(
    entries: Sequence[ExportListEntry], resolved_paths: dict[UUID, Path]
) -> list[RenderClip]:
    """Convert a preflighted Export list into what `VideoCreator` renders.

    Only ever called with a `resolved_paths` that already covers every entry
    -- `render_combined_export` is the one caller, and it checks
    `ExportPreflight.ready` first -- so a missing key here is a programming
    error in this module, not a state a caller needs to handle.
    """

    return [
        RenderClip(
            name=entry.name,
            video_path=str(resolved_paths[entry.source_video_id]),
            start_ms=entry.start_ms,
            end_ms=entry.end_ms,
            notes=entry.notes,
            category=entry.category_name,
        )
        for entry in entries
    ]


def render_combined_export(
    document: AnalysisDocument,
    entries: Sequence[ExportListEntry],
    save_filename: str,
    *,
    include_analysis_title: bool = False,
    logger: object = None,
) -> None:
    """Preflight, then render, a Combined export -- never the other way round.

    Preflighting first and raising `ExportUnavailableError` on any missing
    Source video is what satisfies "no render begins when required media is
    unavailable": `VideoCreator` is never constructed, let alone run, unless
    `ExportPreflight.ready` is true for every Clip in `entries`.

    This runs synchronously, on the calling thread -- rendering several
    minutes of footage is slow, but deciding whether to take that off a UI
    thread is a presentation-layer concern this planning/rendering split
    deliberately does not make. A caller driving this from an interface that
    must stay responsive is expected to run it on a worker thread itself, the
    same way `VideoCreator.start()` always could.
    """

    if not entries:
        raise ValueError("A Combined export needs at least one Clip")
    preflight = preflight_export(document, entries)
    if not preflight.ready:
        raise ExportUnavailableError(preflight.unavailable)

    creator = VideoCreator(
        render_clips_for(entries, preflight.resolved_paths),
        save_filename,
        include_analysis_title,
        logger,
    )
    creator.run()
