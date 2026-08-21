#!/usr/bin/env python3
"""Entry point used by packaged builds."""

import sys
from pathlib import Path, PureWindowsPath


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


def _handle_cs2_setup_command() -> bool:
    """Allow packaged users to repair/install CS2 GSI without a source checkout."""
    if '--install-cs2-gsi' not in sys.argv:
        return False

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
        print(f'Counter-Strike 2 GSI installation failed: {exc}', file=sys.stderr)
        return True

    print('Counter-Strike 2 GSI installed successfully.')
    print(f'Configuration: {target}')
    print('Restart Counter-Strike 2 if it is already running.')
    return True


def main():
    if _handle_cs2_setup_command():
        return

    if '--gui' in sys.argv:
        sys.argv.remove('--gui')
        from config import Config
        from gui_modern import ModernControlPanel

        app = ModernControlPanel(Config())
        app.mainloop()
        return

    _normalize_packaged_args()

    from main import main as service_main
    service_main()


if __name__ == '__main__':
    main()
