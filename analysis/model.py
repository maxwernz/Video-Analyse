from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Final
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

    def set_title(self, title: str) -> None:
        if not isinstance(title, str):
            raise InvalidAnalysisDataError("Analysis title must be text")
        if title == self._title:
            return
        self._title = title
        self._revision += 1

    def source_video(self, source_video_id: UUID) -> SourceVideo:
        source_video = next(
            (source for source in self._source_videos if source.id == source_video_id),
            None,
        )
        if source_video is None:
            raise UnknownEntityError("Analysis has no such Source video")
        return source_video

    def category(self, category_id: UUID) -> Category:
        category = next(
            (existing for existing in self._categories if existing.id == category_id),
            None,
        )
        if category is None:
            raise UnknownEntityError("Analysis has no such Category")
        return category

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
        clip = next(
            (existing for existing in self._clips if existing.id == clip_id),
            None,
        )
        if clip is None:
            raise UnknownEntityError("Analysis has no such Clip")
        return clip

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
        source_video = next(
            (
                source
                for source in self._source_videos
                if source.id == clip.source_video_id
            ),
            None,
        )
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
