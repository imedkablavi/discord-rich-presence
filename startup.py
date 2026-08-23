"""Per-user startup registration for packaged and source runs."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path


APP_NAME = 'DiscordRichPresence'


def startup_command() -> list[str]:
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).resolve()), '--tray']
    root = Path(__file__).resolve().parent
    python = sys.executable
    if sys.platform == 'win32' and python.lower().endswith('python.exe'):
        candidate = python[:-10] + 'pythonw.exe'
        if os.path.exists(candidate):
            python = candidate
    return [python, str(root / 'main.py'), '--tray']


def is_enabled() -> bool:
    if sys.platform == 'win32':
        return _windows_is_enabled()
    if sys.platform.startswith('linux'):
        return _linux_autostart_path().is_file()
    return False


def set_enabled(enabled: bool) -> None:
    if sys.platform == 'win32':
        _windows_set_enabled(enabled)
        return
    if sys.platform.startswith('linux'):
        _linux_set_enabled(enabled)
        return
    raise RuntimeError('Automatic startup is not supported on this platform')


def _windows_is_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except (ImportError, OSError):
        return False


def _windows_set_enabled(enabled: bool) -> None:
    import winreg
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r'Software\Microsoft\Windows\CurrentVersion\Run',
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            command = subprocess_list2cmdline(startup_command())
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def subprocess_list2cmdline(args: list[str]) -> str:
    import subprocess
    return subprocess.list2cmdline(args)


def _linux_autostart_path() -> Path:
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return config_home / 'autostart' / 'discord-rich-presence.desktop'


def _linux_set_enabled(enabled: bool) -> None:
    path = _linux_autostart_path()
    if not enabled:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    command = ' '.join(shlex.quote(part) for part in startup_command())
    content = (
        '[Desktop Entry]\n'
        'Type=Application\n'
        'Name=Discord Rich Presence\n'
        'Comment=Start Discord Rich Presence after login\n'
        f'Exec={command}\n'
        'Terminal=false\n'
        'X-GNOME-Autostart-enabled=true\n'
    )
    temp = path.with_suffix('.tmp')
    temp.write_text(content, encoding='utf-8')
    os.replace(temp, path)
