"""Terminal activity detection using optional per-shell command hooks."""

import logging
import os
import platform
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import psutil

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
            self.cache_dir = (
                (Path(base) if base else Path.home() / 'AppData' / 'Local')
                / 'discord-rich-presence' / 'cache'
            )
            self.cmd_file = self.cache_dir / 'rp_last_cmd.txt'
        else:
            self.cache_dir = Path.home() / '.cache' / 'discord-rich-presence'
            self.cmd_file = self.cache_dir / 'rp_last_cmd'
        self.command_dir = self.cache_dir / 'commands'
        self.command_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._secure_cache_paths()

    def _secure_cache_paths(self) -> None:
        if os.name != 'posix':
            return
        for path in (self.cache_dir, self.command_dir):
            try:
                path.mkdir(parents=True, exist_ok=True, mode=0o700)
                os.chmod(path, 0o700)
            except OSError:
                pass
        for path in [self.cmd_file, *self.command_dir.glob('*.txt')]:
            try:
                if path.exists():
                    os.chmod(path, 0o600)
            except OSError:
                pass

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

        command = self._get_last_command(window_info.get('pid'))
        shell, directory = self._parse_terminal_title(title)
        return {
            'type': 'terminal', 'terminal_name': terminal_name,
            'command': command, 'shell': shell or terminal_name,
            'directory': directory or '', 'has_command': bool(command)
        }

    def _ttl(self) -> int:
        try:
            return max(0, int(self.config.get('rules.terminal_command_ttl_secs', 900) or 900))
        except (TypeError, ValueError):
            return 900

    def _is_fresh(self, path: Path) -> bool:
        ttl = self._ttl()
        try:
            return ttl <= 0 or time.time() - path.stat().st_mtime <= ttl
        except OSError:
            return False

    @staticmethod
    def _read_command(path: Path) -> str:
        try:
            command = path.read_text(encoding='utf-8', errors='replace').strip()
        except OSError:
            return ''
        if len(command) <= 1:
            return ''
        if 'rp_last_cmd' in command or '__drp_' in command or 'Write-DrpCommandCache' in command:
            return ''
        return command[:2048]

    def _candidate_process_ids(self, window_pid: Any) -> set[int]:
        try:
            pid = int(window_pid)
        except (TypeError, ValueError):
            return set()
        if pid <= 0:
            return set()

        candidates = {pid}
        try:
            process = psutil.Process(pid)
            for child in process.children(recursive=True):
                candidates.add(int(child.pid))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        return candidates

    def _matching_command_files(self, process_ids: Iterable[int]) -> list[Path]:
        files = []
        for pid in process_ids:
            path = self.command_dir / f'{int(pid)}.txt'
            if path.exists() and self._is_fresh(path):
                files.append(path)
        try:
            files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        except OSError:
            pass
        return files

    def _fresh_pid_command_files(self) -> list[Path]:
        try:
            return [path for path in self.command_dir.glob('*.txt') if self._is_fresh(path)]
        except OSError:
            return []

    def _cleanup_command_cache(self):
        """Bound stale command files and delete expired legacy command data."""
        try:
            files = list(self.command_dir.glob('*.txt'))
            stale = [path for path in files if not self._is_fresh(path)]
            for path in stale:
                try:
                    path.unlink()
                except OSError:
                    pass
            remaining = [path for path in files if path.exists()]
            if len(remaining) > 100:
                remaining.sort(key=lambda path: path.stat().st_mtime, reverse=True)
                for path in remaining[100:]:
                    try:
                        path.unlink()
                    except OSError:
                        pass
            if self.cmd_file.exists() and not self._is_fresh(self.cmd_file):
                try:
                    self.cmd_file.unlink()
                except OSError:
                    pass
            self._secure_cache_paths()
        except OSError:
            pass

    def _get_last_command(self, window_pid: Any = None) -> str:
        try:
            self._cleanup_command_cache()
            candidates = self._candidate_process_ids(window_pid)
            for path in self._matching_command_files(candidates):
                command = self._read_command(path)
                if command:
                    return command

            # If new PID-scoped hooks are active but none match this focused terminal,
            # returning the global cache could leak a command from another terminal.
            # Only use the old global cache when there are no fresh PID-scoped files.
            if self._fresh_pid_command_files():
                return ''

            if self.cmd_file.exists() and self._is_fresh(self.cmd_file):
                return self._read_command(self.cmd_file)
        except (OSError, ValueError) as e:
            self.logger.debug('Failed to read terminal command cache: %s', e)
        return ''

    def _parse_terminal_title(self, title: str) -> tuple[Optional[str], Optional[str]]:
        if not title:
            return None, None
        title_lower = title.lower()
        shell = next(
            (s for s in ('powershell', 'pwsh', 'bash', 'zsh', 'fish', 'ksh', 'tcsh') if s in title_lower),
            None,
        )

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
