# Prototype B — QML / Qt Quick presentation layer

A **throwaway** prototype. It exists to answer whether a Qt Quick presentation
layer can carry the branded dark visual system of
[ADR 0007](../../docs/adr/0007-branded-dark-visual-system.md) while the existing
Python application layer survives underneath it unchanged.

It is not the production migration, and none of this code should be promoted.
The verdict is in [FINDINGS.md](FINDINGS.md).

## Run it

```sh
# Once: build the fixture media (about 30MB, gitignored, takes ~40s)
uv run python prototype/presentation_b_qml/tools/make_fixture_video.py

# The prototype
uv run python prototype/presentation_b_qml/run.py
```

Other entry points:

```sh
uv run python prototype/presentation_b_qml/run.py --empty      # the empty state
uv run python prototype/presentation_b_qml/capture.py          # the screenshots
uv run python prototype/presentation_b_qml/verify.py           # interaction + performance
uv run python prototype/presentation_b_qml/tools/scrub_probe.py  # Widgets vs Quick video surface
```

`run.py --fake-playback` drives the interface from `playback.FakePlayback` with
no media at all. It is useful for looking at layout, and it is **not** evidence
about the video surface.

## What it does

Two screens at a designed minimum of 1440x900, plus the empty state:

- **Normal workspace** — 44px working toolbar, 300px sidebar with Clips/Videos
  as a segmented control, Clip list grouped by Category in 32px rows, near-black
  stage, the 60px timeline, the 56px transport.
- **Clip-editing state** — large paused frame left, 360px sectioned form right,
  monospace scrub-linked boundary fields with a live duration readout.
- **Empty state** — the designed drop target.

Try: click and drag the timeline; click a Clip range (selects, does not seek);
double-click one (seeks to its start); press `M` twice to mark a Clip; edit a
boundary in the form and watch the video follow it; drag the sidebar's right
edge; switch to the Videos tab and activate the second half.

Keys: `Space` play/pause, `←`/`→` step, `Shift+←`/`→` five seconds, `M` mark,
`Esc` cancel, `Return` keep the Clip being edited.

## How it is put together

```
run.py            entry point: QApplication, native QMenuBar, QML engine
fixture.py        the canonical Analysis, built through the real analysis package
viewmodels.py     WorkspaceViewModel — the whole vocabulary QML has
models.py         QAbstractListModel projections: Clips, ranges, ruler, videos, Categories
timecode.py       every string the interface shows for a time
icons.py          QQuickImageProvider that recolours the SVG icon family
qml/              Theme.qml (the frozen tokens) and the components
qml/icons/        the Lucide-derived SVG family, one stroke weight
```

The application layer is the production one, imported unchanged:
`analysis/`, `application_workflow.py` and `playback/`. Nothing in those
packages was modified for this prototype — the QML video surface attaches
through `Playback.set_video_output` exactly as a widget would.

## What is not real

- The fixture media is generated, not match footage: a synthetic pitch with a
  burned-in timecode, at the real durations (45:00 and 42:30). The timecode
  burnt into the frame is what makes a seek visibly right or wrong in a
  screenshot.
- Toolbar file actions and the export action are inert. The document lifecycle
  they would drive is already covered by `application_workflow.py` and is not
  what this prototype is asking about.
- There are no tests, no error handling beyond what makes it run, and the
  fonts live here rather than in `assets/fonts/` (see FINDINGS.md).
