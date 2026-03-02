"""
Terminal activity detection
"""

import os
import platform
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from config import Config


class TerminalDetector:
    """Detects terminal activity and running commands"""
    
    TERMINALS = {
        # Linux terminals
        'gnome-terminal': 'GNOME Terminal',
        'konsole': 'Konsole',
        'xterm': 'XTerm',
        'kitty': 'Kitty',
        'alacritty': 'Alacritty',
        'terminator': 'Terminator',
        'tilix': 'Tilix',
        'urxvt': 'URxvt',
        'st': 'Simple Terminal',
        'wezterm': 'WezTerm',
        'foot': 'Foot',
        # Windows terminals
        'powershell': 'PowerShell',
        'pwsh': 'PowerShell Core',
        'cmd': 'Command Prompt',
        'windowsterminal': 'Windows Terminal',
        'conhost': 'Console Host',
        'wt': 'Windows Terminal',
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform.system().lower()
        
        if self.platform_name == 'windows':
            # Use Windows-specific paths
            cache_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'discord-rich-presence' / 'cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.cmd_file = cache_dir / 'rp_last_cmd.txt'
            self.pid_file = cache_dir / 'rp_last_pid.txt'
        else:
            # Use Linux paths
            cache_dir = Path.home() / '.cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.cmd_file = cache_dir / 'rp_last_cmd'
            self.pid_file = cache_dir / 'rp_last_pid'
    
    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect if window is a terminal and extract activity"""
        if not window_info:
            return None
        
        if not self.config.get('rules.enabled_detectors.terminal', True):
            return None
        
        app_name = window_info.get('app_name', '').lower()
        title = window_info.get('title', '')
        
        # Check if it's a terminal
        terminal_name = None
        for key, name in self.TERMINALS.items():
            if key in app_name:
                terminal_name = name
                break
        
        if not terminal_name:
            return None
        
        # Try to get last command from cache file
        command = self._get_last_command()
        
        # Try to extract shell and directory from title
        shell, directory = self._parse_terminal_title(title)
        
        return {
            'type': 'terminal',
            'terminal_name': terminal_name,
            'command': command,
            'shell': shell or terminal_name,
            'directory': directory,
            'has_command': bool(command)
        }
    
    def _get_last_command(self) -> str:
        """Read last command from cache file"""
        try:
            if self.cmd_file.exists():
                with open(self.cmd_file, 'r', encoding='utf-8') as f:
                    command = f.read().strip()
                    
                    # Filter out empty or very short commands
                    if len(command) > 1:
                        return command
        except Exception as e:
            self.logger.debug(f"Failed to read command file: {e}")
        
        return ''
    
    def _parse_terminal_title(self, title: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse terminal title to extract shell and directory
        Common formats:
        - "user@host:~/path"
        - "~/path - bash"
        - "bash: ~/path"
        """
        shell = None
        directory = None
        
        if not title:
            return shell, directory
        
        # Try to detect shell from title
        shells = ['bash', 'zsh', 'fish', 'sh', 'ksh', 'tcsh']
        for s in shells:
            if s in title.lower():
                shell = s
                break
        
        # Try to extract directory
        # Format: user@host:~/path
        if ':' in title and '~' in title:
            parts = title.split(':', 1)
            if len(parts) > 1:
                path = parts[1].strip()
                # Remove trailing shell name if present
                for s in shells:
                    if path.endswith(f' - {s}'):
                        path = path.rsplit(f' - {s}', 1)[0]
                
                directory = path
        
        # Format: ~/path
        elif title.startswith('~'):
            directory = title.split()[0]
        
        return shell, directory
