from __future__ import annotations

import pickle
import json
import os
import shutil
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from analysis import (
    Analysis,
    AnalysisDocument,
    EmptyAnalysisError,
    ExternalModificationError,
    InvalidAnalysisDataError,
    LegacySourceOverwriteError,
    MalformedJSONError,
    SaveAsRequiredError,
    UnsafeLegacyAnalysisError,
    UnsupportedContentError,
    UnsupportedSchemaVersionError,
)


def _legacy_analysis_bytes(
    video_path: str,
    protocol: int = pickle.HIGHEST_PROTOCOL,
) -> bytes:
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
            protocol=protocol,
        )
    finally:
        if original_module is None:
            del sys.modules[legacy_module.__name__]
        else:
            sys.modules[legacy_module.__name__] = original_module


@pytest.mark.parametrize("protocol", [0, 1, pickle.HIGHEST_PROTOCOL])
def test_opening_legacy_analysis_preserves_analytical_content(
    tmp_path: Path,
    protocol: int,
) -> None:
    legacy_path = tmp_path / "Cup Final.analysis"
    video_path = str(tmp_path / "match.mp4")
    legacy_path.write_bytes(_legacy_analysis_bytes(video_path, protocol))

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


def test_renamed_and_reordered_source_videos_survive_save_and_reopen(
    tmp_path: Path,
) -> None:
    document = AnalysisDocument.new("Match")
    first = document.analysis.add_source_video(
        "first-half.mp4",
        "/videos/first-half.mp4",
        duration_ms=2_700_000,
        byte_size=123_456,
        fingerprint="sampled-sha256:first",
    )
    second = document.analysis.add_source_video(
        "second-half.mp4",
        "/videos/second-half.mp4",
        duration_ms=2_700_000,
        byte_size=654_321,
        fingerprint="sampled-sha256:second",
    )
    first_clip = document.analysis.add_clip(first.id, "Fast break", 1_000, 2_000)
    second_clip = document.analysis.add_clip(second.id, "Turnover", 3_000, 4_000)

    document.analysis.rename_source_video(first.id, "Halbzeit 1")
    document.analysis.reorder_source_videos([second.id, first.id])

    saved_path = document.save_as(tmp_path / "match")
    reopened = AnalysisDocument.new()
    reopened.load(saved_path)

    reopened_sources = reopened.analysis.source_videos
    assert [source.id for source in reopened_sources] == [second.id, first.id]
    assert reopened.analysis.source_video(first.id).display_name == "Halbzeit 1"
    assert reopened.analysis.source_video(first.id).byte_size == 123_456
    assert reopened.analysis.source_video(first.id).fingerprint == (
        "sampled-sha256:first"
    )
    assert reopened.analysis.clip(first_clip.id).source_video_id == first.id
    assert reopened.analysis.clip(second_clip.id).source_video_id == second.id


def test_an_empty_analysis_after_removing_its_last_source_video_cannot_be_saved(
    tmp_path: Path,
) -> None:
    document = AnalysisDocument.new("Match")
    source_video = document.analysis.add_source_video(
        "first-half.mp4", "/videos/first-half.mp4"
    )

    document.analysis.remove_source_video(source_video.id)

    assert document.analysis.source_videos == ()
    with pytest.raises(EmptyAnalysisError):
        document.save_as(tmp_path / "match")

    document.analysis.add_source_video(
        "second-half.mp4", "/videos/second-half.mp4"
    )
    saved_path = document.save_as(tmp_path / "match")
    assert saved_path.is_file()


@pytest.mark.parametrize("duplicate_kind", ["identity", "media"])
def test_invalid_duplicate_source_does_not_replace_open_analysis(
    tmp_path: Path,
    duplicate_kind: str,
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
                            "fingerprint": (
                                "sampled-sha256:same"
                                if duplicate_kind == "media"
                                else None
                            ),
                        },
                        {
                            "id": (
                                duplicate_source_id
                                if duplicate_kind == "identity"
                                else "560acaff-81e7-4815-805a-4fcc1200121d"
                            ),
                            "display_name": "Second",
                            "location": "/videos/second.mp4",
                            "relative_path": None,
                            "duration_ms": None,
                            "byte_size": None,
                            "fingerprint": (
                                "sampled-sha256:same"
                                if duplicate_kind == "media"
                                else None
                            ),
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

    expected_message = "identity" if duplicate_kind == "identity" else "already"
    with pytest.raises(InvalidAnalysisDataError, match=expected_message):
        document.load(invalid_path)

    assert document.analysis is original_analysis
    assert document.analysis.title == "Keep this Analysis"


@pytest.mark.parametrize(
    "invalid_value",
    [
        "empty display name",
        "empty location",
        "negative duration",
        "negative byte size",
        "duplicate creation order",
    ],
)
def test_invalid_domain_values_do_not_replace_open_analysis(
    tmp_path: Path,
    invalid_value: str,
) -> None:
    source_id = "9ea5191b-ad7f-4b16-9995-9d8aa530419e"
    payload: dict[str, Any] = {
        "schema_version": 1,
        "analysis": {
            "id": "46a96e8d-9f14-4927-b5cd-f1ea68da7d30",
            "title": "Invalid",
            "source_videos": [
                {
                    "id": source_id,
                    "display_name": "Match",
                    "location": "/videos/match.mp4",
                    "relative_path": "match.mp4",
                    "duration_ms": 2_000,
                    "byte_size": 1_024,
                    "fingerprint": "sampled-sha256:abc",
                }
            ],
            "categories": [],
            "clips": [
                {
                    "id": "ea486d7e-9e85-48fb-9df3-8ab314b6e4ba",
                    "source_video_id": source_id,
                    "name": "First",
                    "start_ms": 0,
                    "end_ms": 500,
                    "notes": "",
                    "category_id": None,
                    "creation_order": 0,
                },
                {
                    "id": "d4b7e65c-25eb-462e-84b3-814ce0595af7",
                    "source_video_id": source_id,
                    "name": "Second",
                    "start_ms": 500,
                    "end_ms": 1_000,
                    "notes": "",
                    "category_id": None,
                    "creation_order": 1,
                },
            ],
        },
    }
    source = payload["analysis"]["source_videos"][0]
    if invalid_value == "empty display name":
        source["display_name"] = "   "
    elif invalid_value == "empty location":
        source["location"] = ""
    elif invalid_value == "negative duration":
        source["duration_ms"] = -1
    elif invalid_value == "negative byte size":
        source["byte_size"] = -1
    else:
        payload["analysis"]["clips"][1]["creation_order"] = 0

    invalid_path = tmp_path / "invalid-domain.analysis"
    invalid_path.write_text(json.dumps(payload), encoding="utf-8")
    document = AnalysisDocument.new("Keep this Analysis")
    original_analysis = document.analysis

    with pytest.raises(InvalidAnalysisDataError):
        document.load(invalid_path)

    assert document.analysis is original_analysis


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


# --- Atomic saves, interrupted and failed writes ---------------------------


def _document_with_source(title: str = "Match") -> AnalysisDocument:
    document = AnalysisDocument.new(title)
    document.analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    return document


def test_a_successful_save_writes_no_leftover_temporary_files(tmp_path: Path) -> None:
    document = _document_with_source()
    saved_path = document.save_as(tmp_path / "match")

    assert saved_path.is_file()
    assert list(tmp_path.iterdir()) == [saved_path]
    assert not document.dirty


def test_an_interrupted_write_leaves_the_prior_file_intact_and_stays_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = _document_with_source()
    saved_path = document.save_as(tmp_path / "match")
    original_bytes = saved_path.read_bytes()
    assert not document.dirty

    document.analysis.set_title("Edited after saving")
    assert document.dirty

    def _failing_replace(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", _failing_replace)

    with pytest.raises(OSError):
        document.save()

    assert saved_path.read_bytes() == original_bytes
    assert document.dirty
    assert [entry.name for entry in tmp_path.iterdir()] == [saved_path.name]


def test_a_failed_flush_leaves_the_prior_file_intact_and_stays_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = _document_with_source()
    saved_path = document.save_as(tmp_path / "match")
    original_bytes = saved_path.read_bytes()
    document.analysis.set_title("Edited after saving")

    def _failing_fsync(*_args: object, **_kwargs: object) -> None:
        raise OSError("I/O error")

    monkeypatch.setattr(os, "fsync", _failing_fsync)

    with pytest.raises(OSError):
        document.save()

    assert saved_path.read_bytes() == original_bytes
    assert document.dirty
    assert [entry.name for entry in tmp_path.iterdir()] == [saved_path.name]


def test_a_validation_failure_leaves_the_prior_file_intact_and_stays_dirty(
    tmp_path: Path,
) -> None:
    document = _document_with_source()
    saved_path = document.save_as(tmp_path / "match")
    original_bytes = saved_path.read_bytes()
    source_video = document.analysis.source_videos[0]

    document.analysis.remove_source_video(source_video.id)
    assert document.dirty

    with pytest.raises(EmptyAnalysisError):
        document.save()

    assert saved_path.read_bytes() == original_bytes
    assert document.dirty
    assert [entry.name for entry in tmp_path.iterdir()] == [saved_path.name]


def test_a_permission_failure_leaves_the_prior_file_intact_and_stays_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = _document_with_source()
    saved_path = document.save_as(tmp_path / "match")
    original_bytes = saved_path.read_bytes()
    document.analysis.set_title("Edited after saving")

    def _denied_mkstemp(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr("tempfile.mkstemp", _denied_mkstemp)

    with pytest.raises(PermissionError):
        document.save()

    assert saved_path.read_bytes() == original_bytes
    assert document.dirty


# --- External-modification detection and reload -----------------------------


def test_a_freshly_saved_file_has_no_external_modification(tmp_path: Path) -> None:
    document = _document_with_source()
    document.save_as(tmp_path / "match")

    assert not document.has_external_modification()


def test_a_freshly_loaded_file_has_no_external_modification(tmp_path: Path) -> None:
    written = _document_with_source()
    saved_path = written.save_as(tmp_path / "match")

    reopened = AnalysisDocument.new()
    reopened.load(saved_path)

    assert not reopened.has_external_modification()


def test_saving_over_a_file_changed_outside_the_application_is_refused(
    tmp_path: Path,
) -> None:
    document = _document_with_source()
    saved_path = document.save_as(tmp_path / "match")
    document.analysis.set_title("My unsaved edit")

    # A change from outside this process: different bytes, and a distinct
    # modification time from whatever `save_as` just wrote.
    os.utime(saved_path, ns=(0, 10**18))
    saved_path.write_bytes(saved_path.read_bytes() + b"\n")
    external_bytes = saved_path.read_bytes()

    with pytest.raises(ExternalModificationError):
        document.save()

    assert saved_path.read_bytes() == external_bytes
    assert document.dirty


def test_reload_replaces_in_memory_content_from_the_file_on_disk(
    tmp_path: Path,
) -> None:
    document = _document_with_source("Original title")
    saved_path = document.save_as(tmp_path / "match")

    # Simulate another process (or another window) saving over the file.
    other = AnalysisDocument.new("Title from elsewhere")
    other.analysis.add_source_video("second-half.mp4", "/videos/second-half.mp4")
    other.save_as(saved_path)

    document.analysis.set_title("Unsaved local edit")
    assert document.dirty

    document.reload()

    assert document.analysis.title == "Title from elsewhere"
    assert not document.dirty
    assert not document.has_external_modification()


def test_a_failed_reload_leaves_the_open_analysis_untouched(tmp_path: Path) -> None:
    document = _document_with_source("Kept in memory")
    saved_path = document.save_as(tmp_path / "match")
    original_analysis = document.analysis

    saved_path.write_bytes(b"not an Analysis")

    with pytest.raises(UnsupportedContentError):
        document.reload()

    assert document.analysis is original_analysis
    assert document.analysis.title == "Kept in memory"


def test_reload_without_a_file_requires_save_as(tmp_path: Path) -> None:
    document = _document_with_source()

    with pytest.raises(SaveAsRequiredError):
        document.reload()


# --- Recovered content is never mistaken for a successful save -------------


def test_recovered_content_is_dirty_even_though_nothing_has_edited_it() -> None:
    analysis = Analysis("Recovered analysis")
    analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")

    document = AnalysisDocument.recovered(analysis)

    assert document.dirty
    assert document.path is None
    assert not document.requires_save_as


def test_recovered_content_becomes_clean_once_explicitly_saved(tmp_path: Path) -> None:
    analysis = Analysis("Recovered analysis")
    analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    document = AnalysisDocument.recovered(analysis)

    document.save_as(tmp_path / "restored")

    assert not document.dirty


def test_recovered_content_keeps_the_file_it_was_being_edited_as(
    tmp_path: Path,
) -> None:
    original = _document_with_source("Original title")
    saved_path = original.save_as(tmp_path / "match")

    analysis = Analysis("Recovered work")
    analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    document = AnalysisDocument.recovered(analysis, saved_path)

    assert document.path == saved_path
    assert document.dirty
    # No revision was ever observed for this file, so a save must not assume
    # the file is still whatever it was before the abnormal termination.
    assert document.has_external_modification()


def test_recovered_content_with_no_bound_file_has_no_external_modification() -> None:
    analysis = Analysis("Recovered work")
    analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")

    document = AnalysisDocument.recovered(analysis, None)

    assert document.path is None
    assert not document.has_external_modification()


# --- Opening an Analysis with missing media ---------------------------------
#
# Unavailability is a display state of a Source video, not a load failure:
# these tests load real `.analysis` files whose recorded media does not
# exist, and assert the Analysis still opens with every Source video and
# every Clip intact.


def test_an_analysis_with_every_source_video_present_is_fully_available(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "first-half.mp4"
    video_path.write_bytes(b"video")
    document = AnalysisDocument.new("Match")
    source_video = document.analysis.add_source_video(
        "first-half.mp4", str(video_path)
    )
    saved_path = document.save_as(tmp_path / "match")

    reopened = AnalysisDocument.new()
    reopened.load(saved_path)

    assert reopened.is_source_video_available(source_video.id)
    assert reopened.resolve_source_video(source_video.id) == video_path


def test_loading_with_an_unavailable_source_video_still_opens_and_keeps_its_clip(
    tmp_path: Path,
) -> None:
    document = AnalysisDocument.new("Match")
    source_video = document.analysis.add_source_video(
        "first-half.mp4", str(tmp_path / "gone.mp4"), duration_ms=10_000
    )
    clip = document.analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)
    saved_path = document.save_as(tmp_path / "match")

    reopened = AnalysisDocument.new()
    reopened.load(saved_path)

    assert reopened.analysis.source_videos == (
        reopened.analysis.source_video(source_video.id),
    )
    assert reopened.analysis.clip(clip.id).start_ms == 1_000
    assert not reopened.is_source_video_available(source_video.id)
    assert reopened.resolve_source_video(source_video.id) is None


def test_an_analysis_with_some_sources_missing_marks_only_those_unavailable(
    tmp_path: Path,
) -> None:
    present_path = tmp_path / "first-half.mp4"
    present_path.write_bytes(b"video")
    document = AnalysisDocument.new("Match")
    present = document.analysis.add_source_video("first-half.mp4", str(present_path))
    missing = document.analysis.add_source_video(
        "second-half.mp4", str(tmp_path / "second-half-gone.mp4")
    )
    saved_path = document.save_as(tmp_path / "match")

    reopened = AnalysisDocument.new()
    reopened.load(saved_path)

    assert reopened.is_source_video_available(present.id)
    assert not reopened.is_source_video_available(missing.id)


def test_a_source_video_and_its_analysis_moved_together_still_resolves(
    tmp_path: Path,
) -> None:
    """An Analysis and its video, copied to another folder, keep working.

    `relative_source_video_path` records the relative arrangement at add
    time; after both files move to a new home together, `resolve_source_video`
    must recover the video from that relative path alone, without the
    recorded absolute location ever being valid again.
    """

    original_directory = tmp_path / "original"
    videos_directory = original_directory / "videos"
    videos_directory.mkdir(parents=True)
    video_path = videos_directory / "first-half.mp4"
    video_path.write_bytes(b"video")
    document = AnalysisDocument.new("Match")
    # A brand-new document has no file yet, so nothing is relative to it; a
    # Source video is added first — an Analysis file needs at least one to
    # be saveable at all — and only once this document has a path of its own
    # does `relative_source_video_path` have anything to be relative to.
    # exactly the order `ApplicationWorkflow.add_source_video_file` uses when
    # the document it is adding to already has a home.
    source_video = document.analysis.add_source_video(
        "first-half.mp4", str(video_path)
    )
    saved_path = document.save_as(original_directory / "match.analysis")
    relative_path = document.relative_source_video_path(video_path)
    document.analysis.relink_source_video(
        source_video.id, str(video_path), relative_path=relative_path
    )
    document.save()

    moved_directory = tmp_path / "moved"
    moved_directory.mkdir()
    shutil.move(str(original_directory / "videos"), str(moved_directory / "videos"))
    shutil.move(str(saved_path), str(moved_directory / "match.analysis"))

    reopened = AnalysisDocument.new()
    reopened.load(moved_directory / "match.analysis")

    assert reopened.is_source_video_available(source_video.id)
    assert reopened.resolve_source_video(source_video.id) == (
        moved_directory / "videos" / "first-half.mp4"
    )


def test_relative_source_video_path_is_none_before_the_document_has_a_file() -> None:
    document = AnalysisDocument.new("Match")

    assert document.relative_source_video_path(Path("/videos/first-half.mp4")) is None
