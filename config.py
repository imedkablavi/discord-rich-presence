"""Configuration management for Discord Rich Presence Service."""

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


# Public application identifier shipped with CYBREX Discord Rich Presence.
# Discord Application IDs are public identifiers, not credentials/secrets.
BUILTIN_DISCORD_APPLICATION_ID = '1437867564762923028'
_MAX_CONFIG_BYTES = 2 * 1024 * 1024
_MAX_LIST_ITEMS = 512
_MAX_CUSTOM_SERVICES = 256


DEFAULT_CONFIG = {
    'discord': {
        # Optional advanced override. Normal users do not need a Developer
        # Portal application or an ID of their own.
        'application_id_override': '',
        'buttons': []
    },
    'privacy': {
        'mode': 'balanced',
        # Exact URLs from the browser companion are reduced to their origin by
        # default. Options: none, domain, path, full.
        'browser_url_mode': 'domain',
        'redactions': [
            {'regex': r'(?i)(password|token|secret|key|api[_-]?key)\S*'},
            {'regex': r'([A-Fa-f0-9]{32,})'},
        ],
        'hide_home_paths': True
    },
    'update_interval_secs': 2,
    'system': {
        'start_minimized': False,
        'auto_start': False
    },
    'browser_companion': {
        # Loopback-only bridge for the optional Chromium/Firefox extension.
        'enabled': True,
        'port': 32191,
        'ttl_secs': 15,
        'domain_services': {},
    },
    'cs2_gsi': {
        # Valve Game State Integration. The listener binds IPv4 loopback only
        # and authenticates each POST with a locally generated token.
        'enabled': True,
        'auto_install': True,
        'port': 32192,
        'ttl_secs': 30,
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
            'media': True, 'terminal': True, 'coding': True,
            'browser': True, 'gaming': True, 'application': True
        },
        'activity_priority': {
            # smart: foreground work beats background media, while media wins
            # when its own player/browser is the foreground application.
            'policy': 'smart',
            'custom_order': ['gaming', 'terminal', 'coding', 'browser', 'media', 'application'],
        },
        # Raw command cache is local-only but may contain arguments. Keep it
        # short-lived by default; advanced users can raise it up to seven days.
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

            # Migrate the former user-facing client_id. The old built-in value is
            # discarded; a genuinely custom value is preserved as an advanced
            # override so existing custom setups keep working.
            discord = new_data.get('discord', {})
            if isinstance(discord, dict):
                legacy_id = str(discord.pop('client_id', '') or '').strip()
                current_override = str(discord.get('application_id_override', '') or '').strip()
                if (
                    legacy_id
                    and legacy_id != BUILTIN_DISCORD_APPLICATION_ID
                    and not current_override
                ):
                    discord['application_id_override'] = legacy_id

            self._validate(new_data)
            self.data = new_data
            self.config_path = path
            # Configuration can contain exact URLs, custom rules, and labels.
            # Keep the file private on POSIX even when it predates this release.
            self._chmod_private(path, 0o600)
        except Exception as e:
            raise ValueError(f"Failed to load config from {path}: {e}") from e

    def save(self, path: Optional[Path] = None):
        save_path = Path(path or self.config_path)
        if not save_path:
            raise ValueError('No config path specified')

        self._validate(self.data)
        save_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if save_path == self._get_default_config_path():
            self._chmod_private(save_path.parent, 0o700)

        tmp_path = save_path.with_suffix(save_path.suffix + f'.{os.getpid()}.tmp')
        try:
            fd = os.open(tmp_path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    if _YAML_AVAILABLE:
                        yaml.safe_dump(
                            self.data,
                            f,
                            default_flow_style=False,
                            allow_unicode=True,
                            sort_keys=False,
                        )  # type: ignore
                    else:
                        import json as _json
                        _json.dump(self.data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
            except Exception:
                # fdopen owns fd after construction, but close defensively if
                # construction itself failed.
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
            self._chmod_private(tmp_path, 0o600)
            os.replace(tmp_path, save_path)
            self._chmod_private(save_path, 0o600)
            self.config_path = save_path
        except Exception as e:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise ValueError(f'Failed to save config to {save_path}: {e}') from e

    def get(self, key: str, default: Any = None) -> Any:
        # Runtime compatibility for older code paths while the public config no
        # longer exposes client_id. They transparently receive the built-in ID or
        # the optional advanced override.
        if key == 'discord.client_id':
            discord = self.data.get('discord', {})
            if isinstance(discord, dict):
                override = str(discord.get('application_id_override', '') or '').strip()
                return override or BUILTIN_DISCORD_APPLICATION_ID
            return BUILTIN_DISCORD_APPLICATION_ID

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
    def _validate_url(
        value: Any,
        name: str,
        allow_empty: bool = True,
        *,
        max_length: int = 512,
    ):
        url = str(value or '').strip()
        if not url and allow_empty:
            return
        if not url.startswith(('https://', 'http://')):
            raise ValueError(f'{name} must start with http:// or https://')
        if len(url) > max_length:
            raise ValueError(f'{name} must be at most {max_length} characters')

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
            Config._validate_url(
                button.get('url', ''),
                'Discord button URL',
                allow_empty=False,
                max_length=512,
            )

    @staticmethod
    def _validate_string_list(
        value: Any,
        name: str,
        *,
        max_items: int = _MAX_LIST_ITEMS,
        max_item_length: int = 256,
    ):
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f'{name} must be a list of strings')
        if len(value) > max_items:
            raise ValueError(f'{name} cannot contain more than {max_items} items')
        if any(len(item) > max_item_length for item in value):
            raise ValueError(f'{name} entries must be at most {max_item_length} characters')

    @staticmethod
    def _validate(data: Dict[str, Any]):
        privacy = data.get('privacy', {})
        if not isinstance(privacy, dict):
            raise ValueError('privacy must be an object')
        mode = privacy.get('mode', 'balanced')
        if mode not in {'off', 'balanced', 'strict'}:
            raise ValueError('privacy.mode must be one of: off, balanced, strict')
        browser_url_mode = str(privacy.get('browser_url_mode', 'domain') or 'domain').lower()
        if browser_url_mode not in {'none', 'domain', 'path', 'full'}:
            raise ValueError('privacy.browser_url_mode must be one of: none, domain, path, full')
        if not isinstance(privacy.get('hide_home_paths', True), bool):
            raise ValueError('privacy.hide_home_paths must be true or false')
        redactions = privacy.get('redactions', []) or []
        if not isinstance(redactions, list) or len(redactions) > 64:
            raise ValueError('privacy.redactions must be a list with at most 64 entries')
        for entry in redactions:
            if not isinstance(entry, dict) or not isinstance(entry.get('regex'), str):
                raise ValueError('Each privacy.redactions entry must contain a regex string')
            regex = entry['regex']
            if len(regex) > 512:
                raise ValueError('privacy.redactions regex strings must be at most 512 characters')
            try:
                re.compile(regex)
            except re.error as e:
                raise ValueError(f"Invalid privacy regex {regex!r}: {e}") from e

        interval = data.get('update_interval_secs', 2)
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
        if not isinstance(companion.get('enabled', True), bool):
            raise ValueError('browser_companion.enabled must be true or false')
        port = companion.get('port', 32191)
        if isinstance(port, bool) or not isinstance(port, int) or port < 1024 or port > 65535:
            raise ValueError('browser_companion.port must be an integer between 1024 and 65535')
        companion_ttl = companion.get('ttl_secs', 15)
        if (
            isinstance(companion_ttl, bool)
            or not isinstance(companion_ttl, (int, float))
            or companion_ttl < 2
            or companion_ttl > 300
        ):
            raise ValueError('browser_companion.ttl_secs must be between 2 and 300 seconds')
        domain_services = companion.get('domain_services', {}) or {}
        if not isinstance(domain_services, dict):
            raise ValueError('browser_companion.domain_services must be an object')
        if len(domain_services) > _MAX_CUSTOM_SERVICES:
            raise ValueError(
                f'browser_companion.domain_services cannot exceed {_MAX_CUSTOM_SERVICES} entries'
            )
        for pattern, label in domain_services.items():
            if not isinstance(pattern, str) or not isinstance(label, str):
                raise ValueError('browser_companion.domain_services keys and values must be strings')
            domain = pattern.strip().lower()
            name = label.strip()
            check_domain = domain[2:] if domain.startswith('*.') else domain
            if (
                not domain
                or len(domain) > 255
                or '://' in domain
                or '/' in domain
                or ':' in domain
                or any(char.isspace() for char in domain)
                or not check_domain
                or check_domain.startswith('.')
                or check_domain.endswith('.')
            ):
                raise ValueError(f'Invalid browser_companion domain pattern: {pattern!r}')
            if not (1 <= len(name) <= 80):
                raise ValueError('browser_companion.domain_services labels must be 1-80 characters')

        cs2 = data.get('cs2_gsi', {})
        if not isinstance(cs2, dict):
            raise ValueError('cs2_gsi must be an object')
        for key in ('enabled', 'auto_install'):
            if not isinstance(cs2.get(key, True), bool):
                raise ValueError(f'cs2_gsi.{key} must be true or false')
        cs2_port = cs2.get('port', 32192)
        if (
            isinstance(cs2_port, bool)
            or not isinstance(cs2_port, int)
            or cs2_port < 1024
            or cs2_port > 65535
        ):
            raise ValueError('cs2_gsi.port must be an integer between 1024 and 65535')
        cs2_ttl = cs2.get('ttl_secs', 30)
        if (
            isinstance(cs2_ttl, bool)
            or not isinstance(cs2_ttl, (int, float))
            or cs2_ttl < 5
            or cs2_ttl > 300
        ):
            raise ValueError('cs2_gsi.ttl_secs must be between 5 and 300 seconds')

        images = data.get('images', {})
        if not isinstance(images, dict):
            raise ValueError('images must be an object')
        if not isinstance(images.get('use_external_app_icons', True), bool):
            raise ValueError('images.use_external_app_icons must be true or false')
        icon_overrides = images.get('icon_overrides', {}) or {}
        if not isinstance(icon_overrides, dict) or len(icon_overrides) > 256:
            raise ValueError('images.icon_overrides must be an object with at most 256 entries')
        for key, value in icon_overrides.items():
            if not isinstance(key, str) or not key.strip() or len(key) > 128:
                raise ValueError('images.icon_overrides keys must be 1-128 character strings')
            if not isinstance(value, str) or not (1 <= len(value.strip()) <= 300):
                raise ValueError('images.icon_overrides values must be 1-300 character asset keys or URLs')

        discord = data.get('discord', {})
        if not isinstance(discord, dict):
            raise ValueError('discord must be an object')
        application_id_override = str(discord.get('application_id_override', '') or '').strip()
        if application_id_override and (
            not application_id_override.isdigit() or len(application_id_override) > 32
        ):
            raise ValueError(
                'discord.application_id_override must be empty or a numeric Discord application ID'
            )
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

        priority = rules.get('activity_priority', {})
        if not isinstance(priority, dict):
            raise ValueError('rules.activity_priority must be an object')
        priority_policy = str(priority.get('policy', 'smart') or 'smart').lower()
        if priority_policy not in {'smart', 'foreground_first', 'media_first', 'custom'}:
            raise ValueError(
                'rules.activity_priority.policy must be one of: smart, foreground_first, media_first, custom'
            )
        custom_order = priority.get('custom_order', []) or []
        Config._validate_string_list(custom_order, 'rules.activity_priority.custom_order', max_items=6)
        known_priority_kinds = {'gaming', 'terminal', 'coding', 'browser', 'media', 'application'}
        normalized_order = [str(item).lower() for item in custom_order]
        if any(item not in known_priority_kinds for item in normalized_order):
            raise ValueError('rules.activity_priority.custom_order contains an unknown activity type')
        if len(normalized_order) != len(set(normalized_order)):
            raise ValueError('rules.activity_priority.custom_order cannot contain duplicates')

        ttl = rules.get('terminal_command_ttl_secs', 900)
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or ttl < 0 or ttl > 604800:
            raise ValueError('rules.terminal_command_ttl_secs must be between 0 and 604800')
        if not isinstance(rules.get('clear_on_lock_screen', True), bool):
            raise ValueError('rules.clear_on_lock_screen must be true or false')
        for key in ('youtube_domains', 'private_markers'):
            Config._validate_string_list(rules.get(key, []), f'rules.{key}', max_items=64)
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
            Config._validate_url(
                override.get(key, ''),
                f'override.{key}',
                max_length=256,
            )
        for key in ('details', 'state', 'large_text', 'small_text', 'party_id'):
            value = override.get(key, '')
            if not isinstance(value, str) or len(value) > 512:
                raise ValueError(f'override.{key} must be a string with at most 512 characters')
        for key in ('large_image_key', 'small_image_key'):
            value = override.get(key, '')
            if not isinstance(value, str) or len(value) > 300:
                raise ValueError(f'override.{key} must be a string with at most 300 characters')
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
