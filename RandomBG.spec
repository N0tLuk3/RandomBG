# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\RandomBG\\random_bg\\app.py'],
    pathex=['C:\\RandomBG'],
    binaries=[],
    datas=[('C:\\RandomBG\\logo.png', '.'), ('C:\\RandomBG\\firefox_extension', 'firefox_extension')],
    hiddenimports=['pystray._win32', 'pystray._gtk', 'pystray._xorg', 'PIL._tkinter_finder', 'random_bg', 'random_bg.app', 'random_bg.autostart', 'random_bg.runtime', 'random_bg.wallpaper'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RandomBG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\RandomBG\\build\\logo.ico'],
)
