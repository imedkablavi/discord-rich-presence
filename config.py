"""
Configuration management for Discord Rich Presence Service
"""

import os
import platform
try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except Exception:
    yaml = None  # type: ignore
    _YAML_AVAILABLE = False
    import json
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG = {
    'discord': {
        'client_id': '1437867564762923028',  # Default App ID
        'buttons': []
    },
    'privacy': {
        'mode': 'balanced',  # off | balanced | strict
        'redactions': [
            {'regex': r'(?i)(password|token|secret|key|api[_-]?key)\S*'},
            {'regex': r'([A-Fa-f0-9]{32,})'},  # Long hex strings
        ],
        'hide_home_paths': True
    },
    'update_interval_secs': 5,  # Faster update by default
    'system': {
        'start_minimized': False,
        'auto_start': False
    },
    'images': {
        'browser': 'browser',
        'video': 'video',
        'terminal': 'terminal',
        'code': 'code',
        'app': 'app',
        'apps': {
            'explorer': 'explorer',
            'chrome': 'chrome',
            'msedge': 'edge',
            'edge': 'edge',
            'firefox': 'firefox',
            'brave': 'brave',
            'opera': 'opera',
            'vivaldi': 'vivaldi',
            'code': 'vscode',
            'vs code': 'vscode',
            'pycharm': 'pycharm',
            'trae': 'trae',
            'powershell': 'powershell',
            'cmd': 'cmd'
        },
        'langs': {
            'python': 'py',
            'javascript': 'js',
            'typescript': 'ts',
            'cpp': 'cpp',
            'c': 'c',
            'java': 'java',
            'go': 'go',
            'rust': 'rust',
            'php': 'php',
            'ruby': 'ruby',
            'swift': 'swift',
            'kotlin': 'kotlin',
            'dart': 'dart',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'yaml': 'yaml',
            'markdown': 'md',
        }
        ,
        'players': {
            'spotify': 'spotify',
            'vlc': 'vlc',
            'chrome': 'chrome',
            'edge': 'edge',
            'firefox': 'firefox',
            'mpv': 'mpv',
            'windows media player': 'wmp'
        },
        'sites': {
            'youtube': 'youtube',
            'netflix': 'netflix',
            'hulu': 'hulu',
            'prime video': 'prime'
        },
        'games': {
            'league of legends': 'lol',
            'valorant': 'valorant',
            'minecraft': 'minecraft',
            'rocket league': 'rocketleague',
            'fortnite': 'fortnite',
            'apex legends': 'apex',
            'grand theft auto v': 'gtav',
            'dota 2': 'dota2'
        }
    },
    'rules': {
        'youtube_domains': ['YouTube', 'youtu.be'],
        'private_markers': ['Incognito', 'Private Browsing', 'InPrivate'],
        'enabled_detectors': {
            'media': True,
            'terminal': True,
            'coding': True,
            'browser': True,
            'gaming': True
        },
        'whitelist': {
            'apps': [],
            'sites': [],
            'games': []
        },
        'blacklist': {
            'apps': [],
            'sites': [],
            'games': []
        }
    },
    'override': {
        'enabled': False,
        'details': '',
        'state': '',
        'use_start_timestamp': False,
        'large_image_key': '',
        'large_text': '',
        'small_image_key': '',
        'small_text': '',
        'details_url': '',
        'state_url': '',
        'large_url': '',
        'small_url': '',
        'party_id': '',
        'party_current': 0,
        'party_max': 0,
        'buttons': []
    }
}


class Config:
    """Configuration manager with nested key access"""
    
    def __init__(self, config_path: Optional[Path] = None):
        # Use platform-specific default path if not provided
        if config_path is None:
            config_path = self._get_default_config_path()
        
        self.config_path = config_path
        self.data = DEFAULT_CONFIG.copy()
        
        if config_path and config_path.exists():
            self.load(config_path)
    
    def load(self, path: Path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if _YAML_AVAILABLE:
                    user_config = yaml.safe_load(f)  # type: ignore
                else:
                    user_config = json.load(f)
                if user_config:
                    self._deep_update(self.data, user_config)
        except Exception as e:
            raise ValueError(f"Failed to load config from {path}: {e}")
    
    def save(self, path: Optional[Path] = None):
        save_path = path or self.config_path
        if not save_path:
            raise ValueError("No config path specified")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write: write to temp file then rename
        tmp_path = save_path.with_suffix('.tmp')
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                if _YAML_AVAILABLE:
                    yaml.safe_dump(self.data, f, default_flow_style=False, allow_unicode=True)  # type: ignore
                else:
                    import json as _json
                    _json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            # Atomic rename with retry for Windows
            import time
            max_retries = 3
            for i in range(max_retries):
                try:
                    if os.path.exists(save_path):
                        os.replace(tmp_path, save_path)
                    else:
                        os.rename(tmp_path, save_path)
                    break
                except PermissionError:
                    if i == max_retries - 1:
                        raise
                    time.sleep(0.1)
                except OSError:
                    # On Windows, os.replace might fail if destination exists
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    os.rename(tmp_path, save_path)
                    break
        except Exception as e:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except:
                    pass
            raise ValueError(f"Failed to save config to {save_path}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        Example: config.get('privacy.mode')
        """
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        Example: config.set('privacy.mode', 'strict')
        """
        keys = key.split('.')
        data = self.data
        
        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]
        
        data[keys[-1]] = value
    
    def _deep_update(self, base: Dict, update: Dict):
        """Recursively update nested dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    @staticmethod
    def _get_default_config_path() -> Path:
        """Get platform-specific default config path"""
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows: %APPDATA%\discord-rich-presence\config.yaml
            config_dir = Path(os.environ.get('APPDATA', '')) / 'discord-rich-presence'
        else:
            # Linux/Mac: ~/.config/discord-rich-presence/config.yaml
            config_dir = Path.home() / '.config' / 'discord-rich-presence'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'config.yaml'
