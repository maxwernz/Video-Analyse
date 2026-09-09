# Compose the production workspace in code instead of Qt Designer

The validated desktop UX direction needs a tab-switched sidebar, a dedicated
Clip-editing state, and a compact timeline, which are layout *states* rather than
static widget trees. `main_window.ui` cannot express them without conditional code
that would live outside the file anyway, and it still encodes the single-video
assumptions the Analysis document replaced. The production workspace is therefore
composed in hand-written Python against `AnalysisDocument`, and `main_window.ui`
together with its generated `Ui_main_window.py` is retired.

## Considered options

- **Evolve `main_window.ui`.** Keeps the Designer round-trip and the existing widget
  names, but every new structural element is a mode change Designer renders poorly,
  and the generated file keeps growing as a merge hazard.
- **Compose the workspace in code.** Chosen. Mode changes, tab state, and timeline
  painting become ordinary Python, and the shell can be tested through the same
  controller seam as the rest of the application.

## Consequences

- `main_window.ui` and `Ui_main_window.py` are removed once the shell replaces them.
  `clip_handler.ui` is unaffected: the Clip form is a static widget tree and its
  `ClipDraft` seam is reused unchanged.
- The existing behavioral tests in `tests/test_main_window_workflow.py` are the
  regression contract for the replacement and must stay green.
- Designer remains available for future static forms. This decision is about the
  workspace shell, not a project-wide ban.
- Widgets are still forbidden from mutating the model directly; the shell talks to
  `Analysis` operations exactly as the current window does.
