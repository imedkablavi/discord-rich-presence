# -*- mode: python ; coding: utf-8 -*-

import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('customtkinter')
hiddenimports += collect_submodules('pystray')
hiddenimports += collect_submodules('PIL')
if sys.platform == 'win32':
    hiddenimports += collect_submodules('winsdk')

datas = []
datas += collect_data_files('customtkinter')
datas += [('game_packs/community.json', 'game_packs')]

analysis = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name='DiscordRichPresence',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # Avoid optional UPX compression for release binaries. It saves little for
    # this desktop app and can increase antivirus/SmartScreen false positives.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)