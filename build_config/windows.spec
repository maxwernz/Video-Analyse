# -*- mode: python ; coding: utf-8 -*-
"""Windows-specific packaging details for the x64 Video Analyse application."""

import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(SPECPATH))

from build_config.shared import (  # noqa: E402
    APPLICATION_NAME,
    ENTRY_SCRIPT,
    EXCLUDED_MODULES,
    HIDDEN_IMPORTS,
    PROJECT_ROOT,
    bundled_data,
)
from build_config.windows_version_resource import write_version_resource  # noqa: E402

icon = str(PROJECT_ROOT / "icons" / "app_icon.ico")
version_resource = str(write_version_resource(Path(workpath)))

analysis = Analysis(
    [ENTRY_SCRIPT],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=bundled_data(),
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDED_MODULES,
    noarchive=True,
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
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[icon],
    version=version_resource,
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
