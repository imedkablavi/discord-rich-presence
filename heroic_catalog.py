"""Local Heroic/Legendary installed-game catalog.

Heroic uses Legendary metadata for Epic installs. ``installed.json`` includes the
installed title, path and executable, which is enough for foreground detection
without reading Heroic account/session files or calling a store API.
"""

from __future__ import annotations

import json
import os
import platform
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import psutil


_REFRESH_SECS = 60.0
_MAX_JSON_BYTES = 16 * 1024 * 1024
_GENERIC_EXE_STEMS = {
    'game', 'launcher', 'start', 'run', 'wine', 'wine64', 'wineserver',
    'explorer', 'services', 'cmd', 'powershell',
}


@dataclass(frozen=True)
class HeroicGame:
    app_name: str
    name: str
    install_path: Path
    executable: str

    @property
    def executable_stem(self) -> str:
        raw = self.executable.replace('\\', '/').rsplit('/', 1)[-1]
        return Path(raw).stem


class HeroicGameCatalog:
    """Resolve Heroic/Legendary installed games from local metadata."""

    def __init__(self) -> None:
        self._games: list[HeroicGame] = []
        self._by_exe: Dict[str, HeroicGame] = {}
        self._last_refresh = 0.0
        self.refresh(force=True)

    def refresh(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_refresh < _REFRESH_SECS:
            return
        self._last_refresh = now

        games: Dict[tuple[str, str], HeroicGame] = {}
        for installed_json in _installed_json_paths():
            for game in _read_installed(installed_json):
                key = (os.path.normcase(str(game.install_path)), game.app_name.lower())
                games[key] = game

        self._games = sorted(
            games.values(),
            key=lambda game: len(os.path.normcase(str(game.install_path))),
            reverse=True,
        )
        by_exe: Dict[str, HeroicGame] = {}
        for game in self._games:
            stem = _normalize_process_name(game.executable_stem)
            if len(stem) >= 4 and stem not in _GENERIC_EXE_STEMS:
                # Ambiguous executable stems are removed instead of guessing.
                if stem in by_exe and by_exe[stem] != game:
                    by_exe.pop(stem, None)
                else:
                    by_exe[stem] = game
        self._by_exe = by_exe

    def resolve(self, window_info: dict) -> Optional[HeroicGame]:
        self.refresh()
        app_name = _normalize_process_name(window_info.get('app_name'))
        if app_name:
            direct = self._by_exe.get(app_name)
            if direct:
                return direct

        pid = _clean_pid(window_info.get('pid'))
        if not pid:
            return None

        process_path = _process_path(pid)
        if process_path:
            game = self._from_path(process_path)
            if game:
                return game

        try:
            proc = psutil.Process(pid)
        except (psutil.Error, ValueError):
            return None
        for _ in range(8):
            try:
                cmdline = ' '.join(proc.cmdline())
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                cmdline = ''
            if cmdline:
                normalized_cmd = os.path.normcase(cmdline.replace('\\', '/'))
                for game in self._games:
                    install = os.path.normcase(str(game.install_path).replace('\\', '/'))
                    exe = game.executable.replace('\\', '/').lower()
                    if (install and install in normalized_cmd) or (exe and exe in normalized_cmd.lower()):
                        return game
            try:
                parent = proc.parent()
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                return None
            if parent is None or parent.pid == proc.pid:
                break
            proc = parent
        return None

    def _from_path(self, process_path: Path) -> Optional[HeroicGame]:
        process_norm = os.path.normcase(os.path.abspath(str(process_path)))
        for game in self._games:
            install_norm = os.path.normcase(os.path.abspath(str(game.install_path)))
            try:
                if os.path.commonpath((process_norm, install_norm)) == install_norm:
                    return game
            except (ValueError, OSError):
                continue
        return None


def _installed_json_paths() -> list[Path]:
    home = Path.home()
    paths = [
        home / '.config/legendary/installed.json',
        home / '.config/heroic/legendaryConfig/legendary/installed.json',
        home / '.var/app/com.heroicgameslauncher.hgl/config/legendary/installed.json',
        home / '.var/app/com.heroicgameslauncher.hgl/config/heroic/legendaryConfig/legendary/installed.json',
    ]
    if platform.system().lower() == 'windows':
        appdata = os.environ.get('APPDATA')
        if appdata:
            paths.extend((
                Path(appdata) / 'heroic/legendaryConfig/legendary/installed.json',
                Path(appdata) / 'legendary/installed.json',
            ))

    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = os.path.normcase(str(path))
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _read_installed(path: Path) -> list[HeroicGame]:
    try:
        if not path.is_file() or path.stat().st_size > _MAX_JSON_BYTES:
            return []
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []

    games: list[HeroicGame] = []
    for key, value in data.items():
        if not isinstance(value, dict) or bool(value.get('is_dlc', False)):
            continue
        title = str(value.get('title') or '').strip()
        install = str(value.get('install_path') or '').strip()
        executable = str(value.get('executable') or '').strip()
        app_name = str(value.get('app_name') or key or '').strip()
        if not title or not install:
            continue
        install_path = Path(install).expanduser()
        if not install_path.is_dir():
            continue
        games.append(HeroicGame(
            app_name=app_name[:160],
            name=title[:160],
            install_path=install_path,
            executable=executable[:512],
        ))
    return games


def _normalize_process_name(value: object) -> str:
    text = str(value or '').strip().lower()
    text = text.replace('\\', '/').rsplit('/', 1)[-1]
    if text.endswith('.exe'):
        text = text[:-4]
    return re.sub(r'[^a-z0-9_.+-]+', '', text)


def _clean_pid(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    try:
        pid = int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return None
    return pid if pid > 0 else None


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
