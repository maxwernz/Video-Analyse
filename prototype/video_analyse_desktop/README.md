# Video Analyse desktop UX prototype

> Throwaway design experiment. This is not production code and does not read, save,
> export, or modify Analysis files.

This prototype asks which left-sidebar hierarchy makes multi-Source-video Clip review,
two-press marking, editing, and Combined export easiest to understand. It provides
three structural variants in one PySide6 window:

- **A · Balanced workbench** — Source videos above a chronological Clip list.
- **B · Clip-first command** — Clips dominate; Source videos become a bottom switcher.
- **C · Category lanes** — a narrow Source-video rail beside Category-grouped Clips.

Use the bright bottom bar to switch variants, scenarios, language, and target window
size. Left/right arrow keys switch variants. `Command+R` on macOS or `Ctrl+R` on
Windows exercises the two-press Pending Clip flow.

Run from the repository root:

```sh
conda run -n VideoAnalyse python prototype/video_analyse_desktop/prototype.py
```

Capture representative states:

```sh
QT_QPA_PLATFORM=offscreen conda run -n VideoAnalyse \
  python prototype/video_analyse_desktop/prototype.py --capture
```

Run non-interactive transition checks:

```sh
QT_QPA_PLATFORM=offscreen conda run -n VideoAnalyse \
  python prototype/video_analyse_desktop/prototype.py --smoke
```

All data and behavior are simulated in memory. The painted match view is intentionally
not a real video player.
