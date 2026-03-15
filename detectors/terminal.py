import os
import re
import logging
from typing import Optional, Dict, Any
from config import Config
from core.activity_model import ActivityState
import time

class TerminalDetector:
    TERMINALS = {
        'powershell': 'PowerShell',
        'pwsh': 'PowerShell Core',
        'cmd': 'Command Prompt',
        'windowsterminal': 'Windows Terminal',
        'conhost': 'Console Host',
        'wt': 'Windows Terminal',
        'gnome-terminal': 'GNOME Terminal',
        'konsole': 'Konsole',
        'xterm': 'XTerm',
        'kitty': 'Kitty',
        'alacritty': 'Alacritty',
        'terminator': 'Terminator',
        'bash': 'Bash Shell',
        'zsh': 'Zsh Shell',
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._start_time = int(time.time())

    def REDACT_SENSITIVE(self, command: str) -> str:
        s = command.lower()
        if any(w in s for w in ['password', 'token', 'secret', 'key', 'login']):
            return "[REDACTED COMMAND]"
        
        parts = command.split()
        safe_parts = []
        for p in parts:
            if '=' in p and len(p) > 10:
                safe_parts.append(p.split('=')[0] + '=[...]')
            elif p.startswith('--') and len(p) > 20: 
                safe_parts.append('[...]')
            else:
                safe_parts.append(p)
        return " ".join(safe_parts)

    def detect(self, window_info: Dict[str, Any]) -> Optional[ActivityState]:
        if not self.config.get('rules.enabled_detectors.terminal', True):
            return None
            
        app_name = window_info.get('app_name', '').lower()
        title = window_info.get('title', '')
        cwd = window_info.get('cwd', '')
        
        terminal_name = None
        for key, name in self.TERMINALS.items():
            if key in app_name or key in title.lower():
                terminal_name = name
                break
                
        if not terminal_name:
            return None

        directory = cwd if cwd else ""
        if not directory and ":" in title:
            path_pattern = r'[A-Z]:\\[^\s\|]*'
            matches = re.findall(path_pattern, title)
            if matches:
                directory = matches[-1]
                
        if directory:
            home = str(os.path.expanduser('~'))
            if directory.startswith(home):
                directory = directory.replace(home, '~')
            
        state = f"{terminal_name}"
        if directory:
            state += f" · {directory}"
            
        details = "Terminal Active"
            
        return ActivityState(
            type="terminal",
            details=details,
            state=state,
            large_image=self.config.get('images.terminal', 'terminal'),
            large_text=terminal_name,
            start_time=self._start_time
        )
