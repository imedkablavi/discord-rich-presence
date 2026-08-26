"""Media playback detection for Windows, Linux playerctl/MPRIS, and Browser Companion."""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import time
from typing import Any, Dict, Optional

from browser_companion import get_browser_companion
from config import Config


class MediaDetector:
    """Detect active media playback using bounded, stateless Linux probes."""

    SERVICES = (
        'YouTube Music', 'YouTube', 'Netflix', 'Prime Video', 'Disney+', 'Hulu',
        'SoundCloud', 'Spotify', 'Twitch', 'GitHub'
    )

    SERVICE_URL_MARKERS = {
        'YouTube Music': ('music.youtube.com',),
        'YouTube': ('youtube.com', 'youtu.be', 'ytimg.com', 'googlevideo.com'),
        'Netflix': ('netflix.com',),
        'Prime Video': ('primevideo.com', 'amazon.com/gp/video', 'amazon.com/video'),
        'Disney+': ('disneyplus.com',),
        'Hulu': ('hulu.com',),
        'SoundCloud': ('soundcloud.com',),
        'Spotify': ('spotify.com', 'open.spotify.com'),
        'Twitch': ('twitch.tv',),
        'GitHub': ('github.com',),
    }

    SERVICE_CACHE_TTL_SECS = 6 * 60 * 60
    SERVICE_CACHE_MAX_ENTRIES = 50

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform.system().lower()
        self.playerctl_available = False
        self.windows_media_available = False
        self.windows_detector = None
        self._service_cache: Dict[str, Dict[str, Any]] = {}
        # BrowserDetector normally starts the shared bridge first. Keeping
        # start=False here avoids duplicate bind attempts in isolated tests.
        self.companion = get_browser_companion(config, start=False)

        if self.platform_name == 'windows':
            try:
                from .media_windows import WindowsMediaDetector
                self.windows_detector = WindowsMediaDetector(config)
                if self.windows_detector.is_available():
                    self.windows_media_available = True
                    self.logger.info('Windows Media Control support enabled')
            except ImportError as exc:
                self.logger.warning('Windows media detection unavailable: %s', exc)
        elif self.platform_name == 'linux':
            # Keep Linux MPRIS polling stateless. Repeated pydbus proxy creation
            # caused real-device RSS growth over long sessions. playerctl is a
            # short-lived bounded subprocess and Browser Companion covers exact
            # browser media without retaining GLib/D-Bus proxy objects.
            self.playerctl_available = shutil.which('playerctl') is not None
            if self.playerctl_available:
                self.logger.info('playerctl/MPRIS support enabled')
            elif not self.companion:
                self.logger.warning(
                    'Linux native media detection unavailable; install playerctl '
                    'or use Browser Companion'
                )
        else:
            self.logger.debug('Native media session detection is unsupported on %s', self.platform_name)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.config.get('rules.enabled_detectors.media', True):
            return None

        companion_activity = self._detect_companion_media()
        if companion_activity:
            return companion_activity

        if self.platform_name == 'windows':
            if self.windows_media_available and self.windows_detector:
                activity = self.windows_detector.detect(window_info)
                return self._enrich_with_foreground_service(activity, window_info)
            return None

        if self.platform_name != 'linux' or not self.playerctl_available:
            return None

        activity = self._detect_playerctl()
        if activity:
            return self._enrich_with_foreground_service(activity, window_info)
        return None

    def _detect_companion_media(self) -> Optional[Dict[str, Any]]:
        if not self.companion:
            return None
        snapshot = self.companion.latest_media()
        if not snapshot:
            return None
        media = snapshot.get('media') if isinstance(snapshot.get('media'), dict) else {}
        if not bool(media.get('playing')):
            return None

        player = str(snapshot.get('browser', '') or 'Browser')
        service = str(snapshot.get('service', '') or '')
        if not service:
            service = self._detect_service(snapshot.get('url'), snapshot.get('title')) or ''

        media_title = str(media.get('title', '') or snapshot.get('title', '') or 'Media')
        artist = str(media.get('artist', '') or '')
        full_title = f'{artist} - {media_title}' if artist and artist != media_title else media_title
        try:
            position = max(0, int(float(media.get('position', 0) or 0)))
            duration = max(0, int(float(media.get('duration', 0) or 0)))
        except (TypeError, ValueError):
            position = duration = 0

        activity: Dict[str, Any] = {
            'type': 'media',
            'player': player,
            'title': full_title,
            'is_playing': True,
            'position': position,
            'duration': duration,
            'source': 'companion',
            'tab_focused': bool(snapshot.get('focused')),
        }
        if service:
            activity['service'] = service
            self._remember_service(activity, service)
        return activity

    def _detect_playerctl(self) -> Optional[Dict[str, Any]]:
        """Read all MPRIS players with one bounded playerctl process."""
        separator = '\x1f'
        fmt = separator.join((
            '{{playerName}}', '{{status}}', '{{artist}}', '{{title}}',
            '{{position}}', '{{mpris:length}}', '{{xesam:url}}', '{{mpris:artUrl}}',
        ))
        try:
            result = subprocess.run(
                ['playerctl', '--all-players', 'metadata', '--format', fmt],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            # A pathological MPRIS implementation must not make us retain or
            # parse unbounded metadata returned through stdout/stderr.
            stdout = (result.stdout or '')[:256 * 1024]
            if result.returncode != 0 and not stdout.strip():
                return None

            paused = None
            for line in stdout.splitlines()[:256]:
                parts = line.split(separator)
                if len(parts) != 8:
                    continue
                (
                    player, status, artist, title,
                    position_raw, duration_raw, media_url, art_url,
                ) = parts
                status = status.strip()
                if status not in {'Playing', 'Paused'}:
                    continue

                position = self._microseconds_to_seconds(position_raw)
                duration = self._microseconds_to_seconds(duration_raw)
                display_name = self._display_player_name(player)
                title = title.strip()[:300] or 'Unknown'
                artist = artist.strip()[:200]
                media_url = media_url.strip()[:1024]
                art_url = art_url.strip()[:1024]
                full_title = f'{artist} - {title}' if artist and artist != title else title
                activity = {
                    'type': 'media',
                    'player': display_name,
                    'title': full_title,
                    'is_playing': status == 'Playing',
                    'position': position,
                    'duration': duration,
                    'source': 'mpris',
                }
                service = self._detect_service(media_url, art_url, title, full_title)
                if service:
                    activity['service'] = service
                if activity['is_playing']:
                    return activity
                if paused is None:
                    paused = activity
            return paused
        except subprocess.TimeoutExpired:
            self.logger.debug('playerctl timed out')
        except Exception as exc:
            self.logger.debug('playerctl media detection failed: %s', exc)
        return None

    def _enrich_with_foreground_service(
        self,
        activity: Optional[Dict[str, Any]],
        window_info: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not activity:
            return activity

        existing_service = str(activity.get('service', '') or '')
        if existing_service:
            self._remember_service(activity, existing_service)
            return activity

        player = str(activity.get('player', '')).lower()
        app_name = str((window_info or {}).get('app_name', '')).lower()
        title = str((window_info or {}).get('title', ''))

        browser_aliases = {
            'brave': ('brave',),
            'chrome': ('chrome', 'google-chrome'),
            'chromium': ('chromium',),
            'firefox': ('firefox',),
            'edge': ('edge', 'msedge'),
            'opera': ('opera',),
            'vivaldi': ('vivaldi',),
        }
        matched_browser = any(
            browser in player and any(alias in app_name for alias in aliases)
            for browser, aliases in browser_aliases.items()
        )

        if matched_browser:
            service = self._detect_service(title)
            if service:
                enriched = activity.copy()
                enriched['service'] = service
                self._remember_service(enriched, service)
                return enriched

        cached_service = self._cached_service(activity)
        if cached_service:
            enriched = activity.copy()
            enriched['service'] = cached_service
            return enriched
        return activity

    def _service_cache_key(self, activity: Dict[str, Any]) -> str:
        player = str(activity.get('player', '') or '').strip().lower()
        title = str(activity.get('title', '') or '').strip().lower()
        return f'{player}\0{title}' if player and title else ''

    def _remember_service(self, activity: Dict[str, Any], service: str) -> None:
        key = self._service_cache_key(activity)
        if not key or not service:
            return
        now = time.monotonic()
        self._service_cache[key] = {'service': service, 'seen_at': now}
        self._prune_service_cache(now)

    def _cached_service(self, activity: Dict[str, Any]) -> Optional[str]:
        key = self._service_cache_key(activity)
        if not key:
            return None
        now = time.monotonic()
        record = self._service_cache.get(key)
        if not record:
            self._prune_service_cache(now)
            return None
        if now - float(record.get('seen_at', 0)) > self.SERVICE_CACHE_TTL_SECS:
            self._service_cache.pop(key, None)
            return None
        return str(record.get('service', '') or '') or None

    def _prune_service_cache(self, now: Optional[float] = None) -> None:
        current = time.monotonic() if now is None else now
        expired = [
            key for key, record in self._service_cache.items()
            if current - float(record.get('seen_at', 0)) > self.SERVICE_CACHE_TTL_SECS
        ]
        for key in expired:
            self._service_cache.pop(key, None)
        if len(self._service_cache) > self.SERVICE_CACHE_MAX_ENTRIES:
            oldest = sorted(
                self._service_cache,
                key=lambda key: float(self._service_cache[key].get('seen_at', 0)),
            )[:-self.SERVICE_CACHE_MAX_ENTRIES]
            for key in oldest:
                self._service_cache.pop(key, None)

    def _detect_service(self, *values: Any) -> Optional[str]:
        combined = ' '.join(str(value or '') for value in values).lower()
        if not combined:
            return None

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

    @staticmethod
    def _microseconds_to_seconds(value: Any) -> int:
        try:
            return max(0, int(float(str(value).strip() or '0') / 1_000_000))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _display_player_name(player_name: str) -> str:
        raw = str(player_name or 'Media Player').strip()
        lower_name = raw.lower()
        player_names = {
            'vlc': 'VLC', 'spotify': 'Spotify', 'chromium': 'Chromium',
            'chrome': 'Chrome', 'firefox': 'Firefox', 'mpv': 'MPV',
            'rhythmbox': 'Rhythmbox', 'clementine': 'Clementine',
            'brave': 'Brave', 'edge': 'Edge', 'msedge': 'Edge',
            'opera': 'Opera', 'vivaldi': 'Vivaldi',
        }
        for key, name in player_names.items():
            if key in lower_name:
                return name
        return raw or 'Media Player'
