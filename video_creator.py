from PIL import Image, ImageDraw, ImageFont
from threading import Thread
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, ColorClip, ImageClip
import os
from PySide6.QtCore import QObject, Signal
import numpy as np
from enum import Enum

class ImageType(Enum):
    CATEGORY = 1
    NOTES = 2
    NUMBER = 3



class VideoCreator(Thread, QObject):

    progress_changed = Signal(int)

    def __init__(self, clips, video_filename, save_filename, full_video):
        Thread.__init__(self)
        QObject.__init__(self)

        self.clips = clips
        self.video = VideoFileClip(video_filename)
        self.filename = save_filename
        self.size = self.video.size
        self.full_video = full_video

        self.tempfilename = "/tmp/tmp_video_png.png"

    def run(self):
        category = self.clips[0].category
        if self.full_video:
            video_title = os.path.basename(self.filename).removesuffix('.mp4')
            subclips = [self.create_category_clip(video_title), self.create_category_clip(category)]
        else:
            subclips = [self.create_category_clip(category)]

        for i, clip in enumerate(self.clips):
            clip_category = clip.category
            if clip_category != category:
                category = clip_category
                subclips.append(self.create_category_clip(category))

            if clip.notes:
                text_img = self.create_image(clip.notes, image_type=ImageType.NOTES)
                text_clip = ImageClip(text_img, duration=2)
                subclips.append(text_clip)

            start_time, end_time = clip.clip_times_s()
            video_clip = self.video.subclip(start_time, end_time)

            text_img = self.create_image(f"{i+1}")
            text_clip = ImageClip(text_img, duration=video_clip.duration)
            subclips.append(CompositeVideoClip([video_clip, text_clip]))

            progress = int(i / len(self.clips) * 100)
            self.progress_changed.emit(progress)

        combined_video = concatenate_videoclips(subclips)
        combined_video.write_videofile(self.filename, logger=None, audio=False, threads=4)

        self.progress_changed.emit(100)

    def create_category_clip(self, category):
        category_img = self.create_image(category, image_type=ImageType.CATEGORY)
        text_clip = ImageClip(category_img, duration=1.5)
        return CompositeVideoClip([text_clip])

    def create_image(self, text, image_type=ImageType.NUMBER):
        if image_type == ImageType.NUMBER:
            font_size = 100
            background = (0, 0, 0, 0) # transparent
            position = (50, 50)
        elif image_type == ImageType.CATEGORY:
            font_size = 120
            background = (53, 51, 51, 255) # black
            position = None
        elif image_type == ImageType.NOTES:
            font_size = 40
            background = (53, 51, 51, 255)
            position = None

        image = Image.new("RGBA", self.size, background)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("Arial.ttf", font_size)

        if position is None:
            _, _, w, h = draw.textbbox((0, 0), text, font=font)
            textsize = (w, h)
            position = tuple([(self.size[i] - textsize[i]) / 2 for i in range(2)])

        draw.text(position, text, font=font, fill=(255, 255, 255, 255))

        return np.array(image)



        

