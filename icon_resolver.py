"""Resolve Rich Presence artwork from the application actually producing activity."""

from __future__ import annotations

import re
import urllib.parse
from typing import Iterable, Optional

from config import Config
from url_safety import public_https_url


class IconResolver:
    """Prefer application-specific raster artwork with safe user overrides."""

    # Discord's legacy RPC path is most reliable with raster HTTPS artwork.
    # Google S2 provides a small PNG for public domains and requires no API key.
    BUILTIN_ICON_DOMAINS = {
        # Browsers
        "brave": "brave.com",
        "brave browser": "brave.com",
        "chrome": "google.com/chrome",
        "google chrome": "google.com/chrome",
        "chromium": "chromium.org",
        "firefox": "firefox.com",
        "firefox browser": "firefox.com",
        "edge": "microsoft.com/edge",
        "msedge": "microsoft.com/edge",
        "microsoft edge": "microsoft.com/edge",
        "opera": "opera.com",
        "opera gx": "opera.com/gx",
        "vivaldi": "vivaldi.com",
        "floorp": "floorp.app",
        "zen browser": "zen-browser.app",

        # Media / communication
        "spotify": "spotify.com",
        "vlc": "videolan.org",
        "mpv": "mpv.io",
        "windows media player": "microsoft.com",
        "discord": "discord.com",
        "discord desktop": "discord.com",
        "slack": "slack.com",
        "signal": "signal.org",
        "telegram": "telegram.org",
        "telegram desktop": "telegram.org",
        "whatsapp": "whatsapp.com",
        "microsoft teams": "microsoft.com/microsoft-teams",
        "teams": "microsoft.com/microsoft-teams",
        "zoom": "zoom.us",

        # Editors / IDEs / creative tools
        "visual studio code": "code.visualstudio.com",
        "vs code": "code.visualstudio.com",
        "code": "code.visualstudio.com",
        "vs code oss": "code.visualstudio.com",
        "vscodium": "vscodium.com",
        "cursor": "cursor.com",
        "zed": "zed.dev",
        "pycharm": "jetbrains.com/pycharm",
        "intellij idea": "jetbrains.com/idea",
        "webstorm": "jetbrains.com/webstorm",
        "phpstorm": "jetbrains.com/phpstorm",
        "goland": "jetbrains.com/go",
        "rider": "jetbrains.com/rider",
        "clion": "jetbrains.com/clion",
        "rubymine": "jetbrains.com/ruby",
        "jetbrains toolbox": "jetbrains.com/toolbox-app",
        "android studio": "developer.android.com/studio",
        "sublime text": "sublimetext.com",
        "vim": "vim.org",
        "neovim": "neovim.io",
        "nvim": "neovim.io",
        "emacs": "gnu.org/software/emacs",
        "trae": "trae.ai",
        "obsidian": "obsidian.md",
        "notion": "notion.so",
        "blender": "blender.org",
        "gimp": "gimp.org",
        "krita": "krita.org",
        "inkscape": "inkscape.org",
        "figma": "figma.com",

        # Shells / Linux desktop apps
        "powershell": "microsoft.com/powershell",
        "powershell core": "microsoft.com/powershell",
        "windows terminal": "microsoft.com/windows/terminal",
        "bash": "gnu.org/software/bash",
        "zsh": "zsh.org",
        "fish": "fishshell.com",
        "konsole": "apps.kde.org/konsole",
        "dolphin": "apps.kde.org/dolphin",
        "kate": "kate-editor.org",
        "okular": "okular.kde.org",
        "discover": "apps.kde.org/discover",
        "system settings": "kde.org/plasma-desktop",
        "kde plasma": "kde.org/plasma-desktop",
        "gnome terminal": "apps.gnome.org/Console",
        "nautilus": "apps.gnome.org/Nautilus",
        "thunderbird": "thunderbird.net",
        "libreoffice": "libreoffice.org",

        # Developer / system utilities
        "github desktop": "desktop.github.com",
        "gitkraken": "gitkraken.com",
        "postman": "postman.com",
        "docker desktop": "docker.com/products/docker-desktop",
        "docker": "docker.com",
        "virtualbox": "virtualbox.org",
        "vmware": "vmware.com",

        # Games / launchers
        "counter strike 2": "counter-strike.net",
        "counter-strike 2": "counter-strike.net",
        "cs2": "counter-strike.net",
        "minecraft": "minecraft.net",
        "league of legends": "leagueoflegends.com",
        "valorant": "playvalorant.com",
        "fortnite": "fortnite.com",
        "rocket league": "rocketleague.com",
        "steam": "steampowered.com",
        "epic": "epicgames.com",
        "epic games": "epicgames.com",
        "epic games launcher": "epicgames.com",
        "heroic": "heroicgameslauncher.com",
        "heroic games launcher": "heroicgameslauncher.com",
        "gog": "gog.com",
        "gog galaxy": "gog.com/galaxy",
        "battle.net": "battle.net",
        "battlenet": "battle.net",
        "ubisoft connect": "ubisoft.com",
        "ea desktop": "ea.com/ea-app",
        "ea app": "ea.com/ea-app",
        "riot client": "riotgames.com",
        "xbox": "xbox.com",

        # Web services / social apps
        "youtube": "youtube.com",
        "youtube music": "music.youtube.com",
        "netflix": "netflix.com",
        "prime video": "primevideo.com",
        "twitch": "twitch.tv",
        "github": "github.com",
        "soundcloud": "soundcloud.com",
        "hulu": "hulu.com",
        "disney+": "disneyplus.com",
        "reddit": "reddit.com",
        "chatgpt": "chatgpt.com",
        "x": "x.com",
        "x.com": "x.com",
        "facebook": "facebook.com",
        "messenger": "messenger.com",
        "instagram": "instagram.com",
        "linkedin": "linkedin.com",
        "threads": "threads.com",
        "tiktok": "tiktok.com",
        "snapchat": "snapchat.com",
        "discord web": "discord.com",
        "pinterest": "pinterest.com",
        "bluesky": "bsky.app",
    }

    ALIASES = {
        "google-chrome": "google chrome",
        "google chrome stable": "google chrome",
        "brave-browser": "brave",
        "brave browser beta": "brave",
        "firefox-esr": "firefox",
        "microsoft-edge": "microsoft edge",
        "org.kde.konsole": "konsole",
        "org.kde.dolphin": "dolphin",
        "org.kde.kate": "kate",
        "org.kde.okular": "okular",
        "org.kde.discover": "discover",
        "org.kde.systemsettings": "system settings",
        "com.visualstudio.code": "visual studio code",
        "code oss": "vs code oss",
        "discordcanary": "discord",
        "discordptb": "discord",
        "steamwebhelper": "steam",
        "heroicgameslauncher": "heroic games launcher",
        "epicgameslauncher": "epic games launcher",
        "riotclientservices": "riot client",
        "eadesktop": "ea desktop",
    }

    def __init__(self, config: Config):
        self.config = config

    @classmethod
    def _normalize(cls, value: object) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"\.(exe|bin|app)$", "", text)
        raw = text
        if raw in cls.ALIASES:
            return cls.ALIASES[raw]
        if text.startswith(("org.", "com.", "io.", "net.")) and "." in text:
            text = text.rsplit(".", 1)[-1]
        text = text.replace("_", " ").replace("-", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return cls.ALIASES.get(text, text)

    @staticmethod
    def _png_favicon_url(domain_or_path: str) -> str:
        target = "https://" + str(domain_or_path or "").strip().lstrip("/")
        encoded = urllib.parse.quote(target, safe="")
        return f"https://www.google.com/s2/favicons?domain_url={encoded}&sz=256"

    def _names(self, values: Iterable[object]) -> list[str]:
        names: list[str] = []
        for value in values:
            normalized = self._normalize(value)
            if normalized and normalized not in names:
                names.append(normalized)
        return names

    def _custom_override(self, names: list[str]) -> Optional[str]:
        overrides = self.config.get("images.icon_overrides", {}) or {}
        if not isinstance(overrides, dict):
            return None
        normalized_overrides = {
            self._normalize(key): str(value).strip()
            for key, value in overrides.items()
            if str(value or "").strip()
        }
        for name in names:
            value = normalized_overrides.get(name)
            if not value:
                continue
            # Asset keys are allowed. URLs must meet the same public HTTPS
            # boundary as every other Rich Presence external image.
            if value.lower().startswith(("http://", "https://")):
                safe = public_https_url(value, 300)
                if safe:
                    return safe
                continue
            return value[:300]
        return None

    def resolve_optional(
        self,
        *values: object,
        configured: Optional[str] = None,
    ) -> Optional[str]:
        """Return application-specific artwork, or None when no match exists."""
        names = self._names(values)

        custom = self._custom_override(names)
        if custom:
            return custom

        if self.config.get("images.use_external_app_icons", True):
            for name in names:
                domain = self.BUILTIN_ICON_DOMAINS.get(name)
                if domain:
                    return self._png_favicon_url(domain)

        configured_value = str(configured or "").strip()
        if configured_value.lower().startswith(("http://", "https://")):
            return public_https_url(configured_value, 300)
        return configured_value[:300] or None

    def resolve(
        self,
        *values: object,
        configured: Optional[str] = None,
        fallback: str = "app",
    ) -> str:
        """Resolve artwork for one or more aliases, in priority order."""
        return self.resolve_optional(*values, configured=configured) or str(fallback or "app")
