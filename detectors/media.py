"""Media playback detection for Windows Media Control and Linux MPRIS."""

import logging
import platform
from typing import Optional, Dict, Any

from config import Config


class MediaDetector:
    """Detect active media playback using platform-native session APIs."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform.system().lower()
        self.dbus_available = False
        self.windows_media_available = False
        self.bus = None
        self.windows_detector = None

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
            try:
                import pydbus
                self.bus = pydbus.SessionBus()
                self.dbus_available = True
                self.logger.info('D-Bus/MPRIS support enabled')
            except ImportError:
                self.logger.warning('pydbus unavailable; Linux media detection disabled')
            except Exception as e:
                self.logger.warning('Failed to initialize D-Bus/MPRIS: %s', e)
        else:
            self.logger.debug('Media session detection is unsupported on %s', self.platform_name)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.config.get('rules.enabled_detectors.media', True):
            return None

        if self.platform_name == 'windows':
            if self.windows_media_available and self.windows_detector:
                return self.windows_detector.detect(window_info)
            return None

        if self.platform_name != 'linux' or not self.dbus_available:
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
                if activity.get('is_playing'):
                    return activity
                if paused is None:
                    paused = activity
            return paused
        except Exception as e:
            self.logger.debug('Error detecting MPRIS media: %s', e)
            return None

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

            try:
                position = max(0, int(player.Position // 1_000_000))
            except Exception:
                position = 0
            try:
                duration = max(0, int((metadata.get('mpris:length', 0) or 0) // 1_000_000))
            except (TypeError, ValueError):
                duration = 0

            player_display_name = player_name.replace('org.mpris.MediaPlayer2.', '')
            player_names = {
                'vlc': 'VLC', 'spotify': 'Spotify', 'chromium': 'Chromium',
                'firefox': 'Firefox', 'mpv': 'MPV', 'rhythmbox': 'Rhythmbox',
                'clementine': 'Clementine',
            }
            lower_name = player_display_name.lower()
            for key, name in player_names.items():
                if key in lower_name:
                    player_display_name = name
                    break

            full_title = f'{artist} - {title}' if artist and artist != title else title
            return {
                'type': 'media',
                'player': player_display_name,
                'title': full_title,
                'is_playing': playback_status == 'Playing',
                'position': position,
                'duration': duration,
            }
        except Exception as e:
            self.logger.debug('Failed to get MPRIS activity for %s: %s', player_name, e)
            return None
