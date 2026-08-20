#!/usr/bin/env python3
"""Entry point used by packaged builds."""

import sys


def main():
    if '--gui' in sys.argv:
        sys.argv.remove('--gui')
        from config import Config
        from gui_modern import ModernControlPanel

        app = ModernControlPanel(Config())
        app.mainloop()
        return

    # A normal double-click on the packaged executable should leave the user
    # with a visible tray control instead of starting a silent background process.
    if getattr(sys, 'frozen', False) and len(sys.argv) == 1:
        sys.argv.append('--tray')

    from main import main as service_main
    service_main()


if __name__ == '__main__':
    main()
