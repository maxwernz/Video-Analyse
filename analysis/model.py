from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any, Final, Protocol, TypeVar
from uuid import UUID, uuid4

from .errors import InvalidAnalysisDataError, UnknownEntityError


@dataclass(frozen=True, slots=True)
class SourceVideo:
    id: UUID
    display_name: str
    location: str
    relative_path: str | None = None
    duration_ms: int | None = None
    byte_size: int | None = None
    fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class Category:
    id: UUID
    name: str
    color: str


@dataclass(frozen=True, slots=True)
class Clip:
    id: UUID
    source_video_id: UUID
    name: str
    start_ms: int
    end_ms: int
    notes: str
    category_id: UUID | None
    creation_order: int


class _Unchanged:
    """Marker distinguishing "leave as is" from an explicit ``None``."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "UNCHANGED"


UNCHANGED: Final = _Unchanged()


class Analysis:
    """UI-independent analytical content with stable entity identities."""

    def __init__(self, title: str, *, analysis_id: UUID | None = None) -> None:
        if not isinstance(title, str):
            raise InvalidAnalysisDataError("Analysis title must be text")
        if analysis_id is not None and not isinstance(analysis_id, UUID):
            raise InvalidAnalysisDataError("Analysis identity must be a UUID")
        self._id = analysis_id or uuid4()
        self._title = title
        self._source_videos: list[SourceVideo] = []
        self._categories: list[Category] = []
        self._clips: list[Clip] = []
        self._revision = 0

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def source_videos(self) -> tuple[SourceVideo, ...]:
        return tuple(self._source_videos)

    @property
    def categories(self) -> tuple[Category, ...]:
        return tuple(self._categories)

    @property
    def clips(self) -> tuple[Clip, ...]:
        return tuple(self._clips)

    @property
    def revision(self) -> int:
        return self._revision

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Apply several operations as one change, undone entirely if one fails.

        A rejected change leaves neither content nor revision behind, so a
        failed edit never marks its Analysis document dirty.
        """
        title = self._title
        source_videos = list(self._source_videos)
        categories = list(self._categories)
        clips = list(self._clips)
        revision = self._revision
        try:
            yield
        except Exception:
            self._title = title
            self._source_videos = source_videos
            self._categories = categories
            self._clips = clips
            self._revision = revision
            raise

    def set_title(self, title: str) -> None:
        if not isinstance(title, str):
            raise InvalidAnalysisDataError("Analysis title must be text")
        if title == self._title:
            return
        self._title = title
        self._revision += 1

    def source_video(self, source_video_id: UUID) -> SourceVideo:
        return _required(
            _with_id(self._source_videos, source_video_id),
            "Analysis has no such Source video",
        )

    def category(self, category_id: UUID) -> Category:
        return _required(
            _with_id(self._categories, category_id),
            "Analysis has no such Category",
        )

    def category_named(self, name: str) -> Category | None:
        normalized_name = normalize_category_name(name)
        return next(
            (
                category
                for category in self._categories
                if normalize_category_name(category.name) == normalized_name
            ),
            None,
        )

    def clip(self, clip_id: UUID) -> Clip:
        return _required(
            _with_id(self._clips, clip_id),
            "Analysis has no such Clip",
        )

    def clips_of_source_video(self, source_video_id: UUID) -> tuple[Clip, ...]:
        return tuple(
            clip for clip in self._clips if clip.source_video_id == source_video_id
        )

    def add_source_video(
        self,
        display_name: str,
        location: str,
        *,
        source_video_id: UUID | None = None,
        relative_path: str | None = None,
        duration_ms: int | None = None,
        byte_size: int | None = None,
        fingerprint: str | None = None,
    ) -> SourceVideo:
        """Add a Source video unconditionally, as a new identity.

        This is the structural primitive the codec's decoder calls once per
        JSON entry, and it is deliberately stricter than normal add-time
        identity verification: it rejects a bare fingerprint collision on
        its own, without needing byte size or duration to agree too, because
        two *decoded* entries claiming the same fingerprint is exactly the
        kind of malformed file `AnalysisFileCodec` must refuse to load.
        `add_or_relink_source_video` is the operation with the three-signal
        match a live add or relink actually wants; it calls this method only
        once it has already decided the media is not a relink of something
        already present, so the stricter check here is reachable from it
        only when a fingerprint matches by coincidence while size or
        duration do not — sha256 collisions of unrelated content are not a
        real risk, so that path is expected to behave like any other
        genuine duplicate and raise the same way.
        """
        if not isinstance(display_name, str) or not display_name.strip():
            raise InvalidAnalysisDataError(
                "Source-video display name must not be empty"
            )
        if not isinstance(location, str) or not location.strip():
            raise InvalidAnalysisDataError("Source-video location must not be empty")
        if relative_path is not None and not isinstance(relative_path, str):
            raise InvalidAnalysisDataError("Source-video relative path must be text")
        _validate_optional_non_negative_integer(duration_ms, "Source-video duration")
        _validate_optional_non_negative_integer(byte_size, "Source-video byte size")
        if fingerprint is not None and not isinstance(fingerprint, str):
            raise InvalidAnalysisDataError("Source-video fingerprint must be text")
        identity = source_video_id or uuid4()
        if not isinstance(identity, UUID):
            raise InvalidAnalysisDataError("Source-video identity must be a UUID")
        if any(source.id == identity for source in self._source_videos):
            raise InvalidAnalysisDataError("Source-video identity must be unique")
        if any(source.location == location for source in self._source_videos):
            raise InvalidAnalysisDataError("Source video has already been added")
        if fingerprint is not None and any(
            source.fingerprint == fingerprint for source in self._source_videos
        ):
            raise InvalidAnalysisDataError("Source video has already been added")
        source_video = SourceVideo(
            id=identity,
            display_name=display_name,
            location=location,
            relative_path=relative_path,
            duration_ms=duration_ms,
            byte_size=byte_size,
            fingerprint=fingerprint,
        )
        self._source_videos.append(source_video)
        self._revision += 1
        return source_video

    def rename_source_video(
        self,
        source_video_id: UUID,
        display_name: str,
    ) -> SourceVideo:
        source_video = self.source_video(source_video_id)
        if not isinstance(display_name, str) or not display_name.strip():
            raise InvalidAnalysisDataError(
                "Source-video display name must not be empty"
            )
        if display_name == source_video.display_name:
            return source_video
        renamed = replace(source_video, display_name=display_name)
        self._source_videos[self._source_videos.index(source_video)] = renamed
        self._revision += 1
        return renamed

    def remove_source_video(self, source_video_id: UUID) -> None:
        source_video = self.source_video(source_video_id)
        self._source_videos.remove(source_video)
        self._clips = [
            clip for clip in self._clips if clip.source_video_id != source_video_id
        ]
        self._renumber_clips()
        self._revision += 1

    def reorder_source_videos(self, source_video_ids: Sequence[UUID]) -> None:
        """Set the durable, user-controlled order of every Source video.

        Position is never identity: every Clip keeps naming its Source video
        by UUID, so reordering cannot disturb a single Clip relationship.
        """
        ordered_ids = list(source_video_ids)
        known_ids = {source.id for source in self._source_videos}
        if len(ordered_ids) != len(known_ids) or set(ordered_ids) != known_ids:
            raise InvalidAnalysisDataError(
                "Source-video order must name every Source video exactly once"
            )
        by_id = {source.id: source for source in self._source_videos}
        reordered = [by_id[identity] for identity in ordered_ids]
        if reordered == self._source_videos:
            return
        self._source_videos = reordered
        self._revision += 1

    def add_or_relink_source_video(
        self,
        display_name: str,
        location: str,
        *,
        relative_path: str | None = None,
        duration_ms: int | None = None,
        byte_size: int | None = None,
        fingerprint: str | None = None,
    ) -> SourceVideo:
        """Add a Source video, or recognize it as media already present.

        Normal identity verification never touches every byte of the file: a
        sampled fingerprint combined with byte size and duration is stable
        enough to tell one physical recording from another. When all three
        match an existing Source video, the media is the same recording
        under a possibly different path. Re-adding it from the location
        already on record is rejected as a duplicate; re-adding it from
        anywhere else relinks the existing Source video to that location
        instead of creating a second identity for the same footage.

        A fingerprint match with byte size but not duration — one add
        probed a duration and the earlier one did not, so one side is
        `None` — falls through to :meth:`add_source_video` instead of
        matching here. That still raises: `add_source_video` rejects a
        bare fingerprint collision on its own. The outcome an analyst sees
        is the same duplicate rejection either way; only the raised
        message differs, because this method never reaches its own relink
        branch for a signal it cannot confirm.
        """
        match = self._matching_source_video(
            duration_ms=duration_ms, byte_size=byte_size, fingerprint=fingerprint
        )
        if match is not None:
            if match.location == location:
                raise InvalidAnalysisDataError("Source video has already been added")
            if any(
                source.id != match.id and source.location == location
                for source in self._source_videos
            ):
                raise InvalidAnalysisDataError(
                    "Source video location is already in use"
                )
            relinked = replace(match, location=location, relative_path=relative_path)
            self._source_videos[self._source_videos.index(match)] = relinked
            self._revision += 1
            return relinked
        return self.add_source_video(
            display_name,
            location,
            relative_path=relative_path,
            duration_ms=duration_ms,
            byte_size=byte_size,
            fingerprint=fingerprint,
        )

    def _matching_source_video(
        self,
        *,
        duration_ms: int | None,
        byte_size: int | None,
        fingerprint: str | None,
    ) -> SourceVideo | None:
        """Find an existing Source video verified identical to this media.

        All three signals must be present and agree; a full-file hash is
        never required, but a missing signal never counts as a match either,
        so an unprobed video can never silently absorb another's identity.
        """
        if duration_ms is None or byte_size is None or fingerprint is None:
            return None
        return next(
            (
                source
                for source in self._source_videos
                if source.fingerprint == fingerprint
                and source.byte_size == byte_size
                and source.duration_ms == duration_ms
            ),
            None,
        )

    def add_category(
        self,
        name: str,
        color: str = "#808080",
        *,
        category_id: UUID | None = None,
    ) -> Category:
        normalized_name = normalize_category_name(name)
        if not isinstance(color, str) or not color.strip():
            raise InvalidAnalysisDataError("Category color must not be empty")
        if any(
            normalize_category_name(category.name) == normalized_name
            for category in self._categories
        ):
            raise InvalidAnalysisDataError(
                f"Category names must be unique: {name!r}"
            )
        identity = category_id or uuid4()
        if not isinstance(identity, UUID):
            raise InvalidAnalysisDataError("Category identity must be a UUID")
        if any(category.id == identity for category in self._categories):
            raise InvalidAnalysisDataError("Category identity must be unique")
        category = Category(identity, name.strip(), color)
        self._categories.append(category)
        self._revision += 1
        return category

    def update_category(
        self,
        category_id: UUID,
        *,
        name: str | _Unchanged = UNCHANGED,
        color: str | _Unchanged = UNCHANGED,
    ) -> Category:
        category = self.category(category_id)
        updated = category
        if not isinstance(name, _Unchanged):
            normalized_name = normalize_category_name(name)
            if any(
                other.id != category_id
                and normalize_category_name(other.name) == normalized_name
                for other in self._categories
            ):
                raise InvalidAnalysisDataError(
                    f"Category names must be unique: {name!r}"
                )
            updated = replace(updated, name=name.strip())
        if not isinstance(color, _Unchanged):
            if not isinstance(color, str) or not color.strip():
                raise InvalidAnalysisDataError("Category color must not be empty")
            updated = replace(updated, color=color)
        if updated == category:
            return category
        self._categories[self._categories.index(category)] = updated
        self._revision += 1
        return updated

    def reorder_categories(self, category_ids: Sequence[UUID]) -> None:
        """Set the order that groups Clips throughout this Analysis.

        A Category's UUID, not its position, is what a Clip stores. Keeping
        that distinction means analysts can make the list read like their
        review without silently refiling any existing Clip.
        """

        ordered_ids = list(category_ids)
        known_ids = {category.id for category in self._categories}
        if len(ordered_ids) != len(known_ids) or set(ordered_ids) != known_ids:
            raise InvalidAnalysisDataError(
                "Category order must name every Category exactly once"
            )
        by_id = {category.id: category for category in self._categories}
        reordered = [by_id[identity] for identity in ordered_ids]
        if reordered == self._categories:
            return
        self._categories = reordered
        self._revision += 1

    def remove_category(self, category_id: UUID) -> None:
        category = self.category(category_id)
        self._categories.remove(category)
        self._clips = [
            replace(clip, category_id=None) if clip.category_id == category_id else clip
            for clip in self._clips
        ]
        self._revision += 1

    def add_clip(
        self,
        source_video_id: UUID,
        name: str,
        start_ms: int,
        end_ms: int,
        *,
        notes: str = "",
        category_id: UUID | None = None,
        clip_id: UUID | None = None,
        creation_order: int | None = None,
    ) -> Clip:
        if not isinstance(source_video_id, UUID):
            raise InvalidAnalysisDataError("Clip Source-video identity must be a UUID")
        order = len(self._clips) if creation_order is None else creation_order
        if (
            isinstance(order, bool)
            or not isinstance(order, int)
            or order != len(self._clips)
        ):
            raise InvalidAnalysisDataError(
                "Clip creation order must be contiguous and match stored order"
            )
        identity = clip_id or uuid4()
        if not isinstance(identity, UUID):
            raise InvalidAnalysisDataError("Clip identity must be a UUID")
        if any(clip.id == identity for clip in self._clips):
            raise InvalidAnalysisDataError("Clip identity must be unique")
        clip = self._validated_clip(
            Clip(
                id=identity,
                source_video_id=source_video_id,
                name=name,
                start_ms=start_ms,
                end_ms=end_ms,
                notes=notes,
                category_id=category_id,
                creation_order=order,
            )
        )
        self._clips.append(clip)
        self._revision += 1
        return clip

    def update_clip(
        self,
        clip_id: UUID,
        *,
        name: str | _Unchanged = UNCHANGED,
        start_ms: int | _Unchanged = UNCHANGED,
        end_ms: int | _Unchanged = UNCHANGED,
        notes: str | _Unchanged = UNCHANGED,
        category_id: UUID | None | _Unchanged = UNCHANGED,
    ) -> Clip:
        clip = self.clip(clip_id)
        changes: dict[str, Any] = {
            field: value
            for field, value in (
                ("name", name),
                ("start_ms", start_ms),
                ("end_ms", end_ms),
                ("notes", notes),
                ("category_id", category_id),
            )
            if not isinstance(value, _Unchanged)
        }
        updated = self._validated_clip(replace(clip, **changes))
        if updated == clip:
            return clip
        self._clips[self._clips.index(clip)] = updated
        self._revision += 1
        return updated

    def remove_clip(self, clip_id: UUID) -> None:
        clip = self.clip(clip_id)
        self._clips.remove(clip)
        self._renumber_clips()
        self._revision += 1

    def _validated_clip(self, clip: Clip) -> Clip:
        source_video = _with_id(self._source_videos, clip.source_video_id)
        if source_video is None:
            raise InvalidAnalysisDataError("Clip refers to an unknown Source video")
        if clip.category_id is not None:
            if not isinstance(clip.category_id, UUID):
                raise InvalidAnalysisDataError("Clip Category identity must be a UUID")
            if all(category.id != clip.category_id for category in self._categories):
                raise InvalidAnalysisDataError("Clip refers to an unknown Category")
        if (
            isinstance(clip.start_ms, bool)
            or not isinstance(clip.start_ms, int)
            or isinstance(clip.end_ms, bool)
            or not isinstance(clip.end_ms, int)
            or clip.start_ms < 0
            or clip.end_ms <= clip.start_ms
        ):
            raise InvalidAnalysisDataError(
                "Clip interval must satisfy 0 <= start_ms < end_ms"
            )
        if (
            source_video.duration_ms is not None
            and clip.end_ms > source_video.duration_ms
        ):
            raise InvalidAnalysisDataError(
                "Clip end_ms exceeds its Source video duration"
            )
        if not isinstance(clip.name, str) or not clip.name.strip():
            raise InvalidAnalysisDataError("Clip name must not be empty")
        if not isinstance(clip.notes, str):
            raise InvalidAnalysisDataError("Clip notes must be text")
        return clip

    def _renumber_clips(self) -> None:
        self._clips = [
            replace(clip, creation_order=order)
            for order, clip in enumerate(self._clips)
        ]


class _Identified(Protocol):
    @property
    def id(self) -> UUID: ...


_IdentifiedT = TypeVar("_IdentifiedT", bound=_Identified)


def _with_id(
    entities: Sequence[_IdentifiedT],
    entity_id: UUID,
) -> _IdentifiedT | None:
    return next(
        (entity for entity in entities if entity.id == entity_id),
        None,
    )


def _required(entity: _IdentifiedT | None, message: str) -> _IdentifiedT:
    if entity is None:
        raise UnknownEntityError(message)
    return entity


def normalize_category_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise InvalidAnalysisDataError("Category name must not be empty")
    return name.strip().casefold()


def _validate_optional_non_negative_integer(
    value: int | None,
    field: str,
) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidAnalysisDataError(f"{field} must be a non-negative integer")
