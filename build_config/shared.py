"""Shared PyInstaller configuration for every Video Analyse platform package.

Platform specifications import this module so that application entry points,
dependencies, bundled resources, and metadata cannot drift between platforms.
"""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


APPLICATION_NAME = "Video Analyse"
BUNDLE_IDENTIFIER = "de.maxwernz.videoanalyse"
ARTIFACT_BASE_NAME = "Video-Analyse"
MACOS_ARCHITECTURE = "arm64"
PUBLISHER = "maxwernz"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRY_SCRIPT = str(PROJECT_ROOT / "main.py")

#: The Qt Quick presentation layer, which nothing in Python imports by name.
QT_QUICK_IMPORTS = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtSvg",
]

HIDDEN_IMPORTS = ["moviepy", *QT_QUICK_IMPORTS]

#: Modules PyInstaller must leave out of every package.
#:
#: PyInstaller matches full module names, so every entry is spelled in full.
#: This list once named `QtQml`, `QtQuick`, `QtSvg` and `QtOpenGL` — the very
#: modules the interface is now made of — in a bare spelling that never
#: matched anything, so it excluded nothing while appearing to.
EXCLUDED_MODULES = [
    "PySide6.QtDBus",
    "PySide6.QtPdf",
    "PySide6.QtVirtualKeyboard",
]

#: Qt modules PyInstaller's PySide6 hook collects once the QML module tree is
#: reachable, and that this application never loads. `excludes` cannot reach
#: them, because nothing in Python imports them: they arrive as collected data
#: and binaries and have to be filtered out of the collected tables directly.
#: QtWebEngine alone is roughly 214MB of Chromium.
UNUSED_QT_MODULES = (
    "QtWebEngine",
    "QtWebEngineCore",
    "QtWebEngineQuick",
    "QtWebEngineWidgets",
    "QtWebChannel",
    "QtWebView",
    "QtQuick3D",
    "QtCharts",
    "QtDataVisualization",
    "QtGraphs",
    "Qt3D",
    "QtSensors",
    "QtTest",
    "QtLocation",
    "QtScxml",
    "QtTextToSpeech",
    "QtRemoteObjects",
)

#: The QML module trees the interface imports. PySide6 ships them as data and
#: nothing in Python imports them, so PyInstaller cannot discover them from the
#: source alone.
QML_IMPORT_TREES = (
    "qml/QtCore",
    "qml/QtQml",
    "qml/QtQuick",
    "qml/QtMultimedia",
    "qml/Qt/labs",
)

#: An upper bound on the packaged application, in megabytes.
#:
#: Measured with the Qt Quick presentation layer and the module filter in
#: place: the macOS bundle is 281MB, up from 210MB, and the Windows
#: installation is 352MB. Windows is the binding platform, so one shared bound
#: is set from it.
#:
#: The number this guard exists to catch is the browser engine coming back,
#: which is worth roughly +220MB — the same unfiltered Windows build measured
#: 571MB. A bound of 400 leaves room for ordinary growth on both platforms
#: while still failing well before that returns.
MAXIMUM_PACKAGED_MEGABYTES = 400


def application_version() -> str:
    """The semantic version declared by the single project definition."""

    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_definition:
        return tomllib.load(project_definition)["project"]["version"]


def artifact_name(platform_suffix: str) -> str:
    """The published artifact name for a platform, without its file extension."""

    return f"{ARTIFACT_BASE_NAME}-{application_version()}-{platform_suffix}"


def bundled_data() -> list[tuple[str, str]]:
    """Resources every packaged application must carry."""

    fonts = PROJECT_ROOT / "assets" / "fonts"
    font_files = [
        "NotoSans.ttf",
        "OFL.txt",
        "Inter-Variable.ttf",
        "JetBrainsMono-Regular.ttf",
        "JetBrainsMono-Medium.ttf",
        "OFL-Inter.txt",
        "OFL-JetBrainsMono.txt",
    ]
    icons = PROJECT_ROOT / "assets" / "icons" / "lucide"
    return (
        [(str(fonts / name), "assets/fonts") for name in font_files]
        + [
            (str(icons), "assets/icons/lucide"),
            (str(PROJECT_ROOT / "qml"), "qml"),
        ]
        + copy_metadata("imageio")
        + qml_module_data()
    )


def qml_module_data() -> list[tuple[str, str]]:
    """The Qt Quick module trees the QML engine loads at run time."""

    def wanted(source: str) -> bool:
        path = source.replace("\\", "/")
        return any(
            f"/{tree}/" in path or path.endswith(f"/{tree}") for tree in QML_IMPORT_TREES
        )

    return [
        (source, destination)
        for source, destination in collect_data_files("PySide6", include_py_files=False)
        if wanted(source)
    ]


def carries_unused_qt_module(destination: str) -> bool:
    """Whether a collected file belongs to a Qt module this application never loads.

    Matched without regard to case, because Qt spells the same module both ways:
    `QtWebEngineCore.framework` sits beside `qtwebengine_locales` and
    `libqtwebview_webengine.dylib`, and all three are the same 214MB mistake.

    The major version is normalised away because the two platforms disagree:
    macOS ships `QtWebEngineCore.framework` while Windows ships
    `Qt6WebEngineCore.dll`. Matching the macOS spelling alone silently filtered
    nothing on Windows, and the installer shipped a browser engine.
    """

    path = destination.replace("\\", "/").lower().replace("qt6", "qt")
    return any(module.lower() in path for module in UNUSED_QT_MODULES)


def remove_unused_qt_modules(analysis: Any) -> int:
    """Drop the over-collected Qt modules from an analysis, and say how many.

    This is load-bearing packaging configuration rather than a nicety: it is the
    difference between a 447MB package and a 202MB one, and the standard
    `excludes` mechanism cannot express it.
    """

    before = len(analysis.datas) + len(analysis.binaries)
    analysis.datas = [
        entry for entry in analysis.datas if not carries_unused_qt_module(str(entry[0]))
    ]
    analysis.binaries = [
        entry
        for entry in analysis.binaries
        if not carries_unused_qt_module(str(entry[0]))
    ]
    return before - len(analysis.datas) - len(analysis.binaries)


def macos_disk_image_name() -> str:
    """The single authoritative filename of the macOS disk image."""

    return f"{ARTIFACT_BASE_NAME}-{application_version()}-{MACOS_ARCHITECTURE}.dmg"
