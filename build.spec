# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for AI Quota Monitor
# Build with: pyinstaller build.spec

import sys

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'requests',
        'services.github_copilot',
        'services.github_copilot_web',
        'services.claude_api',
        'services.claude_web',
        'services.openai_api',
        'services.google_gemini',
        'services.local_server',
        'services.browser_data',
        'config.manager',
        'gui.app',
        'gui.widgets',
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
    name='AI額度監控',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # No console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows icon (uncomment and provide icon.ico if available)
    # icon='icon.ico',
)

# macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='AI額度監控.app',
        icon=None,  # Replace with 'icon.icns' if available
        bundle_identifier='com.aimonitor.quotachecker',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
        },
    )
