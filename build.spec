# -*- mode: python ; coding: utf-8 -*-

exclude_modules = ['QtDBus', 'QtNetwork', 'QtOpenGL', 'QtPdf', 'QtQml', 'QtQmlMeta', 'QtQmlModels', 'QtQmlWorkerScript', 'QtQuick', 'QtSvg', 'QtVirtualKeyboard', 'PySide6.QtDBus', 'PySide6.QtNetwork']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['moviepy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=exclude_modules,
    noarchive=True,
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
    onedir=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons/app_icon.icns']
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
