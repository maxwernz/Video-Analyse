# Use one compact timeline as the sole seek surface

The workspace shows a single compact timeline directly beneath the video, scoped to
the Active Source video, and it replaces the separate position slider rather than
sitting alongside it. Two stacked time strips under one video duplicate each other
and leave the user guessing which one seeks; a single strip that carries the
playhead and the Clip ranges of the Active Source video gives one unambiguous
mapping from pixel to time.

## Considered options

- **Scope the timeline to all currently visible Clips.** Better reflects cross-video
  filtering, but needs an invented representation for the durations of videos that
  are not active, which no prototype validated. Cross-video visibility already lives
  in the Clips sidebar tab, where every Clip keeps its Source-video cue.
- **Scope the timeline to the Active Source video.** Chosen. One real time scale, and
  the only option where seeking has a well-defined meaning.
- **Keep the position slider and add a read-only Clip navigator below it.** Rejected
  as the same duplication the design direction rules out for the Clip list.

## Consequences

- `position_slider` is removed with the rest of the Designer main window.
- Interaction grammar: clicking or dragging anywhere on the timeline scrubs the
  playhead to that time, including on top of a Clip range. Clicking a Clip range
  additionally selects that Clip without moving the playhead to its start.
  Double-clicking a Clip range seeks to the Clip start. Navigating to a Clip from the
  Clips sidebar tab activates its Source video and seeks to its start.
- Selected ranges are emphasized with a non-color treatment plus the muted Category
  color, and the selected Clip title and timecode appear near the timeline.
- Clip ranges render with a minimum width of about three pixels. A ninety-minute
  Source video across a twelve-hundred-pixel timeline is roughly four and a half
  seconds per pixel, so short Clips would otherwise be invisible and unclickable.
- The timeline does not zoom in this direction. If the minimum-width treatment proves
  insufficient for dense analyses, zoom is the follow-up, not stacked lanes.
