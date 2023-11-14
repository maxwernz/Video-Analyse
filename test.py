from moviepy.editor import *

def create_text_clip(text, duration, fontsize=70, size=(640, 480)):
    return TextClip(text, fontsize=fontsize, color='white', size=size).set_duration(duration)

# Funktion zur Erstellung des Videoclips mit Text in der Mitte
def create_text_video(text, duration, output_path):
    text_clip = create_text_clip(text, duration)
    video_clip = CompositeVideoClip([text_clip])
    video_clip.write_videofile(output_path, fps=24)


create_text_video("Hallo", 3, "/Users/max/Downloads/text_video.mp4")