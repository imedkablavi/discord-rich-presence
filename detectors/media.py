import platform
import logging
import time
from typing import Optional, Dict, Any
from config import Config
from core.activity_model import ActivityState

class MediaDetector:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform.system().lower()
        self.dbus_available = False
        self.windows_media_available = False
        self.bus = None
        
        if self.platform_name == 'windows':
            try:
                from .media_windows import WindowsMediaDetector
                self.windows_detector = WindowsMediaDetector(config)
                if self.windows_detector.is_available():
                    self.windows_media_available = True
            except ImportError:
                self.windows_detector = None
        else:
            try:
                import pydbus
                self.pydbus = pydbus
                self.bus = pydbus.SessionBus()
                self.dbus_available = True
            except ImportError:
                pass
            except Exception:
                pass
    
    def detect(self, window_info: Dict[str, Any]) -> Optional[ActivityState]:
        if not self.config.get('rules.enabled_detectors.media', True):
            return None
        
        if self.platform_name == 'windows':
            if self.windows_media_available and hasattr(self, 'windows_detector'):
                return self.windows_detector.detect(window_info)
            return None
        
        if not self.dbus_available:
            return None
        
        try:
            players = self._get_mpris_players()
            if not players: return None
            
            for player_name in players:
                activity = self._get_player_activity(player_name)
                if activity and activity.get('is_playing'):
                    return self._build_state(activity)
            
            for player_name in players:
                activity = self._get_player_activity(player_name)
                if activity:
                    return self._build_state(activity)
        except Exception:
            pass
        return None

    def _build_state(self, activity: dict) -> ActivityState:
        player = activity['player']
        title = activity['title']
        is_playing = activity['is_playing']
        
        large_image = self.config.get(f"images.apps.{player.lower().replace(' ', '')}", 'media')
        
        return ActivityState(
            type="media",
            details=f"Listening: {title}",
            state=f"{player} ({'Playing' if is_playing else 'Paused'})",
            large_image=large_image,
            large_text=player,
            start_time=int(time.time()) if is_playing else None
        )

    def _get_mpris_players(self) -> list:
        try:
            dbus_obj = self.bus.get('org.freedesktop.DBus', '/org/freedesktop/DBus')
            names = dbus_obj.ListNames()
            return [name for name in names if name.startswith('org.mpris.MediaPlayer2.')]
        except Exception:
            return []
    
    def _get_player_activity(self, player_name: str) -> Optional[Dict[str, Any]]:
        try:
            player = self.bus.get(player_name, '/org/mpris/MediaPlayer2')
            playback_status = player.PlaybackStatus
            if playback_status not in ['Playing', 'Paused']: return None
            
            metadata = player.Metadata
            title = metadata.get('xesam:title', 'Unknown')
            artist = metadata.get('xesam:artist', [])
            if isinstance(artist, list) and artist: artist = artist[0]
            
            player_display_name = player_name.replace('org.mpris.MediaPlayer2.', '')
            for key, name in {'vlc': 'VLC', 'spotify': 'Spotify', 'chromium': 'Chromium', 'firefox': 'Firefox'}.items():
                if key in player_display_name.lower():
                    player_display_name = name
                    break
            
            full_title = f"{artist} - {title}" if artist and artist != title else title
            return {
                'player': player_display_name,
                'title': full_title,
                'is_playing': playback_status == 'Playing'
            }
        except Exception:
            return None
