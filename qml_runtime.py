"""Show the application's Qt Quick scene, on hardware nobody manages.

Qt Quick renders through a graphics backend — Direct3D 11 on Windows, Metal on
macOS — where Qt Widgets rasterises on the CPU. Video Analyse is delivered to
unmanaged devices ([ADR 0001](docs/adr/0001-cross-platform-internal-releases.md))
whose graphics drivers nobody controls, so this module owns one promise: a
graphics backend that cannot initialise degrades the application to slow
software rendering rather than to a crash.

Callers ask for a scene and get one, or get an exception that says which of the
two failures happened — a scene that cannot be loaded is the developer's
mistake, and a scene graph that cannot start is the machine's.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import partial
import logging
import os
from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject, QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface

from app_runtime import resource_path
from qml_icons import install_icon_provider


#: The application's single QML entry point, bundled as data.
QML_SCENE = "qml/Main.qml"

#: Demand software rendering before any detection, for a driver that takes the
#: process down instead of reporting a failure the application could catch.
SOFTWARE_RENDERING_VARIABLE = "VIDEO_ANALYSE_SOFTWARE_RENDERING"

#: How long a first frame may take before the backend is presumed unusable.
FIRST_FRAME_TIMEOUT_MS = 15_000

logger = logging.getLogger(__name__)


class QmlSceneError(RuntimeError):
    """The QML scene itself could not be loaded, whatever the backend."""


class SceneGraphUnavailable(RuntimeError):
    """The graphics backend could not initialise a Qt Quick scene graph."""


@dataclass(frozen=True)
class QuickScene:
    """A loaded Qt Quick scene and the backend that is drawing it."""

    engine: QQmlApplicationEngine
    window: QQuickWindow
    source: Path
    rendering_backend: str
    warnings: tuple[str, ...] = field(default=())


def quick_scene_path() -> Path:
    """The bundled QML entry point, wherever this application was unpacked."""

    return resource_path(QML_SCENE)


def software_rendering_requested(
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Whether the operator has demanded software rendering up front."""

    values = os.environ if environment is None else environment
    return bool(values.get(SOFTWARE_RENDERING_VARIABLE, "").strip())


def use_software_rendering() -> None:
    """Draw every later Qt Quick scene on the CPU."""

    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)


def rendering_backend_of(window: QQuickWindow) -> str:
    """The graphics backend a window is actually drawing through."""

    renderer = window.rendererInterface()
    if renderer is None:
        return "unknown"
    return renderer.graphicsApi().name.lower()


def build_engine(
    qml_root: Path | None = None,
    *,
    context_objects: Mapping[str, QObject] | None = None,
) -> QQmlApplicationEngine:
    """A QML engine that can find everything this application's QML asks for.

    Two things, and they are the same kind of thing: the directory holding the
    components and the `Theme` singleton has to be an import path, and the icon
    family has to be reachable as an image provider, because Qt's SVG renderer
    cannot recolour an icon on its own. A component that cannot find either
    logs a warning and renders nothing, so both are set up here rather than by
    whoever remembers.

    The third thing a scene needs is whatever Python objects its bindings name
    — the workspace view model above all. A component whose `workspace` does
    not exist logs a warning per binding and draws nothing, so the objects are
    published on the root context before anything is loaded.
    """

    root = quick_scene_path().parent if qml_root is None else qml_root
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(root))
    install_icon_provider(engine)
    for name, published in (context_objects or {}).items():
        # The context holds no reference of its own: an object nobody else
        # keeps is collected, and every binding that named it reads `null`
        # and renders nothing. Ownerless objects are given to the engine so
        # that publishing one is enough to keep it.
        if published.parent() is None:
            published.setParent(engine)
        engine.rootContext().setContextProperty(name, published)
    return engine


def show_quick_scene(
    scene: Path | None = None,
    *,
    context_objects: Mapping[str, QObject] | None = None,
    first_frame_timeout_ms: int = FIRST_FRAME_TIMEOUT_MS,
) -> QuickScene:
    """Load the QML scene and wait until the graphics backend has drawn it.

    Waiting for a frame rather than for a root object is the point: a QML scene
    loads perfectly well on a machine whose graphics backend then fails to
    produce a single pixel, and only the frame distinguishes them.
    """

    scene_file = quick_scene_path() if scene is None else scene
    engine = build_engine(scene_file.parent, context_objects=context_objects)
    warnings: list[str] = []
    engine.warnings.connect(
        lambda reported: warnings.extend(warning.toString() for warning in reported)
    )
    engine.load(QUrl.fromLocalFile(str(scene_file)))

    roots = engine.rootObjects()
    if not roots:
        raise QmlSceneError(
            f"{scene_file} produced no scene: " + ("; ".join(warnings) or "no reason given")
        )
    window = roots[0]
    if not isinstance(window, QQuickWindow):
        raise QmlSceneError(f"{scene_file} is not a Window but a {type(window).__name__}")

    failures: list[str] = []
    window.sceneGraphError.connect(
        lambda _error, message: failures.append(message)
    )

    rendered = _wait_for_first_frame(window, first_frame_timeout_ms, failures)
    if failures:
        raise SceneGraphUnavailable("; ".join(failures))
    if not rendered:
        raise SceneGraphUnavailable(
            f"{scene_file} drew no frame within {first_frame_timeout_ms}ms"
        )

    return QuickScene(
        engine=engine,
        window=window,
        source=scene_file,
        rendering_backend=rendering_backend_of(window),
        warnings=tuple(warnings),
    )


def _wait_for_first_frame(
    window: QQuickWindow, timeout_ms: int, failures: list[str]
) -> bool:
    if window.isSceneGraphInitialized():
        return True

    loop = QEventLoop()
    drawn: list[bool] = []

    def frame_drawn() -> None:
        drawn.append(True)
        loop.quit()

    window.frameSwapped.connect(frame_drawn)
    window.sceneGraphError.connect(lambda *_: loop.quit())
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    return bool(drawn) or (window.isSceneGraphInitialized() and not failures)


def show_quick_scene_with_fallback(
    show: Callable[[], QuickScene] | None = None,
    *,
    select_software: Callable[[], None] = use_software_rendering,
    context_objects: Mapping[str, QObject] | None = None,
) -> QuickScene:
    """Show the scene, retrying once on the software backend if the first fails.

    A scene that cannot be loaded is not retried: software rendering cannot fix
    a QML file, and loading it twice only doubles the noise.
    """

    if show is None:
        show = partial(show_quick_scene, context_objects=context_objects)

    try:
        return show()
    except SceneGraphUnavailable as unavailable:
        logger.warning(
            "The graphics backend could not start Qt Quick (%s); "
            "falling back to software rendering",
            unavailable,
        )
        select_software()
        return show()
