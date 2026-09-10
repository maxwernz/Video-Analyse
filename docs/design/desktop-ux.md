# Desktop UX direction

## Status

The **structural and behavioural** direction in this document, validated by the
second throwaway desktop UX prototype, still stands: one video area with a left
sidebar, Clips/Videos tabs, a dedicated Clip-editing state, and one compact
timeline as the sole seek surface.

The **visual** direction recorded here is superseded. The shipped interface built
on it is functionally correct and visually unacceptable to the owner. See
[Superseded visual assumptions](#superseded-visual-assumptions) for what was
withdrawn and why, and [ADR 0007](../adr/0007-branded-dark-visual-system.md) for
the decision that replaces it.

The presentation-layer technology is **undecided**. Two prototypes settle it; see
[Presentation-layer prototypes](#presentation-layer-prototypes).

## Evidence

Design decisions here are grounded in captured evidence, not description.

- [docs/design/current-ui](current-ui/) -- the shipped interface at 1440x900,
  including copies with the worst areas marked.
- [docs/design/references](references/) -- the applications the owner accepts as
  professional: Catapult (primary), In-Play (secondary), TactiCode.

The references are accepted **for visual character only**. Their features are not
adopted; see [Excluded from the references](#excluded-from-the-references).

## Visual system

Video Analyse presents a branded dark interface, not a native-looking one. It
keeps native *behaviour* -- menu bar, window controls, file dialogs, shortcuts --
and owns its *appearance*.

The character, taken from the Catapult reference:

- near-black video stage, so the frame is the brightest thing on screen;
- three surfaces and one hairline, no gradients, shadows or elevated cards;
- chrome that recedes; the video dominates the window;
- one saturated signature accent, reserved for the playhead, the primary action
  and selection, and used for nothing else;
- a fixed, harmonised ten-entry Category palette, never a free colour picker;
- bundled typography with a monospace for every timecode;
- one open SVG icon family at one stroke weight.

Exact values are frozen in [visual-tokens.md](visual-tokens.md). Both prototypes
consume them unchanged.

Dark only. The interface does not follow the OS theme.

## Workspace

One main video area and a left sidebar.

The chrome above the workspace is a **working toolbar**, roughly 44px: file and
Analysis actions grouped left, the Analysis name and dirty state, view controls
right. There is no product wordmark anywhere in the interface.

The sidebar keeps its separate **Clips** and **Videos** tabs, rendered as a
segmented control rather than underlined web-style tabs:

- **Clips** contains the dense Clip list.
- **Videos** contains the Source-video selector.
- Each Clip retains a Source-video cue so it remains understandable while the
  Videos tab is not visible. The cue is shown only when the Analysis has more
  than one Source video.

Selecting a Clip activates its Source video and seeks the player to the Clip start.

### Clip list

Grouped by Category. There is **no column header**: a spreadsheet header strip is
not something a coach reads, and it was what truncated the Source-video column at
the default sidebar width.

A row is 32px and carries a 3px full-colour Category bar at its leading edge, the
Clip title at 13px, and start time plus duration right-aligned in monospace.
Proportional digits are why the previous columns never aligned optically.

### Empty state

An Analysis with no Source videos renders as the normal workspace with empty
sidebar tabs -- not as a separate welcome screen. The empty stage carries a
designed drop target: a centred bordered zone with an icon, "Video hinzufuegen",
the drag-and-drop hint and the keyboard shortcut. A flat black rectangle is not
an acceptable first impression.

## Clip editing

Completing the second Clip boundary pauses playback and enters a dedicated
Clip-editing state, with a large paused frame on the left and a structured form
on the right, 360px wide.

The form is sectioned with rules and carries Clip title, Category, boundaries,
notes and future optional fields. Boundary fields are monospace, sized for a full
timecode, show a live duration readout, and are **scrub-linked**: adjusting a
boundary moves the video to that frame. The action row resolves to an accent
primary and a quiet secondary.

This dedicated editing state replaces both the centered modal approach and the
permanent bottom dock.

## Timeline

One compact timeline directly beneath the video, scoped to the **Active Source
video**, replacing the position slider so the workspace has exactly one seek
surface. See [ADR 0006](../adr/0006-one-compact-timeline-as-the-sole-seek-surface.md).

Interaction (unchanged):

- Clicking or dragging anywhere on the timeline scrubs the playhead to that time,
  including on top of a Clip range.
- Clicking a Clip range additionally selects that Clip without moving the playhead
  to its start.
- Double-clicking a Clip range seeks to the Clip start.
- Selecting a Clip in the Clips sidebar tab activates its Source video and seeks
  to its start.

Anatomy (new):

- 60px total: a 16px ruler above a 44px track. The previous 30px strip could not
  carry a legible ruler, a grabbable playhead and visible ranges at once, and
  that constraint is most of why it read as an unstyled progress bar.
- The ruler has labelled minute marks at an adaptive interval with unlabelled
  minor ticks.
- Clip ranges are filled bars in the Category colour at 40% alpha with a 1px
  full-colour top edge, not hairline ticks.
- A selected range is emphasised by brightening plus an outline -- a non-colour
  treatment -- and the selected Clip title and timecode appear near the timeline.
- The playhead is a 2px accent line with a grabbable handle at the ruler.
- Hovering shows a thin cursor line and a timecode tooltip.
- Elapsed and total time move out of the timeline's ends and into the transport,
  since the ruler now carries time.

Ranges keep a minimum width of about three pixels. **This is a known limitation,
recorded honestly**: a ninety-minute Source video across a twelve-hundred-pixel
timeline is roughly four and a half seconds per pixel, so a seven-second Clip is
about one and a half pixels and the minimum width makes short Clips overstate
their duration, while two nearby Clips can merge visually. Accepted for now,
because the timeline's job is orientation and scrubbing while precise work happens
in the Clip list and the Clip editor. The named escape hatch, if it proves
insufficient, is **zoom to the selected Clip** -- never permanently stacked
Source-video lanes, and never a duplicate of the Clip list.

## Transport

One row, roughly 56px:

- left: volume and mute;
- centre: a single cluster -- step back, minus five seconds, play/pause rendered
  larger than its neighbours, plus five seconds, step forward;
- right: playback speed as a menu or segmented control, the mark-Clip action as
  the one accent-coloured primary button, and elapsed / total timecode in
  monospace.

Playback speed must not be a stock `QComboBox`. In the captured evidence that one
control signals "default Qt" more loudly than anything else in the window.

## Presentation-layer prototypes

Qt Quick is a **candidate, not a conclusion**. QML does not create good design on
its own, and a carefully redesigned Widgets interface may well reach the bar. Two
throwaway prototypes settle it:

- **A** -- a carefully redesigned, mostly native Qt Widgets interface.
- **B** -- a full-window QML / Qt Quick presentation layer that retains the
  existing Python `Analysis`, `AnalysisDocument`, workflow and playback logic.

Fairness rules:

- Both build the same two screens: the normal workspace (toolbar, sidebar tabs,
  populated Clip list, the 60px timeline with ruler and real ranges, transport)
  and the Clip-editing state.
- Both consume the same frozen tokens, icon set and canonical fixture from
  [visual-tokens.md](visual-tokens.md).
- Both are throwaway and live under `prototype/`. Neither is allowed to be the
  sketch version of the other.
- They are built in parallel from written handoffs, against the frozen spec, so
  neither can copy the other.

Decision criteria:

1. Visual result against the reference captures.
2. Timeline rendering and interaction quality: custom-drawn ranges, smooth
   playhead, hit-testing.
3. Performance during playback and scrubbing.
4. Packaging on **both** macOS and Windows, since delivery is internal
   distribution to unmanaged devices.
5. How much Python the presentation layer needs, and how testable it stays
   against the existing `Analysis` / `AnalysisDocument` / player seams.

Kill conditions, named in advance:

- **B dies** if video rendering into QML or packaging regresses on either
  platform, or if it forces application logic out of Python and into JavaScript.
- **A dies** if the timeline and transport cannot reach the visual bar without
  becoming a volume of custom `paintEvent` code that cannot be maintained.

Judged by running both on real macOS and Windows machines. Not by comparing
screenshots: scrub smoothness, video surface compositing and packaging are all
invisible in a still image.

## Excluded from the references

Accepted for visual character only. These are **not** adopted as features:
on-video annotation and telestration, live tagging button grids, per-tag stacked
lane timelines, tabular event registries, presentation and sharing toggles,
multi-user avatars and notification badges.

Two reference details are kept as *presentation*, not features: In-Play's
labelled time ruler, and Catapult's single centred transport cluster with
timecode pinned right.

## Superseded visual assumptions

Withdrawn. Any document, issue or code comment relying on these is out of date.

- **"Restrained professional desktop character" as executed.** The problem was
  never insufficient colour. It was missing typographic hierarchy, missing
  vertical rhythm, unstyled stock controls and an unstyled timeline.
- **Neutral charcoal surfaces at ten near-identical greys.** Replaced by three
  surfaces and one hairline. Ten greys inside twenty luminance points is not
  restraint, it is the absence of a decision.
- **Compact system typography.** Replaced by bundled typography on a fixed scale
  with monospace timecode. The previous 9px and 10px letterspaced capitals are
  withdrawn outright.
- **"Restrained blue for actions and selection"** (`#5D8FC7`). Replaced by one
  saturated signature accent, reserved for three uses.
- **"Muted Category colours only when they convey analytical meaning", chosen
  freely.** Replaced by a fixed harmonised palette, applied consistently in the
  Clip list and the timeline.
- **The product wordmark strip beneath the native menu bar.** Deleted; replaced
  by a working toolbar.
- **SF Symbols raster icons.** Retired in favour of one open SVG family.
- **The 30px timeline without a ruler.** Replaced by the 60px anatomy above.
- **"The Binary Video Analysis reference informed visual restraint only."**
  Superseded: the accepted references are now Catapult, In-Play and TactiCode,
  captured in this repository.
- **The implicit assumption that Qt Widgets is the presentation layer.** Now an
  open question decided by the prototypes.

Explicitly *not* superseded, and still rejected: the vibrant cyan/navy surfaces,
rounded cards, badges and elevated rows from the first prototype; a centered modal
editor; a bottom editor dock that reduces video height; large per-Source-video
timeline lanes; and treating the throw-origin or goal-target prototype
placeholders as accepted data concepts.

## Responsive and platform validation

Minimum designed window size is 1440x900. Production validation requires
interactive testing on real macOS and Windows machines for window resizing, menus,
dialogs, fonts, shortcuts and video behaviour.

## Resolved product conflicts

1. **Starter Categories.** The three-Category default template from ADR 0003 and
   issue #18 stands: `Abwehr`, `Angriff`, `Tor`. The ten-Category set requested in
   the design discussion is deferred, not rejected. The template is
   installation-local, editable, restorable, and by design never propagates into
   existing Analyses, so growing it later is a template-content change rather than
   a code change and harms nobody who has already started work. Decide the ten
   from real handball coding.
2. **Undo and Redo.** Out of scope for the production UI release, as issue #12
   already states. Undo/Redo constrains every durable mutation rather than adding
   a UI control, and the mutation seam ADR 0003 reserved (`Analysis.transaction()`)
   stays in place for it. The protections available meanwhile are confirmation on
   Source-video removal, Category removal leaving Clips intact and uncategorized,
   and Recovery snapshots (issue #19).

## Production UI release

The behavioural release specified as issue #29 is built and its ordering is
unchanged. The visual work in this document is a **re-presentation** of that
release, not a re-specification of its behaviour.

The behavioural tests in `tests/test_main_window_workflow.py` remain the
regression contract and must stay green through the presentation change,
whichever prototype wins. Reproduction is verified through controller behaviour,
not by comparing screenshots.
