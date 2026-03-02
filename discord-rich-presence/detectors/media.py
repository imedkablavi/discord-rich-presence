"""
Media playback detection via MPRIS (D-Bus)
"""

import platform
import logging
from typing import Optional, Dict, Any
from config import Config


class MediaDetector:
    """Detects media playback via MPRIS interface"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform.system().lower()
        self.dbus_available = False
        self.windows_media_available = False
        self.bus = None
        
        if self.platform_name == 'windows':
            # Try Windows media detector
            try:
                from .media_windows import WindowsMediaDetector
                self.windows_detector = WindowsMediaDetector(config)
                if self.windows_detector.is_available():
                    self.windows_media_available = True
                    self.logger.info("Windows Media Control support enabled")
            except ImportError:
                self.logger.warning("Windows media detection not available")
                self.windows_detector = None
        else:
            # Try to import D-Bus libraries for Linux
            try:
                import pydbus
                self.pydbus = pydbus
                self.bus = pydbus.SessionBus()
                self.dbus_available = True
                self.logger.info("D-Bus/MPRIS support enabled")
            except ImportError:
                self.logger.warning("pydbus not available, media detection disabled")
                self.logger.warning("Install with: pip3 install pydbus")
            except Exception as e:
                self.logger.warning(f"Failed to initialize D-Bus: {e}")
    
    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect media playback via MPRIS or Windows Media Control"""
        if not self.config.get('rules.enabled_detectors.media', True):
            return None
        
        # Use Windows detector if on Windows
        if self.platform_name == 'windows':
            if self.windows_media_available and hasattr(self, 'windows_detector'):
                return self.windows_detector.detect(window_info)
            return None
        
        # Use MPRIS on Linux
        if not self.dbus_available:
            return None
        
        try:
            # Get list of MPRIS players
            players = self._get_mpris_players()
            
            if not players:
                return None
            
            # Check each player for active playback
            for player_name in players:
                activity = self._get_player_activity(player_name)
                if activity and activity.get('is_playing'):
                    return activity
            
            # If no player is playing, return the first paused one
            for player_name in players:
                activity = self._get_player_activity(player_name)
                if activity:
                    return activity
        
        except Exception as e:
            self.logger.debug(f"Error detecting media: {e}")
        
        return None
    
    def _get_mpris_players(self) -> list:
        """Get list of available MPRIS players"""
        try:
            dbus_obj = self.bus.get('org.freedesktop.DBus', '/org/freedesktop/DBus')
            names = dbus_obj.ListNames()
            
            # Filter for MPRIS players
            players = [name for name in names if name.startswith('org.mpris.MediaPlayer2.')]
            return players
        
        except Exception as e:
            self.logger.debug(f"Failed to list MPRIS players: {e}")
            return []
    
    def _get_player_activity(self, player_name: str) -> Optional[Dict[str, Any]]:
        """Get activity information from an MPRIS player"""
        try:
            # Get player interface
            player = self.bus.get(player_name, '/org/mpris/MediaPlayer2')
            
            # Get playback status
            playback_status = player.PlaybackStatus
            
            # Only return if playing or paused
            if playback_status not in ['Playing', 'Paused']:
                return None
            
            # Get metadata
            metadata = player.Metadata
            
            # Extract information
            title = metadata.get('xesam:title', 'Unknown')
            artist = metadata.get('xesam:artist', [])
            album = metadata.get('xesam:album', '')
            
            # Artist can be a list
            if isinstance(artist, list) and artist:
                artist = artist[0]
            
            # Get position and duration (in microseconds)
            position = player.Position // 1000000 if hasattr(player, 'Position') else 0
            duration = metadata.get('mpris:length', 0) // 1000000
            
            # Extract player name
            player_display_name = player_name.replace('org.mpris.MediaPlayer2.', '')
            
            # Capitalize common player names
            player_names = {
                'vlc': 'VLC',
                'spotify': 'Spotify',
                'chromium': 'Chromium',
                'firefox': 'Firefox',
                'mpv': 'MPV',
                'rhythmbox': 'Rhythmbox',
                'clementine': 'Clementine',
            }
            
            for key, name in player_names.items():
                if key in player_display_name.lower():
                    player_display_name = name
                    break
            
            # Build full title
            full_title = title
            if artist and artist != title:
                full_title = f"{artist} - {title}"
            
            return {
                'type': 'media',
                'player': player_display_name,
                'title': full_title,
                'is_playing': playback_status == 'Playing',
                'position': int(position),
                'duration': int(duration)
            }
        
        except Exception as e:
            self.logger.debug(f"Failed to get player activity for {player_name}: {e}")
            return None
