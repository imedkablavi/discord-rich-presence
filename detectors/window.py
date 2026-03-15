"""
Active window detection for X11 and Wayland
"""

import os
import platform
import subprocess
import logging
from typing import Optional, Dict, Any


class WindowDetector:
    """Detects active window information on X11 and Wayland"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform.system().lower()
        
        if self.platform_name == 'windows':
            try:
                from .window_windows import WindowsWindowDetector
                self.windows_detector = WindowsWindowDetector()
                self.logger.info("Using Windows window detector")
            except ImportError:
                self.logger.error("Windows detector not available")
                self.windows_detector = None
        else:
            self.windows_detector = None
            self.session_type = os.environ.get('XDG_SESSION_TYPE', 'x11').lower()
            self.logger.info(f"Detected session type: {self.session_type}")
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active window"""
        if self.platform_name == 'windows':
            if self.windows_detector:
                return self.windows_detector.get_active_window()
            return None
        elif self.session_type == 'wayland':
            return self._get_active_window_wayland()
        else:
            return self._get_active_window_x11()
    
    def _get_active_window_x11(self) -> Optional[Dict[str, Any]]:
        """Get active window info on X11 using xprop"""
        try:
            # Get active window ID
            result = subprocess.run(
                ['xprop', '-root', '_NET_ACTIVE_WINDOW'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                return None
            
            # Extract window ID
            output = result.stdout.strip()
            if 'window id #' not in output.lower():
                return None
            
            window_id = output.split()[-1]
            
            # Get window properties
            result = subprocess.run(
                ['xprop', '-id', window_id, 'WM_CLASS', 'WM_NAME', '_NET_WM_NAME', '_NET_WM_PID'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                return None
            
            props = result.stdout
            
            # Parse properties
            pid = self._extract_pid(props)
            cwd = self._get_cwd_from_pid(pid) if pid else None
            
            window_info = {
                'window_id': window_id,
                'app_name': self._extract_wm_class(props),
                'title': self._extract_wm_name(props),
                'pid': pid,
                'cwd': cwd
            }
            
            return window_info
            
        except subprocess.TimeoutExpired:
            self.logger.warning("xprop command timed out")
            return None
        except FileNotFoundError:
            self.logger.warning("xprop not found, install x11-utils")
            return None
        except Exception as e:
            self.logger.error(f"Error getting X11 window: {e}")
            return None
    
    def _get_active_window_wayland(self) -> Optional[Dict[str, Any]]:
        """
        Get active window info on Wayland (fallback method)
        Wayland doesn't expose window info easily, so we use process inspection
        """
        try:
            # Try to get focused window from swaymsg (if using Sway)
            if self._command_exists('swaymsg'):
                return self._get_sway_window()
            
            # Try GNOME Shell extension (if available)
            # This would require a custom extension, so we fall back to process inspection
            
            # Fallback: inspect running processes
            return self._get_window_from_processes()
            
        except Exception as e:
            self.logger.error(f"Error getting Wayland window: {e}")
            return None
    
    def _get_sway_window(self) -> Optional[Dict[str, Any]]:
        """Get focused window from Sway compositor"""
        try:
            import json
            
            result = subprocess.run(
                ['swaymsg', '-t', 'get_tree'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                return None
            
            tree = json.loads(result.stdout)
            focused = self._find_focused_node(tree)
            
            if focused:
                return {
                    'app_name': focused.get('app_id') or focused.get('window_properties', {}).get('class', 'Unknown'),
                    'title': focused.get('name', ''),
                    'pid': focused.get('pid')
                }
            
        except Exception as e:
            self.logger.debug(f"Sway detection failed: {e}")
        
        return None
    
    def _find_focused_node(self, node: Dict) -> Optional[Dict]:
        """Recursively find focused node in Sway tree"""
        if node.get('focused'):
            return node
        
        for child in node.get('nodes', []) + node.get('floating_nodes', []):
            result = self._find_focused_node(child)
            if result:
                return result
        
        return None
    
    def _get_window_from_processes(self) -> Optional[Dict[str, Any]]:
        """
        Fallback: try to determine active application from running processes
        This is less accurate but works on Wayland
        """
        try:
            # Get list of GUI processes
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                return None
            
            # Look for common GUI applications
            lines = result.stdout.split('\n')
            for line in lines:
                for app in ['firefox', 'chrome', 'chromium', 'code', 'gnome-terminal', 'kitty', 'alacritty']:
                    if app in line.lower() and 'grep' not in line:
                        return {
                            'app_name': app,
                            'title': '',
                            'pid': None
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error inspecting processes: {e}")
            return None
    
    @staticmethod
    def _extract_wm_class(props: str) -> str:
        """Extract application name from WM_CLASS"""
        for line in props.split('\n'):
            if 'WM_CLASS(STRING)' in line:
                # WM_CLASS returns two values, we want the second one
                parts = line.split('=', 1)
                if len(parts) > 1:
                    values = parts[1].strip().strip('"').split('", "')
                    if len(values) > 1:
                        return values[1].strip('"')
                    elif len(values) > 0:
                        return values[0].strip('"')
        return 'Unknown'
    
    @staticmethod
    def _extract_wm_name(props: str) -> str:
        """Extract window title from WM_NAME or _NET_WM_NAME"""
        # Prefer _NET_WM_NAME (UTF-8) over WM_NAME
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
    def _extract_pid(props: str) -> Optional[int]:
        """Extract process ID from _NET_WM_PID"""
        for line in props.split('\n'):
            if '_NET_WM_PID(CARDINAL)' in line:
                parts = line.split('=', 1)
                if len(parts) > 1:
                    try:
                        return int(parts[1].strip())
                    except ValueError:
                        pass
        return None
    
    @staticmethod
    def _get_cwd_from_pid(pid: int) -> Optional[str]:
        """Get current working directory for a given PID"""
        try:
            cwd_link = f'/proc/{pid}/cwd'
            if os.path.islink(cwd_link):
                return os.readlink(cwd_link)
        except Exception:
            pass
        return None
    
    @staticmethod
    def _command_exists(command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            subprocess.run(
                ['which', command],
                capture_output=True,
                timeout=1
            )
            return True
        except:
            return False
