"""`RecoverySnapshotStore` behaviour: atomic writes, honest reads, cleanup.

A Recovery snapshot must never be mistakable for an ordinary Analysis file —
these tests confirm both halves of that: `AnalysisDocument` never recognizes
one as something to open, and this store never offers back content that
merely looks like one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from analysis import Analysis, AnalysisFileCodec
from analysis.recovery import RECOVERY_MARKER, RecoverySnapshotStore


def _analysis(title: str = "Unsaved work") -> Analysis:
    analysis = Analysis(title)
    analysis.add_source_video("first-half.mp4", "/videos/first-half.mp4")
    return analysis


def test_a_written_snapshot_reads_back_with_its_content_and_source_path(
    tmp_path: Path,
) -> None:
    store = RecoverySnapshotStore(tmp_path / "recovery")
    analysis = _analysis("Restored title")
    source_path = tmp_path / "match.analysis"

    store.write(analysis, source_path)
    snapshot = store.read()

    assert snapshot is not None
    assert snapshot.analysis.title == "Restored title"
    assert [source.location for source in snapshot.analysis.source_videos] == [
        "/videos/first-half.mp4"
    ]
    assert snapshot.source_path == source_path
    assert snapshot.recorded_at > 0


def test_a_snapshot_with_no_bound_file_records_no_source_path(tmp_path: Path) -> None:
    store = RecoverySnapshotStore(tmp_path / "recovery")

    store.write(_analysis(), None)
    snapshot = store.read()

    assert snapshot is not None
    assert snapshot.source_path is None


def test_no_stored_snapshot_reads_back_as_none(tmp_path: Path) -> None:
    store = RecoverySnapshotStore(tmp_path / "recovery")

    assert store.read() is None


def test_a_later_write_durably_replaces_the_earlier_snapshot(tmp_path: Path) -> None:
    store = RecoverySnapshotStore(tmp_path / "recovery")

    store.write(_analysis("First"), None)
    store.write(_analysis("Second"), None)
    snapshot = store.read()

    assert snapshot is not None
    assert snapshot.analysis.title == "Second"
    # Exactly one recovery file: no leftover temporary write artifacts.
    assert [entry.name for entry in (tmp_path / "recovery").iterdir()] == [
        store.path.name
    ]


def test_clear_removes_the_snapshot_and_is_safe_when_there_is_none(
    tmp_path: Path,
) -> None:
    store = RecoverySnapshotStore(tmp_path / "recovery")
    store.write(_analysis(), None)

    store.clear()

    assert store.read() is None
    store.clear()  # does not raise


def test_an_interrupted_write_leaves_the_prior_snapshot_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RecoverySnapshotStore(tmp_path / "recovery")
    store.write(_analysis("Kept"), None)

    def _failing_replace(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", _failing_replace)

    with pytest.raises(OSError):
        store.write(_analysis("Lost"), None)

    snapshot = store.read()
    assert snapshot is not None
    assert snapshot.analysis.title == "Kept"
    assert [entry.name for entry in (tmp_path / "recovery").iterdir()] == [
        store.path.name
    ]


def test_the_stored_file_carries_an_explicit_recovery_marker(tmp_path: Path) -> None:
    """A Recovery snapshot must be self-describing, never a plain Analysis file."""

    store = RecoverySnapshotStore(tmp_path / "recovery")
    store.write(_analysis(), None)

    payload = json.loads(store.path.read_bytes())

    assert payload[RECOVERY_MARKER] is True
    assert store.path.name != "match.analysis"
    assert store.path.suffix != ".analysis"


@pytest.mark.parametrize(
    "content",
    [
        b"not json at all",
        json.dumps({"schema_version": 1, "analysis": {}}).encode("utf-8"),
        AnalysisFileCodec().encode(_analysis()),
    ],
    ids=["garbage", "missing_marker", "ordinary_analysis_bytes"],
)
def test_foreign_or_marker_less_content_is_never_offered_as_recovery(
    tmp_path: Path, content: bytes
) -> None:
    directory = tmp_path / "recovery"
    directory.mkdir()
    store = RecoverySnapshotStore(directory)
    store.path.write_bytes(content)

    assert store.read() is None


def test_a_corrupted_marked_snapshot_is_never_offered_as_recovery(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "recovery"
    directory.mkdir()
    store = RecoverySnapshotStore(directory)
    store.path.write_text(
        json.dumps({"schema_version": 1, "analysis": {}, RECOVERY_MARKER: True}),
        encoding="utf-8",
    )

    assert store.read() is None
