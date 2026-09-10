# Prototype A — redesigned Qt Widgets presentation layer

> **Throwaway.** Not production code. Nothing here reads or writes an Analysis
> file, and no state survives the process. It exists to answer one question:
> **can a carefully redesigned, mostly native Qt Widgets interface reach the
> reference visual quality, and what does that cost in custom painting?**

This is one of two competing prototypes. Prototype B is a full-window QML / Qt
Quick presentation layer, built in parallel from `HANDOFF-prototype-b-qml.md`.
The decision belongs to `docs/design/desktop-ux.md`; the verdict from this side
is in [FINDINGS.md](FINDINGS.md).

## Run it

```sh
uv run python prototype/presentation_a_widgets/run.py
```

Opens the normal workspace at 1440x900 against the canonical fixture, with
playback faked so no media files are needed.

| Command | What it does |
| --- | --- |
| `--screen workspace\|editing\|empty` | open in a given state |
| `--media` | run against real media through `QMediaPlayer` |
| `--capture` | write the screenshots (needs `QT_QPA_PLATFORM=offscreen`) |
| `--benchmark` | measure timeline paint cost per frame |
| `--media-check` | play and scrub real media, reporting throughput and seek latency |
| `--smoke` | build every screen and exit |

Inside the running window:

- **Ctrl+1 / Ctrl+2 / Ctrl+3** — workspace, Clip editing, empty state. Also in
  the native **Ansicht** menu, so switching states needs no prototype-only
  chrome bolted onto the design.
- **Space** — play/pause. **R** — mark Clip, which enters the editing state.
- The timeline takes the full ADR 0006 grammar: drag anywhere scrubs, clicking
  a range selects that Clip without seeking to its start, double-clicking a
  range seeks to the Clip start, hovering shows a cursor line and a timecode.

## What it is built on

A presentation layer over the existing seams, exactly as B is: it reads a real
`analysis.Analysis` and drives a real `playback.Playback`. `analysis/`,
`application_workflow.py` and `playback/` are untouched. Nothing outside this
directory was modified.

| File | Role |
| --- | --- |
| `tokens.py` | the frozen tokens, transcribed; never tuned here |
| `theme.py` | the single stylesheet, generated from the tokens |
| `icons.py` | one Lucide SVG family, recoloured by state at the device ratio |
| `fonts.py` | resolves the two token families, and records substitutions |
| `fixture.py` | the canonical Analysis, built through the real domain model |
| `timeline.py` | the 60px custom-painted timeline |
| `clip_list.py` | `QTreeView` plus a delegate: grouped rows, no column header |
| `controls.py` | segmented control, speed menu button, transport buttons |
| `editor.py` | the 360px sectioned Clip form |
| `toolbar.py` / `transport.py` / `stage.py` | the 44px, 56px and stage surfaces |
| `window.py` | the window and all wiring |
| `run.py` | entry point, capture, benchmark, packaging harness |

## Screenshots

`screenshots/`, at 1440x900, from the canonical fixture:

| File | Screen |
| --- | --- |
| `01-workspace-1440x900.png` | normal workspace |
| `02-clip-editing-1440x900.png` | Clip-editing state |
| `03-empty-state-1440x900.png` | empty state |

**The video stage shows a blurred synthetic test pattern, not handball
footage.** There is no sample video in the repository, so `run.py` generates one
with the ffmpeg that ships inside `imageio-ffmpeg` and blurs one frame into
`media/poster.png` for the stage. It is a placeholder chosen to be neutral
enough that the chrome can be judged; it is not a claim about how real footage
will look.

## Throwaway media

`media/*.mp4` are generated on demand for the playback and scrub measurements
and are git-ignored. Delete the directory whenever you like; it rebuilds. The
`PROTOTYPE-…-wipe-me` names are deliberate.

## Packaging probe

`packaging/prototype_a.spec` packages this prototype through the project's real
`build_config/shared.py` configuration, so the packaging criterion is answered
by a build that runs or fails rather than by an estimate:

```sh
uv run pyinstaller prototype/presentation_a_widgets/packaging/prototype_a.spec \
  --noconfirm --distpath prototype/presentation_a_widgets/packaging/out/dist \
  --workpath prototype/presentation_a_widgets/packaging/out/build

QT_QPA_PLATFORM=offscreen \
  prototype/presentation_a_widgets/packaging/out/dist/PrototypeA/PrototypeA --smoke
```

`PROTOTYPE_A_STRICT_EXCLUDE=1` spells the QtSvg exclusion the way PyInstaller
matches PySide6 submodules. What that changes is the packaging finding; see
FINDINGS.md.
