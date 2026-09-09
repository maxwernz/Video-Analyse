# -*- mode: python ; coding: utf-8 -*-
"""macOS-specific packaging details for the ARM64 Video Analyse application."""

import sys

sys.path.insert(0, SPECPATH)

from shared import (  # noqa: E402
    APPLICATION_NAME,
    BUNDLE_IDENTIFIER,
    ENTRY_SCRIPT,
    EXCLUDED_MODULES,
    HIDDEN_IMPORTS,
    MACOS_ARCHITECTURE,
    PROJECT_ROOT,
    application_version,
    bundled_data,
)

MINIMUM_SYSTEM_VERSION = "14.0"

version = application_version()
icon = str(PROJECT_ROOT / "icons" / "app_icon.icns")

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
    target_arch=MACOS_ARCHITECTURE,
    # No Developer ID identity: PyInstaller ad-hoc signs the arm64 binaries,
    # which macOS requires before it will load them.
    codesign_identity=None,
    entitlements_file=None,
    icon=[icon],
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
    icon=icon,
    bundle_identifier=BUNDLE_IDENTIFIER,
    version=version,
    info_plist={
        "CFBundleName": APPLICATION_NAME,
        "CFBundleDisplayName": APPLICATION_NAME,
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "LSMinimumSystemVersion": MINIMUM_SYSTEM_VERSION,
        "NSHighResolutionCapable": True,
    },
)
