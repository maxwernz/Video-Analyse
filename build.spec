# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['moviepy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtCharts', 
            'PySide6.QtDataVisualization', 
            'PySide6.QtWebEngineWidgets', 
            'PySide6.QtWebEngineCore', 
            'PySide6.QtWebChannel', 
            'PySide6.QtQml', 
            'PySide6.QtQuick', 
            'PySide6.QtQuickControls2', 
            'PySide6.QtQuickTemplates2', 
            'PySide6.QtSvg', 
            'PySide6.QtTest'],
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
