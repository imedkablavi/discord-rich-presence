"""Cross-application activity priority selection."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from config import Config


class ActivityPriorityEngine:
    """Choose one activity when foreground and background detectors both match."""

    KNOWN_KINDS = ('gaming', 'terminal', 'coding', 'browser', 'media', 'application')
    FOREGROUND_ORDER = ('gaming', 'terminal', 'coding', 'browser', 'media', 'application')
    MEDIA_FIRST_ORDER = ('gaming', 'media', 'terminal', 'coding', 'browser', 'application')

    def __init__(self, config: Config):
        self.config = config

    def choose(
        self,
        window_info: Dict[str, Any],
        candidates: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        available = {key: value for key, value in candidates.items() if key in self.KNOWN_KINDS and value}
        if not available:
            return None

        policy = str(self.config.get('rules.activity_priority.policy', 'smart') or 'smart').lower()
        if policy == 'media_first':
            return self._first(available, self.MEDIA_FIRST_ORDER)
        if policy == 'foreground_first':
            return self._first(available, self.FOREGROUND_ORDER)
        if policy == 'custom':
            configured = self.config.get('rules.activity_priority.custom_order', []) or []
            order = [str(item).lower() for item in configured if str(item).lower() in self.KNOWN_KINDS]
            order.extend(kind for kind in self.KNOWN_KINDS if kind not in order)
            return self._first(available, tuple(order))

        # Smart is the product default. Games remain strongest. Foreground media
        # wins when the media player/tab is what the user is actually looking at;
        # otherwise coding/terminal/browser activity beats background playback.
        if 'gaming' in available:
            return available['gaming']
        if 'media' in available and self._media_matches_foreground(available['media'], window_info):
            return available['media']
        for kind in ('terminal', 'coding', 'browser'):
            if kind in available:
                return available[kind]
        if 'media' in available:
            return available['media']
        return available.get('application')

    @staticmethod
    def _first(candidates: Dict[str, Dict[str, Any]], order: tuple[str, ...]) -> Optional[Dict[str, Any]]:
        for kind in order:
            if kind in candidates:
                return candidates[kind]
        return None

    @classmethod
    def _media_matches_foreground(cls, media: Dict[str, Any], window_info: Dict[str, Any]) -> bool:
        # The browser companion knows exact tab focus. If it says the playing tab
        # is not focused, do not let background YouTube override the active GitHub
        # tab merely because both live inside Brave/Firefox/Chrome.
        if str(media.get('source', '')).lower() == 'companion' and 'tab_focused' in media:
            return bool(media.get('tab_focused'))

        player = cls._tokens(media.get('player', ''))
        app = cls._tokens(window_info.get('app_name', ''))
        if not player or not app:
            return False

        aliases = {
            'brave': {'brave'},
            'firefox': {'firefox'},
            'chrome': {'chrome', 'googlechrome'},
            'chromium': {'chromium'},
            'edge': {'edge', 'msedge'},
            'opera': {'opera'},
            'vivaldi': {'vivaldi'},
            'spotify': {'spotify'},
            'vlc': {'vlc'},
            'mpv': {'mpv'},
        }
        for canonical, names in aliases.items():
            if canonical in player or player.intersection(names):
                return canonical in app or bool(app.intersection(names))
        return bool(player.intersection(app))

    @staticmethod
    def _tokens(value: Any) -> set[str]:
        raw = str(value or '').lower()
        tokens = set(re.findall(r'[a-z0-9]+', raw))
        compact = ''.join(re.findall(r'[a-z0-9]+', raw))
        if compact:
            tokens.add(compact)
        return tokens
