"""Suite-wide fixtures that keep the test suite from touching real state.

Nothing in this test suite may read or write an analyst's actual installation
data. Two Python-level settings resolve outside `tmp_path` unless something
redirects them: `recovery_settings.installation_recovery_store` and
`category_template_settings.installation_category_template_store` both go
through `QStandardPaths.writableLocation`, which — left alone — points at the
real per-user application-data and application-config directories on
whatever machine or CI runner the suite happens to run on.

A test that builds a `WorkspaceViewModel` or an `ApplicationWorkflow` without
explicitly injecting a `recovery_store` / `template_store` falls back to
those installation locations (`workspace_view_model.py`,
`application_workflow.py`). Most of this suite does exactly that — only a
handful of modules were careful to inject an isolated store themselves. Fixing
this once, here, is what makes that carefulness the suite's default instead
of an opt-in every test author has to remember.
"""

from __future__ import annotations

import gc
import os
from pathlib import Path

import pytest
from PySide6.QtCore import QStandardPaths

# Every QML test tears one `QQuickView`/`QQuickWindow` down and, a few tests
# later, brings another one up in the same process — this suite builds and
# destroys dozens of them across `test_qml_*.py`. Qt Quick's default render
# loop hands that lifecycle to a dedicated render thread whose shutdown is
# itself asynchronous (it posts back to the GUI thread once its GPU context
# is torn down), so a next window's construction can race a previous one's
# still-finishing render-thread teardown. `offscreen` gives every platform
# the same software rasteriser regardless, so there is no GPU throughput to
# lose by asking Qt to render on the GUI thread instead — `basic` — which
# removes that thread handoff, and with it the race, entirely. Set once here,
# before any test module (and therefore any `QQuickView`) exists, so it is
# not a property of which `test_qml_*.py` file happens to run first.
#
# This alone turned out not to be enough (Windows CI still faults, later and
# at a different call site — see the process-isolation note below), so it is
# kept as a real, if partial, mitigation rather than as the fix.
os.environ.setdefault("QSG_RENDER_LOOP", "basic")

#: Set by `test_isolated_qml_suite.py` in the child `pytest` process it
#: spawns for each `test_qml_*.py` file. Its presence is what tells *this*
#: conftest "you are that child" rather than the top-level run, so the
#: `collect_ignore_glob` below does not also hide the file from the process
#: whose entire job is to run it. See that module's docstring for why the
#: isolation exists at all — the short version is a Windows-only access
#: violation (`tests\test_qml_clip_editor.py`, in three different fixtures
#: and test bodies across three attempted fixes) that a `QQuickView`'s
#: teardown was not actually completing before the next one, of any kind,
#: was constructed in the same process.
_QML_ISOLATED_SUBPROCESS_ENV = "VIDEO_ANALYSE_QML_ISOLATED_SUBPROCESS"

if not os.environ.get(_QML_ISOLATED_SUBPROCESS_ENV):
    # Every `test_qml_*.py` file is run instead, one per child process, by
    # `test_isolated_qml_suite.py::test_a_qml_file_runs_cleanly_alone`.
    collect_ignore_glob = ["test_qml_*.py"]


@pytest.fixture(autouse=True)
def _isolated_standard_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect every `QStandardPaths` writable location under `tmp_path`.

    `QStandardPaths.setTestModeEnabled(True)` narrows the *locations Qt
    resolves* but still lands inside the real home or temp directory rather
    than this test's own throwaway `tmp_path`, so a crashing or interrupted
    test run can still leave files behind for the next one to trip over.
    Overriding `writableLocation` directly gives every location its own
    subdirectory under a `tmp_path` that pytest deletes for us, which is a
    stronger and simpler guarantee: nothing this suite does through
    `QStandardPaths` can ever reach outside the test run that made it.
    """

    root = tmp_path / "standard-paths"

    def _writable_location(location: QStandardPaths.StandardLocation) -> str:
        directory = root / QStandardPaths.StandardLocation(location).name
        directory.mkdir(parents=True, exist_ok=True)
        return str(directory)

    monkeypatch.setattr(QStandardPaths, "writableLocation", _writable_location)


@pytest.fixture(autouse=True)
def _collect_cyclic_qobjects_after_every_test() -> None:
    """Force the cycle `WorkspaceViewModel` -> `ApplicationWorkflow` ->
    (bound-method callbacks) -> `WorkspaceViewModel` to be collected at a
    test boundary, not whenever CPython's generational collector next feels
    like it.

    A `WorkspaceViewModel` built with no `parent` — which is how most of
    this suite, and production at the top of the window stack, builds one —
    is a `QObject` owned by Python refcounting rather than by Qt's
    parent/child tree. `ApplicationWorkflow` holds bound methods of the
    view model that constructed it (`on_document_changed` and friends), and
    the view model holds the workflow back, so the pair is a reference
    cycle: plain refcounting never reaches zero for it, no matter how many
    local variables holding it go out of scope. Only the cyclic collector
    ever reclaims it, and until it does, every real `QTimer` that object
    still owns — the priming timer, the interpolation ticker started by
    `playPause()` and left running, the Recovery debounce — stays armed and
    parented to a live C++ object, because Qt's own parent/child ownership
    keeps a child `QTimer` alive exactly as long as its parent `QObject` is.
    That timer fires for real the moment anything in the process spins an
    actual `QEventLoop`, which is rare in this suite but not nonexistent
    (`test_workspace_view_model.py`'s
    `test_priming_uses_the_event_loop_when_nobody_supplies_a_schedule`) —
    and CPython's generational collector can just as easily decide to run
    its own sweep *during* that same real event-loop turn, tearing down an
    unrelated test's leftover view models, players and documents while a
    Windows message pump is mid-dispatch for one of their timers. That is
    consistent with a fault that keeps moving between fixes: it is a race
    between "how much cyclic garbage has piled up" and "does anything ever
    call `gc.collect()`", not a defect in any one test.
    Collecting after every test — a cheap, empty sweep on a clean process —
    keeps that garbage from ever accumulating past a single test's worth,
    so nothing is ever both dangling and armed when a real event loop, if
    one runs at all, gets its turn.
    """

    yield
    gc.collect()
