#!/usr/bin/env python3
"""Entry point used by packaged builds."""

import sys
from pathlib import Path, PureWindowsPath
from typing import Optional


def _argument_name(value: str) -> str:
    """Return a path basename without depending on the runner operating system."""
    if '\\' in value:
        return PureWindowsPath(value).name.lower()
    return Path(value).name.lower()


def _normalize_packaged_args():
    """Translate source-style child launches into packaged service arguments."""
    if not getattr(sys, 'frozen', False):
        return

    # The source GUI starts the service as `python main.py`. In a one-file build
    # sys.executable is the application itself, so treat a trailing main.py
    # argument as a request to start this executable in service/tray mode.
    sys.argv[:] = [
        arg for index, arg in enumerate(sys.argv)
        if index == 0 or _argument_name(arg) != 'main.py'
    ]

    if len(sys.argv) == 1:
        sys.argv.append('--tray')


def _setup_message(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    if stream is not None:
        print(message, file=stream, flush=True)
        return
    # PyInstaller windowed builds have no console streams. Keep the repair
    # command usable there by falling back to a small native dialog.
    if getattr(sys, 'frozen', False):
        try:
            from tkinter import messagebox
            if error:
                messagebox.showerror('CYBREX Rich Presence', message)
            else:
                messagebox.showinfo('CYBREX Rich Presence', message)
        except Exception:
            pass


def _handle_cs2_setup_command() -> Optional[int]:
    """Allow packaged users to repair/install CS2 GSI without a source checkout."""
    if '--install-cs2-gsi' not in sys.argv:
        return None

    index = sys.argv.index('--install-cs2-gsi')
    cfg_dir = None
    if index + 1 < len(sys.argv):
        candidate = sys.argv[index + 1]
        if candidate and not candidate.startswith('--'):
            cfg_dir = Path(candidate)

    from config import Config
    from cs2_gsi import install_gsi_config

    try:
        target = install_gsi_config(Config(), cfg_dir)
    except Exception as exc:
        _setup_message(f'Counter-Strike 2 GSI installation failed: {exc}', error=True)
        return 1

    _setup_message(
        'Counter-Strike 2 GSI installed successfully.\n'
        f'Configuration: {target}\n'
        'Restart Counter-Strike 2 if it is already running.'
    )
    return 0


def main() -> int:
    setup_result = _handle_cs2_setup_command()
    if setup_result is not None:
        return setup_result

    if '--gui' in sys.argv:
        sys.argv.remove('--gui')
        from config import Config
        from gui_modern import ModernControlPanel

        app = ModernControlPanel(Config())
        app.mainloop()
        return 0

    _normalize_packaged_args()

    from main import main as service_main
    service_main()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
