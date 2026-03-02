"""
Terminal activity detection for Windows
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from config import Config


class WindowsTerminalDetector:
    """Detects terminal activity on Windows"""
    
    TERMINALS = {
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
        
        # Use Windows-specific cache location
        cache_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'discord-rich-presence' / 'cache'
        self.cmd_file = cache_dir / 'rp_last_cmd.txt'
        self.pid_file = cache_dir / 'rp_last_pid.txt'
    
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
        
        # Try to extract directory from title
        directory = self._parse_terminal_title(title)
        
        return {
            'type': 'terminal',
            'terminal_name': terminal_name,
            'command': command,
            'shell': terminal_name,
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
    
    def _parse_terminal_title(self, title: str) -> Optional[str]:
        """
        Parse terminal title to extract directory
        Common formats:
        - "PowerShell - C:\\Users\\username\\path"
        - "C:\\Users\\username\\path"
        - "Administrator: PowerShell"
        """
        if not title:
            return None
        
        # Try to find path in title
        # Look for drive letter patterns (C:\, D:\, etc.)
        import re
        path_pattern = r'[A-Z]:\\[^\s\|]*'
        matches = re.findall(path_pattern, title)
        
        if matches:
            # Return the last match (usually the current directory)
            path = matches[-1]
            
            # Convert to short form if it's in user directory
            userprofile = os.environ.get('USERPROFILE', '')
            if userprofile and path.startswith(userprofile):
                path = path.replace(userprofile, '~')
            
            return path
        
        return None
