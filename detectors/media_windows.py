import logging
import time
from typing import Optional, Dict, Any
from config import Config
from core.activity_model import ActivityState

try:
    import asyncio
    from winsdk.windows.media.control import \
        GlobalSystemMediaTransportControlsSessionManager as MediaManager
    from winsdk.windows.media.control import \
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
    WINDOWS_MEDIA_AVAILABLE = True
except ImportError:
    WINDOWS_MEDIA_AVAILABLE = False


class WindowsMediaDetector:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if WINDOWS_MEDIA_AVAILABLE:
            try:
                if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass

    def detect(self, window_info: Dict[str, Any]) -> Optional[ActivityState]:
        if not self.config.get('rules.enabled_detectors.media', True):
            return None
            
        if not WINDOWS_MEDIA_AVAILABLE:
            return None
            
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._detect_async())
            loop.close()
            return result
        except Exception as e:
            self.logger.debug(f"Error detecting Windows media: {e}")
            return None

    async def _detect_async(self) -> Optional[ActivityState]:
        try:
            manager = await MediaManager.request_async()
            if not manager: return None
            
            session = manager.get_current_session()
            if not session: return None
            
            playback_info = session.get_playback_info()
            if not playback_info: return None
            
            status = playback_info.playback_status
            if status not in [PlaybackStatus.PLAYING, PlaybackStatus.PAUSED]:
                return None
                
            props = await session.try_get_media_properties_async()
            if not props: return None
            
            title = props.title or "Unknown"
            artist = props.artist or ""
            
            full_title = f"{artist} - {title}" if artist and artist != title else title
            
            source_app = session.source_app_user_model_id or "Media Player"
            player_name = self._parse_player_name(source_app)
            
            large_image = self.config.get(f"images.apps.{player_name.lower().replace(' ', '')}", 'media')
            
            return ActivityState(
                type="media",
                details=f"Listening: {full_title}",
                state=f"{player_name} ({'Playing' if status == PlaybackStatus.PLAYING else 'Paused'})",
                large_image=large_image,
                large_text=player_name,
                start_time=int(time.time()) if status == PlaybackStatus.PLAYING else None
            )
            
        except Exception:
            return None

    def _parse_player_name(self, source_app: str) -> str:
        player_map = {
            'spotify': 'Spotify',
            'vlc': 'VLC',
            'chrome': 'Chrome',
            'msedge': 'Edge',
            'firefox': 'Firefox',
            'wmplayer': 'Windows Media Player',
            'itunes': 'iTunes',
        }
        low = source_app.lower()
        for k, v in player_map.items():
            if k in low: return v
            
        if '!' in source_app:
            parts = source_app.split('!')
            if len(parts) > 1:
                return parts[-1].replace('Microsoft.', '').replace('_', ' ')
        return "Media Player"

    @staticmethod
    def is_available() -> bool:
        return WINDOWS_MEDIA_AVAILABLE
