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
    sys.argv[:] = [
        arg for index, arg in enumerate(sys.argv)
        if index == 0 or _argument_name(arg) != 'main.py'
    ]
    if len(sys.argv) == 1:
        sys.argv.append('--tray')


def _stop_active_service() -> int:
    from runtime_state import RuntimeState

    runtime = RuntimeState()
    active = runtime.read_active()
    if not active:
        return 0
    return 0 if runtime.terminate_active(timeout=8.0) else 1


def main():
    if '--stop-service' in sys.argv:
        raise SystemExit(_stop_active_service())

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
