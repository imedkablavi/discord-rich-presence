# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('customtkinter')
hiddenimports += collect_submodules('pystray')
hiddenimports += collect_submodules('PIL')
if sys.platform == 'win32':
    hiddenimports += collect_submodules('winsdk')

datas = []
datas += collect_data_files('customtkinter')
datas += [
    ('game_packs/community.json', 'game_packs'),
    ('game_packs/popular_catalog.json', 'game_packs'),
    ('game_packs/popular_cross_launcher.json', 'game_packs'),
    ('game_packs/popular_2026.json', 'game_packs'),
]

# Official release builds can provide a staged Social SDK bundle without
# checking Discord's proprietary SDK archive into this source repository.
# PyInstaller embeds the helper/runtime in the one-file executable and extracts
# them together under sys._MEIPASS, preserving the existing single-file updater.
binaries = []
social_bundle_raw = os.environ.get('CYBREX_SOCIAL_SDK_BUNDLE_DIR', '').strip()
if social_bundle_raw:
    social_bundle = Path(social_bundle_raw).expanduser().resolve()
    if sys.platform == 'win32':
        helper_name = 'cybrex-discord-social-sdk.exe'
        runtime_name = 'discord_partner_sdk.dll'
    elif sys.platform == 'darwin':
        helper_name = 'cybrex-discord-social-sdk'
        runtime_name = 'libdiscord_partner_sdk.dylib'
    else:
        helper_name = 'cybrex-discord-social-sdk'
        runtime_name = 'libdiscord_partner_sdk.so'

    required = [social_bundle / helper_name, social_bundle / runtime_name]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(
            'CYBREX_SOCIAL_SDK_BUNDLE_DIR is incomplete; missing: ' + ', '.join(missing)
        )
    binaries += [(str(path), '.') for path in required]

    for optional_name in ('Discord-Social-SDK-Notices.txt', 'SOCIAL_SDK_MANIFEST.json'):
        optional = social_bundle / optional_name
        if optional.is_file():
            datas.append((str(optional), '.'))

analysis = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=binaries,
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
