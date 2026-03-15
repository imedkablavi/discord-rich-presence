import logging
from typing import Optional, Dict, Any
from .base_window_reader import BaseWindowReader

try:
    import win32gui
    import win32process
    import psutil
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

class WindowsWindowReader(BaseWindowReader):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if not WINDOWS_AVAILABLE:
            self.logger.warning("Windows libraries not available (win32gui, psutil)")

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        if not WINDOWS_AVAILABLE:
            return None
            
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                return None
                
            title = win32gui.GetWindowText(hwnd)
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                return None
                
            if pid <= 0:
                return None
                
            exe_path = ""
            cwd = ""
            app_name = "Unknown"
            
            try:
                process = psutil.Process(pid)
                app_name = process.name()
                try:
                    exe_path = process.exe()
                    cwd = process.cwd()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
            if app_name.lower().endswith('.exe'):
                app_name = app_name[:-4]
                
            friendly = {
                'code': 'VS Code',
                'code - insiders': 'VS Code Insiders',
                'msedge': 'Edge',
                'chrome': 'Chrome',
                'firefox': 'Firefox',
                'brave': 'Brave',
                'opera': 'Opera',
                'vivaldi': 'Vivaldi',
                'explorer': 'Explorer',
                'cmd': 'Command Prompt',
                'conhost': 'Console Host',
                'powershell': 'PowerShell',
                'pwsh': 'PowerShell Core',
                'trae': 'Trae',
                'python': 'Python',
                'notepad': 'Notepad',
                'notepad++': 'Notepad++',
                'discord': 'Discord',
                'spotify': 'Spotify',
                'vlc': 'VLC',
            }
            normalized = app_name.lower()
            if normalized in friendly:
                app_name = friendly[normalized]
                
            return {
                'window_id': str(hwnd),
                'app_name': app_name,
                'title': title,
                'pid': pid,
                'exe_path': exe_path,
                'cwd': cwd
            }
        except Exception as e:
            self.logger.debug(f"Error getting Windows window: {e}")
            return None
