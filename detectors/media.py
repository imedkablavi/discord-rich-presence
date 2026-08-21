"""Media playback detection for Windows Media Control, Linux MPRIS, and browser companion."""

import logging
import platform
import shutil
import subprocess
import time
from typing import Optional, Dict, Any

from browser_companion import get_browser_companion
from config import Config


class MediaDetector:
    """Detect active media playback using the most accurate available source."""

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
        self.dbus_available = False
        self.playerctl_available = False
        self.windows_media_available = False
        self.bus = None
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
            except ImportError as e:
                self.logger.warning('Windows media detection unavailable: %s', e)
        elif self.platform_name == 'linux':
            self.playerctl_available = shutil.which('playerctl') is not None
            if self.playerctl_available:
                self.logger.info('playerctl/MPRIS support enabled')
            try:
                import pydbus
                self.bus = pydbus.SessionBus()
                self.dbus_available = True
                if not self.playerctl_available:
                    self.logger.info('D-Bus/MPRIS support enabled')
            except ImportError:
                if not self.playerctl_available and not self.companion:
                    self.logger.warning(
                        'Linux media detection unavailable; install playerctl or PyGObject/pydbus'
                    )
            except Exception as e:
                if not self.playerctl_available and not self.companion:
                    self.logger.warning('Failed to initialize D-Bus/MPRIS: %s', e)
        else:
            self.logger.debug('Native media session detection is unsupported on %s', self.platform_name)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.config.get('rules.enabled_detectors.media', True):
            return None

        # The companion knows the exact site/tab and HTMLMediaElement timeline,
        # so it is more precise than browser MPRIS sessions when available.
        companion_activity = self._detect_companion_media()
        if companion_activity:
            return companion_activity

        if self.platform_name == 'windows':
            if self.windows_media_available and self.windows_detector:
                activity = self.windows_detector.detect(window_info)
                return self._enrich_with_foreground_service(activity, window_info)
            return None

        if self.platform_name != 'linux':
            return None

        if self.playerctl_available:
            activity = self._detect_playerctl()
            if activity:
                return self._enrich_with_foreground_service(activity, window_info)

        if not self.dbus_available:
            return None

        try:
            players = self._get_mpris_players()
            if not players:
                return None

            paused = None
            for player_name in players:
                activity = self._get_player_activity(player_name)
                if not activity:
                    continue
                activity = self._enrich_with_foreground_service(activity, window_info)
                if activity.get('is_playing'):
                    return activity
                if paused is None:
                    paused = activity
            return paused
        except Exception as e:
            self.logger.debug('Error detecting MPRIS media: %s', e)
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
        """Read all MPRIS players with one playerctl process and prefer active playback."""
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
            if result.returncode != 0 and not result.stdout.strip():
                return None

            paused = None
            for line in result.stdout.splitlines():
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
                title = title.strip() or 'Unknown'
                artist = artist.strip()
                media_url = media_url.strip()
                art_url = art_url.strip()
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
        except Exception as e:
            self.logger.debug('playerctl media detection failed: %s', e)
        return None

    def _enrich_with_foreground_service(
        self,
        activity: Optional[Dict[str, Any]],
        window_info: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Attach only verified web-service metadata to browser-backed media."""
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

    def _get_mpris_players(self) -> list[str]:
        try:
            if self.bus is None:
                return []
            dbus_obj = self.bus.get('org.freedesktop.DBus', '/org/freedesktop/DBus')
            names = dbus_obj.ListNames()
            return [name for name in names if name.startswith('org.mpris.MediaPlayer2.')]
        except Exception as e:
            self.logger.debug('Failed to list MPRIS players: %s', e)
            return []

    def _get_player_activity(self, player_name: str) -> Optional[Dict[str, Any]]:
        try:
            if self.bus is None:
                return None
            player = self.bus.get(player_name, '/org/mpris/MediaPlayer2')
            playback_status = player.PlaybackStatus
            if playback_status not in {'Playing', 'Paused'}:
                return None

            metadata = player.Metadata or {}
            title = str(metadata.get('xesam:title', 'Unknown') or 'Unknown')
            artist = metadata.get('xesam:artist', [])
            if isinstance(artist, (list, tuple)):
                artist = artist[0] if artist else ''
            artist = str(artist or '')
            media_url = str(metadata.get('xesam:url', '') or '')
            art_url = str(metadata.get('mpris:artUrl', '') or '')

            try:
                position = max(0, int(player.Position // 1_000_000))
            except Exception:
                position = 0
            try:
                duration = max(0, int((metadata.get('mpris:length', 0) or 0) // 1_000_000))
            except (TypeError, ValueError):
                duration = 0

            player_display_name = self._display_player_name(
                player_name.replace('org.mpris.MediaPlayer2.', '')
            )
            full_title = f'{artist} - {title}' if artist and artist != title else title
            activity = {
                'type': 'media',
                'player': player_display_name,
                'title': full_title,
                'is_playing': playback_status == 'Playing',
                'position': position,
                'duration': duration,
                'source': 'mpris',
            }
            service = self._detect_service(media_url, art_url, title, full_title)
            if service:
                activity['service'] = service
            return activity
        except Exception as e:
            self.logger.debug('Failed to get MPRIS activity for %s: %s', player_name, e)
            return None
