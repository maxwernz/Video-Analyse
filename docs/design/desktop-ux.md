# Desktop UX direction

## Status

This document records the validated direction from the second throwaway desktop UX
prototype. It guides production UI work but does not make the prototype production
code.

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

The production workspace uses one compact timeline directly beneath the video.

It provides clickable visible Clip ranges or markers. Activating one:

1. selects the Clip;
2. activates its Source video when necessary;
3. seeks to its start;
4. emphasizes the selected range with a non-color treatment and its muted Category
   color;
5. shows the selected Clip title and timecode near the timeline.

The timeline must not have permanently stacked Source-video lanes or duplicate the
Clip list.

### Open timeline decision

Before production UI work begins, choose one scope for the compact timeline:

- **Active Source video only**, which is simpler and gives the clearest time scale; or
- **All currently visible Clips**, which better reflects cross-video filtering but
  needs a clear representation of unrelated source durations.

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

## Open product conflicts

These decisions need explicit resolution before their implementation tickets are
completed:

1. The design discussion requested ten starter handball Categories, while ADR 0003
   and issue #18 currently specify a restorable three-Category default template.
2. The design discussion requested Undo and Redo, while issue #12 currently leaves
   full Undo/Redo out of scope.

