"""Validated data-driven fallback game detection packs."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


_LOGGER = logging.getLogger(__name__)
_MAX_PACK_BYTES = 256 * 1024
_MAX_GAMES = 512
_MAX_PROCESSES_PER_GAME = 24
_MAX_TEXT = 160


@dataclass(frozen=True)
class PackedGame:
    name: str
    launcher: str
    processes: tuple[str, ...]
    steam_appid: Optional[int] = None

    @property
    def artwork_url(self) -> str:
        if not self.steam_appid:
            return ''
        return (
            'https://shared.cloudflare.steamstatic.com/store_item_assets/'
            f'steam/apps/{self.steam_appid}/header.jpg'
        )

    @property
    def store_url(self) -> str:
        if not self.steam_appid:
            return ''
        return f'https://store.steampowered.com/app/{self.steam_appid}/'


def _resource_root() -> Path:
    frozen_root = getattr(sys, '_MEIPASS', None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parent


def _normalize_process(value: object) -> str:
    text = str(value or '').strip().lower()
    if text.endswith('.exe'):
        text = text[:-4]
    if not text or len(text) > 120:
        return ''
    allowed = set('abcdefghijklmnopqrstuvwxyz0123456789._-')
    if any(char not in allowed for char in text):
        return ''
    return text


def _clean_text(value: object, default: str = '') -> str:
    text = str(value or '').replace('\x00', '').replace('\r', ' ').replace('\n', ' ').strip()
    return ' '.join(text.split())[:_MAX_TEXT] or default


def _parse_game(item: object) -> Optional[PackedGame]:
    if not isinstance(item, dict):
        return None
    name = _clean_text(item.get('name'))
    launcher = _clean_text(item.get('launcher'), 'Gaming')
    raw_processes = item.get('processes')
    if not name or not isinstance(raw_processes, list):
        return None

    processes: list[str] = []
    for raw in raw_processes[:_MAX_PROCESSES_PER_GAME]:
        process = _normalize_process(raw)
        if process and process not in processes:
            processes.append(process)
    if not processes:
        return None

    appid: Optional[int] = None
    raw_appid = item.get('steam_appid')
    if raw_appid is not None:
        if isinstance(raw_appid, bool):
            return None
        try:
            parsed = int(raw_appid)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed <= 0 or parsed > 2_147_483_647:
            return None
        appid = parsed

    return PackedGame(name=name, launcher=launcher, processes=tuple(processes), steam_appid=appid)


def load_pack(path: Path) -> tuple[PackedGame, ...]:
    """Load one pack with strict size/schema/count validation."""
    try:
        if path.stat().st_size > _MAX_PACK_BYTES:
            raise ValueError('game pack is too large')
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f'could not read game pack: {exc}') from exc
    if len(raw) > _MAX_PACK_BYTES:
        raise ValueError('game pack is too large')
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('game pack contains invalid JSON') from exc
    if not isinstance(payload, dict) or payload.get('schema') != 1:
        raise ValueError('unsupported game pack schema')
    games = payload.get('games')
    if not isinstance(games, list) or len(games) > _MAX_GAMES:
        raise ValueError('game pack has an invalid game list')

    result: list[PackedGame] = []
    seen_processes: set[str] = set()
    for item in games:
        game = _parse_game(item)
        if game is None:
            continue
        # Ambiguous aliases fail closed: first valid definition wins and later
        # collisions lose only the colliding process, never overwrite a title.
        unique = tuple(process for process in game.processes if process not in seen_processes)
        if not unique:
            continue
        seen_processes.update(unique)
        result.append(PackedGame(game.name, game.launcher, unique, game.steam_appid))
    return tuple(result)


class GamePackRegistry:
    """Small exact-process fallback registry loaded once per service process."""

    def __init__(self, paths: Optional[list[Path]] = None):
        if paths is None:
            paths = [_resource_root() / 'game_packs' / 'community.json']
        games: list[PackedGame] = []
        for path in paths:
            try:
                games.extend(load_pack(path))
            except ValueError as exc:
                _LOGGER.warning('Ignoring invalid game pack %s: %s', path, exc)
        self.games = tuple(games[:_MAX_GAMES])
        self._by_process: dict[str, PackedGame] = {}
        for game in self.games:
            for process in game.processes:
                self._by_process.setdefault(process, game)

    def match(self, process_name: object) -> Optional[PackedGame]:
        process = _normalize_process(process_name)
        if not process:
            return None
        return self._by_process.get(process)

    def activity(self, process_name: object) -> Optional[dict[str, Any]]:
        game = self.match(process_name)
        if game is None:
            return None
        activity: dict[str, Any] = {
            'type': 'gaming',
            'game_name': game.name,
            'launcher': game.launcher,
            'game_source': game.launcher,
            'is_game': True,
        }
        if game.steam_appid:
            activity.update({
                'steam_appid': game.steam_appid,
                'game_source': 'Steam',
                'artwork_url': game.artwork_url,
                'store_url': game.store_url,
            })
        return activity
