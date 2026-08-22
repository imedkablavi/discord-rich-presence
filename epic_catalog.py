"""Local Epic Games Launcher installed-game catalog for Windows.

Epic's launcher keeps JSON ``.item`` manifests under ProgramData. The catalog
reads only local installation metadata and resolves a foreground process by its
executable path. No Epic account, OAuth token, or web API is used.
"""

from __future__ import annotations

import json
import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import psutil


_REFRESH_SECS = 60.0
_MAX_MANIFEST_BYTES = 2 * 1024 * 1024
_MAX_MANIFESTS = 4096
_NON_GAME_MARKERS = (
    'unreal engine',
    'epic games launcher',
    'epic online services',
    'twinmotion',
)


@dataclass(frozen=True)
class EpicGame:
    app_name: str
    name: str
    install_path: Path


class EpicGameCatalog:
    """Resolve native Epic Launcher games from local ``.item`` manifests."""

    def __init__(self) -> None:
        self._games: list[EpicGame] = []
        self._last_refresh = 0.0
        self.refresh(force=True)

    def refresh(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_refresh < _REFRESH_SECS:
            return
        self._last_refresh = now

        games: Dict[str, EpicGame] = {}
        count = 0
        for directory in _manifest_dirs():
            try:
                iterator = directory.glob('*.item')
            except OSError:
                continue
            try:
                for manifest in iterator:
                    if count >= _MAX_MANIFESTS:
                        break
                    count += 1
                    game = _parse_manifest(manifest)
                    if game is not None:
                        games[os.path.normcase(str(game.install_path))] = game
            except OSError:
                continue
            if count >= _MAX_MANIFESTS:
                break

        self._games = sorted(
            games.values(),
            key=lambda game: len(os.path.normcase(str(game.install_path))),
            reverse=True,
        )

    def resolve(self, window_info: dict) -> Optional[EpicGame]:
        self.refresh()
        pid = _clean_pid(window_info.get('pid'))
        if not pid:
            return None

        process_path = _process_path(pid)
        if process_path:
            game = self._from_path(process_path)
            if game:
                return game

        # Some launch chains leave the foreground game under a child/parent
        # process whose executable is outside the install root. Inspect only a
        # short foreground ancestry and match explicit install paths in cmdline.
        try:
            proc = psutil.Process(pid)
        except (psutil.Error, ValueError):
            return None
        for _ in range(6):
            try:
                cmdline = ' '.join(proc.cmdline())
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                cmdline = ''
            if cmdline:
                lowered = os.path.normcase(cmdline)
                for game in self._games:
                    install = os.path.normcase(str(game.install_path))
                    if install and install in lowered:
                        return game
            try:
                parent = proc.parent()
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                return None
            if parent is None or parent.pid == proc.pid:
                break
            proc = parent
        return None

    def _from_path(self, process_path: Path) -> Optional[EpicGame]:
        process_norm = os.path.normcase(os.path.abspath(str(process_path)))
        for game in self._games:
            install_norm = os.path.normcase(os.path.abspath(str(game.install_path)))
            try:
                if os.path.commonpath((process_norm, install_norm)) == install_norm:
                    return game
            except (ValueError, OSError):
                continue
        return None


def _manifest_dirs() -> list[Path]:
    if platform.system().lower() != 'windows':
        return []
    program_data = os.environ.get('PROGRAMDATA') or r'C:\ProgramData'
    return [Path(program_data) / 'Epic/EpicGamesLauncher/Data/Manifests']


def _specific_install_path(value: str) -> Optional[Path]:
    try:
        path = Path(value).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None
    if not path.is_dir():
        return None
    try:
        anchor = Path(path.anchor).resolve(strict=False) if path.anchor else None
    except (OSError, RuntimeError, ValueError):
        anchor = None
    if anchor is not None and path == anchor:
        return None
    return path


def _parse_manifest(path: Path) -> Optional[EpicGame]:
    try:
        if not path.is_file() or path.stat().st_size > _MAX_MANIFEST_BYTES:
            return None
        data = json.loads(path.read_text(encoding='utf-8', errors='strict'))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    name = str(data.get('DisplayName') or '').strip()
    install = str(data.get('InstallLocation') or '').strip()
    app_name = str(data.get('AppName') or data.get('MainGameAppName') or '').strip()
    if not name or not install:
        return None
    lowered = name.lower()
    if any(marker in lowered for marker in _NON_GAME_MARKERS):
        return None

    install_path = _specific_install_path(install)
    if install_path is None:
        return None
    return EpicGame(app_name=app_name[:160], name=name[:160], install_path=install_path)


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
