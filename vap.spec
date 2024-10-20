# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
#    datas=[
#       ('icons/*', 'icons'),
#        ('icons/forward.svg', 'icons')
#        ],
    datas=[],
    hiddenimports=['moviepy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
#    excludes=['PySide6.QtMultimedia', 'PySide6.QtSensors', 'PySide6.QtPrintSupport'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Video Analyse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons/app_icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Video Analyse',
)
app = BUNDLE(
    coll,
    name='Video Analyse.app',
    icon='icons/app_icon.icns',
    bundle_identifier=None,
)
