The fastest good route is to stop treating this as one giant refactor and work toward a concrete milestone:

> A distributable macOS/Windows app with the prototype’s core UI, working multi-video analysis, reliable playback, Clip creation/editing, saving, and basic export.

You do not need another architecture review. That review already identified the remaining four areas. Each now enters the normal Matt workflow.

First, finish testing and merging #8 and #14. Then make sure GitHub `main` is clean and current. Every future ticket must branch from that exact main commit.

Next, finish the UI planning before writing production UI code. In the original UX/design session, run:

> `$grill-with-docs Resolve the three open decisions in docs/design/desktop-ux.md and define the smallest production UI release that reproduces the validated V2 prototype on top of AnalysisDocument.`

The three open decisions are timeline scope, default Categories, and Undo/Redo scope. Then, without clearing that context, run:

```text
$to-spec
$to-tickets
```

That produces the missing UI implementation tickets with dependencies. The prototype code itself stays on its prototype branch; production tickets use [desktop-ux.md](/Users/maxwernz/development/VideoAnalysePy/docs/design/desktop-ux.md), screenshots, and prototype behavior as references.

The fastest implementation order after that is:

| Phase | Work |
|---|---|
| 1 | Merge #8 and #14 |
| 2 | Resolve UX decisions and generate UI tickets |
| 3 | Update #15 to use the validated Clips/Videos sidebar design, then implement #15 |
| 4 | Deepen and implement Playback |
| 5 | Deepen and implement Application Workflow |
| 6 | Implement the core UI tickets: shell, sidebar, Clip editor, compact timeline |
| 7 | Implement #16, #17, #18, and #19 around the new interface |
| 8 | Deepen Export, then implement #20 |
| 9 | Finish #9/#10 and publish through #11 |

Playback should come before the final timeline because the timeline needs trustworthy player state, errors, duration, seeking, and end-of-Clip behavior.

Application Workflow should come before most production UI wiring because it removes coordination from `MainWindow`. The new UI can then call clear actions such as open Analysis, add Source video, begin Clip, save Clip, and export instead of rebuilding another large `MainWindow`.

For each remaining architecture candidate, use these prompts in a dedicated planning session:

> `$grill-with-docs Deepen the Playback module from the completed architecture review, focusing on reliable Qt media state, seeking, errors, Clip preview, and the compact timeline.`

> `$grill-with-docs Deepen the Application Workflow module from the completed architecture review, focusing on document actions, playback coordination, Clip capture, dialogs, and export without letting MainWindow own every workflow.`

> `$grill-with-docs Turn the validated desktop UX in docs/design/desktop-ux.md into the smallest production Presentation module that works at 1280×720 on macOS and Windows.`

> `$grill-with-docs Deepen the Export job module from the completed architecture review, using multi-video Analysis state and the validated Combined-export workflow.`

For each one, keep the sequence together:

```text
$grill-with-docs
→ $to-spec
→ $to-tickets
```

Then every generated ticket gets a fresh session and worktree:

```text
$implement #ticket
```

`$implement` should perform focused TDD, run `$code-review`, commit, and push. Do not reuse an implementation session for the next ticket; clear it and start fresh.

Parallelize planning aggressively, but code conservatively. This repository still has central files such as `mainwindow.py`, `analysis/model.py`, and `AnalysisDocument`, so multiple implementation agents touching those files often lose more time during integration than they save.

A safe pattern is:

- One production feature or architecture ticket that changes `MainWindow` or Analysis state.
- One packaging/CI ticket in parallel.
- One planning or prototype-evaluation session in parallel.
- Additional implementation only when its file ownership is clearly separate.

When two branches run in parallel, merge the more foundational one first. Rebase the other onto updated main, rerun its complete test suite, then merge it.

Testing should happen at ticket boundaries:

1. Focused tests while implementing.
2. Full tests and smoke test before committing.
3. PR CI on macOS and Windows.
4. After merging, full tests on main plus one short manual workflow.
5. After every few merged tickets, build an internal installer and test the whole user journey.

You do not need to perform an exhaustive manual test after every ticket. For the basic app milestone, manually verify this sequence after relevant merges:

```text
launch
→ create/open Analysis
→ add multiple Source videos
→ play and seek
→ mark and edit Clips
→ switch videos by selecting Clips
→ save and reopen
→ export a short result
→ close safely
```

The four remaining architecture candidates are therefore not a separate long project that must finish before the UI. Playback and Application Workflow prepare the UI; Presentation is the UI implementation itself; Export follows once the multi-video model and Category behavior are stable.
