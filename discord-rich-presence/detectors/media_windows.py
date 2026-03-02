"""
Media playback detection for Windows using Windows Media Control
"""

import logging
from typing import Optional, Dict, Any
from config import Config

try:
    # Try to import Windows Runtime for media control
    import asyncio
    from winsdk.windows.media.control import \
        GlobalSystemMediaTransportControlsSessionManager as MediaManager
    WINDOWS_MEDIA_AVAILABLE = True
except ImportError:
    WINDOWS_MEDIA_AVAILABLE = False


class WindowsMediaDetector:
    """Detects media playback via Windows Media Control"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if not WINDOWS_MEDIA_AVAILABLE:
            self.logger.warning("Windows Media Control not available")
            self.logger.warning("Install with: pip install winsdk")
        else:
            try:
                # Use Proactor policy once to avoid repeated loop setup overhead
                if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
    
    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect media playback via Windows Media Control"""
        if not self.config.get('rules.enabled_detectors.media', True):
            return None
        
        if not WINDOWS_MEDIA_AVAILABLE:
            return None
        
        try:
            # Run async detection in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._detect_async())
            loop.close()
            return result
        except Exception as e:
            self.logger.debug(f"Error detecting Windows media: {e}")
            return None
    
    async def _detect_async(self) -> Optional[Dict[str, Any]]:
        """Async detection of media playback"""
        try:
            # Get media session manager
            manager = await MediaManager.request_async()
            
            if not manager:
                return None
            
            # Get current session
            session = manager.get_current_session()
            
            if not session:
                return None
            
            # Get playback info
            playback_info = session.get_playback_info()
            if not playback_info:
                return None
            
            playback_status = playback_info.playback_status
            
            # Only return if playing or paused
            from winsdk.windows.media.control import \
                GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
            
            if playback_status not in [PlaybackStatus.PLAYING, PlaybackStatus.PAUSED]:
                return None
            
            # Get media properties
            media_properties = await session.try_get_media_properties_async()
            
            if not media_properties:
                return None
            
            # Extract information
            title = media_properties.title or "Unknown"
            artist = media_properties.artist or ""
            album = media_properties.album_title or ""
            
            # Get timeline properties for position/duration
            timeline = session.get_timeline_properties()
            position = 0
            duration = 0
            
            if timeline:
                try:
                    # winsdk returns Python timedelta on some builds; prefer total_seconds
                    if hasattr(timeline.position, 'total_seconds'):
                        position = int(timeline.position.total_seconds())
                    elif hasattr(timeline.position, 'duration'):
                        position = int(timeline.position.duration / 10000000)
                    if hasattr(timeline.end_time, 'total_seconds'):
                        duration = int(timeline.end_time.total_seconds())
                    elif hasattr(timeline.end_time, 'duration'):
                        duration = int(timeline.end_time.duration / 10000000)
                except Exception as _e:
                    self.logger.debug(f"Timeline parse error: {_e}")
                    position = 0
                    duration = 0
            
            # Get source app
            source_app = session.source_app_user_model_id or "Media Player"
            
            # Extract readable app name
            player_name = self._extract_player_name(source_app)
            
            # Build full title
            full_title = title
            if artist and artist != title:
                full_title = f"{artist} - {title}"
            
            return {
                'type': 'media',
                'player': player_name,
                'title': full_title,
                'is_playing': playback_status == PlaybackStatus.PLAYING,
                'position': position,
                'duration': duration
            }
            
        except Exception as e:
            self.logger.debug(f"Error in async media detection: {e}")
            return None
    
    def _extract_player_name(self, source_app: str) -> str:
        """Extract readable player name from source app ID"""
        # Common Windows app IDs
        player_map = {
            'spotify': 'Spotify',
            'vlc': 'VLC',
            'chrome': 'Chrome',
            'msedge': 'Edge',
            'firefox': 'Firefox',
            'wmplayer': 'Windows Media Player',
            'groove': 'Groove Music',
            'itunes': 'iTunes',
            'foobar': 'foobar2000',
            'aimp': 'AIMP',
            'musicbee': 'MusicBee',
        }
        
        source_lower = source_app.lower()
        for key, name in player_map.items():
            if key in source_lower:
                return name
        
        # Try to extract from app ID (e.g., "Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic")
        if '!' in source_app:
            parts = source_app.split('!')
            if len(parts) > 1:
                app_name = parts[-1].replace('Microsoft.', '').replace('_', ' ')
                return app_name
        
        return "Media Player"
    
    @staticmethod
    def is_available() -> bool:
        """Check if Windows media detection is available"""
        return WINDOWS_MEDIA_AVAILABLE
