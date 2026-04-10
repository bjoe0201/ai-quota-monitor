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
    [],
    exclude_binaries=True,  # onedir mode: binaries go to COLLECT
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
    # icon='icon.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI額度監控-桌面小工具',
)

# macOS app bundle
import sys
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='AI額度監控.app',
        icon=None,
        bundle_identifier='com.aimonitor.widget',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.8.2',
            'LSUIElement': False,
        },
    )
