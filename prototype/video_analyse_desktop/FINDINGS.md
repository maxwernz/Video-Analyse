# Desktop UX prototype findings

## Question and verdict

The prototype asked which left-sidebar hierarchy makes multi-Source-video Clip review,
two-press marking, detailed editing, and Combined export easiest to understand at
1440×900 and 1280×720.

**Use Variant A, “Balanced workbench,” as the implementation direction.** Keep its
always-visible Source-video list and combined chronological Clip list. Borrow the
compact editor treatment from Variant B and Category section headers from Variant C
only where a grouped view is explicitly selected.

This is a design verdict, not production-ready code. The prototype remains isolated
from the current widgets, persistence, MoviePy, and real media.

Primary-source capture: branch `prototype/desktop-ux-2026-09-09`, commit
`8420bde19fc3ecb9d7935b3257267ae1f159ea97`.

## Variant comparison

| Variant | What worked | What did not |
| --- | --- | --- |
| A · Balanced workbench | The Source video → Clip relationship is continuously visible. Three Source videos and roughly six Clip rows fit at 1440×900. A selected Clip remains easy to connect to the timeline. | The list shows fewer Clips than B. Opening the editor reduces the list to a handful of rows at 1280×720. |
| B · Clip-first command | Highest Clip density and the strongest home for the compact editor. The video remains usefully large with a 390 px editing sidebar at 1280×720. | Source videos become small controls below the fold and are too easy to treat as a secondary filter rather than owners of Clips. |
| C · Category lanes | Category grouping and counts are immediately legible; it maps well to grouped export. | The numeric Source-video rail is too cryptic, and a ten-Category Analysis becomes a long scan. It also hides chronological relationships across Categories. |

## Answers to the prototype questions

1. **Sidebar scan:** yes in A. Source rows need the fixed 46 px height used here;
   smaller thumbnail rows became unreadable during the first capture pass. B scans
   Clips fastest but weakens Source-video awareness. C should be an optional grouped
   view, not the default.
2. **Two-press marking:** yes after start is set. The cyan Pending Clip banner,
   persistent timecode, disabled/enabled Set end button, and platform shortcut keycap
   make the second action unambiguous. The idle shortcut hint is intentionally quiet
   and should be reinforced by onboarding/empty-state copy.
3. **Relationships:** A communicates them best. Combined-view rows name the Source
   video, Category is represented by both name and color, and the timeline repeats the
   color while selection adds a non-color outline. Selecting a Clip switches the fake
   active Source video and reports the seek time.
4. **Clip editing:** usable at 1280×720 when the sidebar temporarily grows to about
   390 px. The video remains larger than 800 px wide. An invalid end boundary remains
   in the field, shows a specific inline explanation, and visibly blocks Save.
5. **Combined export:** the two-column ordering/settings layout is understandable.
   The summary states that five visible Clips from all Source videos are seeded under
   the Angriff + Abwehr filter. Drag affordances and the “does not change the Analysis”
   note distinguish the Export list from durable Clip order.
6. **Recovery and failure states:** the Source-video removal warning names the video,
   says the original is not deleted, reports the exact affected count, defaults visual
   emphasis to Cancel, and gives the destructive button an outcome label. Missing
   media preserves visible Clips. Recovery distinguishes the Analysis file from the
   newer Recovery snapshot. Export progress, completion, and failure remain persistent
   and actionable.
7. **Localization and 1280×720:** core German and English workspace controls fit.
   Category names and Source-video titles remain Analysis content and therefore do not
   translate. The Windows build still needs a real 1280×720 check because only Qt's
   macOS/offscreen rendering was available here.
8. **Visual identity:** bright cyan works as an energetic action/selection accent on
   deep navy and stays distinct from the more muted Category ranges. Category names,
   dots, and selection outlines prevent color from carrying meaning alone. The palette
   takes only blue/white energy from the [HiM reference](https://www.him-spvgg.de/);
   it does not brand the general-purpose product as the club.

## Decisions to carry into production work

- Keep one resizable, collapsible left sidebar with Source videos first and Clips below.
- Default to all Clips across all Source videos; always show the Source-video name in
  that combined view. Hide it only when one Source video is explicitly filtered.
- Grow the sidebar to roughly 390 px while the compact editor is open rather than
  adding a permanent right inspector.
- Keep both direct boundary controls and the Command/Ctrl+R flow. Use a persistent
  Pending Clip banner until the pending state is resolved.
- Treat a Category-grouped Clip view as a user-selected presentation, not durable order.
- Keep Combined export on a dedicated two-column surface and the export job in a
  persistent bottom item so users can continue reviewing.
- Use specific recovery/removal/missing-media copy from the prototype as a starting
  point, adapted to real counts, names, paths, and platform Finder/Explorer wording.

## Spec conflicts to resolve before implementation

- The prototype handoff requests a built-in ten-Category handball template. ADR 0003,
  issue #12, and issue #18 currently define the built-in template as only `Abwehr`,
  `Angriff`, and `Tor`. The prototype displays the ten-Category handoff version to test
  density, but implementation must not silently change the ADR-backed contract.
- The handoff requests Undo/Redo for several mutations. Issue #12 explicitly leaves
  full Undo/Redo out of scope while preserving a future mutation seam. The UI may show
  the intended controls, but implementation scope needs an explicit follow-up decision.

## Verification performed

- `python -m py_compile prototype/video_analyse_desktop/prototype.py`
- `QT_QPA_PLATFORM=offscreen conda run -n VideoAnalyse python prototype/video_analyse_desktop/prototype.py --smoke`
- `QT_QPA_PLATFORM=offscreen conda run -n VideoAnalyse python prototype/video_analyse_desktop/prototype.py --capture`
- `git diff --check -- prototype/video_analyse_desktop`

The smoke path exercised marking, editor completion, Source-video and Category filters,
variant switching, localization, Combined export, and missing-media state. Fourteen PNG
captures cover the three variants and the required major states. A direct native window
launch was attempted but this execution environment reported “no screens available”;
the prototype therefore still needs a five-minute interactive pass in a normal macOS
desktop session and a Windows 11 pass before production implementation.
