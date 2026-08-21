"""Local Steam game catalog and foreground-process resolver.

The resolver is intentionally offline-first: installed game names/AppIDs come
from Steam's local ``appmanifest_*.acf`` files. No Steam Web API key, account
login, profile scraping, or network lookup is required.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

import psutil


LOGGER = logging.getLogger(__name__)
_REFRESH_SECS = 60.0
_STEAM_APP_CLASS_RE = re.compile(r'(?i)(?:^|[^a-z0-9])steam_app_(\d+)(?:$|[^0-9])')
_STEAM_LAUNCH_RE = re.compile(r'(?i)SteamLaunch\s+AppId=(\d+)(?:\s|$)')
_MANIFEST_FIELDS = {
    'appid': re.compile(r'(?im)^\s*"appid"\s+"(\d+)"'),
    'name': re.compile(r'(?im)^\s*"name"\s+"([^"]+)"'),
    'installdir': re.compile(r'(?im)^\s*"installdir"\s+"([^"]+)"'),
}

# Steam installs tools/runtimes through the same appmanifest mechanism. They
# should never become a game presence merely because a helper process is active.
_NON_GAME_NAME_MARKERS = (
    'steamworks common redistributables',
    'steam linux runtime',
    'proton ',
    'proton experimental',
    'steamvr',
)


@dataclass(frozen=True)
class SteamGame:
    appid: int
    name: str
    install_path: Path
    steam_root: Path

    @property
    def artwork_url(self) -> str:
        # Valve/Steam-hosted public store artwork. External Discord Rich
        # Presence assets can use HTTPS URLs; no API key is required.
        return (
            'https://shared.cloudflare.steamstatic.com/store_item_assets/'
            f'steam/apps/{self.appid}/header.jpg'
        )


class SteamGameCatalog:
    """Resolve a foreground Steam game from AppID, PID ancestry, or exe path."""

    def __init__(self) -> None:
        self._by_appid: Dict[int, SteamGame] = {}
        self._games: list[SteamGame] = []
        self._last_refresh = 0.0
        self.refresh(force=True)

    def refresh(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_refresh < _REFRESH_SECS:
            return
        self._last_refresh = now

        games: Dict[int, SteamGame] = {}
        for steam_root, steamapps in _steamapps_locations():
            try:
                manifests = list(steamapps.glob('appmanifest_*.acf'))
            except OSError:
                continue
            for manifest in manifests:
                game = _parse_manifest(manifest, steam_root, steamapps)
                if game is not None:
                    games[game.appid] = game

        self._by_appid = games
        # Longest paths first so nested/shared directories cannot steal a match.
        self._games = sorted(
            games.values(),
            key=lambda game: len(os.path.normcase(str(game.install_path))),
            reverse=True,
        )
        LOGGER.debug('Steam catalog loaded %d installed game manifests', len(games))

    def by_appid(self, appid: object) -> Optional[SteamGame]:
        self.refresh()
        try:
            key = int(appid)
        except (TypeError, ValueError, OverflowError):
            return None
        return self._by_appid.get(key)

    def resolve(self, window_info: dict) -> Optional[SteamGame]:
        """Return the installed Steam game represented by the foreground window."""
        self.refresh()
        app_name = str(window_info.get('app_name', '') or '')

        match = _STEAM_APP_CLASS_RE.search(app_name)
        if match:
            game = self.by_appid(match.group(1))
            if game:
                return game

        pid = _clean_pid(window_info.get('pid'))
        if pid:
            appid = self._appid_from_process_tree(pid)
            if appid:
                game = self.by_appid(appid)
                if game:
                    return game

            process_path = self._process_path(pid)
            if process_path:
                game = self._game_from_path(process_path)
                if game:
                    return game

        return None

    def _appid_from_process_tree(self, pid: int) -> Optional[int]:
        """Find Steam's AppID marker in the foreground process ancestry.

        Steam for Linux keeps a per-game reaper whose command line contains
        ``SteamLaunch AppId=<id>``. Walking only the foreground process ancestry
        avoids global process scanning and works for many native/Proton games.
        """
        try:
            proc = psutil.Process(pid)
        except (psutil.Error, ValueError):
            return None

        for _ in range(8):
            try:
                cmdline = ' '.join(proc.cmdline())
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                cmdline = ''
            match = _STEAM_LAUNCH_RE.search(cmdline)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
            try:
                parent = proc.parent()
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                return None
            if parent is None or parent.pid == proc.pid:
                return None
            proc = parent
        return None

    @staticmethod
    def _process_path(pid: int) -> Optional[Path]:
        try:
            raw = psutil.Process(pid).exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            return None
        if not raw:
            return None
        try:
            return Path(raw).resolve(strict=False)
        except (OSError, RuntimeError):
            return Path(raw)

    def _game_from_path(self, process_path: Path) -> Optional[SteamGame]:
        process_norm = os.path.normcase(os.path.abspath(str(process_path)))
        for game in self._games:
            install_norm = os.path.normcase(os.path.abspath(str(game.install_path)))
            try:
                if os.path.commonpath((process_norm, install_norm)) == install_norm:
                    return game
            except (ValueError, OSError):
                continue
        return None


def _clean_pid(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    try:
        pid = int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return None
    return pid if pid > 0 else None


def _windows_registry_steam_roots() -> Iterable[Path]:
    if platform.system().lower() != 'windows':
        return []
    try:
        import winreg
    except ImportError:
        return []

    roots: list[Path] = []
    locations = (
        (winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam'),
    )
    for hive, key_name in locations:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                for value_name in ('SteamPath', 'InstallPath'):
                    try:
                        raw, _ = winreg.QueryValueEx(key, value_name)
                    except OSError:
                        continue
                    if raw:
                        roots.append(Path(str(raw)))
                        break
        except OSError:
            continue
    return roots


def _steam_roots() -> Iterable[Path]:
    system = platform.system().lower()
    roots: list[Path] = []
    steam_env = os.environ.get('STEAM_PATH')
    if steam_env:
        roots.append(Path(steam_env))

    if system == 'windows':
        roots.extend(_windows_registry_steam_roots())
        for env_name in ('PROGRAMFILES(X86)', 'PROGRAMFILES'):
            base = os.environ.get(env_name)
            if base:
                roots.append(Path(base) / 'Steam')
    else:
        home = Path.home()
        roots.extend((
            home / '.local/share/Steam',
            home / '.steam/steam',
            home / '.var/app/com.valvesoftware.Steam/.local/share/Steam',
        ))

    seen: set[str] = set()
    for root in roots:
        try:
            expanded = root.expanduser()
        except (TypeError, ValueError):
            continue
        key = os.path.normcase(str(expanded))
        if key in seen:
            continue
        seen.add(key)
        yield expanded


def _steamapps_locations() -> Iterable[tuple[Path, Path]]:
    seen: set[str] = set()
    for steam_root in _steam_roots():
        libraries = [steam_root]
        library_file = steam_root / 'steamapps/libraryfolders.vdf'
        try:
            text = library_file.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            text = ''
        for match in re.finditer(r'"path"\s+"([^"]+)"', text, re.IGNORECASE):
            libraries.append(Path(match.group(1).replace('\\\\', '\\')))

        for library in libraries:
            steamapps = library / 'steamapps'
            key = os.path.normcase(os.path.abspath(str(steamapps)))
            if key in seen or not steamapps.is_dir():
                continue
            seen.add(key)
            # The root hosting appcache/artwork remains the primary Steam root;
            # a secondary library only changes the manifest/install location.
            yield steam_root, steamapps


def _parse_manifest(manifest: Path, steam_root: Path, steamapps: Path) -> Optional[SteamGame]:
    try:
        if manifest.stat().st_size > 2 * 1024 * 1024:
            return None
        text = manifest.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return None

    values: Dict[str, str] = {}
    for key, pattern in _MANIFEST_FIELDS.items():
        match = pattern.search(text)
        if not match:
            return None
        values[key] = match.group(1).strip()

    try:
        appid = int(values['appid'])
    except ValueError:
        return None
    name = values['name'].strip()
    installdir = values['installdir'].strip()
    if appid <= 0 or not name or not installdir:
        return None
    lowered = name.lower()
    if any(marker in lowered for marker in _NON_GAME_NAME_MARKERS):
        return None

    install_path = steamapps / 'common' / installdir
    return SteamGame(
        appid=appid,
        name=name[:160],
        install_path=install_path,
        steam_root=steam_root,
    )
