# Model Analysis as a multi-video document

An Analysis is a UI-independent domain model with a stable identity, user-controlled title, ordered Source videos, ordered color-coded Categories, and Clips; an Analysis document owns the editing lifecycle for exactly one Analysis per window. This replaces the current UI-owned global state because multiple Source videos require explicit identity, relationships, and invariants that widgets and path strings cannot enforce.

## Consequences

- Analysis, Source video, Clip, and Category identities are stable UUIDs. A Clip belongs to exactly one Source video and satisfies `0 <= start < end <= duration` whenever its media is available for validation.
- An in-memory Analysis may contain no Source videos, but an Analysis file requires at least one. Source videos have a durable user-controlled order; Clip creation order is durable while view sorting is transient.
- Source videos remain external to the Analysis file. Each records an editable display name, last-known location, relocatable path information, duration, size, and a sampled-content fingerprint. The same media cannot be added twice.
- Missing Source videos do not prevent an Analysis from opening. The application tries the recorded location and a location relative to the Analysis file, then offers verified manual relinking. A fingerprint mismatch requires explicit confirmation before adopting replacement media.
- Removing a Source video with Clips requires confirmation and removes those Clips. Removing a Category preserves its Clips as uncategorized. Category names are non-empty and unique within an Analysis after trimmed, case-insensitive comparison.
- Category templates are installation-local starting collections copied into new Analyses; changing a template never changes an existing Analysis. The initial editable default template contains `Abwehr`, `Angriff`, and `Tor` and can be restored.
- One player and a Source-video selector switch the Active Source video. Navigating to a Clip switches to its Source video and seeks to its start. Loading or dropping a video adds it; starting over is a distinct New Analysis action. The selector was first described here as a persistent thumbnail strip; the validated direction replaced it with the sidebar's Videos tab, recorded in [the desktop UX direction](../design/desktop-ux.md) and built in issue #15.
- A Combined export may use Clips from several Source videos. Its initial Export list groups by Analysis-defined Category order, orders Clips within each group by Source-video order then start time, and places uncategorized Clips last; rearranging it does not mutate the Analysis.
- Durable mutations go through Analysis operations rather than direct widget mutation. The model and persistence layers do not import PySide. Mutation boundaries should permit later undo/redo, but undo/redo is outside this change.
- The reverted `Multiple-Videos` branch is a thumbnail-layout prototype, not a multi-video domain implementation. Reuse focused UI ideas only; do not replay its source-tree relocation, generated files, packaging experiments, scripts, hard-coded paths, or single-video state handling.
