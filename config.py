"""Configuration manager for Discord Rich Presence Service."""

import copy
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


_MAX_CONFIG_BYTES = 1024 * 1024
_BUILTIN_DISCORD_APPLICATION_ID = '1416813807751336047'
BUILTIN_DISCORD_APPLICATION_ID = _BUILTIN_DISCORD_APPLICATION_ID


DEFAULT_CONFIG: Dict[str, Any] = {
    'discord': {
        'application_id_override': '',
        'buttons': [],
    },
    'privacy': {
        'mode': 'balanced',
        'browser_url_mode': 'domain',
        'redactions': [
            {'regex': r'(?i)(password|token|secret|key|api[_-]?key)\S*'},
            {'regex': r'([A-Fa-f0-9]{32,})'},
        ],
        'hide_home_paths': True,
    },
    'update_interval_secs': 2,
    'system': {
        'start_minimized': False,
        'auto_start': False,
    },
    'browser_companion': {
        'enabled': True,
        'port': 32191,
        'ttl_secs': 15,
        'domain_services': {},
    },
    'cs2_gsi': {
        'enabled': True,
        'auto_install': True,
        'port': 32192,
        'ttl_secs': 30,
    },
    'fivem': {
        'enabled': False,
        'port': 32193,
        'ttl_secs': 15,
        'show_server_name': False,
        'show_player_count': True,
        'allow_join_button': False,
    },
    'minecraft': {
        'enabled': False,
        'port': 32194,
        'ttl_secs': 15,
        'show_server_name': False,
    },
    'game_library': {
        'enabled': True,
        'sources': {
            'steam': True,
            'epic': True,
            'heroic': True,
        },
        'custom_games': [],
    },
    'game_packs': {
        'enabled': True,
        'directory': '',
    },
    'league': {
        'enabled': True,
        'show_champion': True,
        'show_queue': True,
        'show_score': False,
    },
    'gamer_mode': {
        'enabled': False,
        'startup_profile': 'default',
    },
    'social': {
        'buttons': True,
    },
    'images': {
        'use_external_app_icons': True,
        'icon_overrides': {},
        'browser': 'browser',
        'video': 'video',
        'terminal': 'terminal',
        'code': 'code',
        'app': 'app',
        'apps': {
            'explorer': 'explorer', 'chrome': 'chrome', 'msedge': 'edge',
            'edge': 'edge', 'firefox': 'firefox', 'brave': 'brave',
            'opera': 'opera', 'vivaldi': 'vivaldi', 'code': 'vscode',
            'vs code': 'vscode', 'pycharm': 'pycharm', 'trae': 'trae',
            'powershell': 'powershell', 'cmd': 'cmd'
        },
        'langs': {
            'python': 'py', 'javascript': 'js', 'typescript': 'ts',
            'cpp': 'cpp', 'c': 'c', 'java': 'java', 'go': 'go',
            'rust': 'rust', 'php': 'php', 'ruby': 'ruby', 'swift': 'swift',
            'kotlin': 'kotlin', 'dart': 'dart', 'html': 'html', 'css': 'css',
            'json': 'json', 'yaml': 'yaml', 'markdown': 'md'
        },
        'players': {
            'spotify': 'spotify', 'vlc': 'vlc', 'chrome': 'chrome',
            'edge': 'edge', 'firefox': 'firefox', 'mpv': 'mpv',
            'windows media player': 'wmp'
        },
        'sites': {
            'youtube': 'youtube', 'netflix': 'netflix', 'hulu': 'hulu',
            'prime video': 'prime'
        },
        'games': {
            'league of legends': 'lol', 'valorant': 'valorant',
            'minecraft': 'minecraft', 'rocket league': 'rocketleague',
            'fortnite': 'fortnite', 'apex legends': 'apex',
            'grand theft auto v': 'gtav', 'dota 2': 'dota2'
        }
    },
    'rules': {
        'youtube_domains': ['YouTube', 'youtu.be'],
        'private_markers': ['Incognito', 'Private Browsing', 'InPrivate'],
        'enabled_detectors': {
            'media': True, 'terminal': False, 'coding': True,
            'browser': True, 'gaming': True, 'application': True
        },
        'activity_priority': {
            'policy': 'smart',
            'custom_order': ['gaming', 'terminal', 'coding', 'browser', 'media', 'application'],
        },
        'terminal_command_ttl_secs': 900,
        'clear_on_lock_screen': True,
        'whitelist': {'apps': [], 'sites': [], 'games': []},
        'blacklist': {'apps': [], 'sites': [], 'games': []}
    },
    'override': {
        'enabled': False, 'details': '', 'state': '',
        'use_start_timestamp': False, 'large_image_key': '',
        'large_text': '', 'small_image_key': '', 'small_text': '',
        'details_url': '', 'state_url': '', 'large_url': '', 'small_url': '',
        'party_id': '', 'party_current': 0, 'party_max': 0, 'buttons': []
    }
}


def resolve_discord_application_id(config: 'Config') -> str:
    """Return the application ID used for local Discord RPC."""
    override = str(config.get('discord.application_id_override', '') or '').strip()
    return override or BUILTIN_DISCORD_APPLICATION_ID


class Config:
    """Configuration manager with nested key access and safe hot reloads."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = self._get_default_config_path()
        self.config_path = Path(config_path)
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        if self.config_path.exists():
            self.load(self.config_path)

    @staticmethod
    def _chmod_private(path: Path, mode: int) -> None:
        if os.name != 'posix':
            return
        try:
            os.chmod(path, mode)
        except OSError:
            pass

    def load(self, path: Path):
        """Load from defaults + file, replacing the previous in-memory snapshot."""
        path = Path(path)
        try:
            try:
                size = path.stat().st_size
            except OSError as exc:
                raise ValueError(f'Cannot stat configuration: {exc}') from exc
            if size > _MAX_CONFIG_BYTES:
                raise ValueError(f'Configuration file exceeds {_MAX_CONFIG_BYTES} bytes')

            with open(path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f) or {}
            if not isinstance(loaded, dict):
                raise ValueError('Configuration root must be a mapping')
            data = copy.deepcopy(DEFAULT_CONFIG)
            self._deep_merge(data, loaded)
            self._validate(data)
            self.data = data
            self.config_path = path
            self._chmod_private(path, 0o600)
        except yaml.YAMLError as exc:
            raise ValueError(f'Invalid YAML configuration: {exc}') from exc

    def save(self, path: Optional[Path] = None):
        """Persist configuration atomically without exposing secrets to other users."""
        path = Path(path or self.config_path)
        self._validate(self.data)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._chmod_private(path.parent, 0o700)
        serialized = yaml.safe_dump(self.data, sort_keys=False, allow_unicode=True)
        if len(serialized.encode('utf-8')) > _MAX_CONFIG_BYTES:
            raise ValueError(f'Configuration exceeds {_MAX_CONFIG_BYTES} bytes')
        fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=str(path.parent))
        try:
            if os.name == 'posix':
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
            self.config_path = path
            self._chmod_private(path, 0o600)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """Return a nested dot-separated configuration value."""
        if key == 'discord.client_id':
            discord = self.data.get('discord', {})
            if isinstance(discord, dict):
                override = str(discord.get('application_id_override', '') or '').strip()
                return override or BUILTIN_DISCORD_APPLICATION_ID
            return BUILTIN_DISCORD_APPLICATION_ID

        value: Any = self.data
        for part in str(key).split('.'):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a nested dot-separated configuration value in memory."""
        parts = [part for part in str(key).split('.') if part]
        if not parts:
            raise ValueError('Configuration key cannot be empty')
        data = self.data
        for part in parts[:-1]:
            child = data.get(part)
            if not isinstance(child, dict):
                child = {}
                data[part] = child
            data = child
        data[parts[-1]] = value

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]):
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    @staticmethod
    def _validate(data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError('Configuration root must be a mapping')

        discord = data.get('discord', {})
        if not isinstance(discord, dict):
            raise ValueError('discord must be a mapping')
        application_id = discord.get('application_id_override', '')
        if application_id not in (None, ''):
            text = str(application_id).strip()
            if not re.fullmatch(r'\d{17,20}', text):
                raise ValueError('discord.application_id_override must be a 17-20 digit Discord application ID')
        buttons = discord.get('buttons', [])
        if not isinstance(buttons, list) or len(buttons) > 2:
            raise ValueError('discord.buttons must be a list with at most two entries')
        for item in buttons:
            if not isinstance(item, dict):
                raise ValueError('discord.buttons entries must be mappings')
            label = str(item.get('label', '') or '').strip()
            url = str(item.get('url', '') or '').strip()
            if not (1 <= len(label) <= 32):
                raise ValueError('discord button labels must be 1-32 characters')
            if not (1 <= len(url) <= 512):
                raise ValueError('discord button URLs must be 1-512 characters')

        privacy = data.get('privacy', {})
        if not isinstance(privacy, dict):
            raise ValueError('privacy must be a mapping')
        mode = str(privacy.get('mode', 'balanced') or 'balanced').lower()
        if mode not in {'off', 'balanced', 'strict'}:
            raise ValueError('privacy.mode must be off, balanced, or strict')
        browser_url_mode = str(privacy.get('browser_url_mode', 'domain') or 'domain').lower()
        if browser_url_mode not in {'none', 'domain', 'path', 'full'}:
            raise ValueError('privacy.browser_url_mode must be none, domain, path, or full')
        redactions = privacy.get('redactions', [])
        if not isinstance(redactions, list) or len(redactions) > 100:
            raise ValueError('privacy.redactions must be a list with at most 100 entries')
        for item in redactions:
            if not isinstance(item, dict):
                raise ValueError('privacy.redactions entries must be mappings')
            expression = str(item.get('regex', '') or '')
            if not expression or len(expression) > 512:
                raise ValueError('privacy redaction regex must be 1-512 characters')
            try:
                re.compile(expression)
            except re.error as exc:
                raise ValueError(f'invalid privacy redaction regex: {exc}') from exc

        update_interval = data.get('update_interval_secs', 2)
        if isinstance(update_interval, bool):
            raise ValueError('update_interval_secs must be numeric')
        try:
            update_interval = float(update_interval)
        except (TypeError, ValueError) as exc:
            raise ValueError('update_interval_secs must be numeric') from exc
        if not (0.5 <= update_interval <= 300):
            raise ValueError('update_interval_secs must be between 0.5 and 300')

        Config._validate_local_service(data, 'browser_companion', default_port=32191)
        Config._validate_local_service(data, 'cs2_gsi', default_port=32192)
        Config._validate_local_service(data, 'fivem', default_port=32193)
        Config._validate_local_service(data, 'minecraft', default_port=32194)

        browser = data.get('browser_companion', {})
        if not isinstance(browser.get('domain_services', {}), dict):
            raise ValueError('browser_companion.domain_services must be a mapping')
        if len(browser.get('domain_services', {})) > 100:
            raise ValueError('browser_companion.domain_services has too many entries')
        for host, service in browser.get('domain_services', {}).items():
            host_text = str(host or '').strip().lower()
            service_text = str(service or '').strip()
            if not host_text or len(host_text) > 253 or not service_text or len(service_text) > 64:
                raise ValueError('browser companion domain service entries are invalid')
            candidate = host_text[2:] if host_text.startswith('*.') else host_text
            if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', candidate):
                raise ValueError('browser companion domain service hostname is invalid')

        rules = data.get('rules', {})
        if not isinstance(rules, dict):
            raise ValueError('rules must be a mapping')
        enabled = rules.get('enabled_detectors', {})
        if not isinstance(enabled, dict):
            raise ValueError('rules.enabled_detectors must be a mapping')
        for name in {'media', 'terminal', 'coding', 'browser', 'gaming', 'application'}:
            if not isinstance(enabled.get(name), bool):
                raise ValueError(f'rules.enabled_detectors.{name} must be boolean')

        priority = rules.get('activity_priority', {})
        if not isinstance(priority, dict):
            raise ValueError('rules.activity_priority must be a mapping')
        policy = str(priority.get('policy', 'smart') or 'smart').strip().lower()
        if policy not in {'smart', 'foreground_first', 'media_first', 'custom'}:
            raise ValueError('rules.activity_priority.policy is invalid')
        custom_order = priority.get('custom_order', [])
        if not isinstance(custom_order, list):
            raise ValueError('rules.activity_priority.custom_order must be a list')
        allowed_order = {'gaming', 'terminal', 'coding', 'browser', 'media', 'application'}
        normalized_order = [str(item).strip().lower() for item in custom_order]
        if len(normalized_order) != len(set(normalized_order)) or any(item not in allowed_order for item in normalized_order):
            raise ValueError('rules.activity_priority.custom_order contains invalid/duplicate entries')

        try:
            ttl = int(rules.get('terminal_command_ttl_secs', 900))
        except (TypeError, ValueError) as exc:
            raise ValueError('rules.terminal_command_ttl_secs must be an integer') from exc
        if not (5 <= ttl <= 604800):
            raise ValueError('rules.terminal_command_ttl_secs must be between 5 and 604800')

        for section, keys in (
            ('system', {'start_minimized', 'auto_start'}),
            ('cs2_gsi', {'enabled', 'auto_install'}),
            ('fivem', {'enabled', 'show_server_name', 'show_player_count', 'allow_join_button'}),
            ('minecraft', {'enabled', 'show_server_name'}),
            ('league', {'enabled', 'show_champion', 'show_queue', 'show_score'}),
            ('gamer_mode', {'enabled'}),
            ('social', {'buttons'}),
        ):
            values = data.get(section, {})
            if not isinstance(values, dict):
                raise ValueError(f'{section} must be a mapping')
            for key in keys:
                if not isinstance(values.get(key), bool):
                    raise ValueError(f'{section}.{key} must be boolean')

        game_library = data.get('game_library', {})
        if not isinstance(game_library, dict):
            raise ValueError('game_library must be a mapping')
        if not isinstance(game_library.get('enabled'), bool):
            raise ValueError('game_library.enabled must be boolean')
        sources = game_library.get('sources', {})
        if not isinstance(sources, dict):
            raise ValueError('game_library.sources must be a mapping')
        for source in {'steam', 'epic', 'heroic'}:
            if not isinstance(sources.get(source), bool):
                raise ValueError(f'game_library.sources.{source} must be boolean')
        custom_games = game_library.get('custom_games', [])
        if not isinstance(custom_games, list) or len(custom_games) > 200:
            raise ValueError('game_library.custom_games must be a list with at most 200 entries')
        for game in custom_games:
            if not isinstance(game, dict):
                raise ValueError('game_library.custom_games entries must be mappings')
            name = str(game.get('name', '') or '').strip()
            executable = str(game.get('executable', '') or '').strip()
            if not name or len(name) > 128 or not executable or len(executable) > 260:
                raise ValueError('custom game name/executable is invalid')

        game_packs = data.get('game_packs', {})
        if not isinstance(game_packs, dict) or not isinstance(game_packs.get('enabled'), bool):
            raise ValueError('game_packs.enabled must be boolean')
        directory = str(game_packs.get('directory', '') or '')
        if len(directory) > 1024 or '\x00' in directory:
            raise ValueError('game_packs.directory is invalid')

        override = data.get('override', {})
        if not isinstance(override, dict):
            raise ValueError('override must be a mapping')
        if not isinstance(override.get('enabled'), bool):
            raise ValueError('override.enabled must be boolean')
        if not isinstance(override.get('use_start_timestamp'), bool):
            raise ValueError('override.use_start_timestamp must be boolean')
        for key in {'details', 'state', 'large_image_key', 'large_text', 'small_image_key', 'small_text'}:
            if len(str(override.get(key, '') or '')) > 512:
                raise ValueError(f'override.{key} is too long')
        for key in {'details_url', 'state_url', 'large_url', 'small_url'}:
            if len(str(override.get(key, '') or '')) > 2048:
                raise ValueError(f'override.{key} is too long')
        party_id = str(override.get('party_id', '') or '')
        if len(party_id) > 128 or any(ord(char) < 32 for char in party_id):
            raise ValueError('override.party_id is invalid')
        for key in {'party_current', 'party_max'}:
            value = override.get(key, 0)
            if isinstance(value, bool):
                raise ValueError(f'override.{key} must be an integer')
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f'override.{key} must be an integer') from exc
            if not (0 <= number <= 100000):
                raise ValueError(f'override.{key} is out of range')

    @staticmethod
    def _validate_local_service(data: Dict[str, Any], section: str, *, default_port: int) -> None:
        values = data.get(section, {})
        if not isinstance(values, dict):
            raise ValueError(f'{section} must be a mapping')
        if not isinstance(values.get('enabled'), bool):
            raise ValueError(f'{section}.enabled must be boolean')
        try:
            port = int(values.get('port', default_port))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{section}.port must be an integer') from exc
        if not (1024 <= port <= 65535):
            raise ValueError(f'{section}.port must be between 1024 and 65535')
        try:
            ttl = int(values.get('ttl_secs', 15))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{section}.ttl_secs must be an integer') from exc
        if not (5 <= ttl <= 3600):
            raise ValueError(f'{section}.ttl_secs must be between 5 and 3600')

    @staticmethod
    def _get_default_config_path() -> Path:
        if os.name == 'nt':
            base = os.environ.get('APPDATA')
            config_dir = (
                Path(base) / 'discord-rich-presence'
                if base
                else Path.home() / 'AppData' / 'Roaming' / 'discord-rich-presence'
            )
        else:
            config_dir = Path.home() / '.config' / 'discord-rich-presence'
        config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        Config._chmod_private(config_dir, 0o700)
        return config_dir / 'config.yaml'
