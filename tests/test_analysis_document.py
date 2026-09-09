from __future__ import annotations

import pickle
import json
import os
import sys
import types
from pathlib import Path

import pytest

from analysis import (
    AnalysisDocument,
    InvalidAnalysisDataError,
    LegacySourceOverwriteError,
    MalformedJSONError,
    SaveAsRequiredError,
    UnsafeLegacyAnalysisError,
    UnsupportedContentError,
    UnsupportedSchemaVersionError,
)


def _legacy_analysis_bytes(video_path: str) -> bytes:
    legacy_module = types.ModuleType("treewidget_item")
    legacy_clip_type = type("ClipItem", (), {})
    legacy_clip_type.__module__ = legacy_module.__name__
    setattr(legacy_module, "ClipItem", legacy_clip_type)

    original_module = sys.modules.get(legacy_module.__name__)
    sys.modules[legacy_module.__name__] = legacy_module
    try:
        first_clip = legacy_clip_type()
        first_clip.name = "Fast break"
        first_clip.start_position = 1_250
        first_clip.end_position = 4_500
        first_clip.notes = "Left wing finishes"
        first_clip.category = "Angriff"

        second_clip = legacy_clip_type()
        second_clip.name = "Defensive stop"
        second_clip.start_position = 8_000
        second_clip.end_position = 10_250
        second_clip.notes = ""
        second_clip.category = "Abwehr"

        third_clip = legacy_clip_type()
        third_clip.name = "Transition"
        third_clip.start_position = 12_000
        third_clip.end_position = 13_000
        third_clip.notes = "Uncategorized"
        third_clip.category = None

        return pickle.dumps(
            (video_path, [first_clip, second_clip, third_clip]),
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    finally:
        if original_module is None:
            del sys.modules[legacy_module.__name__]
        else:
            sys.modules[legacy_module.__name__] = original_module


def test_opening_legacy_analysis_preserves_analytical_content(tmp_path: Path) -> None:
    legacy_path = tmp_path / "Cup Final.analysis"
    video_path = str(tmp_path / "match.mp4")
    legacy_path.write_bytes(_legacy_analysis_bytes(video_path))

    document = AnalysisDocument.new("Current analysis")
    document.load(legacy_path)

    assert document.analysis.title == "Cup Final"
    assert [source.location for source in document.analysis.source_videos] == [video_path]
    assert [category.name for category in document.analysis.categories] == [
        "Angriff",
        "Abwehr",
    ]
    assert [clip.name for clip in document.analysis.clips] == [
        "Fast break",
        "Defensive stop",
        "Transition",
    ]
    assert [
        (clip.start_ms, clip.end_ms, clip.notes) for clip in document.analysis.clips
    ] == [
        (1_250, 4_500, "Left wing finishes"),
        (8_000, 10_250, ""),
        (12_000, 13_000, "Uncategorized"),
    ]
    categories_by_id = {
        category.id: category.name for category in document.analysis.categories
    }
    assert [
        None
        if clip.category_id is None
        else categories_by_id[clip.category_id]
        for clip in document.analysis.clips
    ] == ["Angriff", "Abwehr", None]
    assert [clip.creation_order for clip in document.analysis.clips] == [0, 1, 2]
    assert document.requires_save_as
    assert document.path is None

    original_bytes = legacy_path.read_bytes()
    with pytest.raises(LegacySourceOverwriteError, match="original legacy"):
        document.save_as(legacy_path)
    assert legacy_path.read_bytes() == original_bytes


def test_legacy_analysis_requires_save_as_then_round_trips_as_json(
    tmp_path: Path,
) -> None:
    legacy_path = tmp_path / "original.data"
    original_bytes = _legacy_analysis_bytes(str(tmp_path / "match.mp4"))
    legacy_path.write_bytes(original_bytes)
    document = AnalysisDocument.new()
    document.load(legacy_path)
    imported_state = (
        document.analysis.id,
        document.analysis.title,
        document.analysis.source_videos,
        document.analysis.categories,
        document.analysis.clips,
    )

    with pytest.raises(SaveAsRequiredError, match="Save As"):
        document.save()

    saved_path = document.save_as(tmp_path / "converted")

    assert saved_path == tmp_path / "converted.analysis"
    assert legacy_path.read_bytes() == original_bytes
    assert json.loads(saved_path.read_text(encoding="utf-8"))["schema_version"] == 1
    assert not document.requires_save_as
    assert not document.dirty

    reopened = AnalysisDocument.new()
    reopened.load(saved_path)
    assert (
        reopened.analysis.id,
        reopened.analysis.title,
        reopened.analysis.source_videos,
        reopened.analysis.categories,
        reopened.analysis.clips,
    ) == imported_state


def test_invalid_duplicate_identity_does_not_replace_open_analysis(
    tmp_path: Path,
) -> None:
    duplicate_source_id = "9ea5191b-ad7f-4b16-9995-9d8aa530419e"
    invalid_path = tmp_path / "invalid.analysis"
    invalid_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "analysis": {
                    "id": "46a96e8d-9f14-4927-b5cd-f1ea68da7d30",
                    "title": "Invalid",
                    "source_videos": [
                        {
                            "id": duplicate_source_id,
                            "display_name": "First",
                            "location": "/videos/first.mp4",
                            "relative_path": None,
                            "duration_ms": None,
                            "byte_size": None,
                            "fingerprint": None,
                        },
                        {
                            "id": duplicate_source_id,
                            "display_name": "Second",
                            "location": "/videos/second.mp4",
                            "relative_path": None,
                            "duration_ms": None,
                            "byte_size": None,
                            "fingerprint": None,
                        },
                    ],
                    "categories": [],
                    "clips": [],
                },
            }
        ),
        encoding="utf-8",
    )
    document = AnalysisDocument.new("Keep this Analysis")
    original_analysis = document.analysis

    with pytest.raises(InvalidAnalysisDataError, match="identity"):
        document.load(invalid_path)

    assert document.analysis is original_analysis
    assert document.analysis.title == "Keep this Analysis"


class _ExecutableReducer:
    def __init__(self, marker_path: Path) -> None:
        self._marker_path = marker_path

    def __reduce__(self) -> tuple[object, tuple[str]]:
        return os.system, (f"touch {self._marker_path}",)


def test_executable_legacy_reducer_is_rejected_without_side_effects(
    tmp_path: Path,
) -> None:
    marker_path = tmp_path / "reducer-ran"
    hostile_path = tmp_path / "hostile.analysis"
    hostile_path.write_bytes(
        pickle.dumps(_ExecutableReducer(marker_path), protocol=pickle.HIGHEST_PROTOCOL)
    )
    document = AnalysisDocument.new("Still open")
    original_analysis = document.analysis

    with pytest.raises(UnsafeLegacyAnalysisError, match="unsupported global"):
        document.load(hostile_path)

    assert not marker_path.exists()
    assert document.analysis is original_analysis


@pytest.mark.parametrize(
    ("filename", "content", "error_type"),
    [
        ("malformed.analysis", b'{"schema_version":', MalformedJSONError),
        ("unsupported.analysis", b"not an Analysis", UnsupportedContentError),
        (
            "newer.analysis",
            json.dumps({"schema_version": 2, "analysis": {}}).encode("utf-8"),
            UnsupportedSchemaVersionError,
        ),
    ],
)
def test_specific_load_failures_leave_current_analysis_open(
    tmp_path: Path,
    filename: str,
    content: bytes,
    error_type: type[Exception],
) -> None:
    bad_path = tmp_path / filename
    bad_path.write_bytes(content)
    document = AnalysisDocument.new("Still open")
    original_analysis = document.analysis

    with pytest.raises(error_type):
        document.load(bad_path)

    assert document.analysis is original_analysis
    assert document.analysis.title == "Still open"
