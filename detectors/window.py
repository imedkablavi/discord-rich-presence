"""Foreground-window detection for Windows, Linux/X11, and Sway."""

import json
import logging
import os
import platform
import shutil
import subprocess
from typing import Optional, Dict, Any


class WindowDetector:
    """Return foreground-window metadata only when it can be determined reliably."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform.system().lower()
        self.windows_detector = None
        self.session_type = ''

        if self.platform_name == 'windows':
            try:
                from .window_windows import WindowsWindowDetector
                self.windows_detector = WindowsWindowDetector()
                self.logger.info('Using Windows foreground-window detector')
            except ImportError as e:
                self.logger.error('Windows foreground-window detector unavailable: %s', e)
        elif self.platform_name == 'linux':
            self.session_type = os.environ.get('XDG_SESSION_TYPE', 'x11').lower()
            self.logger.info('Detected Linux session type: %s', self.session_type)
        else:
            self.logger.warning(
                'Foreground-window detection is not implemented for %s; activity publishing is disabled',
                self.platform_name or 'this platform',
            )

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        if self.platform_name == 'windows':
            return self.windows_detector.get_active_window() if self.windows_detector else None
        if self.platform_name != 'linux':
            return None
        if self.session_type == 'wayland':
            return self._get_active_window_wayland()
        return self._get_active_window_x11()

    def _get_active_window_x11(self) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ['xprop', '-root', '_NET_ACTIVE_WINDOW'],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode != 0:
                return None
            output = result.stdout.strip()
            if 'window id #' not in output.lower():
                return None
            window_id = output.split()[-1]
            if window_id in {'0x0', '0'}:
                return None

            result = subprocess.run(
                ['xprop', '-id', window_id, 'WM_CLASS', 'WM_NAME', '_NET_WM_NAME', '_NET_WM_PID'],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode != 0:
                return None
            props = result.stdout
            return {
                'window_id': window_id,
                'app_name': self._extract_wm_class(props),
                'title': self._extract_wm_name(props),
                'pid': self._extract_pid(props),
            }
        except subprocess.TimeoutExpired:
            self.logger.warning('xprop command timed out')
        except FileNotFoundError:
            self.logger.warning('xprop not found; install x11-utils for X11 detection')
        except Exception as e:
            self.logger.error('Error getting X11 foreground window: %s', e)
        return None

    def _get_active_window_wayland(self) -> Optional[Dict[str, Any]]:
        """Support Sway/wlroots only; never guess foreground state from process lists."""
        if self._command_exists('swaymsg'):
            return self._get_sway_window()
        self.logger.debug(
            'Reliable foreground-window detection is unavailable for this Wayland compositor'
        )
        return None

    def _get_sway_window(self) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ['swaymsg', '-t', 'get_tree'],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode != 0:
                return None
            focused = self._find_focused_node(json.loads(result.stdout))
            if not focused:
                return None
            return {
                'app_name': focused.get('app_id')
                or focused.get('window_properties', {}).get('class', 'Unknown'),
                'title': focused.get('name', ''),
                'pid': focused.get('pid'),
            }
        except Exception as e:
            self.logger.debug('Sway detection failed: %s', e)
            return None

    def _find_focused_node(self, node: Dict) -> Optional[Dict]:
        if node.get('focused'):
            return node
        for child in node.get('nodes', []) + node.get('floating_nodes', []):
            result = self._find_focused_node(child)
            if result:
                return result
        return None

    @staticmethod
    def _extract_wm_class(props: str) -> str:
        for line in props.split('\n'):
            if 'WM_CLASS(STRING)' not in line:
                continue
            parts = line.split('=', 1)
            if len(parts) <= 1:
                continue
            values = parts[1].strip().strip('"').split('", "')
            if len(values) > 1:
                return values[1].strip('"')
            if values:
                return values[0].strip('"')
        return 'Unknown'

    @staticmethod
    def _extract_wm_name(props: str) -> str:
        for marker in ('_NET_WM_NAME(UTF8_STRING)', 'WM_NAME(STRING)'):
            for line in props.split('\n'):
                if marker in line:
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        return parts[1].strip().strip('"')
        return ''

    @staticmethod
    def _extract_pid(props: str) -> Optional[int]:
        for line in props.split('\n'):
            if '_NET_WM_PID(CARDINAL)' not in line:
                continue
            parts = line.split('=', 1)
            if len(parts) > 1:
                try:
                    return int(parts[1].strip())
                except ValueError:
                    return None
        return None

    @staticmethod
    def _command_exists(command: str) -> bool:
        return shutil.which(command) is not None
