from __future__ import annotations

from pathlib import Path

from analysis import (
    AnalysisFileError,
    UnsavedChangesChoice,
    new_analysis_document,
)


def _dirty_document(tmp_path: Path):
    document = new_analysis_document("Match")
    source_video = document.analysis.add_source_video(
        "first-half.mp4",
        str(tmp_path / "first-half.mp4"),
    )
    document.analysis.add_clip(source_video.id, "Fast break", 1_000, 2_000)
    return document


def test_a_clean_document_closes_without_asking(tmp_path: Path) -> None:
    document = _dirty_document(tmp_path)
    document.save_as(tmp_path / "match.analysis")
    asked = False

    def ask() -> UnsavedChangesChoice:
        nonlocal asked
        asked = True
        return UnsavedChangesChoice.CANCEL

    assert document.request_close(ask, lambda: True) is True
    assert asked is False


def test_cancelling_prevents_close_and_preserves_unsaved_state(tmp_path: Path) -> None:
    document = _dirty_document(tmp_path)

    assert (
        document.request_close(lambda: UnsavedChangesChoice.CANCEL, lambda: True)
        is False
    )
    assert document.dirty is True
    assert len(document.analysis.clips) == 1


def test_a_failed_save_prevents_close(tmp_path: Path) -> None:
    document = _dirty_document(tmp_path)

    def failing_save() -> bool:
        return False

    assert (
        document.request_close(lambda: UnsavedChangesChoice.SAVE, failing_save) is False
    )
    assert document.dirty is True


def test_a_save_that_raises_prevents_close(tmp_path: Path) -> None:
    document = _dirty_document(tmp_path)

    def raising_save() -> bool:
        raise AnalysisFileError("disk is full")

    assert (
        document.request_close(lambda: UnsavedChangesChoice.SAVE, raising_save) is False
    )
    assert document.dirty is True


def test_a_successful_save_allows_close(tmp_path: Path) -> None:
    document = _dirty_document(tmp_path)

    def save() -> bool:
        document.save_as(tmp_path / "match.analysis")
        return True

    assert document.request_close(lambda: UnsavedChangesChoice.SAVE, save) is True
    assert document.dirty is False
    assert (tmp_path / "match.analysis").is_file()


def test_discarding_allows_close_without_writing(tmp_path: Path) -> None:
    document = _dirty_document(tmp_path)
    saved = False

    def save() -> bool:
        nonlocal saved
        saved = True
        return True

    assert document.request_close(lambda: UnsavedChangesChoice.DISCARD, save) is True
    assert saved is False
    assert document.dirty is True
