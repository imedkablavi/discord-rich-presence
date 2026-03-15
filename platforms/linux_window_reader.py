import os
import subprocess
import logging
from typing import Optional, Dict, Any
from .base_window_reader import BaseWindowReader

class LinuxWindowReader(BaseWindowReader):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session_type = os.environ.get('XDG_SESSION_TYPE', 'x11').lower()

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        if self.session_type == 'wayland':
            return self._get_active_window_wayland()
        else:
            return self._get_active_window_x11()

    def _get_active_window_x11(self) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'], capture_output=True, text=True, timeout=2)
            if result.returncode != 0: return None
            output = result.stdout.strip()
            if 'window id #' not in output.lower(): return None
            
            window_id = output.split()[-1]
            result = subprocess.run(['xprop', '-id', window_id, 'WM_CLASS', 'WM_NAME', '_NET_WM_NAME', '_NET_WM_PID'],
                                    capture_output=True, text=True, timeout=2)
            if result.returncode != 0: return None
            props = result.stdout
            
            pid = self._extract_pid(props)
            cwd = self._get_cwd_from_pid(pid) if pid else None
            
            app_name = self._extract_wm_class(props)
            title = self._extract_wm_name(props)
            
            return {
                'window_id': window_id,
                'app_name': app_name,
                'title': title,
                'pid': pid,
                'cwd': cwd
            }
        except Exception as e:
            self.logger.debug(f"X11 error: {e}")
            return None

    def _get_active_window_wayland(self) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    for app in ['firefox', 'chrome', 'chromium', 'code', 'gnome-terminal', 'kitty', 'alacritty']:
                        if app in line.lower() and 'grep' not in line:
                            return {'app_name': app, 'title': '', 'pid': None, 'cwd': None}
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_pid(props: str) -> Optional[int]:
        for line in props.split('\n'):
            if '_NET_WM_PID(CARDINAL)' in line:
                parts = line.split('=', 1)
                if len(parts) > 1:
                    try: return int(parts[1].strip())
                    except ValueError: pass
        return None

    @staticmethod
    def _extract_wm_class(props: str) -> str:
        for line in props.split('\n'):
            if 'WM_CLASS(STRING)' in line:
                parts = line.split('=', 1)
                if len(parts) > 1:
                    values = parts[1].strip().strip('"').split('", "')
                    return values[1].strip('"') if len(values) > 1 else values[0].strip('"') if values else 'Unknown'
        return 'Unknown'

    @staticmethod
    def _extract_wm_name(props: str) -> str:
        for line in props.split('\n'):
            if '_NET_WM_NAME(UTF8_STRING)' in line:
                parts = line.split('=', 1)
                if len(parts) > 1:
                    return parts[1].strip().strip('"')
        for line in props.split('\n'):
            if 'WM_NAME(STRING)' in line:
                parts = line.split('=', 1)
                if len(parts) > 1:
                    return parts[1].strip().strip('"')
        return ''

    @staticmethod
    def _get_cwd_from_pid(pid: int) -> Optional[str]:
        try:
            cwd_link = f'/proc/{pid}/cwd'
            if os.path.islink(cwd_link):
                return os.readlink(cwd_link)
        except Exception:
            pass
        return None
