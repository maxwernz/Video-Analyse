from __future__ import annotations

import builtins
import copyreg
import io
import pickle
from pathlib import Path, PureWindowsPath
from typing import Any

from .errors import InvalidAnalysisDataError, UnsafeLegacyAnalysisError
from .model import Analysis, Category, normalize_category_name


class _LegacyClip:
    """Inert target for the one historical class accepted by the importer."""


class _RestrictedLegacyUnpickler(pickle.Unpickler):
    _SAFE_BUILTINS = {"dict", "frozenset", "list", "object", "set", "tuple"}

    def find_class(self, module: str, name: str) -> Any:
        if module == "treewidget_item" and name == "ClipItem":
            return _LegacyClip
        if module in {"builtins", "__builtin__"} and name in self._SAFE_BUILTINS:
            return getattr(builtins, name)
        if module in {"copyreg", "copy_reg"} and name == "_reconstructor":
            return getattr(copyreg, name)
        raise UnsafeLegacyAnalysisError(
            f"Legacy Analysis contains unsupported global {module}.{name}"
        )

    def persistent_load(self, pid: object) -> Any:
        raise UnsafeLegacyAnalysisError(
            f"Legacy Analysis contains unsupported persistent reference {pid!r}"
        )


class LegacyAnalysisImporter:
    """Converts the exact historical single-video pickle without UI imports."""

    _CLIP_FIELDS = {
        "name",
        "start_position",
        "end_position",
        "notes",
        "category",
    }

    def import_bytes(self, data: bytes, source_path: Path) -> Analysis:
        pickle_stream = io.BytesIO(data)
        try:
            payload = _RestrictedLegacyUnpickler(pickle_stream).load()
        except UnsafeLegacyAnalysisError:
            raise
        except Exception as error:
            raise InvalidAnalysisDataError(
                "Legacy Analysis payload is malformed"
            ) from error
        if pickle_stream.read():
            raise InvalidAnalysisDataError(
                "Legacy Analysis contains unsupported trailing content"
            )

        if (
            not isinstance(payload, tuple)
            or len(payload) != 2
            or not isinstance(payload[0], str)
            or not isinstance(payload[1], list)
        ):
            raise InvalidAnalysisDataError(
                "Legacy Analysis must contain a Source-video path and Clip list"
            )

        video_path, legacy_clips = payload
        analysis = Analysis(source_path.stem)
        source_video = analysis.add_source_video(
            _display_name(video_path),
            video_path,
            relative_path=_relative_path(video_path, source_path.parent),
        )

        categories_by_name: dict[str, Category] = {}
        for position, legacy_clip in enumerate(legacy_clips):
            if not isinstance(legacy_clip, _LegacyClip):
                raise InvalidAnalysisDataError(
                    "Legacy Analysis contains an unsupported Clip value"
                )
            state = vars(legacy_clip)
            if set(state) != self._CLIP_FIELDS:
                raise InvalidAnalysisDataError(
                    "Legacy Clip does not match the historical representation"
                )

            category_name = state["category"]
            category_id = None
            if category_name is not None:
                if not isinstance(category_name, str):
                    raise InvalidAnalysisDataError("Legacy Category name must be text")
                normalized_name = normalize_category_name(category_name)
                category = categories_by_name.get(normalized_name)
                if category is None:
                    category = analysis.add_category(category_name)
                    categories_by_name[normalized_name] = category
                category_id = category.id

            name = state["name"]
            notes = state["notes"]
            if not isinstance(name, str) or not isinstance(notes, str):
                raise InvalidAnalysisDataError("Legacy Clip text fields must be text")
            analysis.add_clip(
                source_video.id,
                name,
                state["start_position"],
                state["end_position"],
                notes=notes,
                category_id=category_id,
                creation_order=position,
            )
        return analysis


def _display_name(location: str) -> str:
    if "\\" in location:
        return PureWindowsPath(location).name
    return Path(location).name


def _relative_path(location: str, analysis_directory: Path) -> str | None:
    media_path = Path(location)
    if not media_path.is_absolute():
        return location
    try:
        return str(media_path.relative_to(analysis_directory))
    except ValueError:
        return None
