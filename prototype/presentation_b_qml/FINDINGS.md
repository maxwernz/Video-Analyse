# Prototype B — findings

Qt Quick can carry this visual system, the existing Python survives underneath
it unchanged, and neither of B's named kill conditions fired. The cost is
concrete and it is not free: **+62MB of package**, a **QML module tree that must
be told what to leave out**, and **one dependency the current build pipeline
deliberately excludes**.

Everything below was measured on this machine. Windows was **not** built and is
reported as untested, because the handoff asks for observations rather than
estimates.

Reproduce with:

```sh
uv run python prototype/presentation_b_qml/verify.py            # interaction + performance
uv run python prototype/presentation_b_qml/tools/scrub_probe.py # Widgets vs Quick surfaces
uv run pyinstaller prototype/presentation_b_qml/packaging/prototype_macos.spec \
  --noconfirm --distpath prototype/presentation_b_qml/packaging/dist \
  --workpath prototype/presentation_b_qml/packaging/build
```

---

## Verdict on B's kill conditions

> **B dies** if video rendering into QML or packaging regresses on either
> platform, or if it forces application logic out of Python and into JavaScript.

### 1. Video rendering into QML — did not fire

The video renders into the Qt Quick scene graph through a real
`QtMultimedia.VideoOutput`, playing a real 45-minute H.264 file. The screenshots
show a decoded frame with a burned-in timecode that agrees with the transport,
which is what makes the seek visibly correct rather than merely reported.

It attaches through the **unmodified** production seam. `Playback.set_video_output`
already takes a plain `QObject`, and a `VideoOutput` carries the `videoSink`
property `QMediaPlayer` looks for:

```
videoOutput: PySide6.QtQuick.QQuickItem(id="output", geometry=0,0 1120x662)
videoSink:   PySide6.QtMultimedia.QVideoSink
hasVideo: True   seekable: True   duration: 2700000
```

`playback/` was not edited. Neither was `analysis/` or `application_workflow.py`.

One real behaviour found, and it is **not** a QML deficit: Qt's FFmpeg backend
hands the video sink nothing until playback has started at least once, so
seeking a freshly loaded, never-played file moves the position and decodes
**zero** frames. Qt Widgets meets the same thing. The prototype primes the
surface with a ~140ms play/pause through the public seam
(`WorkspaceViewModel._prime_video_surface`). Whichever prototype wins needs
this, or a newly opened Analysis shows black until the coach presses play.

### 2. Packaging — did not fire on macOS; **untested on Windows**

The prototype packages with PyInstaller through `build_config/shared.py`, ad-hoc
signs, launches, and passes a smoke check equivalent to the one
`scripts/build_macos.sh` runs:

```json
{"status": "ok", "window": "1440x900", "mode": "workspace",
 "fonts": "Inter, JetBrains Mono",
 "qml": ".../Video Analyse QML Prototype.app/Contents/Frameworks/qml/Main.qml",
 "media": "halbzeit-1.mp4", "hasVideo": true, "durationMs": 2700000,
 "mediaError": "none"}
```

That is the packaged binary loading its QML from inside the bundle, registering
both bundled fonts, building the full workspace, and decoding real media with
the bundled Qt Multimedia backend. What it cost is in
[What packaging actually costs](#what-packaging-actually-costs).

**Windows is untested and this prototype cannot honestly clear it.** See
[Windows](#windows-untested).

### 3. Logic leaking into JavaScript — did not fire

Every handler in the QML is a one-line delegation to a Python slot, or a
concern that is genuinely the view's (canvas painting, tooltip visibility,
splitter geometry, pixel↔millisecond conversion). There are no workflow rules,
no model rules, no validation and no formatting in JavaScript.

The audit did find exactly one leak, and it is recorded because it shows how
the leak happens rather than because it survived: the transport was computing
which playback rate was selected with a `for` loop over strings and a magic
fallback of `1`. That is a state question wearing presentation clothes. It is
now `WorkspaceViewModel.playbackRateIndex` and the QML reads
`currentIndex: workspace.playbackRateIndex`.

The structural reason it stayed clean is that QML never sees an `Analysis`, a
`Clip` or the `Playback`. It gets properties, slots and item models, so a
delegate has nothing to reach into.

---

## Against the five decision criteria

### 1. Visual result

See `screenshots/`, captured at a true 1440x900 on this machine's GPU with the
real media:

| | |
| --- | --- |
| `01-workspace-clips.png` | the normal workspace |
| `02-workspace-videos.png` | the Videos sidebar tab |
| `03-clip-editing.png` | the Clip-editing state, existing Clip |
| `04-pending-clip.png` | a Pending Clip, first boundary set |
| `05-clip-editing-new.png` | the Clip-editing state, second boundary just set |
| `06-empty-state.png` | the designed drop target |

Every frozen token is consumed unchanged, transcribed once into `qml/Theme.qml`
and referenced from nowhere else. Nothing in the prototype writes a colour or a
metric of its own except one value the tokens do not name
([below](#where-the-frozen-spec-and-the-prototype-disagreed)).

Specifically against the marked failures in `docs/design/current-ui/`:

- the `VIDEO ANALYSE` wordmark strip is gone, replaced by a working toolbar;
- there is no column header above the Clip list;
- one SVG icon family at one stroke weight, recoloured by state, no raster
  exports on three optical grids;
- the playback rate is a segmented control, not a `QComboBox`;
- timecode is tabular monospace throughout, so the columns align optically;
- the timeline is 60px with a labelled ruler and visible ranges;
- the Clip editor's boundary fields are sized for a whole timecode.

Qt Quick Controls is **not** imported anywhere. Every control — segmented
control, fields, steppers, buttons, tooltips — is drawn from primitives. That
matters more than it sounds: there is no platform style underneath arguing
with the design, and therefore no restyling-a-stock-control smell, which is
precisely the failure mode ADR 0007 was written about.

### 2. Timeline rendering and interaction quality

The full ADR 0006 grammar is implemented and verified by sending real mouse
events to the real window (`verify.py`, 16/16):

```
[ok] pressing empty track scrubs              — asked 1440000ms, playhead 1440000ms
[ok] pressing empty track selects nothing
[ok] clicking a range selects it              — 'Nachwurf nach Block'
[ok] clicking a range does not seek to its start
[ok] double-clicking a range seeks to the Clip start
[ok] a 6.8s Clip is still clickable           — drawn 2.9px wide, floor is 3px
```

Ranges are scene-graph `Item`s, so **Qt does the hit-testing**: the handler asks
`childAt(x, y)` what is under the cursor. There is no JavaScript loop over
Clips, and the three-pixel minimum width is a real hit target rather than only
a drawing — the 6.8s `Siebenmeter` Clip, 2.9px wide at this scale, selects on a
single click.

The ruler is adaptive and its interval is chosen **in Python**
(`models.RulerModel`) from the width the track actually got, because "which
interval is legible at this width" is a rule with arithmetic in it and is
exactly the kind of thing that grows into a JavaScript helper module. The
timeline calls one slot on resize. At 1140px across 45 minutes it picks
five-minute labels.

The documented minimum-width limitation is visible as specified: the fixture's
two Clips 4.5s apart sit about two pixels apart at 2.37 s/px and merge visually.

### 3. Performance during playback and scrubbing

```
drag rate   handling (median/worst)   frames decoded during 1s of dragging
 60/s         0.38ms /  0.57ms             0-5 of 60 moves
 20/s         0.40ms /  0.64ms            17 of 20 moves
 10/s         0.57ms /  0.68ms            10 of 10 moves
one click to a new frame: median 16ms, worst 25ms (10/10 seeks)
playback: 74 frames in 3s, interval median 40.2ms, worst 42.3ms (source 25fps)
```

Event handling is two orders of magnitude inside a 60Hz frame. Playback holds
the source rate with a 2ms worst-case jitter. A single click on the timeline
puts a new frame on screen in about one frame's time.

The one soft spot: dragging at a full 60 samples per second outruns the
decoder, and the picture updates only a handful of times per second while the
pointer keeps up perfectly. At hand speed (10–20 samples/s) the picture
follows one-for-one.

`tools/scrub_probe.py` exists to find out whether that is a Qt Quick problem,
and it is not — the same rapid seeks against a Widgets `QVideoWidget` behave
the same, and Qt Quick is marginally ahead:

```
Qt Widgets (QVideoWidget)      Qt Quick (QML VideoOutput)
60 seeks/s : 23 frames         60 seeks/s : 29 frames
20 seeks/s : 20 frames         20 seeks/s : 20 frames
10 seeks/s : 10 frames         10 seeks/s : 10 frames
```

So this is `QMediaPlayer` coalescing seeks, it affects both candidates equally,
and it should not weigh in the A/B decision. It is worth its own note for the
production build: throttling scrub seeks to ~20/s would cost nothing visible
and would keep the picture glued to the pointer.

### 4. Packaging on macOS and Windows

#### macOS — built, signed, launched, verified

| | Production `main.py` | This prototype |
| --- | --- | --- |
| `.app` total | 210MB | **202MB** |
| `Contents/Frameworks/PySide6` | 90MB | **152MB** |
| Qt QML module tree | absent | 17MB |

The totals are not a like-for-like comparison — the production app carries
`imageio_ffmpeg` (47MB), PIL and numpy for Combined export, which the prototype
does not. **The honest number is the PySide6 delta: +62MB** for the Qt Quick
presentation layer.

#### What packaging actually costs

Three things had to change, and they are the real finding:

1. **`build_config/shared.py` excludes exactly what B is made of.**
   `EXCLUDED_MODULES` lists `QtQml`, `QtQmlMeta`, `QtQmlModels`,
   `QtQmlWorkerScript`, `QtQuick`, `QtSvg` and `QtOpenGL`. Adopting B means
   removing those, which also means `tests/test_windows_packaging_contract.py`
   (which asserts on `EXCLUDED_MODULES`) changes with it. `QtSvg` is needed
   for the icon family, not only for QML.

2. **PyInstaller's PySide6 hook over-collects, spectacularly.** Give it
   `QtQml` and it collects the entire Qt QML module tree, including
   QtWebEngine, which drags in **214MB of Chromium** this application will
   never load. `excludes` cannot reach it, because nothing in Python imports
   it. The spec filters the collected tables directly; the build reports
   `dropped 854 data and 62 binary entries`, and that single filter is the
   difference between a 447MB bundle and a 202MB one. There is a few MB more
   to win — `QtLocation`, `QtWebView`, `QtScxml`, `QtTextToSpeech` and
   `QtRemoteObjects` are still collected and unused.

3. **Modules resolve against `Contents/Resources`, not `Contents/Frameworks`.**
   A path built from `Path(__file__).parent` lands in the wrong half of the
   bundle for data. It happened to work for `qml/` (PyInstaller cross-symlinks
   the two) and did not for the prototype's fixture media. Any real migration
   needs one deliberate resource-root helper rather than per-module guessing.

None of these is a reason B cannot ship. All three are reasons the estimate
"we'll just swap the presentation layer" is wrong by about a day of build work.

#### Windows — untested

This machine is ARM64 macOS; `scripts/build_macos.sh` refuses anything else and
there is no Windows machine in reach. **I did not build it, and I am not going
to estimate it.** What is factually knowable:

- `build_config/windows.spec` imports the same `EXCLUDED_MODULES` from
  `shared.py`, so change (1) above applies identically there.
- Change (2) is PyInstaller hook behaviour, not platform behaviour, so the
  over-collection will happen on Windows too; the same TOC filter should apply.
- Change (3) is macOS bundle layout and does **not** apply to the Windows
  one-dir layout.

The open Windows risk this prototype **cannot** answer, and which the decision
should not pretend is answered: Qt Quick's default RHI backend on Windows is
Direct3D 11, where Widgets rasterises on the CPU. On unmanaged devices with old
or broken GPU drivers that is a new failure mode with no equivalent in A.
Per the handoff's own rule — judged by running both on real machines — **B is
not clearable until someone launches this on a real Windows machine.** It is
the single largest piece of unfinished evidence in this prototype.

### 5. How much Python, and how testable it stays

```
Python (presentation only)   1403 lines   run.py, viewmodels.py, models.py,
                                          timecode.py, icons.py
QML                          2187 lines   19 components + 28 SVG icons
```

Roughly a 2:3 split, and the Python half is the half that can be tested without
a window. What is in it, and why:

| Python | Why it is not in QML |
| --- | --- |
| `WorkspaceViewModel` | every action's meaning; the only vocabulary QML has |
| `ClipListModel` | Category grouping and ordering is a rule about the Analysis |
| `RulerModel` | which tick interval is legible at a given width |
| `TimelineRangeModel` | ranges in milliseconds; only px↔ms is left to the view |
| `timecode.py` | every string shown for a time |
| `icons.py` | Qt's SVG renderer has no `currentColor` (~80 lines) |

`icons.py` is presentation work that had to be in Python, and it is counted as
a cost rather than hidden. The alternative was one SVG per colour per state.

**Testability is unchanged and arguably better.** The whole state machine runs
headless against `playback.FakePlayback` with no QML engine at all — the
Pending Clip round trip, the editor, commit and both cancel paths were all
exercised that way before a window existed. The seams the existing tests use
are untouched, and `uv run pytest` is **191 passed, 12 skipped** with the
prototype present.

`git status` is clean outside `prototype/presentation_b_qml/`.

---

## Where the frozen spec and the prototype disagreed

Per the handoff these were used as frozen and recorded rather than tuned.

1. **The bundled fonts do not exist.** `visual-tokens.md` says Inter and
   JetBrains Mono are "bundled in `assets/fonts/`". `assets/fonts/` contains
   only `NotoSans.ttf`, and neither font is installed on this machine. The
   prototype carries its own copies in `prototype/presentation_b_qml/fonts/`
   (Inter variable + JetBrains Mono Regular/Medium, both SIL OFL). **Before A
   and B are compared, the fonts must land in `assets/fonts/` — otherwise the
   two prototypes are being judged in different typefaces.**

2. **The transport asks for a volume control the `Playback` seam cannot
   provide.** The direction says "left: volume and mute". `Playback` exposes
   `is_muted`/`set_muted` and no level, and `QAudioOutput` is private to
   `MediaPlayerPlayback`. Rather than reach past the seam or fake a slider,
   the prototype shows mute alone. Adopting the designed transport needs a
   volume property added to `playback/player.py`.

3. **The Source-video cue does not fit a 32px row at 300px.** The row must
   carry a title, a start and a duration in monospace, and `halbzeit-1.mp4`
   leaves nothing for the title at the 260px minimum. The prototype shortens
   it to a badge — `halbzeit-1.mp4` → `H1`, first letter plus trailing number,
   in `models.source_badge` — with the full name on hover. This is a design
   decision the spec did not make, and Prototype A will have hit the same
   wall; the two should be compared before either is adopted.

4. **Two metrics the tokens do not name.** The three-pixel minimum range width
   (ADR 0006 says "about three pixels") and a 30px Category header row in the
   Clip list. Both are in `Theme.qml` beside the frozen ones so they are as
   visible as the rest.

5. **The tokens describe no disabled-primary state.** A disabled accent button
   still shouts. The prototype gives the accent back and renders it on
   `control-disabled`, on the grounds that the accent has three permitted uses
   and a control nobody can press is none of them.

## What I could not make work

- **Windows. Not attempted, not estimated.** See above. This is the gap that
  matters.
- **A Qt Quick menu bar was never tried.** The menu bar is a real parentless
  `QMenuBar` created in Python, which on macOS is the system menu bar. That
  keeps ADR 0007's native-behaviour promise, but it means the prototype has
  **not** shown whether Qt Quick's own `MenuBar` could serve, and the Python
  menu is currently inert — its actions are not wired to
  `ApplicationWorkflow`.
- **The toolbar's file and export actions are inert.** The document lifecycle
  they drive is already `application_workflow.py`'s, and wiring it would have
  proved nothing this prototype is asking. The workflow object *is* constructed
  and drives the window title and the dirty marker, so the seam is real —
  but "Open" does not open anything.
- **The scrub seek rate is not throttled.** The measurement above says it
  should be; the prototype deliberately leaves it unthrottled so the raw
  number is honest.
- **No Retina comparison beyond this display.** Everything was captured on one
  built-in 1440x900 2x screen. Window resizing beyond the designed minimum got
  only light manual exercise (the sidebar splitter and the editor's 360px both
  behave), and the transport had to be taught to drop the rate control and the
  mark button in the editing state, where the row loses 360px — at that width
  the centred cluster and the right-hand group collided. Narrower windows than
  1200px were not examined.
- **Teardown noise.** Shutting the interpreter down collects the view model
  before the QML engine, so every binding re-evaluates against `null` and Qt
  prints a screen of `TypeError`s at exit. Harmless, cosmetic, not chased.

## What this prototype does not settle

It shows Qt Quick *can* reach the bar. It cannot show that Qt Quick is
*necessary* — that depends entirely on whether Prototype A reaches the same bar
without the volume of custom `paintEvent` code that is A's own kill condition.
The two questions that should decide it, neither answerable from here:

1. Does A's timeline reach this quality without becoming unmaintainable?
2. Does B run correctly on a real Windows machine?
