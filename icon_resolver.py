"""Resolve Rich Presence artwork from the application actually producing activity."""

import re
from typing import Iterable, Optional

from config import Config


class IconResolver:
    """Prefer per-application artwork while keeping existing asset-key fallbacks."""

    # Discord's traditional desktop RPC path is more reliable with raster
    # external artwork. Google S2 returns PNG favicons and avoids sending SVG
    # artwork that some Discord desktop clients silently ignore.
    BUILTIN_ICON_DOMAINS = {
        # Browsers
        'brave': 'brave.com',
        'chrome': 'chrome.google.com',
        'google chrome': 'chrome.google.com',
        'chromium': 'chromium.org',
        'firefox': 'firefox.com',
        'firefox browser': 'firefox.com',
        'edge': 'microsoftedge.microsoft.com',
        'microsoft edge': 'microsoftedge.microsoft.com',
        'opera': 'opera.com',
        'vivaldi': 'vivaldi.com',

        # Media
        'spotify': 'spotify.com',
        'vlc': 'videolan.org',
        'mpv': 'mpv.io',
        'windows media player': 'microsoft.com',

        # Editors / IDEs
        'visual studio code': 'code.visualstudio.com',
        'vs code': 'code.visualstudio.com',
        'vs code oss': 'code.visualstudio.com',
        'vscodium': 'vscodium.com',
        'pycharm': 'jetbrains.com',
        'intellij idea': 'jetbrains.com',
        'webstorm': 'jetbrains.com',
        'phpstorm': 'jetbrains.com',
        'goland': 'jetbrains.com',
        'rider': 'jetbrains.com',
        'clion': 'jetbrains.com',
        'rubymine': 'jetbrains.com',
        'android studio': 'developer.android.com',
        'sublime text': 'sublimetext.com',
        'vim': 'vim.org',
        'neovim': 'neovim.io',
        'emacs': 'gnu.org',
        'trae': 'trae.ai',

        # Shells / terminals / KDE applications
        'powershell': 'microsoft.com',
        'powershell core': 'microsoft.com',
        'windows terminal': 'microsoft.com',
        'bash': 'gnu.org',
        'konsole': 'kde.org',
        'dolphin': 'kde.org',
        'kate': 'kate-editor.org',
        'okular': 'okular.kde.org',
        'kde plasma': 'kde.org',

        # Games / services / launchers useful as secondary artwork too
        'counter strike 2': 'counter-strike.net',
        'counter-strike 2': 'counter-strike.net',
        'cs2': 'counter-strike.net',
        'youtube': 'youtube.com',
        'youtube music': 'music.youtube.com',
        'netflix': 'netflix.com',
        'prime video': 'primevideo.com',
        'twitch': 'twitch.tv',
        'github': 'github.com',
        'soundcloud': 'soundcloud.com',
        'hulu': 'hulu.com',
        'disney+': 'disneyplus.com',
        'reddit': 'reddit.com',
        'chatgpt': 'chatgpt.com',
        'x': 'x.com',
        'x.com': 'x.com',
        'steam': 'steampowered.com',
        'discord': 'discord.com',
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

    @staticmethod
    def _png_favicon_url(domain: str) -> str:
        return f'https://www.google.com/s2/favicons?domain={domain}&sz=256'

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

    def resolve_optional(
        self,
        *values: object,
        configured: Optional[str] = None,
    ) -> Optional[str]:
        """Return matching artwork, or None when no specific artwork exists."""
        names = self._names(values)

        custom = self._custom_override(names)
        if custom:
            return custom

        if self.config.get('images.use_external_app_icons', True):
            for name in names:
                domain = self.BUILTIN_ICON_DOMAINS.get(name)
                if domain:
                    return self._png_favicon_url(domain)

        configured_value = str(configured or '').strip()
        return configured_value or None

    def resolve(
        self,
        *values: object,
        configured: Optional[str] = None,
        fallback: str = 'app',
    ) -> str:
        """Resolve artwork for one or more aliases, in priority order."""
        return self.resolve_optional(*values, configured=configured) or str(fallback or 'app')
