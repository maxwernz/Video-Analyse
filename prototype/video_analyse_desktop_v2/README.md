# Restrained desktop UX prototype — iteration two

> Throwaway PySide6 design experiment. No Analysis files or videos are read or changed.

This round responds to feedback that the first prototype felt too vibrant, rounded,
and “AI-designed.” It borrows only visual restraint from
[Binary Video Analysis](https://apps.microsoft.com/detail/9p4mkf8055v7): flat charcoal
surfaces, thin rules, square controls, compact type, and sparing accent color.

The three variants answer different structural questions:

- **A · Tabbed library + modal:** Clips/Videos share the sidebar; finishing a Clip
  pauses into a focused editor window.
- **B · Video tabs + editing dock:** Clips remain visible; Source videos switch above
  the player; the editor opens as a wide bottom dock.
- **C · Source lanes + edit workspace:** the timeline has one lane per Source video;
  editing becomes a dedicated workspace with a frozen video frame.

All timeline Clip blocks are clickable. Selecting one switches the active Source video,
seeks to its start in the simulated state, and updates the selected range without using
color alone. The optional shot map is a layout experiment only, not an accepted domain
concept.

Run from the repository root:

```sh
conda run -n VideoAnalyse python prototype/video_analyse_desktop_v2/prototype.py
```

Use the light prototype bar to switch variants, Clips/Videos tabs, editor state, and
window size. `Command+R` or `Ctrl+R` still exercises the two-press marking flow.

Capture and smoke commands:

```sh
QT_QPA_PLATFORM=offscreen conda run -n VideoAnalyse \
  python prototype/video_analyse_desktop_v2/prototype.py --capture

QT_QPA_PLATFORM=offscreen conda run -n VideoAnalyse \
  python prototype/video_analyse_desktop_v2/prototype.py --smoke
```
