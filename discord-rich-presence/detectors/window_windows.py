"""
Active window detection for Windows
"""

import logging
from typing import Optional, Dict, Any

try:
    import win32gui
    import win32process
    import psutil
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False


class WindowsWindowDetector:
    """Detects active window information on Windows"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not WINDOWS_AVAILABLE:
            self.logger.warning("Windows libraries not available (win32gui, psutil)")
            self.logger.warning("Install with: pip install pywin32 psutil")
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active window"""
        if not WINDOWS_AVAILABLE:
            return None
        
        try:
            # Get foreground window handle
            hwnd = win32gui.GetForegroundWindow()
            
            # Check if handle is valid
            if not hwnd or not win32gui.IsWindow(hwnd):
                return None
                
            # Skip hidden windows or taskbar
            if not win32gui.IsWindowVisible(hwnd):
                return None
            
            # Get window title
            title = win32gui.GetWindowText(hwnd)
            
            # Get process ID
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                return None
                
            if pid <= 0:
                return None
            
            # Get process information
            exe_path = ""
            app_name = "Unknown"
            
            try:
                process = psutil.Process(pid)
                app_name = process.name()
                try:
                    exe_path = process.exe()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process might have died or is protected
                pass
            
            # Clean app name (remove .exe) and normalize
            if app_name.lower().endswith('.exe'):
                app_name = app_name[:-4]
            
            normalized = app_name.lower()
            
            # Friendly name mapping
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
                'applicationframehost': 'App Host',
                'discord': 'Discord',
                'spotify': 'Spotify',
                'vlc': 'VLC',
            }
            
            if normalized in friendly:
                app_name = friendly[normalized]
            
            window_info = {
                'window_id': str(hwnd),
                'app_name': app_name,
                'title': title,
                'pid': pid,
                'exe_path': exe_path
            }
            
            return window_info
            
        except Exception as e:
            self.logger.debug(f"Error getting Windows window: {e}")
            return None
    
    @staticmethod
    def is_available() -> bool:
        """Check if Windows detection is available"""
        return WINDOWS_AVAILABLE
