"""Browser activity detection."""

import logging
import urllib.parse
from typing import Optional, Dict, Any

from browser_companion import get_browser_companion
from config import Config


class BrowserDetector:
    """Detect browser activity, preferring exact companion metadata when available."""

    BROWSERS = {
        'firefox': 'Firefox',
        'chrome': 'Chrome',
        'chromium': 'Chromium',
        'brave': 'Brave',
        'msedge': 'Edge',
        'edge': 'Edge',
        'opera': 'Opera',
        'vivaldi': 'Vivaldi',
    }

    SERVICES = (
        'YouTube Music', 'YouTube', 'Netflix', 'Prime Video', 'Disney+', 'Hulu',
        'SoundCloud', 'Spotify', 'Twitch', 'GitHub', 'Reddit', 'ChatGPT', 'X'
    )

    SERVICE_URL_MARKERS = {
        'YouTube Music': ('music.youtube.com',),
        'YouTube': ('youtube.com', 'youtu.be'),
        'Netflix': ('netflix.com',),
        'Prime Video': ('primevideo.com', 'amazon.com/gp/video'),
        'Disney+': ('disneyplus.com',),
        'Hulu': ('hulu.com',),
        'SoundCloud': ('soundcloud.com',),
        'Spotify': ('open.spotify.com', 'spotify.com'),
        'Twitch': ('twitch.tv',),
        'GitHub': ('github.com',),
        'Reddit': ('reddit.com',),
        'ChatGPT': ('chatgpt.com',),
        'X': ('x.com', 'twitter.com'),
    }

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.companion = get_browser_companion(config, start=True)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not window_info:
            return None
        if not self.config.get('rules.enabled_detectors.browser', True):
            return None

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
            return self._private_activity(browser_name)

        companion_activity = self._from_companion(browser_name)
        if companion_activity:
            return companion_activity

        service = self._detect_service(raw_title)
        page_title = self._extract_page_title(raw_title, browser_name, service)
        url = self._generate_url(service, page_title)

        return {
            'type': 'browser',
            'browser_name': browser_name,
            'is_private': False,
            'page_title': page_title,
            'service': service or '',
            'url': url,
            'url_is_exact': False,
            'source': 'window',
        }

    def _from_companion(self, browser_name: str) -> Optional[Dict[str, Any]]:
        if not self.companion:
            return None
        snapshot = self.companion.latest(browser_name)
        if not snapshot:
            return None
        if bool(snapshot.get('private')):
            return self._private_activity(browser_name)

        raw_title = str(snapshot.get('title', '') or '')
        exact_url = snapshot.get('url')
        service = (
            str(snapshot.get('service', '') or '')
            or self._configured_service(exact_url)
            or self._detect_service(exact_url, raw_title)
            or ''
        )
        page_title = self._extract_page_title(raw_title, browser_name, service or None)
        media = snapshot.get('media') if isinstance(snapshot.get('media'), dict) else {}

        return {
            'type': 'browser',
            'browser_name': browser_name,
            'is_private': False,
            'page_title': page_title,
            'service': service,
            'url': exact_url,
            'url_is_exact': bool(exact_url),
            'source': 'companion',
            'media': media,
        }

    @staticmethod
    def _private_activity(browser_name: str) -> Dict[str, Any]:
        return {
            'type': 'browser',
            'browser_name': browser_name,
            'is_private': True,
            'page_title': '',
            'service': '',
            'url': None,
            'url_is_exact': False,
            'source': 'private',
        }

    def _configured_service(self, raw_url: Any) -> Optional[str]:
        """Map exact or wildcard custom domains to a local service label."""
        url = str(raw_url or '').strip()
        if not url:
            return None
        try:
            hostname = (urllib.parse.urlsplit(url).hostname or '').lower().rstrip('.')
        except ValueError:
            return None
        if not hostname:
            return None

        configured = self.config.get('browser_companion.domain_services', {}) or {}
        if not isinstance(configured, dict):
            return None
        for pattern, label in configured.items():
            domain = str(pattern or '').strip().lower().rstrip('.')
            name = str(label or '').strip()
            if not domain or not name:
                continue
            if domain.startswith('*.'):
                suffix = domain[2:]
                if hostname == suffix or hostname.endswith('.' + suffix):
                    return name
            elif hostname == domain:
                return name
        return None

    def _detect_service(self, *values: Any) -> Optional[str]:
        combined = ' '.join(str(value or '') for value in values).lower()
        for service, markers in self.SERVICE_URL_MARKERS.items():
            if any(marker in combined for marker in markers):
                return service
        youtube_markers = self.config.get('rules.youtube_domains', []) or []
        if any(str(marker).lower() in combined for marker in youtube_markers if marker):
            return 'YouTube'
        for service in self.SERVICES:
            if service.lower() in combined:
                return service
        return None

    def _generate_url(self, service: Optional[str], title: str) -> Optional[str]:
        """Generate a search/home URL only when the companion has no exact tab URL."""
        if not service:
            return None
        query = urllib.parse.quote(title)

        if service == 'YouTube':
            return f"https://www.youtube.com/results?search_query={query}" if title else 'https://www.youtube.com'
        if service == 'YouTube Music':
            return f"https://music.youtube.com/search?q={query}" if title else 'https://music.youtube.com'
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
        if service == 'Reddit':
            return 'https://www.reddit.com'
        if service == 'ChatGPT':
            return 'https://chatgpt.com'
        if service == 'X':
            return 'https://x.com'
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
