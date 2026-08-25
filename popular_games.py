"""Curated popular-game compatibility catalog.

This catalog is a product/QA layer, not a process scanner. Runtime game
identification remains launcher-metadata-first (Steam/Epic/Heroic), with the
strict exact-process Community Game Pack used only as a conservative fallback.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional


_LOGGER = logging.getLogger(__name__)
_MAX_CATALOG_BYTES = 128 * 1024
_MAX_GAMES = 1024
_MAX_TITLE = 160
_BUNDLED_CATALOGS = ('popular_catalog.json', 'popular_cross_launcher.json')


def _resource_root() -> Path:
    frozen_root = getattr(sys, '_MEIPASS', None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parent


def normalize_title(value: object) -> str:
    """Normalize a display title for exact, case-insensitive catalog matching."""
    text = str(value or '').replace('\x00', ' ').replace('\r', ' ').replace('\n', ' ')
    return ' '.join(text.split()).casefold()


def load_popular_catalog(path: Path) -> tuple[str, ...]:
    """Load a bounded schema-1 title catalog and reject ambiguous data."""
    try:
        if path.stat().st_size > _MAX_CATALOG_BYTES:
            raise ValueError('popular game catalog is too large')
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f'could not read popular game catalog: {exc}') from exc

    if len(raw) > _MAX_CATALOG_BYTES:
        raise ValueError('popular game catalog is too large')
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('popular game catalog contains invalid JSON') from exc

    if not isinstance(payload, dict) or payload.get('schema') != 1:
        raise ValueError('unsupported popular game catalog schema')
    games = payload.get('games')
    if not isinstance(games, list) or not games or len(games) > _MAX_GAMES:
        raise ValueError('popular game catalog has an invalid game list')

    result: list[str] = []
    seen: set[str] = set()
    for item in games:
        if not isinstance(item, str):
            raise ValueError('popular game titles must be strings')
        title = ' '.join(item.replace('\x00', ' ').replace('\r', ' ').replace('\n', ' ').split())
        normalized = normalize_title(title)
        if not title or len(title) > _MAX_TITLE or not normalized:
            raise ValueError('popular game catalog contains an invalid title')
        if normalized in seen:
            raise ValueError(f'duplicate popular game title: {title}')
        seen.add(normalized)
        result.append(title)
    return tuple(result)


class PopularGameCatalog:
    """Exact normalized membership test for the bundled curated title set."""

    def __init__(self, path: Optional[Path] = None):
        sources = (
            (path,)
            if path is not None
            else tuple(_resource_root() / 'game_packs' / name for name in _BUNDLED_CATALOGS)
        )
        games: list[str] = []
        seen: set[str] = set()
        for source in sources:
            try:
                loaded = load_popular_catalog(source)
            except ValueError as exc:
                _LOGGER.warning('Popular game catalog unavailable (%s): %s', source, exc)
                continue
            for title in loaded:
                normalized = normalize_title(title)
                if normalized in seen:
                    _LOGGER.warning('Ignoring duplicate popular game title across catalogs: %s', title)
                    continue
                seen.add(normalized)
                games.append(title)
                if len(games) >= _MAX_GAMES:
                    break
            if len(games) >= _MAX_GAMES:
                break
        self.games = tuple(games)
        self._normalized = frozenset(seen)

    def contains(self, title: object) -> bool:
        normalized = normalize_title(title)
        return bool(normalized and normalized in self._normalized)
