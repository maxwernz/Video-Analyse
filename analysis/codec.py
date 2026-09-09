from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from .errors import (
    InvalidAnalysisDataError,
    MalformedJSONError,
    UnsupportedContentError,
    UnsupportedSchemaVersionError,
)
from .legacy import LegacyAnalysisImporter
from .model import Analysis, Category, Clip, SourceVideo


CURRENT_SCHEMA_VERSION = 1


class AnalysisFileFormat(Enum):
    JSON = "json"
    LEGACY_PICKLE = "legacy_pickle"


@dataclass(frozen=True, slots=True)
class DecodedAnalysis:
    analysis: Analysis
    file_format: AnalysisFileFormat


class AnalysisFileCodec:
    def __init__(self, legacy_importer: LegacyAnalysisImporter | None = None) -> None:
        self._legacy_importer = legacy_importer or LegacyAnalysisImporter()

    def decode(self, data: bytes, source_path: Path) -> DecodedAnalysis:
        json_candidate = data.lstrip()
        if json_candidate.startswith(b"\xef\xbb\xbf"):
            json_candidate = json_candidate[3:].lstrip()
        if json_candidate.startswith((b"{", b"[")):
            return DecodedAnalysis(
                self._decode_json(data),
                AnalysisFileFormat.JSON,
            )
        if data.startswith(b"\x80"):
            return DecodedAnalysis(
                self._legacy_importer.import_bytes(data, source_path),
                AnalysisFileFormat.LEGACY_PICKLE,
            )
        raise UnsupportedContentError(
            "Analysis file is neither versioned JSON nor supported legacy content"
        )

    def encode(self, analysis: Analysis) -> bytes:
        payload = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "analysis": {
                "id": str(analysis.id),
                "title": analysis.title,
                "source_videos": [
                    self._source_video_to_data(source) for source in analysis.source_videos
                ],
                "categories": [
                    self._category_to_data(category)
                    for category in analysis.categories
                ],
                "clips": [self._clip_to_data(clip) for clip in analysis.clips],
            },
        }
        return (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")

    def _decode_json(self, data: bytes) -> Analysis:
        try:
            payload = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise MalformedJSONError("Analysis contains malformed UTF-8 JSON") from error

        root = _mapping(payload, "Analysis file root")
        schema_version = root.get("schema_version")
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise InvalidAnalysisDataError("schema_version must be an integer")
        if schema_version != CURRENT_SCHEMA_VERSION:
            direction = "newer" if schema_version > CURRENT_SCHEMA_VERSION else "older"
            raise UnsupportedSchemaVersionError(
                f"Analysis schema version {schema_version} is an unsupported {direction} version"
            )

        analysis_data = _mapping(root.get("analysis"), "analysis")
        try:
            analysis = Analysis(
                _text(analysis_data.get("title"), "analysis.title"),
                analysis_id=_uuid(analysis_data.get("id"), "analysis.id"),
            )
            for index, source_data_value in enumerate(
                _list(analysis_data.get("source_videos"), "analysis.source_videos")
            ):
                source_data = _mapping(
                    source_data_value, f"analysis.source_videos[{index}]"
                )
                analysis.add_source_video(
                    _text(source_data.get("display_name"), "Source video display_name"),
                    _text(source_data.get("location"), "Source video location"),
                    source_video_id=_uuid(source_data.get("id"), "Source video id"),
                    relative_path=_optional_text(
                        source_data.get("relative_path"), "Source video relative_path"
                    ),
                    duration_ms=_optional_int(
                        source_data.get("duration_ms"), "Source video duration_ms"
                    ),
                    byte_size=_optional_int(
                        source_data.get("byte_size"), "Source video byte_size"
                    ),
                    fingerprint=_optional_text(
                        source_data.get("fingerprint"), "Source video fingerprint"
                    ),
                )
            for index, category_data_value in enumerate(
                _list(analysis_data.get("categories"), "analysis.categories")
            ):
                category_data = _mapping(
                    category_data_value, f"analysis.categories[{index}]"
                )
                analysis.add_category(
                    _text(category_data.get("name"), "Category name"),
                    _text(category_data.get("color"), "Category color"),
                    category_id=_uuid(category_data.get("id"), "Category id"),
                )
            for index, clip_data_value in enumerate(
                _list(analysis_data.get("clips"), "analysis.clips")
            ):
                clip_data = _mapping(clip_data_value, f"analysis.clips[{index}]")
                raw_category_id = clip_data.get("category_id")
                analysis.add_clip(
                    _uuid(clip_data.get("source_video_id"), "Clip source_video_id"),
                    _text(clip_data.get("name"), "Clip name"),
                    _integer(clip_data.get("start_ms"), "Clip start_ms"),
                    _integer(clip_data.get("end_ms"), "Clip end_ms"),
                    notes=_text(clip_data.get("notes"), "Clip notes"),
                    category_id=(
                        None
                        if raw_category_id is None
                        else _uuid(raw_category_id, "Clip category_id")
                    ),
                    clip_id=_uuid(clip_data.get("id"), "Clip id"),
                    creation_order=_integer(
                        clip_data.get("creation_order"), "Clip creation_order"
                    ),
                )
        except (TypeError, ValueError) as error:
            raise InvalidAnalysisDataError("Analysis contains invalid domain data") from error
        if not analysis.source_videos:
            raise InvalidAnalysisDataError(
                "An Analysis file must contain at least one Source video"
            )
        return analysis

    @staticmethod
    def _source_video_to_data(source: SourceVideo) -> dict[str, object]:
        return {
            "id": str(source.id),
            "display_name": source.display_name,
            "location": source.location,
            "relative_path": source.relative_path,
            "duration_ms": source.duration_ms,
            "byte_size": source.byte_size,
            "fingerprint": source.fingerprint,
        }

    @staticmethod
    def _category_to_data(category: Category) -> dict[str, object]:
        return {
            "id": str(category.id),
            "name": category.name,
            "color": category.color,
        }

    @staticmethod
    def _clip_to_data(clip: Clip) -> dict[str, object]:
        return {
            "id": str(clip.id),
            "source_video_id": str(clip.source_video_id),
            "name": clip.name,
            "start_ms": clip.start_ms,
            "end_ms": clip.end_ms,
            "notes": clip.notes,
            "category_id": None if clip.category_id is None else str(clip.category_id),
            "creation_order": clip.creation_order,
        }


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise InvalidAnalysisDataError(f"{field} must be an object")
    return value


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise InvalidAnalysisDataError(f"{field} must be an array")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidAnalysisDataError(f"{field} must be text")
    return value


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidAnalysisDataError(f"{field} must be an integer")
    return value


def _optional_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    return _integer(value, field)


def _uuid(value: object, field: str) -> UUID:
    if not isinstance(value, str):
        raise InvalidAnalysisDataError(f"{field} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as error:
        raise InvalidAnalysisDataError(f"{field} must be a UUID string") from error
