"""Compatibility contract for durable Analyses from the original application."""

from __future__ import annotations

from pathlib import Path

from analysis import AnalysisDocument, UnsupportedContentError
from application_workflow import ApplicationWorkflow
from media_probe import ProbedMedia


LEGACY_FIXTURE = Path(__file__).parent / "fixtures" / "legacy" / "cup-final.analysis"


class _FixturePresenter:
    """Records the one confirmation legacy media cannot supply on its own."""

    def confirm_source_video_replacement(self, display_name: str) -> bool:
        return True

    def report_failure(self, title: str, message: str) -> None:
        raise AssertionError(f"{title}: {message}")


class _FixtureMediaProbe:
    """Keeps the fixture test at the workflow seam, not a video decoder seam."""

    def probe(self, path: Path) -> ProbedMedia:
        return ProbedMedia(
            byte_size=path.stat().st_size,
            fingerprint="fixture-replacement",
            duration_ms=18_000,
        )


def test_legacy_fixture_restores_analytical_content_and_can_relink(
    tmp_path: Path,
) -> None:
    """A moved Source video does not erase the Analysis it belongs to.

    The original single-video Analysis had no media identity signals, so the
    workflow asks before adopting a replacement. That preserves the analyst's
    Clip timestamps and notes while keeping the Source video outside the
    Analysis file, as the storage-independent compatibility contract requires.
    """
    document = AnalysisDocument.new("Open work must survive a failed import")
    document.load(LEGACY_FIXTURE)

    source_video = document.analysis.source_videos[0]
    assert document.analysis.title == "cup-final"
    assert source_video.display_name == "cup-final.mp4"
    assert source_video.location == "/fixtures/missing/cup-final.mp4"
    assert document.is_source_video_available(source_video.id) is False
    assert [category.name for category in document.analysis.categories] == [
        "Angriff",
        "Abwehr",
    ]
    assert [
        (clip.name, clip.start_ms, clip.end_ms, clip.notes)
        for clip in document.analysis.clips
    ] == [
        ("Fast break", 1_250, 4_500, "Left wing finishes"),
        ("Defensive stop", 8_000, 10_250, ""),
        ("Transition", 12_000, 13_000, "Uncategorized"),
    ]
    categories_by_id = {
        category.id: category.name for category in document.analysis.categories
    }
    assert [
        None if clip.category_id is None else categories_by_id[clip.category_id]
        for clip in document.analysis.clips
    ] == ["Angriff", "Abwehr", None]

    replacement = tmp_path / "cup-final-moved.mp4"
    replacement.write_bytes(b"replacement remains external to the Analysis")
    workflow = ApplicationWorkflow(
        _FixturePresenter(), document=document, media_probe=_FixtureMediaProbe()
    )

    assert workflow.relink_source_video_file(source_video.id, replacement) is True
    relinked = workflow.analysis.source_video(source_video.id)
    assert relinked.location == str(replacement)
    assert workflow.document.resolve_source_video(source_video.id) == replacement
    assert len(workflow.analysis.source_videos) == 1
    assert [clip.source_video_id for clip in workflow.analysis.clips] == [
        source_video.id,
        source_video.id,
        source_video.id,
    ]

    saved_path = workflow.document.save_as(tmp_path / "relinked-cup-final")
    assert replacement.read_bytes() not in saved_path.read_bytes()

    reopened = AnalysisDocument.new()
    reopened.load(saved_path)
    reopened_source = reopened.analysis.source_videos[0]
    assert reopened.resolve_source_video(reopened_source.id) == replacement
    assert len(reopened.analysis.source_videos) == 1
    assert [clip.source_video_id for clip in reopened.analysis.clips] == [
        reopened_source.id,
        reopened_source.id,
        reopened_source.id,
    ]
    reopened_categories = {
        category.id: category.name for category in reopened.analysis.categories
    }
    assert [
        None
        if clip.category_id is None
        else reopened_categories[clip.category_id]
        for clip in reopened.analysis.clips
    ] == ["Angriff", "Abwehr", None]


def test_malformed_legacy_content_preserves_the_open_analysis(tmp_path: Path) -> None:
    """Malformed legacy input is rejected transactionally, not pre-approved.

    A pickle header only routes the bytes to the restricted reader. It is not a
    safety check for unknown pickle data; an untrusted legacy Analysis must
    never be opened merely because its bytes resemble a pickle.
    """
    malformed = tmp_path / "truncated.analysis"
    malformed.write_bytes(b"\x80\x04\x95")
    document = AnalysisDocument.new("Open work")
    original = document.analysis

    try:
        document.load(malformed)
    except UnsupportedContentError:
        pass
    else:
        raise AssertionError("malformed legacy content was accepted")

    assert document.analysis is original
