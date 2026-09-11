# Present the workspace through a QML / Qt Quick layer over Python

Video Analyse's presentation layer becomes QML / Qt Quick. The existing Python
keeps every responsibility it has today: `analysis/` owns the model,
`application_workflow.py` owns the document lifecycle, `playback/` owns the
player seam, and QML sees none of them directly -- only view-model properties,
slots and item models.

This closes the question [ADR 0007](0007-branded-dark-visual-system.md) opened
and [desktop-ux.md](../design/desktop-ux.md) deliberately left undecided.

## Why, honestly

**Prototype A did not die.** Its kill condition was that reaching the visual bar
would turn the timeline and transport into an unmaintainable volume of custom
painting. It did not: the timeline came to 120 lines of painting in seven
single-purpose functions, the transport to 30, and 341 lines across the whole
interface. A cleared every failure marked in
[current-ui](../design/current-ui/). Anyone reading this later should know that
Qt Widgets **could** have carried this design.

Qt Quick was chosen anyway, by the owner, on the visual result and on one
structural property that showed up in prototype B: B imports no Qt Quick
Controls at all and draws every control from primitives, so there is no platform
style underneath arguing with the design. That is the exact failure mode ADR 0007
was written about -- an interface that reads as restyled stock controls -- and
Quick removes the possibility rather than managing it.

Both prototypes are recorded in `prototype/presentation_a_widgets/FINDINGS.md`
and `prototype/presentation_b_qml/FINDINGS.md`.

**One caveat on the comparison.** `visual-tokens.md` specified bundled Inter and
JetBrains Mono, but `assets/fonts/` contained only `NotoSans.ttf`. B vendored its
own copies; A fell back to Noto Sans and Menlo. The two prototypes were therefore
judged in different typefaces, and typography was one of the original complaints.
The decision was taken with that known.

## Considered options

- **A carefully redesigned Qt Widgets interface.** Cheapest by a wide margin: no
  new Qt modules, no packaging change, no size increase, and a presentation layer
  in one language. Rejected on the visual result, not on capability.
- **A QML / Qt Quick presentation layer over the existing Python.** Chosen.
- **Keep the shipped Widgets interface and restyle it.** Never seriously in
  play; ADR 0007 records why the shipped appearance is unacceptable.

## Costs accepted

Measured in prototype B, not estimated:

- **+62MB of PySide6** in the macOS bundle for the Qt Quick module tree.
- **`build_config/shared.py` must stop excluding what the app is made of.**
  `EXCLUDED_MODULES` lists `QtQml`, `QtQmlMeta`, `QtQmlModels`, `QtQmlWorkerScript`,
  `QtQuick`, `QtSvg` and `QtOpenGL`. Those entries go, and
  `tests/test_windows_packaging_contract.py` changes with them. Note that
  prototype A found the bare spellings never actually bit -- PyInstaller matches
  full module names -- so this is a correction of a list that was already
  misleading rather than a loosening of a real guard.
- **A PyInstaller TOC filter is load-bearing.** The PySide6 hook, given `QtQml`,
  collects the whole Qt QML tree including QtWebEngine and 214MB of Chromium that
  this application will never load. `excludes` cannot reach it because nothing in
  Python imports it. Filtering the collected tables is the difference between a
  447MB bundle and a 202MB one, and it must live in `build_config/`, not in a
  prototype spec.
- **A deliberate resource-root helper.** In a macOS bundle, modules resolve
  against `Contents/Resources` while `Path(__file__).parent` lands in
  `Contents/Frameworks`. This must be decided once rather than guessed per module.
- **Two languages in the presentation layer**, roughly 1400 lines of Python to
  2200 of QML, and an `icons.py` shim because Qt's SVG renderer has no
  `currentColor`.

## The unresolved Windows risk

Qt Quick's default RHI backend on Windows is Direct3D 11; Qt Widgets rasterises
on the CPU. Video Analyse is distributed to unmanaged Windows devices
([ADR 0001](0001-cross-platform-internal-releases.md)) whose GPU drivers nobody
controls. This is a failure mode A does not have, and **no prototype has cleared
it**: B was built on ARM64 macOS and never launched on Windows.

It is bounded three ways rather than left open:

1. The existing `package-windows` CI job on `windows-2025` builds the installer
   and verifies it end to end. Extended to assert that the QML engine loaded and
   a scene rendered, it settles packaging, module collection and startup -- the
   largest part of the risk.
2. CI runners have no real GPU, so a green run proves the **software fallback**
   path. The application therefore ships a detected fallback to
   `QSG_RHI_BACKEND=software`, so a driver failure degrades to slow instead of
   crashing.
3. One launch on a real Windows machine remains a release gate, as
   `desktop-ux.md` has required all along. Migration work proceeds meanwhile; the
   cutover does not ship before that launch happens.

## Consequences

- The presentation layer is rewritten; `analysis/`, `application_workflow.py` and
  `playback/` are not. Both prototypes confirmed those seams take a new interface
  without modification.
- `tests/test_main_window_workflow.py` stays the regression contract and must
  stay green throughout, driven through the view models rather than through
  widgets.
- `visual_system.py`, `workspace.py`, `timeline.py`, `clip_handler.py`,
  `source_video_list.py`, `treewidget*.py` and the `icons/*.png` set are retired
  at the end of the migration, not at its start.
- `playback/player.py` gains a volume property; the designed transport asks for
  one and the seam cannot currently express it.
- The menu bar stays a real parentless `QMenuBar` in Python, so ADR 0007's
  native-behaviour promise survives. Qt Quick's own `MenuBar` was never evaluated.
- Appearance is not covered by the test suite in either technology. That is
  unchanged by this decision, and it is why the visual direction is recorded in
  prose and tokens rather than in assertions.
