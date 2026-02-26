# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for AI Quota Monitor Desktop Widget
# Build with: pyinstaller widget_build.spec

block_cipher = None

a = Analysis(
    ['widget_main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'requests',
        'pystray',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'services.local_server',
        'services.browser_data',
        'services.base',
        'config.manager',
        'gui.widgets',
        'desktop_widget.app',
        'desktop_widget.clock',
        'desktop_widget.cards',
        'desktop_widget.tray',
        'desktop_widget.styles',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI額度監控-桌面小工具',
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
    # icon='icon.ico',
)
