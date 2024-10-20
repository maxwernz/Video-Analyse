from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip

# Load the video file from the given path
video = VideoFileClip("/Volumes/T7/Handball/Videos/Handschuhsheim/TSV vs. S3L.mp4")

# Extract the subclip from 10 seconds to 17 seconds
subclip = video.subclip(10, 17)

# Create a TextClip with the number "1" in the top-left corner
text = TextClip("1", fontsize=70, color='white').set_position(("left", "top")).set_duration(subclip.duration)

# Overlay the text onto the subclip
video_with_text = CompositeVideoClip([subclip, text])

# Create a black clip with the text "Angriff" for 2 seconds
black_clip = ColorClip(size=video.size, color=(0, 0, 0), duration=2)  # Black background
angriff_text = TextClip("Angriff", fontsize=70, color='white').set_position("center").set_duration(2)
black_clip_with_text = CompositeVideoClip([black_clip, angriff_text])

# Concatenate the black clip with the video clip
final_video = CompositeVideoClip([black_clip_with_text, video_with_text.set_start(black_clip_with_text.duration)])

# Save the resulting video
final_video.write_videofile("clip_with_overlay_and_intro.mp4", codec="libx264")
