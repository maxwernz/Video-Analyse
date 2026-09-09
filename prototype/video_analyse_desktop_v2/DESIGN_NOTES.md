# Design notes — restrained desktop iteration

## What changed from V1

The first prototype used too many saturated colors, rounded containers, badges, and
individually elevated rows. Those choices made it feel generated rather than like a
focused desktop tool.

This iteration uses the Binary Video Analysis reference only for visual principles:

- neutral charcoal instead of blue-black page backgrounds;
- panes separated by thin rules instead of floating cards;
- square or 2 px-radius controls;
- compact system typography and denser rows;
- one muted blue interaction accent;
- muted Category colors confined mostly to Clip markers and timelines.

It does not copy the reference application's tool density, layout, or feature set.

## Three structural ideas

### A · Tabbed library + modal

The left pane switches between Clips and Source videos. This directly tests the user's
tab idea and keeps each mode calm. Completing the second Clip boundary pauses playback
and opens a focused editor over the frozen video.

Likely strength: clearest overall hierarchy and strongest post-marking moment.

Risk: Source videos are not visible while the Clip tab is active. Each Clip therefore
must retain its `V1`/`V2`/`V3` cue, and timeline selection must switch the active Source
video automatically.

### B · Video tabs + editing dock

The Clip list is permanent. Source videos become conventional tabs immediately above
the player. The editor opens as a wide dock below the timeline, keeping both the Clip
list and paused frame visible.

Likely strength: quickest for repeated coding because context never disappears.

Risk: the editor makes the video substantially shorter at 1280×720, and future rich
fields would force scrolling or a larger dock.

### C · Source lanes + edit workspace

The normal view uses one timeline lane per Source video. Finishing a Clip enters a
dedicated edit workspace with a large paused frame and a structured editor on the
right.

Likely strength: best explanation of multi-video time and most room for future fields.

Risk: switching into an edit workspace is a larger mode change and may feel heavy for
quick Clip naming.

## Timeline behavior

Every colored rectangle is a real clickable target in the prototype. Clicking it:

1. selects the Clip with a white outline and blue underline;
2. switches the active Source video when necessary;
3. updates the current Clip title and timecode;
4. represents a seek to the Clip start in the state bar.

Variant A/B use a single chronological navigator. Variant C uses one lane per Source
video. Category color is deliberately subdued and never acts alone: the sidebar names
the Category and the selected range gains a non-color outline.

## Clip editor and shot-map placeholder

The optional shot map is only a spatial-layout experiment. The left half marks a throw
origin; the right half marks a goal target; both are clickable. It demonstrates how a
future richer Clip annotation can fit without turning the main workspace into a form.

No `Goal`, `Shot`, `Throw`, position, or outcome concept has been added to `CONTEXT.md`.
That domain work should happen only after the interaction proves useful and the actual
data questions are known.

## Suggested review order

1. Open A at 1280×720, switch Clips/Videos, then open the editor.
2. Open B at 1280×720 and judge whether the smaller video is acceptable during editing.
3. Open C, click several blocks across V1/V2/V3, then open the editor.
4. Decide independently on visual style, video navigation, editor location, and
   timeline type. A mixed answer is expected.
