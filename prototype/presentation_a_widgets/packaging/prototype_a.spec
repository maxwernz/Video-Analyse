# -*- mode: python ; coding: utf-8 -*-
"""THROWAWAY PROTOTYPE A -- packaging probe.

Packages the prototype through the project's real PyInstaller configuration so
the packaging criterion is answered by a build that either works or fails,
rather than by an estimate.

Set PROTOTYPE_A_ALLOW_QTSVG=1 to drop QtSvg from the project's exclusion list.
Running it both ways is the experiment: the prototype's icon family needs
QtSvg, and ``build_config/shared.py`` currently excludes it.
"""

import os
import sys

SPEC_DIRECTORY = os.path.abspath(SPECPATH)
PROJECT_ROOT = os.path.abspath(os.path.join(SPEC_DIRECTORY, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "build_config"))

from shared import EXCLUDED_MODULES, HIDDEN_IMPORTS, bundled_data  # noqa: E402

allow_qtsvg = os.environ.get("PROTOTYPE_A_ALLOW_QTSVG") == "1"

excluded = list(EXCLUDED_MODULES)
hidden = list(HIDDEN_IMPORTS)
if os.environ.get("PROTOTYPE_A_STRICT_EXCLUDE") == "1":
    # Does the exclusion actually bite when spelled the way PyInstaller
    # matches PySide6 submodules?
    excluded.append("PySide6.QtSvg")
if allow_qtsvg:
    excluded = [module for module in excluded if module != "QtSvg"]
    hidden.append("PySide6.QtSvg")

entry = os.path.join(
    PROJECT_ROOT, "prototype", "presentation_a_widgets", "run.py"
)

analysis = Analysis(
    [entry],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=bundled_data(),
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded,
    noarchive=True,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="PrototypeA",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)
collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="PrototypeA",
)
