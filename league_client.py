"""Privacy-minimal League of Legends Live Client Data integration.

Riot's documented game-client API is exposed only on the local machine at
https://127.0.0.1:2999 while a match is running. The client uses the documented
small endpoints instead of retaining the full allgamedata response.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Optional


_BASE = 'https://127.0.0.1:2999/liveclientdata'
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_TIMEOUT = 0.65
_CACHE_TTL = 1.5

_MODE_NAMES = {
    'CLASSIC': "Summoner's Rift",
    'ARAM': 'ARAM',
    'CHERRY': 'Arena',
    'URF': 'URF',
    'ONEFORALL': 'One for All',
    'PRACTICETOOL': 'Practice Tool',
    'TUTORIAL': 'Tutorial',
    'ULTBOOK': 'Ultimate Spellbook',
    'NEXUSBLITZ': 'Nexus Blitz',
    'SWIFTPLAY': 'Swiftplay',
}

_POSITION_NAMES = {
    'TOP': 'Top',
    'JUNGLE': 'Jungle',
    'MIDDLE': 'Mid',
    'MID': 'Mid',
    'BOTTOM': 'Bot',
    'BOT': 'Bot',
    'UTILITY': 'Support',
    'SUPPORT': 'Support',
}


class LeagueLiveClient:
    """Read only the local player's display-safe current-match context."""

    def __init__(self):
        # Riot's local game client uses a self-signed certificate. Certificate
        # verification is disabled only for the fixed IPv4 loopback endpoint;
        # callers cannot redirect this client to a network host.
        self._ssl_context = ssl._create_unverified_context()  # noqa: S323
        self._cached: Optional[dict[str, Any]] = None
        self._cached_at = 0.0

    def _get_json(self, endpoint: str) -> Any:
        if not endpoint.startswith('/') or '..' in endpoint:
            return None
        request = urllib.request.Request(
            _BASE + endpoint,
            headers={'User-Agent': 'CYBREX-Rich-Presence/League'},
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=_TIMEOUT,
                context=self._ssl_context,
            ) as response:
                if response.status != 200:
                    return None
                data = response.read(_MAX_RESPONSE_BYTES + 1)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError):
            return None
        if len(data) > _MAX_RESPONSE_BYTES:
            return None
        try:
            return json.loads(data.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _safe_text(value: Any, limit: int = 64) -> str:
        text = ' '.join(str(value or '').replace('\x00', ' ').split())
        return text[:limit]

    def snapshot(self) -> Optional[dict[str, Any]]:
        now = time.monotonic()
        if now - self._cached_at < _CACHE_TTL:
            return dict(self._cached) if self._cached else None

        self._cached_at = now
        self._cached = None

        stats = self._get_json('/gamestats')
        player_name = self._get_json('/activeplayername')
        players = self._get_json('/playerlist')
        if not isinstance(stats, dict) or not isinstance(player_name, str) or not isinstance(players, list):
            return None

        # playerlist contains every champion, but we use it only transiently to
        # locate the local player. No Riot IDs, names, KDA, items, runes or enemy
        # information are retained in the snapshot or sent to Discord.
        own_player = None
        for player in players[:20]:
            if not isinstance(player, dict):
                continue
            identities = {
                str(player.get('riotId') or ''),
                str(player.get('summonerName') or ''),
            }
            if player_name in identities:
                own_player = player
                break
        if own_player is None:
            return None

        champion = self._safe_text(own_player.get('championName'))
        raw_position = self._safe_text(own_player.get('position')).upper()
        raw_mode = self._safe_text(stats.get('gameMode')).upper()
        try:
            game_time = max(0, int(float(stats.get('gameTime') or 0)))
        except (TypeError, ValueError, OverflowError):
            game_time = 0

        snapshot = {
            'champion': champion,
            'position': _POSITION_NAMES.get(raw_position, ''),
            'mode': _MODE_NAMES.get(raw_mode, self._safe_text(raw_mode.title())),
            'game_time': game_time,
        }
        self._cached = snapshot
        return dict(snapshot)
