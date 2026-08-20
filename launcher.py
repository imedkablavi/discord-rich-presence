#!/usr/bin/env python3
"""Entry point used by packaged builds."""

import sys
from pathlib import Path


def _normalize_packaged_args():
    """Translate source-style child launches into packaged service arguments."""
    if not getattr(sys, 'frozen', False):
        return

    # The source GUI starts the service as `python main.py`. In a one-file build
    # sys.executable is the application itself, so treat a trailing main.py
    # argument as a request to start this executable in service/tray mode.
    sys.argv[:] = [
        arg for index, arg in enumerate(sys.argv)
        if index == 0 or Path(arg).name.lower() != 'main.py'
    ]

    if len(sys.argv) == 1:
        sys.argv.append('--tray')


def main():
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
