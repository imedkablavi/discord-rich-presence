"""Resolve Rich Presence artwork from the application actually producing activity."""

import re
from typing import Iterable, Optional

from config import Config


class IconResolver:
    """Prefer per-application artwork while keeping existing asset-key fallbacks."""

    # Discord accepts external image URLs for Rich Presence assets. These URLs
    # are only placed in the RPC payload; this service does not download them.
    # Simple Icons provides stable brand artwork for common applications.
    BUILTIN_EXTERNAL_ICONS = {
        # Browsers
        'brave': 'https://cdn.simpleicons.org/brave',
        'chrome': 'https://cdn.simpleicons.org/googlechrome',
        'google chrome': 'https://cdn.simpleicons.org/googlechrome',
        'chromium': 'https://cdn.simpleicons.org/chromium',
        'firefox': 'https://cdn.simpleicons.org/firefoxbrowser',
        'firefox browser': 'https://cdn.simpleicons.org/firefoxbrowser',
        'edge': 'https://cdn.simpleicons.org/microsoftedge',
        'microsoft edge': 'https://cdn.simpleicons.org/microsoftedge',
        'opera': 'https://cdn.simpleicons.org/opera',
        'vivaldi': 'https://cdn.simpleicons.org/vivaldi',

        # Media
        'spotify': 'https://cdn.simpleicons.org/spotify',
        'mpv': 'https://cdn.simpleicons.org/mpv',

        # Editors / IDEs
        'visual studio code': 'https://cdn.simpleicons.org/visualstudiocode',
        'vs code': 'https://cdn.simpleicons.org/visualstudiocode',
        'vs code oss': 'https://cdn.simpleicons.org/visualstudiocode',
        'vscodium': 'https://cdn.simpleicons.org/vscodium',
        'pycharm': 'https://cdn.simpleicons.org/pycharm',
        'intellij idea': 'https://cdn.simpleicons.org/intellijidea',
        'webstorm': 'https://cdn.simpleicons.org/webstorm',
        'phpstorm': 'https://cdn.simpleicons.org/phpstorm',
        'goland': 'https://cdn.simpleicons.org/goland',
        'rider': 'https://cdn.simpleicons.org/rider',
        'clion': 'https://cdn.simpleicons.org/clion',
        'rubymine': 'https://cdn.simpleicons.org/rubymine',
        'android studio': 'https://cdn.simpleicons.org/androidstudio',
        'sublime text': 'https://cdn.simpleicons.org/sublimetext',
        'vim': 'https://cdn.simpleicons.org/vim',
        'neovim': 'https://cdn.simpleicons.org/neovim',
        'emacs': 'https://cdn.simpleicons.org/gnuemacs',

        # Shells / terminals / KDE applications
        'powershell': 'https://cdn.simpleicons.org/powershell',
        'powershell core': 'https://cdn.simpleicons.org/powershell',
        'windows terminal': 'https://cdn.simpleicons.org/windowsterminal',
        'bash': 'https://cdn.simpleicons.org/gnubash',
        'konsole': 'https://cdn.simpleicons.org/kdeplasma',
        'dolphin': 'https://cdn.simpleicons.org/kdeplasma',
        'kate': 'https://cdn.simpleicons.org/kdeplasma',
        'okular': 'https://cdn.simpleicons.org/kdeplasma',
        'kde plasma': 'https://cdn.simpleicons.org/kdeplasma',

        # Services / launchers that are useful as secondary artwork too
        'youtube': 'https://cdn.simpleicons.org/youtube',
        'netflix': 'https://cdn.simpleicons.org/netflix',
        'twitch': 'https://cdn.simpleicons.org/twitch',
        'github': 'https://cdn.simpleicons.org/github',
        'soundcloud': 'https://cdn.simpleicons.org/soundcloud',
        'hulu': 'https://cdn.simpleicons.org/hulu',
        'disney+': 'https://cdn.simpleicons.org/disneyplus',
        'steam': 'https://cdn.simpleicons.org/steam',
        'discord': 'https://cdn.simpleicons.org/discord',
    }

    def __init__(self, config: Config):
        self.config = config

    @staticmethod
    def _normalize(value: object) -> str:
        text = str(value or '').strip().lower()
        if text.startswith(('org.', 'com.', 'io.', 'net.')) and '.' in text:
            text = text.rsplit('.', 1)[-1]
        text = text.replace('_', ' ').replace('-', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    def _names(self, values: Iterable[object]) -> list[str]:
        names = []
        for value in values:
            normalized = self._normalize(value)
            if normalized and normalized not in names:
                names.append(normalized)
        return names

    def _custom_override(self, names: list[str]) -> Optional[str]:
        overrides = self.config.get('images.icon_overrides', {}) or {}
        if not isinstance(overrides, dict):
            return None
        normalized_overrides = {
            self._normalize(key): str(value).strip()
            for key, value in overrides.items()
            if str(value or '').strip()
        }
        for name in names:
            value = normalized_overrides.get(name)
            if value:
                return value
        return None

    def resolve(
        self,
        *values: object,
        configured: Optional[str] = None,
        fallback: str = 'app',
    ) -> str:
        """Resolve artwork for one or more aliases, in priority order."""
        names = self._names(values)

        custom = self._custom_override(names)
        if custom:
            return custom

        if self.config.get('images.use_external_app_icons', True):
            for name in names:
                external = self.BUILTIN_EXTERNAL_ICONS.get(name)
                if external:
                    return external

        configured_value = str(configured or '').strip()
        if configured_value:
            return configured_value
        return str(fallback or 'app')
