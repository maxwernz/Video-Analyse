"""Run every `test_qml_*.py` file alone, in its own process.

This is containment, not a root-cause fix, and it should be read that way.

Windows CI (only Windows; macOS and both packaging jobs stayed green
throughout) hit a `Windows fatal exception: access violation` partway
through the `test_qml_*.py` family, always in the *second* such file to run
in the process, never the first. Across three independent pushes it moved:

1. `tests/test_qml_clip_editor.py::form`, at `QQuickView.show()` — the very
   first `QQuickView` built after `test_qml_category_manager.py`'s own view
   had been closed, `setSource(QUrl())`'d, `deleteLater()`'d and the event
   loop pumped once.
2. After adding `QSG_RENDER_LOOP=basic` (see `conftest.py`), the same file's
   `form` fixture started surviving `show()` — three whole tests (three
   fresh `QQuickView`s, built and torn down) passed — before the fault
   recurred inside `Form.settle()`'s `QApplication.processEvents(); QTest
   .qWait(...); QApplication.processEvents()`, mid the *fourth* test.

Ruled out along the way, with evidence, not by assumption:

- **A real `FileDialog`'s `.open()` corrupting later `QQmlApplicationEngine`
  compilations** — a genuine, separately-observed Qt hazard on this branch
  (see `Dialogs.qml`'s own docstring and the neutralised-`open()` test in
  `test_qml_workspace.py`) — does not explain this failure: neither
  `test_qml_category_manager.py` nor `test_qml_clip_editor.py` ever loads
  `Main.qml` or `Dialogs.qml`, and both sort ahead of every file that does.
- **A dangling Recovery `QTimer`** (PR #77's own fix, for the same crash
  signature in a different fixture) — both files already inject an inert
  recovery scheduler and already do the complete
  `close(); setSource(QUrl()); deleteLater(); processEvents()` teardown PR
  #77 established. There is no real `QTimer` for either to leave behind.
- **The threaded render loop's asynchronous shutdown** — `QSG_RENDER_LOOP
  =basic` measurably changed the failure (delayed it by three whole
  QQuickView lifecycles) without eliminating it, which is evidence it was
  part of the picture, not the whole of it.

What is left, after those three, is Qt/QML process-global state that a
`QQuickView`'s teardown is not actually releasing before the next one — of
any kind, in any file — is built, and that only Windows's allocator is
strict enough to fault on. Nobody has found the dangling object. Rather than
guess a fourth time against a slow, one-shot-per-push CI signal, this file
makes the question moot: each `test_qml_*.py` file gets its own interpreter,
so there is no "later" for anything to leak into.

If a future contributor finds the actual dangling reference, removing it
(and this file) is the better fix — this one is deliberately a fence, not a
diagnosis.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from conftest import _QML_ISOLATED_SUBPROCESS_ENV

TESTS_DIR = Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent

#: Every file this suite otherwise hides from the top-level collection (see
#: `conftest.py`'s `collect_ignore_glob`) — discovered rather than
#: hand-listed, so a new `test_qml_*.py` file is isolated the same way
#: without anyone having to remember to add it here.
QML_TEST_FILES = sorted(
    path for path in TESTS_DIR.glob("test_qml_*.py") if path.name != Path(__file__).name
)

#: Long enough for a whole file's `QQuickView`-driving tests to run under a
#: loaded CI runner; short enough that a genuinely hung child still fails
#: the job instead of the job timing out an hour later with no diagnosis.
CHILD_TIMEOUT_S = 300


@pytest.mark.parametrize("qml_test_file", QML_TEST_FILES, ids=lambda path: path.name)
def test_a_qml_file_runs_cleanly_alone(qml_test_file: Path) -> None:
    """Every test in one `test_qml_*.py` file, in a process of its own."""

    env = dict(os.environ)
    env[_QML_ISOLATED_SUBPROCESS_ENV] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(qml_test_file), "-q"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_S,
    )

    assert result.returncode == 0, (
        f"{qml_test_file.name} failed in its own process "
        f"(exit code {result.returncode}):\n\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
