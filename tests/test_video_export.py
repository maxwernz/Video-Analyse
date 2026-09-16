from dataclasses import dataclass
from pathlib import Path

from moviepy.editor import ColorClip, VideoFileClip

from video_creator import VideoCreator


@dataclass(frozen=True)
class ExportListItem:
    """The narrow Combined-export value the video creator needs."""

    name: str
    start_position: int
    end_position: int
    notes: str
    category: str | None = None

    def clip_times_s(self) -> tuple[float, float]:
        return self.start_position / 1000, self.end_position / 1000


def test_export_creates_playable_video_with_bundled_font_overlay(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.mp4"
    output_path = tmp_path / "export.mp4"

    source = ColorClip(size=(96, 64), color=(20, 80, 140), duration=0.6)
    try:
        source.write_videofile(
            str(source_path),
            fps=10,
            codec="libx264",
            audio=False,
            logger=None,
        )
    finally:
        source.close()

    clip = ExportListItem(
        name="Fast break",
        start_position=100,
        end_position=500,
        notes="Cross-platform overlay",
        category="Angriff",
    )
    creator = VideoCreator(
        clips=[clip],
        video_filename=str(source_path),
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
