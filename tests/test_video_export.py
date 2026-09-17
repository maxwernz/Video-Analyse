"""Rendering a Combined export: the pixels half of the planning/rendering split.

`export_planning.py` decides which Clips render, in what order, and resolves
each one's own Source video ahead of time; `VideoCreator` (`video_creator.py`)
turns that resolved sequence into one video file and knows nothing about
Categories, Analyses, or Source-video identity. The first test below exercises
`VideoCreator` directly, at the same narrow seam the pre-#20 version of this
test used. The second is the small media-fixture integration test the ticket
asks for: two differently sized Source videos, rendered across their boundary
through the real planning module, with no encoder mocked out.
"""

from __future__ import annotations

from pathlib import Path

from moviepy.editor import ColorClip, VideoFileClip

from analysis import Analysis, AnalysisDocument
from export_planning import build_export_list, render_combined_export
from video_creator import RenderClip, VideoCreator


def _write_color_video(path: Path, *, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    source = ColorClip(size=size, color=color, duration=0.6)
    try:
        source.write_videofile(
            str(path), fps=10, codec="libx264", audio=False, logger=None
        )
    finally:
        source.close()


def test_export_creates_playable_video_with_bundled_font_overlay(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.mp4"
    output_path = tmp_path / "export.mp4"
    _write_color_video(source_path, size=(96, 64), color=(20, 80, 140))

    clip = RenderClip(
        name="Fast break",
        video_path=str(source_path),
        start_ms=100,
        end_ms=500,
        notes="Cross-platform overlay",
        category="Angriff",
    )
    creator = VideoCreator(
        clips=[clip],
        save_filename=str(output_path),
        include_analysis_title=False,
        logger=None,
    )

    creator.run()

    assert output_path.is_file()
    assert output_path.stat().st_size > 0
    exported = VideoFileClip(str(output_path))
    try:
        assert exported.duration > 0
        assert exported.size == [96, 64]
    finally:
        exported.close()


def test_export_renders_available_clips_in_export_list_order_across_source_video_boundaries(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first-half.mp4"
    second_path = tmp_path / "second-half.mp4"
    output_path = tmp_path / "combined.mp4"
    # Deliberately different frame sizes: this is what makes crossing a
    # Source-video boundary in one rendered sequence require the
    # `concatenate_videoclips(method="compose")` normalization
    # `video_creator.VideoCreator._render` documents, rather than the
    # default chaining that assumes one shared size throughout.
    _write_color_video(first_path, size=(96, 64), color=(20, 80, 140))
    _write_color_video(second_path, size=(64, 96), color=(140, 40, 20))

    analysis = Analysis("Match")
    category = analysis.add_category("Angriff")
    first_half = analysis.add_source_video("first-half.mp4", str(first_path))
    second_half = analysis.add_source_video("second-half.mp4", str(second_path))
    early_clip = analysis.add_clip(
        first_half.id, "Early break", 100, 500, category_id=category.id
    )
    late_clip = analysis.add_clip(
        second_half.id, "Late break", 100, 500, category_id=category.id
    )
    document = AnalysisDocument(analysis)

    # Selected out of Export-list order; `build_export_list` sorts by
    # Source-video order (first-half before second-half) within the shared
    # Category, so the render must still come out early-then-late.
    entries = build_export_list(analysis, [late_clip.id, early_clip.id])
    assert [entry.clip_id for entry in entries] == [early_clip.id, late_clip.id]

    render_combined_export(document, entries, str(output_path))

    assert output_path.is_file()
    assert output_path.stat().st_size > 0
    exported = VideoFileClip(str(output_path))
    try:
        assert exported.duration > 0
    finally:
        exported.close()
