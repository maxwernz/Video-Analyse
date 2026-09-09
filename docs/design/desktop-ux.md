# Desktop UX direction

## Status

This document records the validated direction from the second throwaway desktop UX
prototype. It guides production UI work but does not make the prototype production
code.

The timeline scope, the starter-Category count, and Undo/Redo were open when this
document was first written. All three are now resolved below, together with the scope
and ordering of the production UI release.

The prototype source and captures are in
[prototype/video_analyse_desktop_v2](../../prototype/video_analyse_desktop_v2/).
Its evaluation notes are in
[DESIGN_NOTES.md](../../prototype/video_analyse_desktop_v2/DESIGN_NOTES.md).

## Visual system

Video Analyse uses a restrained professional desktop character:

- neutral charcoal workspace surfaces;
- flat, flush panes separated by thin rules;
- square or minimally rounded controls;
- compact system typography and dense, readable rows;
- restrained blue for actions and selection;
- muted Category colors only when they convey analytical meaning.

The Binary Video Analysis reference informed visual restraint only. It does not define
Video Analyse's layout, feature set, or interaction density.

Category color is always secondary to the Category name and selection treatment.

## Workspace

The normal Analysis workspace has one main video area and a left sidebar.

The sidebar has separate **Clips** and **Videos** tabs:

- **Clips** contains the dense Clip list.
- **Videos** contains the Source-video selector.
- Each Clip retains a Source-video cue so it remains understandable while the Videos
  tab is not visible.

Selecting a Clip activates its Source video and seeks the player to the Clip start.

## Clip editing

Completing the second Clip boundary pauses playback and enters a dedicated Clip-editing
workspace. The editor keeps a large paused frame on the left and a structured editing
form on the right.

The form accommodates Clip title, Category, boundaries, notes, and future optional
fields without reducing the video workspace during normal review. This dedicated
editing state replaces both the centered modal approach and the permanent bottom dock.

Spatial shot-map controls were only a layout experiment. They do not introduce any
accepted sport-specific concepts or fields.

## Timeline

The production workspace uses one compact timeline directly beneath the video. It is
scoped to the **Active Source video** and it replaces the position slider rather than
sitting beside it, so the workspace has exactly one seek surface. See
[ADR 0006](../adr/0006-one-compact-timeline-as-the-sole-seek-surface.md).

Interaction:

- Clicking or dragging anywhere on the timeline scrubs the playhead to that time,
  including on top of a Clip range.
- Clicking a Clip range additionally selects that Clip without moving the playhead to
  its start.
- Double-clicking a Clip range seeks to the Clip start.
- Selecting a Clip in the Clips sidebar tab activates its Source video and seeks to
  its start.

A selected range is emphasized with a non-color treatment and its muted Category
color, and the selected Clip title and timecode appear near the timeline.

Clip ranges render with a minimum width of roughly three pixels: a ninety-minute
Source video across a twelve-hundred-pixel timeline is about four and a half seconds
per pixel, so short Clips would otherwise be invisible and unclickable. The timeline
does not zoom in this direction.

The timeline must not have permanently stacked Source-video lanes or duplicate the
Clip list.

## Responsive and platform validation

The chosen structure rendered cleanly at 1280×720 in offscreen checks. Production
validation still requires interactive testing on real macOS and Windows machines for
window resizing, menus, dialogs, fonts, shortcuts, and video behavior.

## Explicitly rejected directions

- The vibrant cyan/navy surfaces, rounded cards, badges, and elevated rows from the
  first prototype.
- A centered modal editor.
- A bottom editor dock that reduces video height.
- Large per-Source-video timeline lanes.
- Treating the throw-origin or goal-target prototype placeholders as accepted data
  concepts.

## Resolved product conflicts

1. **Starter Categories.** The three-Category default template from ADR 0003 and
   issue #18 stands: `Abwehr`, `Angriff`, `Tor`. The ten-Category set requested in the
   design discussion is deferred, not rejected. The template is installation-local,
   editable, restorable, and by design never propagates into existing Analyses, so
   growing it later is a template-content change rather than a code change and harms
   nobody who has already started work. Decide the ten from real handball coding.
2. **Undo and Redo.** Out of scope for the production UI release, as issue #12 already
   states. Undo/Redo constrains every durable mutation rather than adding a UI
   control, and the mutation seam ADR 0003 reserved (`Analysis.transaction()`) stays
   in place for it. The protections available meanwhile are confirmation on
   Source-video removal, Category removal leaving Clips intact and uncategorized, and
   Recovery snapshots (issue #19).

## Production UI release

The smallest release that reproduces this direction on top of `AnalysisDocument` is
specified as issue #29, which carries its user stories, implementation and testing
decisions, and ticket list. In order:

1. **Deepen playback** into an explicit player seam: load/unload, play/pause, seek,
   position, duration, rate, and stepping, with no widget construction inside it and a
   fake implementation for controller tests. Stepping uses a fixed interval
   independent of playback rate. Playback state stays transient and never dirties the
   Analysis document.
2. **Deepen application workflow**: New, Open, Save, Save As, Close, the
   unsaved-changes decision flow, additive video adding by dialog and drag-and-drop,
   the window title and dirty indicator, menus, and shortcuts. Recovery snapshots
   (#19), relinking (#17), and a recent-files list are excluded.
3. **Workspace shell**, replacing `main_window.ui`. See
   [ADR 0005](../adr/0005-compose-the-workspace-in-code.md). An Analysis with no
   Source videos renders as the normal workspace with an empty player, empty sidebar
   tabs, and an add-video call to action, not as a separate welcome screen.
4. **Clips/Videos sidebar and multi-video Clip work** (issue #15), which owns the
   sidebar rather than the thumbnail strip its original text described.
5. **Clip-editing state**: one editor serves both creating a Clip and editing an
   existing one. Cancelling a newly marked Clip discards the Pending Clip, which is
   not part of the Analysis. Clip boundaries are editable in the form.
6. **Compact timeline**, as described above.

Issues #16, #17, #19, and #20 follow against the finished interface. Category
management (#18) also follows: the release ships on the existing behavior where
typing an unknown Category name creates it.

The behavioral tests in `tests/test_main_window_workflow.py` are the regression
contract for this release and must stay green. Reproduction is verified through
controller behavior, not by comparing screenshots against the throwaway prototype.
Interactive validation on real macOS and Windows machines remains a pre-release step.

