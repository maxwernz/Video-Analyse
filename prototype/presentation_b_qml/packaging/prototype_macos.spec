# -*- mode: python ; coding: utf-8 -*-
"""Package the QML prototype the way the application is packaged.

This deliberately reuses `build_config/shared.py` so that what it proves is
about the real pipeline and not about a spec written to succeed. What it has to
change to work at all is the finding: see FINDINGS.md.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parents[2]
PROTOTYPE = PROJECT_ROOT / "prototype" / "presentation_b_qml"
sys.path.insert(0, str(PROJECT_ROOT / "build_config"))

from PyInstaller.utils.hooks import collect_data_files  # noqa: E402

from shared import (  # noqa: E402
    BUNDLE_IDENTIFIER,
    EXCLUDED_MODULES,
    MACOS_ARCHITECTURE,
    application_version,
)

APPLICATION_NAME = "Video Analyse QML Prototype"

# The shipped pipeline excludes every module a Qt Quick presentation layer is
# made of. Prototype B cannot be packaged without giving these back.
QML_MODULES = {
    "QtQml",
    "QtQmlMeta",
    "QtQmlModels",
    "QtQmlWorkerScript",
    "QtQuick",
    "QtSvg",
    "QtOpenGL",
}
excludes = [name for name in EXCLUDED_MODULES if name not in QML_MODULES]

# Handing QtQml back to PyInstaller lets it discover every QML module PySide6
# ships, and one of them is QtWebEngine, which drags in a 214MB Chromium. None
# of it is reachable from this application. Naming the unwanted ones is the
# price of a Qt Quick presentation layer that packages at a sane size.
excludes += [
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
    "PySide6.QtQuick3D",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.Qt3DCore",
]

#: The QML module trees this interface actually imports.
QML_IMPORT_TREES = (
    "qml/QtQml",
    "qml/QtQuick",
    "qml/QtMultimedia",
    "qml/QtCore",
    "qml/Qt/labs",
)

hidden_imports = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtMultimedia",
    "PySide6.QtSvg",
]

datas = [
    (str(PROTOTYPE / "qml"), "qml"),
    (str(PROTOTYPE / "fonts"), "fonts"),
]
# The Qt Quick module tree: PySide6 ships it as data, and nothing imports it,
# so PyInstaller has no way to discover it from the Python code.
datas += [
    (source, destination)
    for source, destination in collect_data_files("PySide6", include_py_files=False)
    if any(
        f"/{tree}/" in source.replace("\\", "/") or source.replace("\\", "/").endswith(f"/{tree}")
        for tree in QML_IMPORT_TREES
    )
]

analysis = Analysis(
    [str(PROTOTYPE / "run.py")],
    pathex=[str(PROJECT_ROOT), str(PROTOTYPE)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=True,
)

# PyInstaller's own PySide6 hook collects the *entire* Qt QML module tree as
# soon as QtQml is importable, and `excludes` cannot reach it because nothing
# in Python imports it. WebEngine alone is a 214MB Chromium this application
# will never load, so the collected tables are filtered directly. This is the
# concrete packaging cost of a Qt Quick presentation layer: not that it cannot
# be packaged, but that the package has to be told what to leave out.
UNWANTED = (
    "QtWebEngine",
    "QtWebChannel",
    "QtQuick3D",
    "QtCharts",
    "QtDataVisualization",
    "QtGraphs",
    "Qt3D",
    "QtSensors",
    "QtTest",
)


def _wanted(entry):
    destination = str(entry[0]).replace("\\", "/")
    return not any(name in destination for name in UNWANTED)


removed_datas = [entry for entry in analysis.datas if not _wanted(entry)]
removed_binaries = [entry for entry in analysis.binaries if not _wanted(entry)]
analysis.datas = [entry for entry in analysis.datas if _wanted(entry)]
analysis.binaries = [entry for entry in analysis.binaries if _wanted(entry)]
print(
    f"[prototype spec] dropped {len(removed_datas)} data and "
    f"{len(removed_binaries)} binary entries the interface never loads"
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=APPLICATION_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=MACOS_ARCHITECTURE,
    codesign_identity=None,
    entitlements_file=None,
)
collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APPLICATION_NAME,
)
application = BUNDLE(
    collection,
    name=f"{APPLICATION_NAME}.app",
    bundle_identifier=f"{BUNDLE_IDENTIFIER}.prototype.qml",
    version=application_version(),
    info_plist={
        "CFBundleName": APPLICATION_NAME,
        "LSMinimumSystemVersion": "14.0",
        "NSHighResolutionCapable": True,
    },
)
