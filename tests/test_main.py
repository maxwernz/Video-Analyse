"""Application composition tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import main


class RecordingPresenter:
    """Records the scene window received after the QML scene is shown."""

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.window: object | None = None

    def set_scene_window(self, window: object) -> None:
        self.events.append("presenter")
        self.window = window


def test_the_presenter_receives_the_window_only_after_the_scene_is_shown(
    monkeypatch: Any,
) -> None:
    """Native panels need the actual, already-shown QQuickWindow as their owner."""

    events: list[str] = []
    scene_window = object()
    presenter = RecordingPresenter(events)
    monkeypatch.setattr(
        main,
        "show_quick_scene_with_fallback",
        lambda **_kwargs: events.append("shown")
        or SimpleNamespace(window=scene_window),
    )

    main._show_workspace_scene({}, presenter)

    assert events == ["shown", "presenter"]
    assert presenter.window is scene_window
