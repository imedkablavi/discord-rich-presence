"""Media playback detection for Windows using Windows Media Control."""

import asyncio
import logging
from typing import Any, Dict, Optional

from config import Config

try:
    from winsdk.windows.media.control import \
        GlobalSystemMediaTransportControlsSessionManager as MediaManager
    WINDOWS_MEDIA_AVAILABLE = True
except ImportError:
    MediaManager = None
    WINDOWS_MEDIA_AVAILABLE = False


class WindowsMediaDetector:
    """Detect media playback via Windows Media Control."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        if not WINDOWS_MEDIA_AVAILABLE:
            self.logger.warning('Windows Media Control not available')
            self.logger.warning('Install with: pip install winsdk')
        else:
            try:
                if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as exc:
                self.logger.debug('Could not set Windows Proactor event loop policy: %s', exc)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run one bounded async media query and always close its event-loop resources."""
        if not self.config.get('rules.enabled_detectors.media', True):
            return None
        if not WINDOWS_MEDIA_AVAILABLE:
            return None

        try:
            # asyncio.run owns the loop lifecycle and closes it even when the
            # WinRT coroutine raises. The previous manual loop setup could leave
            # a loop open/current on exceptional paths during long-running use.
            return asyncio.run(self._detect_async())
        except Exception as exc:
            self.logger.debug('Error detecting Windows media: %s', exc)
            return None

    async def _detect_async(self) -> Optional[Dict[str, Any]]:
        """Async detection of media playback."""
        try:
            manager = await MediaManager.request_async()
            if not manager:
                return None

            session = manager.get_current_session()
            if not session:
                return None

            playback_info = session.get_playback_info()
            if not playback_info:
                return None
            playback_status = playback_info.playback_status

            from winsdk.windows.media.control import \
                GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus

            if playback_status not in [PlaybackStatus.PLAYING, PlaybackStatus.PAUSED]:
                return None

            media_properties = await session.try_get_media_properties_async()
            if not media_properties:
                return None

            title = media_properties.title or 'Unknown'
            artist = media_properties.artist or ''

            timeline = session.get_timeline_properties()
            position = 0
            duration = 0
            if timeline:
                try:
                    if hasattr(timeline.position, 'total_seconds'):
                        position = int(timeline.position.total_seconds())
                    elif hasattr(timeline.position, 'duration'):
                        position = int(timeline.position.duration / 10000000)
                    if hasattr(timeline.end_time, 'total_seconds'):
                        duration = int(timeline.end_time.total_seconds())
                    elif hasattr(timeline.end_time, 'duration'):
                        duration = int(timeline.end_time.duration / 10000000)
                except Exception as exc:
                    self.logger.debug('Timeline parse error: %s', exc)
                    position = 0
                    duration = 0

            source_app = session.source_app_user_model_id or 'Media Player'
            player_name = self._extract_player_name(source_app)
            full_title = title if not artist or artist == title else f'{artist} - {title}'

            return {
                'type': 'media',
                'player': player_name,
                'title': full_title,
                'is_playing': playback_status == PlaybackStatus.PLAYING,
                'position': max(0, position),
                'duration': max(0, duration),
            }
        except Exception as exc:
            self.logger.debug('Error in async media detection: %s', exc)
            return None

    def _extract_player_name(self, source_app: str) -> str:
        """Extract a readable player name from a Windows app ID."""
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

        if '!' in source_app:
            parts = source_app.split('!')
            if len(parts) > 1:
                return parts[-1].replace('Microsoft.', '').replace('_', ' ')

        return 'Media Player'

    @staticmethod
    def is_available() -> bool:
        """Check whether Windows media detection dependencies are available."""
        return WINDOWS_MEDIA_AVAILABLE
