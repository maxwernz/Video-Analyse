import customtkinter as ctk
from tkinter import Tk
from tkinter import filedialog

# Create the main application window
root = Tk()
root.title("Modern Video Player")
root.geometry("1600x900")

# Set appearance mode (light/dark system mode)
ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

# Menu functions
def load_video():
    filedialog.askopenfilename(title="Load Video")

def load_analysis():
    filedialog.askopenfilename(title="Load Analysis")

def save_analysis():
    filedialog.asksaveasfilename(title="Save Analysis")

def export_clips():
    filedialog.asksaveasfilename(title="Export Clips")

# Create a frame for the menu bar
menu_frame = ctk.CTkFrame(root)
menu_frame.pack(fill="x")

# Add buttons to the menu bar
menu_button = ctk.CTkButton(menu_frame, text="Load Video", command=load_video)
menu_button.pack(side="left", padx=10, pady=5)

menu_button = ctk.CTkButton(menu_frame, text="Load Analysis", command=load_analysis)
menu_button.pack(side="left", padx=10, pady=5)

menu_button = ctk.CTkButton(menu_frame, text="Save Analysis", command=save_analysis)
menu_button.pack(side="left", padx=10, pady=5)

menu_button = ctk.CTkButton(menu_frame, text="Export Clips", command=export_clips)
menu_button.pack(side="left", padx=10, pady=5)

# Create a frame for the video player and controls
main_frame = ctk.CTkFrame(root)
main_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Left side: Clip list
clip_list_frame = ctk.CTkFrame(main_frame)
clip_list_frame.pack(side="left", fill="y", padx=10, pady=10)

# Placeholder label for clips
clip_label = ctk.CTkLabel(clip_list_frame, text="Clip List", font=ctk.CTkFont(size=20))
clip_label.pack(pady=10)

# Placeholder clip list
clip_list = ctk.CTkTextbox(clip_list_frame, width=200, height=500)
clip_list.pack()

# Right side: Video player (placeholder)
video_player_frame = ctk.CTkFrame(main_frame, width=1000, height=500)
video_player_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

video_label = ctk.CTkLabel(video_player_frame, text="Video Player", font=ctk.CTkFont(size=24))
video_label.pack(pady=20)

# Bottom control panel
control_frame = ctk.CTkFrame(root)
control_frame.pack(fill="x", padx=10, pady=10)

# Add playback control buttons
sound_button = ctk.CTkButton(control_frame, text="🔊", width=50)
sound_button.pack(side="left", padx=5)

backward_button = ctk.CTkButton(control_frame, text="⏪", width=50)
backward_button.pack(side="left", padx=5)

play_pause_button = ctk.CTkButton(control_frame, text="⏯", width=50)
play_pause_button.pack(side="left", padx=5)

forward_button = ctk.CTkButton(control_frame, text="⏩", width=50)
forward_button.pack(side="left", padx=5)

# Playback speed control
speed_label = ctk.CTkLabel(control_frame, text="Speed:")
speed_label.pack(side="left", padx=10)

speed_box = ctk.CTkComboBox(control_frame, values=["0.25x", "0.5x", "1x", "2x"])
speed_box.set("1x")
speed_box.pack(side="left", padx=5)

# Record/Clip button
clip_button = ctk.CTkButton(control_frame, text="🎥 Clip", width=50)
clip_button.pack(side="right", padx=5)

# Start the application
root.mainloop()