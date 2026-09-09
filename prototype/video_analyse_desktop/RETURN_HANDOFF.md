# Return handoff: Video Analyse desktop UX prototype

## Outcome

The throwaway PySide6 prototype is complete and isolated under
`prototype/video_analyse_desktop/`.

Recommended direction: implement **Variant A · Balanced workbench** as the base. It
keeps three Source videos continuously visible above a combined chronological Clip list,
and each Clip names its Source video. Borrow Variant B's compact 390 px editor and use
Variant C's Category headers only for an explicitly grouped view.

## Run and inspect

```sh
cd /Users/maxwernz/development/VideoAnalysePy
conda run -n VideoAnalyse python prototype/video_analyse_desktop/prototype.py
```

The fixed bottom bar switches A/B/C, all 13 requested scenarios, language, and target
window size. Left/right changes variant. Command+R on macOS and Ctrl+R on Windows run
the two-press Pending Clip flow.

Read the evidence and verdict in `prototype/video_analyse_desktop/FINDINGS.md`.
Fourteen captures are in `prototype/video_analyse_desktop/screenshots/`.

The visual primary source is preserved on remote branch
`prototype/desktop-ux-2026-09-09` at commit
`8420bde19fc3ecb9d7935b3257267ae1f159ea97`. Keep that branch throwaway and out of
`main`; production code should implement only the accepted decisions.

## Validated design decisions

- Always-visible Source-video list above Clips is clearest for multi-video ownership.
- Default combined Clip rows must name their Source video; omit it only under an active
  single-Source-video filter.
- Cyan Pending Clip banner + explicit start time + enabled Set end control makes the
  two-press flow understandable.
- A temporary 390 px sidebar while editing keeps inputs usable at 1280×720 without
  making the video too small.
- Invalid timecode remains visible, gets a specific inline reason, and blocks Save.
- Category color works when repeated on the timeline but must be backed by name, dot,
  and selected-range outline.
- Combined export works best as a two-column surface with ordering left and presentation
  settings right; its persistent bottom status supports progress, completion, failure,
  retry, and Finder/Explorer reveal.
- Recovery, missing-media, and cascade-removal copy is specific enough to guide action.
- Core German and English workspace labels fit at 1280×720 in the rendered captures.

## Decisions needed before production UI work

1. The handoff specifies ten built-in handball Categories, but ADR 0003 and GitHub
   issues #12/#18 specify only Abwehr, Angriff, and Tor. The prototype deliberately uses
   ten to test density. Resolve and update the ADR/spec before implementation.
2. The handoff asks for Undo/Redo, while issue #12 explicitly leaves full Undo/Redo out
   of the current change. Decide whether to create a follow-up issue or expand scope.
3. Run the prototype interactively on a normal macOS desktop and Windows 11 at 1280×720.
   Automated offscreen capture and transition checks passed, but the sandbox had no
   native display available for the final launch.

## Relevant implementation issues

- Parent architecture/spec: #12
- Multi-video Clip navigation: #15
- Source-video lifecycle/removal: #16
- Missing media and relinking: #17
- Categories/templates: #18
- Recovery snapshots: #19
- Combined exports: #20

Do not copy the prototype wholesale into production. Rebuild the accepted behaviors
against the Analysis/AnalysisDocument model and preserve the prototype on its throwaway
branch as the visual primary source.
