from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from .errors import InvalidAnalysisDataError


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


class Analysis:
    """UI-independent analytical content with stable entity identities."""

    def __init__(self, title: str, *, analysis_id: UUID | None = None) -> None:
        if not isinstance(title, str):
            raise InvalidAnalysisDataError("Analysis title must be text")
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
        identity = source_video_id or uuid4()
        if any(source.id == identity for source in self._source_videos):
            raise InvalidAnalysisDataError("Source-video identity must be unique")
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

    def add_category(
        self,
        name: str,
        color: str = "#808080",
        *,
        category_id: UUID | None = None,
    ) -> Category:
        normalized_name = _normalized_category_name(name)
        if any(
            _normalized_category_name(category.name) == normalized_name
            for category in self._categories
        ):
            raise InvalidAnalysisDataError(
                f"Category names must be unique: {name!r}"
            )
        identity = category_id or uuid4()
        if any(category.id == identity for category in self._categories):
            raise InvalidAnalysisDataError("Category identity must be unique")
        category = Category(identity, name.strip(), color)
        self._categories.append(category)
        self._revision += 1
        return category

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
        source_video = next(
            (source for source in self._source_videos if source.id == source_video_id),
            None,
        )
        if source_video is None:
            raise InvalidAnalysisDataError("Clip refers to an unknown Source video")
        if category_id is not None and all(
            category.id != category_id for category in self._categories
        ):
            raise InvalidAnalysisDataError("Clip refers to an unknown Category")
        if (
            isinstance(start_ms, bool)
            or not isinstance(start_ms, int)
            or isinstance(end_ms, bool)
            or not isinstance(end_ms, int)
            or start_ms < 0
            or end_ms <= start_ms
        ):
            raise InvalidAnalysisDataError(
                "Clip interval must satisfy 0 <= start_ms < end_ms"
            )
        if source_video.duration_ms is not None and end_ms > source_video.duration_ms:
            raise InvalidAnalysisDataError(
                "Clip end_ms exceeds its Source video duration"
            )
        order = len(self._clips) if creation_order is None else creation_order
        identity = clip_id or uuid4()
        if any(clip.id == identity for clip in self._clips):
            raise InvalidAnalysisDataError("Clip identity must be unique")
        clip = Clip(
            id=identity,
            source_video_id=source_video_id,
            name=name,
            start_ms=start_ms,
            end_ms=end_ms,
            notes=notes,
            category_id=category_id,
            creation_order=order,
        )
        self._clips.append(clip)
        self._revision += 1
        return clip


def _normalized_category_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise InvalidAnalysisDataError("Category name must not be empty")
    return name.strip().casefold()
