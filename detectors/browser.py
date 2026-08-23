"""Browser activity detection."""

import logging
import re
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
        'SoundCloud', 'Spotify', 'Twitch', 'GitHub', 'Reddit', 'ChatGPT', 'X',
        'WhatsApp', 'Facebook', 'Messenger', 'Instagram', 'LinkedIn', 'Threads',
        'TikTok', 'Telegram', 'Snapchat', 'Discord Web', 'Pinterest', 'Bluesky',
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
        'WhatsApp': ('web.whatsapp.com',),
        'Facebook': ('facebook.com',),
        'Messenger': ('messenger.com', 'facebook.com/messages'),
        'Instagram': ('instagram.com',),
        'LinkedIn': ('linkedin.com',),
        'Threads': ('threads.com', 'threads.net'),
        'TikTok': ('tiktok.com',),
        'Telegram': ('web.telegram.org',),
        'Snapchat': ('web.snapchat.com',),
        'Discord Web': ('discord.com/app', 'discord.com/channels'),
        'Pinterest': ('pinterest.com',),
        'Bluesky': ('bsky.app',),
    }

    SOCIAL_SERVICES = frozenset({
        'Reddit', 'X', 'WhatsApp', 'Facebook', 'Messenger', 'Instagram',
        'LinkedIn', 'Threads', 'TikTok', 'Telegram', 'Snapchat', 'Discord Web',
        'Pinterest', 'Bluesky',
    })

    SOCIAL_HOME_URLS = {
        'Reddit': 'https://www.reddit.com',
        'X': 'https://x.com',
        'WhatsApp': 'https://web.whatsapp.com',
        'Facebook': 'https://www.facebook.com',
        'Messenger': 'https://www.messenger.com',
        'Instagram': 'https://www.instagram.com',
        'LinkedIn': 'https://www.linkedin.com',
        'Threads': 'https://www.threads.com',
        'TikTok': 'https://www.tiktok.com',
        'Telegram': 'https://web.telegram.org',
        'Snapchat': 'https://web.snapchat.com',
        'Discord Web': 'https://discord.com/app',
        'Pinterest': 'https://www.pinterest.com',
        'Bluesky': 'https://bsky.app',
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
        if service in self.SOCIAL_SERVICES:
            return self._social_activity(browser_name, service, source='window')

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
        snapshot_service = str(snapshot.get('service', '') or '').strip()

        # Exact URL is authoritative. A stale content-script/service-worker label
        # from a previously focused tab must never override the current domain
        # (for example X leaking into a ChatGPT/Firefox activity).
        if exact_url:
            service = (
                self._configured_service(exact_url)
                or self._detect_service_from_url(exact_url)
                or ''
            )
        else:
            service = snapshot_service or self._detect_service(raw_title) or ''

        # Social/messaging titles and deep links routinely contain account names,
        # conversation names, profile IDs, post IDs, or message context. Never
        # forward those fields to Presence. Keep only a generic service identity
        # and a public homepage link, even when browser_url_mode is path/full.
        if service in self.SOCIAL_SERVICES:
            return self._social_activity(browser_name, service, source='companion')

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

    @classmethod
    def _social_activity(
        cls,
        browser_name: str,
        service: str,
        *,
        source: str,
    ) -> Dict[str, Any]:
        return {
            'type': 'browser',
            'browser_name': browser_name,
            'is_private': False,
            'page_title': f'Using {service}',
            'service': service,
            'url': cls.SOCIAL_HOME_URLS.get(service),
            'url_is_exact': False,
            'source': source,
            'social': True,
            'media': {},
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

    @staticmethod
    def _url_matches_marker(hostname: str, path: str, marker: str) -> bool:
        """Match a known service marker against URL structure, never query text."""
        marker = str(marker or '').strip().lower().lstrip('/')
        if not marker:
            return False
        marker_host, separator, marker_path = marker.partition('/')
        if '.' not in marker_host:
            return False
        if hostname != marker_host and not hostname.endswith('.' + marker_host):
            return False
        if not separator or not marker_path:
            return True
        expected_path = '/' + marker_path.rstrip('/')
        normalized_path = path.rstrip('/') or '/'
        return normalized_path == expected_path or normalized_path.startswith(expected_path + '/')

    @staticmethod
    def _marker_specificity(marker: str) -> tuple[int, int]:
        """Rank route-specific markers ahead of generic host-only markers."""
        normalized = str(marker or '').strip().lower().lstrip('/')
        _, separator, marker_path = normalized.partition('/')
        return (1 if separator and marker_path else 0, len(normalized))

    def _detect_service_from_url(self, raw_url: Any) -> Optional[str]:
        url = str(raw_url or '').strip()
        if not url:
            return None
        try:
            parsed = urllib.parse.urlsplit(url)
            hostname = (parsed.hostname or '').lower().rstrip('.')
            path = parsed.path.lower() or '/'
        except ValueError:
            return None
        if parsed.scheme.lower() not in {'http', 'https'} or not hostname:
            return None

        candidates = [
            (service, marker)
            for service, markers in self.SERVICE_URL_MARKERS.items()
            for marker in markers
        ]
        candidates.sort(key=lambda item: self._marker_specificity(item[1]), reverse=True)
        for service, marker in candidates:
            if self._url_matches_marker(hostname, path, marker):
                return service

        youtube_markers = self.config.get('rules.youtube_domains', []) or []
        if any(
            self._url_matches_marker(hostname, path, str(marker))
            for marker in youtube_markers
            if marker
        ):
            return 'YouTube'
        return None

    def _detect_service(self, *values: Any) -> Optional[str]:
        """Best-effort title fallback used only when no exact URL is available."""
        combined = ' '.join(str(value or '') for value in values).strip().lower()
        if not combined:
            return None

        # URL markers remain safe even if a caller passes a URL among the values.
        url_service = self._detect_service_from_url(combined)
        if url_service:
            return url_service

        # Match readable service names as words/phrases rather than substrings.
        # In particular, never classify an arbitrary title as X simply because
        # it contains the letter "x".
        for service in self.SERVICES:
            if len(service) < 3:
                continue
            pattern = rf'(?<!\w){re.escape(service.lower())}(?!\w)'
            if re.search(pattern, combined):
                return service

        # X/Twitter needs explicit markers because the one-letter brand cannot
        # be safely inferred from normal page-title text.
        if re.search(r'(?<!\w)twitter(?!\w)', combined) or 'x.com' in combined:
            return 'X'
        return None

    def _generate_url(self, service: Optional[str], title: str) -> Optional[str]:
        """Generate a search/home URL only when the companion has no exact tab URL."""
        if not service:
            return None

        social_url = self.SOCIAL_HOME_URLS.get(service)
        if social_url:
            return social_url

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
        if service == 'ChatGPT':
            return 'https://chatgpt.com'
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
