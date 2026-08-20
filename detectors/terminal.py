"""Terminal activity detection using optional shell hooks."""

import os
import platform
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from config import Config


class TerminalDetector:
    TERMINALS = {
        'gnome-terminal': 'GNOME Terminal', 'konsole': 'Konsole', 'xterm': 'XTerm',
        'kitty': 'Kitty', 'alacritty': 'Alacritty', 'terminator': 'Terminator',
        'tilix': 'Tilix', 'urxvt': 'URxvt', 'wezterm': 'WezTerm', 'foot': 'Foot',
        'powershell': 'PowerShell', 'pwsh': 'PowerShell Core', 'cmd': 'Command Prompt',
        'windowsterminal': 'Windows Terminal', 'conhost': 'Console Host', 'wt': 'Windows Terminal',
    }

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform.system().lower()
        if self.platform_name == 'windows':
            base = os.environ.get('LOCALAPPDATA')
            cache_dir = (Path(base) if base else Path.home() / 'AppData' / 'Local') / 'discord-rich-presence' / 'cache'
            self.cmd_file = cache_dir / 'rp_last_cmd.txt'
        else:
            self.cmd_file = Path.home() / '.cache' / 'discord-rich-presence' / 'rp_last_cmd'
        self.cmd_file.parent.mkdir(parents=True, exist_ok=True)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not window_info or not self.config.get('rules.enabled_detectors.terminal', True):
            return None

        app_name = str(window_info.get('app_name', '')).lower()
        title = str(window_info.get('title', ''))
        terminal_name = None
        for key, name in self.TERMINALS.items():
            if key in app_name:
                terminal_name = name
                break
        if not terminal_name:
            return None

        command = self._get_last_command()
        shell, directory = self._parse_terminal_title(title)
        return {
            'type': 'terminal', 'terminal_name': terminal_name,
            'command': command, 'shell': shell or terminal_name,
            'directory': directory or '', 'has_command': bool(command)
        }

    def _get_last_command(self) -> str:
        try:
            if not self.cmd_file.exists():
                return ''
            ttl = int(self.config.get('rules.terminal_command_ttl_secs', 21600) or 21600)
            if ttl > 0 and time.time() - self.cmd_file.stat().st_mtime > ttl:
                return ''
            command = self.cmd_file.read_text(encoding='utf-8', errors='replace').strip()
            if len(command) <= 1:
                return ''
            # Avoid recursively publishing the hook implementation itself.
            if 'rp_last_cmd' in command or '__drp_' in command:
                return ''
            return command[:2048]
        except (OSError, ValueError) as e:
            self.logger.debug('Failed to read terminal command cache: %s', e)
            return ''

    def _parse_terminal_title(self, title: str) -> tuple[Optional[str], Optional[str]]:
        if not title:
            return None, None
        title_lower = title.lower()
        shell = next((s for s in ('powershell', 'pwsh', 'bash', 'zsh', 'fish', 'ksh', 'tcsh') if s in title_lower), None)

        if self.platform_name == 'windows':
            import re
            matches = re.findall(r'[A-Za-z]:\\[^|]*', title)
            directory = matches[-1].strip() if matches else None
            if directory:
                profile = os.environ.get('USERPROFILE', '')
                if profile and directory.lower().startswith(profile.lower()):
                    directory = '~' + directory[len(profile):]
            return shell, directory

        directory = None
        if ':' in title and '~' in title:
            directory = title.split(':', 1)[1].strip()
            for candidate in ('bash', 'zsh', 'fish', 'sh', 'ksh', 'tcsh'):
                suffix = f' - {candidate}'
                if directory.endswith(suffix):
                    directory = directory[:-len(suffix)]
        elif title.startswith('~'):
            directory = title.split()[0]
        return shell, directory
