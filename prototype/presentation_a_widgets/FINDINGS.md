# Prototype A — findings

Reported against the five decision criteria in `docs/design/desktop-ux.md`,
followed by an explicit verdict on A's kill condition and an honest list of what
could not be made to work.

Measured on macOS 15.5, Apple Silicon, PySide6 6.10.0, Python 3.12. Everything
numeric below came from running the prototype, not from estimating.

---

## 1. Visual result against the reference captures

**A reaches the bar on the two screens that were built.** Every failure marked
in `docs/design/current-ui/*-marked.png` is gone:

| Marked failure | What replaced it |
| --- | --- |
| Product wordmark strip | 44px working toolbar: file and Analysis actions left, Analysis name and dirty dot centre, view controls right |
| Tree column header (`Clip / Start / Stop`) | No header. A delegate paints the whole row |
| Colour-as-text Category cues | 3px full-colour bar at the leading edge; the label itself is neutral `text-muted` |
| Proportional digits in timecode columns | Monospace throughout, right-aligned, so the columns align optically |
| Unstyled scrollbar | 10px styled handle on a transparent trough |
| Mismatched raster icons | One Lucide SVG family, stroke 1.75, recoloured per state, rasterised at the device ratio |
| Stock `QComboBox` for speed | A menu button painted from the tokens, with a native `QMenu` popup |
| Clipped duration fields | Boundary fields sized from `QFontMetrics` of `00:00:00.000` plus padding, so they cannot clip |

The character of the Catapult reference carries over: the stage is the darkest
surface, chrome recedes, there are three surfaces and one hairline, and the
accent appears in exactly three places — playhead, primary action, selection.

Two judgement calls worth challenging in review:

- **A 22px context strip under the timeline** carries the selected Clip's title
  and range. The direction asks for these "near the timeline" without giving
  them a metric; this is my reading, and it is extra chrome the tokens do not
  name.
- **The editing state keeps the timeline and transport.** The direction
  describes only "a large paused frame on the left and a structured form on the
  right". I kept them because the boundary fields are scrub-linked and the
  timeline is the one seek surface, so removing it would leave nothing to scrub
  against. The transport's accent "Clip markieren" button *is* hidden there, so
  the editing state still has exactly one accent primary.

## 2. Timeline rendering and interaction quality

The full ADR 0006 anatomy renders: a 16px ruler with adaptive labelled marks and
minor ticks over a 44px track, ranges at 40% alpha with a 1px full-colour top
edge, a 2px accent playhead with a grabbable handle, hover cursor line and
timecode tooltip. The whole interaction grammar works — drag-anywhere scrub,
click-a-range-to-select-without-seeking, double-click-to-seek-to-start.

The ruler interval is chosen from the widest candidate that keeps labels at
least 88px apart, so it reads correctly at 45 minutes and at the 4-minute
measurement clip without being told which it is.

**The minimum-range-width limitation is real and visible.** At 1440x900 the
timeline is 1139px for a 45-minute Source video: 2.37 seconds per pixel. The
7-second selected Clip is 3px, held at the 3px floor, and it visually merges
with the Clip 5 seconds later. The screenshots show this. ADR 0006 predicted it
and accepted it; the prototype confirms the prediction rather than softening it.

Hit-testing is exact — range rectangles are recorded as they are painted, so
what is clickable is what is drawn, with no second geometry to drift.

## 3. Performance during playback and scrubbing

Timeline repaint, 600 frames, 1139px wide, offscreen raster:

```
playhead-only repaint : 0.076 ms/frame  (13199 fps)
full rebuild repaint  : 0.356 ms/frame  ( 2807 fps)
```

The prototype caches the static layer (ruler, ticks, labels, ranges) into a
pixmap and repaints only the playhead and hover line per frame. **That
optimisation turns out to be unnecessary**: even rebuilding everything on every
single frame runs at 2807fps. Painting this timeline is free at this scale, and
would still be free with ten times the Clips. I kept the cache because it costs
13 lines, but nobody should cite it as a cost of reaching the visual bar.

Real media through `QMediaPlayer` (`--media-check`, synthetic 240s H.264 720p):

```
loaded: True  duration: 240.0s
playback: 64 position updates in 4.1s (16 per second)
scrub: 40 seeks, median 1.8 ms, worst 3.1 ms
```

**The 16-updates-per-second figure is the important one, and it is a problem
neither prototype avoids.** Qt 6's `QMediaPlayer` emits `positionChanged`
roughly every 62ms and offers no notify-interval control. A playhead driven
straight off that signal will visibly step during playback. Driving the fake
player at 33ms produces a smooth playhead, which is what the screenshots and the
benchmark show — so *the prototype has not demonstrated a smooth playhead on
real media*. Making it smooth needs position interpolation between
notifications, which I did not build. This is a finding about the player seam,
not about Widgets, and B will hit it identically.

The seek latency figure is honest but narrow: 1.8ms is how long `seek()` takes to
return, not how long until the decoded frame appears. Frame-settle latency needs
a real display.

## 4. Packaging on macOS and Windows

**macOS: packages and runs, through the project's own configuration, unchanged.**
`packaging/prototype_a.spec` builds the prototype using `build_config/shared.py`
verbatim. The packaged binary passes its smoke check:

```
prototype A smoke check passed
```

But there is a real trap underneath that, and it is worth the owner's attention
whichever prototype wins:

`build_config/shared.py` lists `"QtSvg"` in `EXCLUDED_MODULES`, alongside
`"QtQml"`, `"QtQuick"` and `"QtQmlModels"`. Prototype A depends on QtSvg for its
icon family. It packages anyway — **because that exclusion does not actually
bite**. PyInstaller matches full module names, and the PySide6 hook pulls
`PySide6.QtSvg` in regardless of a bare `"QtSvg"` entry. The list already hints
at this: it carries both `"QtDBus"` and `"PySide6.QtDBus"`, so the bare spellings
appear to be vestigial.

I verified the fragility rather than asserting it. Adding `"PySide6.QtSvg"` to
the exclusion list (`PROTOTYPE_A_STRICT_EXCLUDE=1`) and rebuilding produces a
package that dies on launch:

```
File "prototype/presentation_a_widgets/icons.py", line 15, in <module>
    from PySide6.QtSvg import QSvgRenderer
ModuleNotFoundError: No module named 'PySide6.QtSvg'
```

So: **if A wins, `"QtSvg"` must be deleted from `EXCLUDED_MODULES` as a
deliberate act**, not left to survive by accident. That is a one-line change in
`build_config/shared.py`, which is outside this prototype's boundary, so I have
not made it. The same list is the reason B's packaging deserves the same
scrutiny: `"QtQml"` and `"QtQuick"` are excluded by the same ineffective bare
spellings.

**Windows: not attempted. I have no Windows machine.** The only thing I can say
honestly is structural: `build_config/windows.spec` imports the same
`EXCLUDED_MODULES` and `HIDDEN_IMPORTS` from `shared.py`, so the QtSvg question
is identical there and needs the same one-line fix. Whether PyInstaller's
Windows PySide6 hook happens to pull QtSvg in the same way is untested. Criterion
4 is therefore **half answered**, and the direction document is right that the
decision needs real machines.

## 5. How much Python the presentation layer needs, and how testable it stays

2389 lines of code in the package. Excluding `run.py` (the harness) and
`fixture.py` (the fixture), the interface itself is **2001 lines**.

The presentation layer holds no analytical logic. It reads a real
`analysis.Analysis` and drives a real `playback.Playback`; `window.py` is pure
wiring, and the domain seams took the prototype without modification. Two
concrete signs the seams are sound:

- The canonical fixture is expressible entirely through `Analysis.add_*`, with
  no prototype-local model.
- When I lazily pointed both Source videos at one file, `Analysis` rejected it
  with "Source video has already been added". The domain rule caught my
  shortcut. That is the seam working.

Testability is good, and better than the shipped interface's. Every custom
surface is a plain `QWidget` or `QStyledItemDelegate` with no singletons and no
global state: `Timeline` takes an `Analysis`, a Source-video id and a duration
and emits `scrubbed` / `clip_selected` / `clip_activated`, so its whole grammar
is testable by synthesising mouse events without any media. The behavioural
contract in `tests/test_main_window_workflow.py` is unaffected — the full suite
still passes (191 passed, 12 skipped) because nothing outside this directory was
touched.

The honest caveat: **appearance is not testable this way.** 341 lines of
painting can only be regression-checked by comparing rendered images, which the
direction document explicitly rules out as a decision method and which nobody
here has tooling for.

---

## Verdict on A's kill condition

> *A dies if the timeline and transport cannot reach the visual bar without
> becoming a volume of custom `paintEvent` code that cannot be maintained.*

**A does not die.** The number:

| Surface | Painting | Total | Note |
| --- | --- | --- | --- |
| `timeline.py` | **120** | 278 | ruler, ranges, selection, hover, playhead |
| `clip_list.py` | **134** | 290 | the row delegate |
| `editor.py` | 30 | 232 | Category menu button |
| `controls.py` | 30 | 168 | speed button, jump-button numerals |
| `stage.py` | 27 | 121 | stage letterbox, empty-state drop zone |
| **Total** | **341** | **2389** | 14% of the package, 17% of the interface |

The timeline — the surface the kill condition names — is **120 lines**, split
into seven single-purpose functions, the largest of which (`_paint_ruler`) is 33
lines. That is a small, ordinary custom widget, not an unmaintainable volume.

The transport needed **almost no painting at all**: 30 lines in `controls.py`,
and 23 of those are the speed menu button that exists only because a stock
`QComboBox` was explicitly rejected. Everything else in the transport is stock
`QToolButton` and `QPushButton` driven by one stylesheet.

The genuine surprise is that **the Clip list cost more painting than the
timeline** — 134 lines against 120. Nobody flagged the list as the risk, but
"no column header, a colour bar, a 13px title and two right-aligned monospace
fields in a 32px row" is not something a stylesheet can express, so the whole
row shape becomes delegate code. If A wins, budget for that: it is where the
next visual change will land.

One structural point in A's favour: the styling is genuinely single-source. No
widget in this package calls `setStyleSheet`. Everything is either the one
generated sheet in `theme.py` or a dynamic property that sheet keys off. That is
the discipline whose absence let the shipped interface drift, and it held for a
whole interface without strain.

## What I could not make work, and what I did not do

1. **The specified typography is not on screen.** The tokens call for bundled
   Inter and JetBrains Mono in `assets/fonts/`. Neither is in the repository —
   only `NotoSans.ttf` is. `fonts.py` falls back to Noto Sans and Menlo and
   records the substitution. **The screenshots therefore do not show the
   specified type.** This also defeats the stated reason for bundling: the mono
   fallback is Menlo on macOS and Consolas on Windows, so the two platforms will
   not render identically until the fonts are actually vendored. Per the
   handoff I used the tokens as written and did not edit them.

2. **The icon geometry is hand-transcribed Lucide, not vendored Lucide.** With
   no network access I wrote the 25 icon paths from the Lucide set into
   `icons.py`. They are the right family, grid and stroke weight and look
   correct at 16px and 20px, but they are not guaranteed identical to upstream,
   and no ISC licence file is vendored. A real implementation must vendor the
   actual SVGs and the licence.

3. **Video compositing was never seen on a real display.** Everything ran
   headless; Qt reported `No RHI backend. Using CPU conversion.` A `QVideoWidget`
   inside a `QSplitter` is a native child surface, and its z-order behaviour
   against sibling widgets is exactly the kind of thing that is invisible
   headless and obvious on a real machine. Untested.

4. **No smooth playhead on real media**, for the `QMediaPlayer` reason in
   criterion 3. Interpolation is not implemented.

5. **Windows entirely untested.**

6. **The prototype mutates nothing.** Choosing a Category, editing a title or
   notes, and "Clip sichern" update no `Analysis`; the empty state accepts drag
   events but has no drop handler; toolbar file actions are inert. Deliberate,
   per the prototype rules — persistence is what a prototype checks, not what it
   depends on — but it means the editing state's *round trip* is unproven.

7. **Sidebar Clip titles elide sooner than I would like.** At the 300px default
   width, a row spends its right half on the Source cue, start timecode and
   duration, so "Tor nach Kreuzbewegung" shows as "Tor nach Kreuzbe…". Tooltips
   carry the full name and the sidebar is resizable to 420px, but if the owner
   reads truncation as the same failure the shipped column layout had, this
   needs a second look — probably dropping the duration column at narrow widths.

8. **Dark theme only, as specified**, so no light-mode work exists to judge.
