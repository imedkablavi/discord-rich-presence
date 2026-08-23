"""Configuration management for Discord Rich Presence Service."""

import base64
import copy
import os
import platform
import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except Exception:
    yaml = None  # type: ignore
    _YAML_AVAILABLE = False
    import json


DEFAULT_CONFIG = {
    'discord': {
        'client_id': '1437867564762923028',
        'buttons': []
    },
    'privacy': {
        'mode': 'balanced',
        'redactions': [
            {'regex': r'(?i)(password|token|secret|key|api[_-]?key)\S*'},
            {'regex': r'([A-Fa-f0-9]{32,})'},
        ],
        'hide_home_paths': True
    },
    'update_interval_secs': 5,
    'system': {
        'start_minimized': False,
        'auto_start': False
    },
    'browser_companion': {
        'enabled': False,
        'port': 17653,
        'ttl_secs': 15,
        'allow_titles': True,
        'allow_origin': True,
        'allow_exact_url': False,
    },
    'updates': {
        'enabled': True,
        'auto_install': False,
        'manifest_url': 'https://github.com/imedkablavi/discord-rich-presence/releases/latest/download/update-manifest.json',
        'public_key': 'zx3g5J29SZVSwcJ3pbux7VBorpZAOoCHJPfPz1KLXxk=',
    },
    'images': {
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
            'media': True, 'terminal': True, 'coding': True,
            'browser': True, 'gaming': True, 'application': True
        },
        'terminal_command_ttl_secs': 21600,
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


class Config:
    """Configuration manager with nested key access and safe hot reloads."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = self._get_default_config_path()
        self.config_path = config_path
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        if config_path and config_path.exists():
            self.load(config_path)

    def load(self, path: Path):
        """Load from defaults + file, replacing the previous in-memory snapshot."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if _YAML_AVAILABLE:
                    user_config = yaml.safe_load(f)  # type: ignore
                else:
                    user_config = json.load(f)

            if user_config is None:
                user_config = {}
            if not isinstance(user_config, dict):
                raise ValueError('Top-level configuration must be a mapping/object')

            new_data = copy.deepcopy(DEFAULT_CONFIG)
            self._deep_update(new_data, user_config)
            self._validate(new_data)
            self.data = new_data
            self.config_path = path
        except Exception as e:
            raise ValueError(f"Failed to load config from {path}: {e}") from e

    def save(self, path: Optional[Path] = None):
        save_path = path or self.config_path
        if not save_path:
            raise ValueError("No config path specified")

        self._validate(self.data)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = save_path.with_suffix(save_path.suffix + '.tmp')
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                if _YAML_AVAILABLE:
                    yaml.safe_dump(self.data, f, default_flow_style=False, allow_unicode=True)  # type: ignore
                else:
                    import json as _json
                    _json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, save_path)
        except Exception as e:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise ValueError(f"Failed to save config to {save_path}: {e}") from e

    def get(self, key: str, default: Any = None) -> Any:
        value: Any = self.data
        for part in key.split('.'):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        keys = key.split('.')
        data = self.data
        for part in keys[:-1]:
            if part not in data or not isinstance(data[part], dict):
                data[part] = {}
            data = data[part]
        data[keys[-1]] = value

    @staticmethod
    def _deep_update(base: Dict, update: Dict):
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_update(base[key], value)
            else:
                base[key] = copy.deepcopy(value)

    @staticmethod
    def _validate_url(value: Any, name: str, allow_empty: bool = True, https_only: bool = False):
        url = str(value or '').strip()
        if not url and allow_empty:
            return
        allowed = ('https://',) if https_only else ('https://', 'http://')
        if not url.startswith(allowed):
            expected = 'https://' if https_only else 'http:// or https://'
            raise ValueError(f'{name} must start with {expected}')
        if len(url) > 512:
            raise ValueError(f'{name} must be at most 512 characters')

    @staticmethod
    def _validate_buttons(buttons: Any, name: str):
        if buttons is None:
            buttons = []
        if not isinstance(buttons, list) or len(buttons) > 2:
            raise ValueError(f'{name} must be a list with at most 2 buttons')
        for button in buttons:
            if not isinstance(button, dict):
                raise ValueError(f'Each {name} entry must be an object')
            label = str(button.get('label', '')).strip()
            if not (1 <= len(label) <= 32):
                raise ValueError('Discord button labels must be 1-32 characters')
            Config._validate_url(button.get('url', ''), 'Discord button URL', allow_empty=False)

    @staticmethod
    def _validate_string_list(value: Any, name: str):
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f'{name} must be a list of strings')

    @staticmethod
    def _validate(data: Dict[str, Any]):
        privacy = data.get('privacy', {})
        if not isinstance(privacy, dict):
            raise ValueError('privacy must be an object')
        mode = privacy.get('mode', 'balanced')
        if mode not in {'off', 'balanced', 'strict'}:
            raise ValueError("privacy.mode must be one of: off, balanced, strict")
        if not isinstance(privacy.get('hide_home_paths', True), bool):
            raise ValueError('privacy.hide_home_paths must be true or false')
        redactions = privacy.get('redactions', []) or []
        if not isinstance(redactions, list):
            raise ValueError('privacy.redactions must be a list')
        for entry in redactions:
            if not isinstance(entry, dict) or not isinstance(entry.get('regex'), str):
                raise ValueError('Each privacy.redactions entry must contain a regex string')
            try:
                re.compile(entry['regex'])
            except re.error as e:
                raise ValueError(f"Invalid privacy regex {entry['regex']!r}: {e}") from e

        interval = data.get('update_interval_secs', 5)
        if isinstance(interval, bool) or not isinstance(interval, (int, float)):
            raise ValueError('update_interval_secs must be a number')
        if interval < 1 or interval > 3600:
            raise ValueError('update_interval_secs must be between 1 and 3600 seconds')

        system = data.get('system', {})
        if not isinstance(system, dict):
            raise ValueError('system must be an object')
        for key in ('start_minimized', 'auto_start'):
            if not isinstance(system.get(key, False), bool):
                raise ValueError(f'system.{key} must be true or false')

        companion = data.get('browser_companion', {})
        if not isinstance(companion, dict):
            raise ValueError('browser_companion must be an object')
        for key in ('enabled', 'allow_titles', 'allow_origin', 'allow_exact_url'):
            if not isinstance(companion.get(key, False), bool):
                raise ValueError(f'browser_companion.{key} must be true or false')
        port = companion.get('port', 17653)
        if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
            raise ValueError('browser_companion.port must be an integer between 1024 and 65535')
        ttl = companion.get('ttl_secs', 15)
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or not 1 <= ttl <= 300:
            raise ValueError('browser_companion.ttl_secs must be between 1 and 300 seconds')

        updates = data.get('updates', {})
        if not isinstance(updates, dict):
            raise ValueError('updates must be an object')
        for key in ('enabled', 'auto_install'):
            if not isinstance(updates.get(key, False), bool):
                raise ValueError(f'updates.{key} must be true or false')
        Config._validate_url(
            updates.get('manifest_url', ''),
            'updates.manifest_url',
            allow_empty=False,
            https_only=True,
        )
        public_key = str(updates.get('public_key', '') or '').strip()
        if public_key:
            try:
                decoded_key = base64.b64decode(public_key, validate=True)
            except ValueError as e:
                raise ValueError('updates.public_key must be valid base64') from e
            if len(decoded_key) != 32:
                raise ValueError('updates.public_key must contain a 32-byte Ed25519 public key')
        if updates.get('enabled') and not public_key:
            raise ValueError('updates.public_key is required when updates.enabled is true')
        if updates.get('auto_install') and not updates.get('enabled'):
            raise ValueError('updates.auto_install requires updates.enabled=true')

        discord = data.get('discord', {})
        if not isinstance(discord, dict):
            raise ValueError('discord must be an object')
        client_id = str(discord.get('client_id', '')).strip()
        if not client_id or not client_id.isdigit():
            raise ValueError('discord.client_id must be a numeric Discord application ID')
        Config._validate_buttons(discord.get('buttons', []), 'discord.buttons')

        rules = data.get('rules', {})
        if not isinstance(rules, dict):
            raise ValueError('rules must be an object')
        detectors = rules.get('enabled_detectors', {})
        if not isinstance(detectors, dict):
            raise ValueError('rules.enabled_detectors must be an object')
        for key in ('media', 'terminal', 'coding', 'browser', 'gaming', 'application'):
            if not isinstance(detectors.get(key, True), bool):
                raise ValueError(f'rules.enabled_detectors.{key} must be true or false')
        ttl = rules.get('terminal_command_ttl_secs', 21600)
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or ttl < 0 or ttl > 604800:
            raise ValueError('rules.terminal_command_ttl_secs must be between 0 and 604800')
        if not isinstance(rules.get('clear_on_lock_screen', True), bool):
            raise ValueError('rules.clear_on_lock_screen must be true or false')
        for key in ('youtube_domains', 'private_markers'):
            Config._validate_string_list(rules.get(key, []), f'rules.{key}')
        for section in ('whitelist', 'blacklist'):
            mapping = rules.get(section, {})
            if not isinstance(mapping, dict):
                raise ValueError(f'rules.{section} must be an object')
            for key in ('apps', 'sites', 'games'):
                Config._validate_string_list(mapping.get(key, []), f'rules.{section}.{key}')

        override = data.get('override', {})
        if not isinstance(override, dict):
            raise ValueError('override must be an object')
        for key in ('enabled', 'use_start_timestamp'):
            if not isinstance(override.get(key, False), bool):
                raise ValueError(f'override.{key} must be true or false')
        Config._validate_buttons(override.get('buttons', []), 'override.buttons')
        for key in ('details_url', 'state_url', 'large_url', 'small_url'):
            Config._validate_url(override.get(key, ''), f'override.{key}')
        try:
            party_current = int(override.get('party_current', 0) or 0)
            party_max = int(override.get('party_max', 0) or 0)
        except (TypeError, ValueError) as e:
            raise ValueError('override party sizes must be integers') from e
        if party_current < 0 or party_max < 0:
            raise ValueError('override party sizes cannot be negative')
        if party_max and party_current > party_max:
            raise ValueError('override.party_current cannot exceed override.party_max')

    @staticmethod
    def _get_default_config_path() -> Path:
        system = platform.system().lower()
        if system == 'windows':
            base = os.environ.get('APPDATA')
            config_dir = Path(base) / 'discord-rich-presence' if base else Path.home() / 'AppData' / 'Roaming' / 'discord-rich-presence'
        else:
            config_dir = Path.home() / '.config' / 'discord-rich-presence'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'config.yaml'
