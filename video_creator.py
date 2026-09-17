"""Renders a Combined export from a resolved, ordered sequence of Clips.

This module is deliberately ignorant of `Analysis`, `Clip`, Category order,
and Source-video identity: `export_planning.py` decides *what* to render and
*in what order*, resolves every Clip's Source video to a real path, and hands
this module the narrow `RenderClip` value below. That split is what makes the
planning rules (grouping, ordering, preflight) testable without an encoder,
and keeps this module's job to exactly one thing -- turning already-resolved
Clips into pixels -- unchanged from how it worked before Combined export
could cross Source videos.

`VideoCreator` still subclasses `Thread` as it always has; nothing here
starts it on a background thread. `run()` is written to be safe to call
directly, synchronously, exactly as the existing test does -- rendering
several minutes of footage is slow, and deciding *when* to take that off the
UI thread is a presentation-layer decision for whoever wires a render button
to this, not one this module makes for them.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Thread
from typing import Any

import numpy as np
from moviepy.editor import (
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont
from proglog import ProgressBarLogger
from PySide6.QtCore import QObject, Signal

from app_runtime import overlay_font_path


class ImageType(Enum):
    CATEGORY = 1
    NOTES = 2
    NUMBER = 3


@dataclass(frozen=True, slots=True)
class RenderClip:
    """The narrow Combined-export value `VideoCreator` needs for one Clip.

    `video_path` is this Clip's own Source video, already resolved to a real
    on-disk location by `export_planning.preflight_export` -- never the
    currently Active Source video's path. Carrying it per-Clip, rather than
    once for the whole export, is what lets a rendered sequence cross
    Source-video boundaries at all.
    """

    name: str
    video_path: str
    start_ms: int
    end_ms: int
    notes: str
    category: str | None = None

    def clip_times_s(self) -> tuple[float, float]:
        return self.start_ms / 1000, self.end_ms / 1000


class VideoCreator(Thread, QObject):
    """Concatenates `RenderClip`s, in order, into one presentation video."""

    def __init__(
        self,
        clips: list[RenderClip],
        save_filename: str,
        include_analysis_title: bool,
        logger: Any,
    ) -> None:
        Thread.__init__(self)
        QObject.__init__(self)

        if not clips:
            raise ValueError("VideoCreator requires at least one Clip")

        self.clips = clips
        self.filename = save_filename
        self.include_analysis_title = include_analysis_title
        self.logger = logger

        #: Every distinct Source video this export touches, opened once and
        #: reused for each of its Clips rather than once per Clip -- a Clip
        #: list that revisits a Source video (Category grouping means it
        #: usually does) would otherwise reopen and re-decode the same file
        #: repeatedly.
        self._videos: dict[str, VideoFileClip] = {}

    def run(self) -> None:
        try:
            self._render()
        finally:
            for video in self._videos.values():
                video.close()

    def _render(self) -> None:
        first_video = self._video_for(self.clips[0].video_path)
        category = self.clips[0].category
        if self.include_analysis_title:
            video_title = Path(self.filename).stem
            subclips = [
                self.create_category_clip(video_title, first_video.size),
                self.create_category_clip(category, first_video.size),
            ]
        else:
            subclips = [self.create_category_clip(category, first_video.size)]

        for i, clip in enumerate(self.clips):
            video = self._video_for(clip.video_path)
            clip_category = clip.category
            if clip_category != category:
                category = clip_category
                subclips.append(self.create_category_clip(category, video.size))

            if clip.notes:
                text_img = self.create_image(clip.notes, video.size, image_type=ImageType.NOTES)
                text_clip = ImageClip(text_img, duration=2).set_position(
                    ("center", 0.9), relative=True
                )
                subclips.append(text_clip)

            start_time, end_time = clip.clip_times_s()
            video_clip = video.subclip(start_time, end_time)

            text_img = self.create_image(f"{i + 1}", video.size)
            text_clip = ImageClip(text_img, duration=video_clip.duration)
            subclips.append(CompositeVideoClip([video_clip, text_clip]))

        # `method="compose"` rather than the default `"chain"`: chaining
        # requires every subclip to share one frame size, which held for
        # free when every Clip came from the same Source video. Crossing
        # Source-video boundaries can no longer assume that, so composing
        # (each subclip laid on its own canvas, letterboxed as needed) is
        # the one piece of normalization this module accepts as technically
        # required -- it changes how differently sized footage is packed
        # into the timeline, not the footage, overlays, or Category grouping
        # an analyst already sees within a single Source video.
        combined_video = concatenate_videoclips(subclips, method="compose")
        try:
            combined_video.write_videofile(
                self.filename, logger=self.logger, audio=False, threads=4
            )
        finally:
            combined_video.close()

    def _video_for(self, video_path: str) -> VideoFileClip:
        video = self._videos.get(video_path)
        if video is None:
            video = VideoFileClip(video_path)
            self._videos[video_path] = video
        return video

    def create_category_clip(self, category: str | None, size: tuple[int, int]) -> CompositeVideoClip:
        category_img = self.create_image(category, size, image_type=ImageType.CATEGORY)
        text_clip = ImageClip(category_img, duration=1.5)
        return CompositeVideoClip([text_clip])

    def create_image(
        self,
        text: str | None,
        size: tuple[int, int],
        image_type: ImageType = ImageType.NUMBER,
    ) -> np.ndarray:
        if image_type == ImageType.NUMBER:
            font_size = 100
            background = (0, 0, 0, 0)  # transparent
            position: tuple[float, float] | None = (50, 50)
        elif image_type == ImageType.CATEGORY:
            font_size = 120
            background = (53, 51, 51, 255)  # black
            position = None
        else:  # ImageType.NOTES
            font_size = 40
            background = (53, 51, 51, 255)
            position = None

        image = Image.new("RGBA", size, background)
        draw = ImageDraw.Draw(image)

        font = ImageFont.truetype(str(overlay_font_path()), font_size)

        lines = (text or "").splitlines()
        wrapped = "\n".join(textwrap.fill(line, width=45) for line in lines)

        if position is None:
            _, _, w, h = draw.textbbox((0, 0), wrapped, font=font)
            textsize = (w, h)
            position = tuple((size[i] - textsize[i]) / 2 for i in range(2))

        draw.text(position, wrapped, font=font, fill=(255, 255, 255, 255))

        return np.array(image)


class ProgressLogger(QObject, ProgressBarLogger):

    progress_changed = Signal(int)
    export_finished = Signal()

    def bars_callback(
        self, bar: str, attr: str, value: float, old_value: float | None = None
    ) -> None:
        # Every time the logger progress is updated, this function is called
        percentage = (value / self.bars[bar]["total"]) * 100

        self.progress_changed.emit(percentage)

        if old_value is not None and percentage == 100:
            self.export_finished.emit()
