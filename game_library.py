"""Local installed-game library and gamer-mode controls.

The library is deliberately offline-first. It reuses the same Steam, Epic and
Heroic metadata readers as foreground detection and never requires a store
account, API token or cloud inventory lookup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from config import Config, DEFAULT_CONFIG
from epic_catalog import EpicGameCatalog
from heroic_catalog import HeroicGameCatalog
from popular_games import PopularGameCatalog
from steam_catalog import SteamGameCatalog


_MAX_LIBRARY_ITEMS = 8192
_DETECTOR_NAMES = ('media', 'terminal', 'coding', 'browser', 'gaming', 'application')
_ENHANCED_GAMES = {
    'counter-strike 2',
    'counter-strike: global offensive',
    'league of legends',
}


@dataclass(frozen=True)
class GameLibraryEntry:
    key: str
    name: str
    source: str
    enhanced: bool = False
    app_id: str = ''
    curated: bool = False


def _slug(value: object) -> str:
    text = str(value or '').strip().lower()
    text = re.sub(r'[^a-z0-9._-]+', '-', text).strip('-')
    return text[:160] or 'unknown'


def _catalog_snapshot(catalog: object) -> Sequence[object]:
    """Return a defensive snapshot without exposing mutable catalog storage."""
    refresh = getattr(catalog, 'refresh', None)
    if callable(refresh):
        try:
            refresh(force=True)
        except (OSError, ValueError, TypeError):
            pass
    raw = getattr(catalog, '_games', ())
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(raw[:_MAX_LIBRARY_ITEMS])


def _is_enhanced(name: object) -> bool:
    return str(name or '').strip().lower() in _ENHANCED_GAMES


def discover_games() -> list[GameLibraryEntry]:
    """Discover installed games from local launcher metadata.

    No install paths are returned to the UI. Paths are useful internally for
    foreground matching but are unnecessarily sensitive for a library view.

    The bundled PopularGameCatalog marks well-known compatibility targets for
    QA/documentation only. It never replaces authoritative launcher metadata.
    """
    entries: list[GameLibraryEntry] = []
    popular = PopularGameCatalog()

    steam = SteamGameCatalog()
    for game in _catalog_snapshot(steam):
        name = str(getattr(game, 'name', '') or '').strip()
        appid = str(getattr(game, 'appid', '') or '').strip()
        if not name or not appid.isdigit():
            continue
        entries.append(GameLibraryEntry(
            key=f'steam:{appid}',
            name=name[:160],
            source='Steam',
            app_id=appid,
            enhanced=_is_enhanced(name) or appid == '730',
            curated=popular.contains(name),
        ))

    epic = EpicGameCatalog()
    for game in _catalog_snapshot(epic):
        name = str(getattr(game, 'name', '') or '').strip()
        app_name = str(getattr(game, 'app_name', '') or '').strip()
        if not name:
            continue
        identity = _slug(app_name or name)
        entries.append(GameLibraryEntry(
            key=f'epic:{identity}',
            name=name[:160],
            source='Epic Games',
            app_id=app_name[:160],
            enhanced=_is_enhanced(name),
            curated=popular.contains(name),
        ))

    heroic = HeroicGameCatalog()
    for game in _catalog_snapshot(heroic):
        name = str(getattr(game, 'name', '') or '').strip()
        app_name = str(getattr(game, 'app_name', '') or '').strip()
        if not name:
            continue
        identity = _slug(app_name or name)
        entries.append(GameLibraryEntry(
            key=f'heroic:{identity}',
            name=name[:160],
            source='Heroic',
            app_id=app_name[:160],
            enhanced=_is_enhanced(name),
            curated=popular.contains(name),
        ))

    # Keep one row per launcher identity, then sort predictably for search/UI.
    unique: dict[str, GameLibraryEntry] = {}
    for entry in entries[:_MAX_LIBRARY_ITEMS]:
        unique.setdefault(entry.key, entry)
    return sorted(unique.values(), key=lambda item: (item.name.casefold(), item.source.casefold()))


def _blacklisted_games(config: Config) -> list[str]:
    value = config.get('rules.blacklist.games', []) or []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def is_game_enabled(config: Config, game_name: object) -> bool:
    target = str(game_name or '').strip().casefold()
    if not target:
        return False
    return all(item.strip().casefold() != target for item in _blacklisted_games(config))


def set_game_enabled(config: Config, game_name: object, enabled: bool, *, save: bool = True) -> None:
    """Enable/disable a game using the existing runtime blacklist contract."""
    name = str(game_name or '').strip()[:160]
    if not name:
        raise ValueError('Game name cannot be empty')
    target = name.casefold()
    current = _blacklisted_games(config)
    filtered = [item for item in current if item.strip().casefold() != target]
    if not enabled:
        filtered.append(name)
    # Deduplicate while preserving unrelated user rules and their original case.
    deduped: list[str] = []
    seen: set[str] = set()
    for item in filtered:
        key = item.strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item.strip()[:256])
    config.set('rules.blacklist.games', deduped)
    if save:
        config.save()


def gamer_mode_enabled(config: Config) -> bool:
    return config.get('gaming.gamer_mode.enabled', False) is True


def _current_detectors(config: Config) -> dict[str, bool]:
    current = config.get('rules.enabled_detectors', {}) or {}
    defaults = DEFAULT_CONFIG['rules']['enabled_detectors']
    result: dict[str, bool] = {}
    for name in _DETECTOR_NAMES:
        value = current.get(name, defaults[name]) if isinstance(current, dict) else defaults[name]
        result[name] = value if isinstance(value, bool) else bool(defaults[name])
    return result


def set_gamer_mode(config: Config, enabled: bool, *, save: bool = True) -> None:
    """Switch between normal detection and an explicit games-only mode.

    Entering gamer mode snapshots detector preferences and suppresses all
    non-gaming detectors. Leaving it restores that snapshot, so a user who had
    browser/media detection disabled before gamer mode keeps those preferences.
    """
    enabled = bool(enabled)
    active = gamer_mode_enabled(config)
    if enabled == active:
        return

    if enabled:
        previous = _current_detectors(config)
        config.set('gaming.gamer_mode.previous_detectors', previous)
        config.set('gaming.gamer_mode.enabled', True)
        for name in _DETECTOR_NAMES:
            config.set(f'rules.enabled_detectors.{name}', name == 'gaming')
    else:
        previous = config.get('gaming.gamer_mode.previous_detectors', {}) or {}
        defaults = DEFAULT_CONFIG['rules']['enabled_detectors']
        for name in _DETECTOR_NAMES:
            value = previous.get(name, defaults[name]) if isinstance(previous, dict) else defaults[name]
            config.set(f'rules.enabled_detectors.{name}', value if isinstance(value, bool) else defaults[name])
        config.set('gaming.gamer_mode.enabled', False)
        config.set('gaming.gamer_mode.previous_detectors', {})

    if save:
        config.save()


def library_counts(entries: Iterable[GameLibraryEntry]) -> tuple[int, int]:
    total = 0
    enhanced = 0
    for entry in entries:
        total += 1
        enhanced += int(bool(entry.enhanced))
    return total, enhanced
