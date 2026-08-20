"""Discord Rich Presence payload builder."""

import time
import urllib.parse
from typing import Dict, Any, Optional

from pypresence.types import ActivityType

from config import Config
from privacy import PrivacyRedactor


class PresenceBuilder:
    """Build Discord Rich Presence payloads from normalized activity data."""

    FRIENDLY_APP_NAMES = {
        'org.kde.konsole': 'Konsole',
        'org.kde.dolphin': 'Dolphin',
        'org.kde.kate': 'Kate',
        'org.kde.okular': 'Okular',
        'org.kde.discover': 'Discover',
        'org.kde.systemsettings': 'System Settings',
    }

    def __init__(self, config: Config):
        self.config = config
        self.redactor = PrivacyRedactor(config)
        self.activity_start_times: Dict[str, int] = {}
        self.media_timelines: Dict[str, Dict[str, int]] = {}

    def reload(self):
        """Refresh cached privacy state after a config hot reload."""
        self.redactor.reload()

    def build(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        activity_type = activity.get('type', 'application')
        activity = self.redactor.redact_activity(activity)

        if activity_type == 'media':
            return self._build_media(activity)
        if activity_type == 'terminal':
            return self._build_terminal(activity)
        if activity_type == 'coding':
            return self._build_coding(activity)
        if activity_type == 'browser':
            return self._build_browser(activity)
        if activity_type == 'gaming':
            return self._build_gaming(activity)
        return self._build_application(activity)

    def _build_media(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        title = str(activity.get('title', 'Unknown'))
        player = str(activity.get('player', 'Media Player'))
        is_playing = bool(activity.get('is_playing', False))
        position = max(0, int(activity.get('position', 0) or 0))
        duration = max(0, int(activity.get('duration', 0) or 0))

        details = (
            f"{'Listening' if player.lower() == 'spotify' else 'Watching'} · {title}"
            if is_playing else f"Paused · {title}"
        )
        state = player
        if not is_playing and duration > 0:
            state = f"{player} · {self._format_time(position)}/{self._format_time(duration)}"

        payload: Dict[str, Any] = {
            'activity_type': ActivityType.LISTENING if player.lower() == 'spotify' else ActivityType.WATCHING,
            'details': details[:128],
            'state': state[:128],
            'large_image': self._resolve_media_image(player),
            'large_text': player[:128],
        }

        if is_playing:
            start_ms, end_ms = self._get_media_timeline(player, title, position, duration)
            payload['start'] = start_ms
            if end_ms is not None:
                payload['end'] = end_ms

        self._add_buttons(payload)
        return payload

    def _get_media_timeline(
        self,
        player: str,
        title: str,
        position: int,
        duration: int,
    ) -> tuple[int, Optional[int]]:
        """Return a stable timeline, resetting it only for a track change or seek."""
        now_sec = int(time.time())
        key = f"{player}\0{title}\0{duration}"
        timeline = self.media_timelines.get(key)

        if timeline:
            predicted_position = max(0, now_sec - timeline['start_sec'])
            if abs(predicted_position - position) > 3:
                timeline = None

        if timeline is None:
            start_sec = max(0, now_sec - position)
            timeline = {'start_sec': start_sec, 'last_seen': now_sec}
            self.media_timelines[key] = timeline
        else:
            timeline['last_seen'] = now_sec

        if len(self.media_timelines) > 10:
            oldest = sorted(
                self.media_timelines,
                key=lambda k: self.media_timelines[k]['last_seen'],
            )[:-10]
            for old_key in oldest:
                del self.media_timelines[old_key]

        start_ms = timeline['start_sec'] * 1000
        end_ms = (timeline['start_sec'] + duration) * 1000 if duration > 0 else None
        return start_ms, end_ms

    def _build_terminal(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        command = str(activity.get('command', ''))
        shell = str(activity.get('shell', 'Terminal'))
        directory = str(activity.get('directory', '') or '')
        payload = {
            'activity_type': ActivityType.PLAYING,
            'details': (f"Terminal · {command}" if command else "Terminal")[:128],
            'state': (f"{shell} · {directory}" if directory else shell)[:128],
            'large_image': self.config.get('images.terminal', 'terminal'),
            'large_text': shell[:128],
            'start': self._get_activity_start('terminal', command or 'idle'),
        }
        self._add_buttons(payload)
        return payload

    def _build_coding(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        filename = str(activity.get('filename', ''))
        language = str(activity.get('language', ''))
        editor = str(activity.get('editor', 'Code Editor'))
        project = str(activity.get('project', '') or '')
        payload = {
            'activity_type': ActivityType.PLAYING,
            'details': (f"Coding · {filename}" if filename else "Coding")[:128],
            'state': (f"{editor} · {project}" if project else editor)[:128],
            'large_image': self.config.get('images.code', 'code'),
            'large_text': editor[:128],
            'start': self._get_activity_start('coding', project or filename or editor),
        }
        if language:
            lang_key = self.config.get(f'images.langs.{language.lower()}')
            if lang_key:
                payload['small_image'] = lang_key
                payload['small_text'] = language.title()[:128]
        self._add_buttons(payload)
        return payload

    def _build_browser(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        browser_name = str(activity.get('browser_name', 'Browser'))
        is_private = bool(activity.get('is_private', False))
        page_title = str(activity.get('page_title', ''))
        service = str(activity.get('service', '') or '')
        url = activity.get('url')

        details = "Private browsing" if is_private else (page_title or "Browsing")
        state = browser_name if not service else f"{browser_name} · {service}"
        payload: Dict[str, Any] = {
            'activity_type': ActivityType.WATCHING if service in {'YouTube', 'Netflix', 'Prime Video', 'Disney+', 'Hulu', 'Twitch'} else ActivityType.PLAYING,
            'details': details[:128],
            'state': state[:128],
            'large_image': self._resolve_browser_image(service or page_title),
            'large_text': (service or browser_name)[:128],
            'start': self._get_activity_start('browser', service or browser_name),
        }
        if url and not is_private and self.config.get('privacy.mode', 'balanced') != 'strict':
            payload['details_url'] = url
            payload['large_url'] = url
        self._add_buttons(payload, url=url if not is_private else None, service=service)
        return payload

    def _build_application(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        raw_app_name = str(activity.get('app_name', 'Application'))
        app_name = self._display_app_name(raw_app_name)
        window_title = str(activity.get('window_title', '') or '')
        apps_map = self.config.get('images.apps', {}) or {}
        image_key = (
            apps_map.get(raw_app_name.lower())
            or apps_map.get(app_name.lower())
            or self.config.get('images.app', 'app')
        )
        payload = {
            'activity_type': ActivityType.PLAYING,
            'details': f"{app_name} active"[:128],
            'state': (window_title if window_title else app_name)[:128],
            'large_image': image_key,
            'large_text': app_name[:128],
            'start': self._get_activity_start('app', raw_app_name),
        }
        self._add_buttons(payload)
        return payload

    def _build_gaming(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        game_name = str(activity.get('game_name') or activity.get('launcher') or 'Game')
        launcher = str(activity.get('launcher') or 'Gaming')
        key = (
            self.config.get(f"images.apps.{game_name.lower()}")
            or self.config.get(f"images.games.{game_name.lower()}")
            or self.config.get('images.app', 'app')
        )
        payload = {
            'activity_type': ActivityType.PLAYING,
            'details': f"Playing · {game_name}"[:128],
            'state': launcher[:128],
            'large_image': key,
            'large_text': game_name[:128],
            'start': self._get_activity_start('gaming', game_name),
        }
        self._add_buttons(payload)
        return payload

    @classmethod
    def _display_app_name(cls, app_name: str) -> str:
        raw = str(app_name or 'Application').strip()
        mapped = cls.FRIENDLY_APP_NAMES.get(raw.lower())
        if mapped:
            return mapped
        if raw.lower().startswith(('org.', 'com.', 'io.', 'net.')) and '.' in raw:
            raw = raw.rsplit('.', 1)[-1]
        cleaned = raw.replace('_', ' ').replace('-', ' ').strip()
        return cleaned.title() if cleaned and cleaned.islower() else (cleaned or 'Application')

    def _add_buttons(self, payload: Dict[str, Any], url: Optional[str] = None, service: str = ''):
        if self.config.get('privacy.mode', 'balanced') == 'strict':
            return

        buttons = []
        configured = self.config.get('discord.buttons', []) or []
        if isinstance(configured, list):
            for button in configured[:2]:
                if not isinstance(button, dict):
                    continue
                label = str(button.get('label', '')).strip()
                button_url = str(button.get('url', '')).strip().strip('`')
                if 1 <= len(label) <= 32 and len(button_url) <= 512 and button_url.startswith(('http://', 'https://')):
                    buttons.append({'label': label, 'url': button_url})

        if len(buttons) < 2 and url and str(url).startswith(('http://', 'https://')):
            if service == 'YouTube':
                label = 'Search on YouTube'
            elif service == 'GitHub':
                label = 'Open GitHub'
            elif service:
                label = f"Open {service}"[:32]
            else:
                try:
                    domain = urllib.parse.urlparse(str(url)).netloc.replace('www.', '')
                    label = f"Open {domain.split('.')[0].title()}"[:32]
                except (ValueError, AttributeError):
                    label = 'Open Link'
            candidate = {'label': label, 'url': str(url)[:512]}
            if candidate not in buttons:
                buttons.append(candidate)

        if buttons:
            payload['buttons'] = buttons[:2]

    def _get_activity_start(self, activity_type: str, activity_id: str) -> int:
        """Return an epoch timestamp in milliseconds, as required by pypresence 4.6.x."""
        key = f"{activity_type}:{activity_id}"
        if key not in self.activity_start_times:
            self.activity_start_times[key] = int(time.time() * 1000)
        if len(self.activity_start_times) > 20:
            oldest = sorted(self.activity_start_times, key=self.activity_start_times.get)[:-20]
            for old_key in oldest:
                del self.activity_start_times[old_key]
        return self.activity_start_times[key]

    @staticmethod
    def _format_time(seconds: int) -> str:
        seconds = max(0, int(seconds))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"

    def _resolve_media_image(self, player: str) -> str:
        key = self.config.get(f'images.players.{str(player).lower()}') if player else None
        return key or self.config.get('images.video', 'video')

    def _resolve_browser_image(self, title_or_service: str) -> str:
        sites = self.config.get('images.sites', {}) or {}
        value = str(title_or_service).lower()
        for key, image in sites.items():
            if key and str(key).lower() in value:
                return image
        return self.config.get('images.browser', 'browser')
