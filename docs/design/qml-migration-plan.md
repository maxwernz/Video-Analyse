# QML presentation-layer migration plan

Ready to be filed as a GitHub issue, in the style of issue #29. Decided by
[ADR 0008](../adr/0008-qml-presentation-layer.md); the design it implements is
[desktop-ux.md](desktop-ux.md) and [visual-tokens.md](visual-tokens.md).

## The one structural risk, named first

`tests/test_main_window_workflow.py` is the regression contract for the shipped
behaviour, and today it drives **widgets**. The migration deletes those widgets.
So the contract has to be re-expressed against the view models -- and if that
happens *while* the interface is being rewritten, a weakened assertion and a
broken feature are indistinguishable.

**Therefore stage 2 re-points the contract before any widget is replaced**, while
the old interface is still running and can prove the re-pointed tests still fail
for the right reasons. No stage after 2 may modify that file except to add cases.

## Stage 0 -- prerequisites, no user-visible change

Independent of everything else; can start immediately.

- **#a Vendor the typography.** Inter and JetBrains Mono into `assets/fonts/`
  with their SIL OFL licences. The spec has claimed these are bundled since it
  was written and it has never been true; both prototypes worked around it
  differently. Register them at startup and assert the registration, so a missing
  font fails loudly instead of silently falling back to Menlo or Consolas.
- **#b Vendor the icon family.** The real Lucide SVGs plus the ISC licence.
  Prototype A hand-transcribed 25 paths because it had no network; those are
  the right family but are not guaranteed to match upstream. Do not carry
  transcriptions into production.
- **#c Add volume to the player seam.** `playback/player.py` gains a volume
  property with a fake implementation, per
  [visual-tokens.md](visual-tokens.md#volume). The designed transport needs it
  and the seam cannot currently express it.
- **#d One resource-root helper.** In a macOS bundle, modules resolve against
  `Contents/Resources` while `Path(__file__).parent` lands in
  `Contents/Frameworks`. Prototype B found this the hard way. Decide it once;
  every later stage loads QML, fonts and icons through it.

## Stage 1 -- packaging foundation

Before there is any QML in production, prove production packaging can carry it.

- **#e Correct `EXCLUDED_MODULES`.** Remove `QtQml`, `QtQmlMeta`, `QtQmlModels`,
  `QtQmlWorkerScript`, `QtQuick`, `QtSvg` and `QtOpenGL`. Note prototype A's
  finding that the bare spellings never actually bit -- PyInstaller matches full
  module names -- so the list was already misleading. Update
  `tests/test_windows_packaging_contract.py` in the same change.
- **#f Move the TOC filter into `build_config/`.** The PySide6 hook, given
  `QtQml`, collects the whole Qt QML tree including QtWebEngine and 214MB of
  Chromium this application never loads, and `excludes` cannot reach it. The
  filter is the difference between a 447MB bundle and a 202MB one. It is
  load-bearing production configuration, not a prototype detail. Also drop
  `QtLocation`, `QtWebView`, `QtScxml`, `QtTextToSpeech` and `QtRemoteObjects`.
- **#g Guard the bundle size.** A test asserting an upper bound on the packaged
  size, so a future dependency cannot silently re-add Chromium. The accepted
  cost is +62MB of PySide6; anything far beyond that is a regression.
- **#h Software-rendering fallback.** Detect RHI initialisation failure and fall
  back to `QSG_RHI_BACKEND=software`, so an unmanaged Windows device with stale
  GPU drivers degrades to slow rather than crashing. This is the mitigation ADR
  0008 accepts in place of hardware nobody has.
- **#i Extend the Windows CI package job.** `tests/test_windows_package.py`
  should assert the QML engine loaded and a scene rendered, not merely that the
  process started. CI runners have no GPU, so this verifies the fallback path --
  which is exactly the path #h exists to protect.

## Stage 2 -- the view-model seam, no QML yet

- **#j Port the view models.** `WorkspaceViewModel`, `ClipListModel`,
  `RulerModel`, `TimelineRangeModel`, `timecode.py` and `icons.py` move from
  `prototype/presentation_b_qml/` into production. Pure Python, no QML engine,
  tested headless against `playback.FakePlayback` -- which is how the prototype
  built them in the first place.
- **#k Re-point the regression contract.** `tests/test_main_window_workflow.py`
  drives the view models instead of widgets, **while the existing interface still
  runs**. Every case must keep failing for the same reason it fails today; prove
  that by breaking each behaviour deliberately once. This is the stage that keeps
  the migration honest.

## Stage 3 -- shell cutover

- **#l The QML window replaces `workspace.py`.** Full-window Qt Quick, loaded
  through the stage-0 resource root, with the frozen tokens transcribed once into
  `Theme.qml` and referenced nowhere else.
- **#m Wire the menu bar.** A real parentless `QMenuBar` in Python -- the system
  menu bar on macOS, per ADR 0007's native-behaviour promise -- with its actions
  connected to `ApplicationWorkflow`. The prototype left this inert; New, Open,
  Save, Save As, Close, the unsaved-changes flow and shortcuts all land here.
- **#n Wire the toolbar.** The file and Analysis actions the prototype also left
  inert, plus the window title and dirty marker, plus drag-and-drop video adding.

## Stage 4 -- the surfaces

Each is a working surface against the real `Analysis`, not a rendering.

- **#o Timeline.** The 60px anatomy and the full ADR 0006 grammar. Ranges stay
  scene-graph items so Qt does the hit-testing; the ruler interval stays a Python
  decision.
- **#p Clip list.** Grouped by Category, 32px rows, no column header, monospace
  timecode. **Resolve the Source-video cue question first** -- see
  [visual-tokens.md](visual-tokens.md#source-video-cue); it is the one part of
  the design still genuinely open, and both prototypes hit the wall.
- **#q Transport.** Centred cluster, segmented speed control, mute plus the
  volume from #c, timecode right.
- **#r Clip editor.** Sectioned form, scrub-linked monospace boundary fields,
  live duration, accent primary and quiet secondary -- and the **full round trip
  to the Analysis**, which neither prototype implemented. Creating, editing,
  cancelling a Pending Clip and cancelling an edit all mutate or correctly fail
  to mutate the document.
- **#s Empty state.** The designed drop target with a working drop handler.

## Stage 5 -- playback correctness

Not visual work, and not optional. Both prototypes found all three.

- **#t Prime the video surface.** Qt's FFmpeg backend decodes nothing until
  playback has started once, so a freshly opened Analysis shows black until the
  coach presses play. A short priming play/pause through the public seam fixes it.
- **#u Interpolate the playhead.** `QMediaPlayer` emits position about sixteen
  times a second with no notify-interval control, so an uninterpolated playhead
  visibly steps. **Neither prototype demonstrated a smooth playhead on real
  media**; this is unproven work, not a port.
- **#v Throttle scrub seeks** to about twenty per second. Beyond that
  `QMediaPlayer` coalesces seeks and the picture stops following the pointer.
  Measured identically on Widgets and Quick surfaces.

## Stage 6 -- retire the old interface

Only once every surface is live. Delete `visual_system.py`, `workspace.py`,
`timeline.py`, `clip_handler.py`, `Ui_clip_handler.py`, `clip_handler.ui`,
`source_video_list.py`, `treewidget.py`, `treewidget_item.py`, `videowidget.py`,
`mainwindow.py`, `duration_edit.py`, `resources.qrc`, `resources_rc.py` and
`icons/` -- each only when nothing imports it. Retire
`prototype/presentation_a_widgets/` and `prototype/presentation_b_qml/` to the
same status as the earlier throwaway prototypes: kept as evidence, not as code.

## Stage 7 -- release gate

- **#w Real macOS launch.** Window resizing below the designed 1440x900 minimum
  (prototype B examined nothing narrower than 1200px), menus, dialogs, fonts,
  shortcuts, video compositing on a real display and on a Retina screen.
- **#x Real Windows launch.** **The gate ADR 0008 leaves open.** CI settles
  packaging, module collection, startup and the software fallback; it cannot
  settle Direct3D 11 on an unmanaged device's actual GPU driver. One launch on a
  real Windows machine. The cutover does not ship before this happens.

## Out of scope

Unchanged by this migration, and still owned by their existing issues: Recovery
snapshots (#19), relinking (#17), Category management (#18), a recent-files list,
Undo/Redo (#12), Combined export, and any feature from the reference
applications. This is a re-presentation of issue #29's behaviour, not a
re-specification of it.
