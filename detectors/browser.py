"""Browser activity detection with an optional privacy-preserving local companion."""

import logging
import urllib.parse
from typing import Optional, Dict, Any

from browser_companion import BrowserCompanionServer
from config import Config


class BrowserDetector:
    """Detect browser activity without pretending inferred URLs are exact URLs."""

    BROWSERS = {
        'firefox': 'Firefox',
        'chrome': 'Chrome',
        'chromium': 'Chromium',
        'brave': 'Brave',
        'msedge': 'Edge',
        'edge': 'Edge',
        'opera': 'Opera',
        'vivaldi': 'Vivaldi',
        'floorp': 'Floorp',
        'librewolf': 'LibreWolf',
        'zen': 'Zen',
    }

    SERVICES = (
        'YouTube', 'Netflix', 'Prime Video', 'Disney+', 'Hulu',
        'SoundCloud', 'Spotify', 'Twitch', 'GitHub'
    )

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.companion: Optional[BrowserCompanionServer] = None
        self._sync_companion_state()

    def close(self) -> None:
        if self.companion:
            self.companion.stop()
            self.companion = None

    def companion_status(self) -> Dict[str, Any]:
        self._sync_companion_state()
        if not self.companion:
            return {'enabled': False, 'running': False}
        server = self.companion._server
        return {
            'enabled': True,
            'running': bool(server),
            'host': '127.0.0.1',
            'port': server.server_address[1] if server else int(
                self.config.get('browser_companion.port', 17653) or 17653
            ),
            'token_path': str(self.companion.token_path),
        }

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not window_info:
            return None
        if not self.config.get('rules.enabled_detectors.browser', True):
            return None

        self._sync_companion_state()
        app_name = str(window_info.get('app_name', '')).lower()
        raw_title = str(window_info.get('title', ''))

        browser_name = None
        for key, name in self.BROWSERS.items():
            if key in app_name:
                browser_name = name
                break
        if not browser_name:
            return None

        if self._is_private_browsing(raw_title):
            return {
                'type': 'browser',
                'browser_name': browser_name,
                'is_private': True,
                'page_title': '',
                'service': '',
                'url': None,
                'source': 'window',
            }

        companion = self.companion.snapshot(browser_name) if self.companion else None
        if companion and companion.get('private'):
            return {
                'type': 'browser',
                'browser_name': browser_name,
                'is_private': True,
                'page_title': '',
                'service': '',
                'url': None,
                'source': 'companion',
            }

        service = str(companion.get('service') or '').strip() if companion else ''
        if not service:
            service = self._detect_service(raw_title) or ''
        page_title = str(companion.get('title') or '').strip() if companion else ''
        if not page_title:
            page_title = self._extract_page_title(raw_title, browser_name, service or None)

        url = companion.get('url') if companion else None
        url_kind = 'companion' if url else 'generated'
        if not url:
            url = self._generate_url(service or None, page_title)

        return {
            'type': 'browser',
            'browser_name': browser_name,
            'is_private': False,
            'page_title': page_title,
            'service': service,
            'url': url,
            'url_kind': url_kind,
            'source': 'companion' if companion else 'window',
        }

    def _sync_companion_state(self) -> None:
        enabled = bool(self.config.get('browser_companion.enabled', False))
        if enabled and self.companion is None:
            try:
                self.companion = BrowserCompanionServer(self.config)
                self.companion.start()
            except Exception as exc:
                self.logger.warning('Browser companion could not start: %s', exc)
                if self.companion:
                    self.companion.stop()
                self.companion = None
        elif not enabled and self.companion is not None:
            self.companion.stop()
            self.companion = None

    def _detect_service(self, raw_title: str) -> Optional[str]:
        title_lower = raw_title.lower()
        youtube_markers = self.config.get('rules.youtube_domains', []) or []
        if any(str(marker).lower() in title_lower for marker in youtube_markers if marker):
            return 'YouTube'
        for service in self.SERVICES:
            if service.lower() in title_lower:
                return service
        return None

    def _generate_url(self, service: Optional[str], title: str) -> Optional[str]:
        """Generate a search/home URL. This is intentionally not the exact tab URL."""
        if not service:
            return None
        query = urllib.parse.quote(title)

        if service == 'YouTube':
            return f"https://www.youtube.com/results?search_query={query}" if title else 'https://www.youtube.com'
        if service == 'SoundCloud':
            return f"https://soundcloud.com/search?q={query}" if title else 'https://soundcloud.com'
        if service == 'Netflix':
            return f"https://www.netflix.com/search?q={query}" if title else 'https://www.netflix.com'
        if service == 'Twitch':
            if title and ' ' not in title:
                return f"https://www.twitch.tv/{urllib.parse.quote(title, safe='')}"
            return f"https://www.twitch.tv/search?term={query}" if title else 'https://www.twitch.tv'
        if service == 'Spotify':
            return f"https://open.spotify.com/search/{query}" if title else 'https://open.spotify.com'
        if service == 'GitHub':
            return 'https://github.com'
        if service == 'Disney+':
            return 'https://www.disneyplus.com'
        if service == 'Hulu':
            return 'https://www.hulu.com'
        if service == 'Prime Video':
            return f"https://www.amazon.com/s?k={query}&i=instant-video" if title else 'https://www.amazon.com/gp/video/storefront'
        return None

    def _is_private_browsing(self, title: str) -> bool:
        markers = self.config.get('rules.private_markers', []) or []
        title_lower = title.lower()
        if any(str(marker).lower() in title_lower for marker in markers if marker):
            return True
        return '⧉' in title or '🕶' in title

    def _extract_page_title(self, title: str, browser_name: str, service: Optional[str]) -> str:
        if not title:
            return ''

        cleaned = title
        for sep in (' - ', ' — ', ' – '):
            suffix = sep + browser_name
            if cleaned.lower().endswith(suffix.lower()):
                cleaned = cleaned[:-len(suffix)]
                break

        if service:
            for sep in (' - ', ' | ', ' — ', ' – '):
                suffix = sep + service
                if cleaned.lower().endswith(suffix.lower()):
                    cleaned = cleaned[:-len(suffix)]
                    break

        return cleaned.strip()
