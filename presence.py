"""Discord Rich Presence payload builder."""

import time
import urllib.parse
from typing import Dict, Any, Optional

from pypresence.types import ActivityType

from config import Config
from icon_resolver import IconResolver
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

    TOOLTIP_ALIASES = {
        'x': 'X.com',
        'c': 'C language',
    }

    STEAM_ICON = 'https://www.google.com/s2/favicons?domain=steampowered.com&sz=128'

    def __init__(self, config: Config):
        self.config = config
        self.redactor = PrivacyRedactor(config)
        self.icons = IconResolver(config)
        self.activity_start_times: Dict[str, int] = {}
        self.media_timelines: Dict[str, Dict[str, int]] = {}

    def reload(self):
        """Refresh cached privacy state after a config hot reload."""
        self.redactor.reload()

    def build(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        activity_type = activity.get('type', 'application')
        activity = self.redactor.redact_activity(activity)

        if activity_type == 'media':
            payload = self._build_media(activity)
        elif activity_type == 'terminal':
            payload = self._build_terminal(activity)
        elif activity_type == 'coding':
            payload = self._build_coding(activity)
        elif activity_type == 'browser':
            payload = self._build_browser(activity)
        elif activity_type == 'gaming':
            payload = self._build_gaming(activity)
        else:
            payload = self._build_application(activity)
        return self._sanitize_discord_fields(payload)

    @classmethod
    def _sanitize_discord_fields(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Keep detector output inside Discord RPC's text-field contract."""
        result = {key: value for key, value in payload.items() if value is not None}
        for key in ('details', 'state', 'large_text', 'small_text'):
            if key not in result:
                continue
            text = str(result[key]).strip()
            if key in {'large_text', 'small_text'}:
                text = cls.TOOLTIP_ALIASES.get(text.lower(), text)
            if len(text) < 2:
                result.pop(key, None)
                continue
            result[key] = text[:128]
        return result

    def _build_media(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        title = str(activity.get('title', 'Unknown'))
        player = str(activity.get('player', 'Media Player'))
        player_display = self._display_app_name(player)
        service = str(activity.get('service', '') or '')
        is_playing = bool(activity.get('is_playing', False))
        position = max(0, int(activity.get('position', 0) or 0))
        duration = max(0, int(activity.get('duration', 0) or 0))

        listening = player.lower() == 'spotify' or service.lower() == 'spotify'
        details = (
            f"{'Listening' if listening else 'Watching'} · {title}"
            if is_playing else f"Paused · {title}"
        )
        state = f"{service} · {player_display}" if service else player_display
        if not is_playing and duration > 0:
            state = f"{state} · {self._format_time(position)}/{self._format_time(duration)}"

        service_image = self._resolve_service_image(service) if service else None
        player_image = self._resolve_media_image(player, player_display)
        payload: Dict[str, Any] = {
            'activity_type': ActivityType.LISTENING if listening else ActivityType.WATCHING,
            'details': details[:128],
            'state': state[:128],
            'large_image': service_image or player_image,
            'large_text': (service or player_display)[:128],
        }

        if service and service.lower() != player_display.lower():
            configured_player = self._configured_app_image(player, player_display)
            small_image = self.icons.resolve_optional(
                player,
                player_display,
                configured=configured_player,
            )
            if small_image:
                payload['small_image'] = small_image
                payload['small_text'] = player_display[:128]

        if is_playing:
            start_ms, end_ms = self._get_media_timeline(player, title, position, duration)
            payload['start'] = start_ms
            if end_ms is not None:
                payload['end'] = end_ms

        self._add_buttons(payload, service=service)
        return payload

    def _get_media_timeline(
        self,
        player: str,
        title: str,
        position: int,
        duration: int,
    ) -> tuple[int, Optional[int]]:
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
        terminal_name = str(activity.get('terminal_name') or shell or 'Terminal')
        directory = str(activity.get('directory', '') or '')
        configured = self._configured_app_image(terminal_name, shell)
        payload = {
            'activity_type': ActivityType.PLAYING,
            'details': (f"Terminal · {command}" if command else 'Terminal')[:128],
            'state': (f"{shell} · {directory}" if directory else shell)[:128],
            'large_image': self.icons.resolve(
                terminal_name,
                shell,
                configured=configured,
                fallback=self.config.get('images.terminal', 'terminal'),
            ),
            'large_text': terminal_name[:128],
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
            'details': (f"Coding · {filename}" if filename else 'Coding')[:128],
            'state': (f"{editor} · {project}" if project else editor)[:128],
            'large_image': self.icons.resolve(
                editor,
                configured=self._configured_app_image(editor),
                fallback=self.config.get('images.code', 'code'),
            ),
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

        details = 'Private browsing' if is_private else (page_title or 'Browsing')
        state = browser_name if not service else f"{service} · {browser_name}"
        browser_image = self.icons.resolve(
            browser_name,
            configured=self._configured_app_image(browser_name),
            fallback=self.config.get('images.browser', 'browser'),
        )
        service_image = self._resolve_service_image(service) if service else None

        payload: Dict[str, Any] = {
            'activity_type': ActivityType.WATCHING if service in {
                'YouTube', 'Netflix', 'Prime Video', 'Disney+', 'Hulu', 'Twitch'
            } else ActivityType.PLAYING,
            'details': details[:128],
            'state': state[:128],
            'large_image': service_image or browser_image,
            'large_text': (service or browser_name)[:128],
            'start': self._get_activity_start('browser', service or browser_name),
        }

        if service and service_image:
            small_browser = self.icons.resolve_optional(
                browser_name,
                configured=self._configured_app_image(browser_name),
            )
            if small_browser:
                payload['small_image'] = small_browser
                payload['small_text'] = browser_name[:128]

        if url and not is_private and self.config.get('privacy.mode', 'balanced') != 'strict':
            payload['details_url'] = url
            payload['large_url'] = url
        self._add_buttons(payload, url=url if not is_private else None, service=service)
        return payload

    def _build_application(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        raw_app_name = str(activity.get('app_name', 'Application'))
        app_name = self._display_app_name(raw_app_name)
        window_title = str(activity.get('window_title', '') or '')
        image = self.icons.resolve(
            raw_app_name,
            app_name,
            configured=self._configured_app_image(raw_app_name, app_name),
            fallback=self.config.get('images.app', 'app'),
        )
        payload = {
            'activity_type': ActivityType.PLAYING,
            'details': f"{app_name} active"[:128],
            'state': (window_title if window_title else app_name)[:128],
            'large_image': image,
            'large_text': app_name[:128],
            'start': self._get_activity_start('app', raw_app_name),
        }
        self._add_buttons(payload)
        return payload

    def _build_gaming(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        game_name = str(activity.get('game_name') or activity.get('launcher') or 'Game')
        launcher = str(activity.get('launcher') or 'Gaming')
        artwork_url = str(activity.get('artwork_url', '') or '').strip()
        store_url = str(activity.get('store_url', '') or '').strip()
        source = str(activity.get('game_source', '') or '').strip()

        configured = (
            self._configured_app_image(game_name, launcher)
            or self.config.get(f"images.games.{game_name.lower()}")
        )
        resolved_image = self.icons.resolve(
            game_name,
            launcher,
            configured=configured,
            fallback=self.config.get('images.app', 'app'),
        )
        large_image = (
            artwork_url
            if artwork_url.startswith(('https://', 'http://')) and len(artwork_url) <= 300
            else resolved_image
        )

        if activity.get('gsi'):
            mode = str(activity.get('mode', '') or '').strip()
            map_name = str(activity.get('map', '') or '').strip()
            team_name = str(activity.get('team_name', '') or '').strip()
            ct_score = int(activity.get('ct_score', 0) or 0)
            t_score = int(activity.get('t_score', 0) or 0)
            mode_key = str(activity.get('mode_key', '') or '').lower()

            details = ' · '.join(part for part in (game_name, mode) if part)
            state_parts = [part for part in (map_name, team_name) if part]
            score_is_meaningful = (
                mode_key in {
                    'competitive', 'casual', 'scrimcomp2v2', 'scrimpcomp2v2',
                    'wingman', 'gungametrbomb', 'demolition',
                }
                or ct_score > 0
                or t_score > 0
            )
            if score_is_meaningful:
                state_parts.append(f'{ct_score}–{t_score}')
            state = ' · '.join(state_parts) or launcher
        else:
            details = game_name
            state = source or launcher

        payload: Dict[str, Any] = {
            'activity_type': ActivityType.PLAYING,
            'details': details[:128],
            'state': state[:128],
            'large_image': large_image,
            'large_text': game_name[:128],
            'start': self._get_activity_start('gaming', game_name),
        }

        if source.lower() == 'steam':
            payload['small_image'] = self.STEAM_ICON
            payload['small_text'] = 'Steam'

        self._add_buttons(
            payload,
            url=store_url if store_url.startswith(('https://', 'http://')) else None,
            service='Steam' if source.lower() == 'steam' else '',
        )
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

    def _configured_app_image(self, *names: object) -> Optional[str]:
        apps = self.config.get('images.apps', {}) or {}
        if not isinstance(apps, dict):
            return None
        normalized = {str(key).strip().lower(): str(value).strip() for key, value in apps.items()}
        for name in names:
            raw = str(name or '').strip().lower()
            if raw in normalized and normalized[raw]:
                return normalized[raw]
        return None

    def _resolve_media_image(self, player: str, player_display: str) -> str:
        players = self.config.get('images.players', {}) or {}
        configured = None
        if isinstance(players, dict):
            configured = players.get(str(player).lower()) or players.get(str(player_display).lower())
        configured = configured or self._configured_app_image(player, player_display)
        return self.icons.resolve(
            player,
            player_display,
            configured=str(configured or ''),
            fallback=self.config.get('images.video', 'video'),
        )

    def _resolve_service_image(self, service: str) -> Optional[str]:
        if not service:
            return None
        sites = self.config.get('images.sites', {}) or {}
        configured = None
        if isinstance(sites, dict):
            configured = sites.get(str(service).lower())
        return self.icons.resolve_optional(service, configured=str(configured or ''))

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
                if (
                    1 <= len(label) <= 32
                    and len(button_url) <= 512
                    and button_url.startswith(('http://', 'https://'))
                ):
                    buttons.append({'label': label, 'url': button_url})

        auto_url = str(url or '').strip().strip('`')
        if (
            len(buttons) < 2
            and auto_url.startswith(('http://', 'https://'))
            and len(auto_url) <= 512
        ):
            if service == 'YouTube':
                label = 'Search on YouTube'
            elif service == 'GitHub':
                label = 'Open GitHub'
            elif service == 'Steam':
                label = 'View on Steam'
            elif service:
                label = f"Open {service}"[:32]
            else:
                try:
                    domain = urllib.parse.urlparse(auto_url).netloc.replace('www.', '')
                    label = f"Open {domain.split('.')[0].title()}"[:32]
                except (ValueError, AttributeError):
                    label = 'Open Link'
            candidate = {'label': label, 'url': auto_url}
            if candidate not in buttons:
                buttons.append(candidate)

        if buttons:
            payload['buttons'] = buttons[:2]

    def _get_activity_start(self, activity_type: str, activity_id: str) -> int:
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
