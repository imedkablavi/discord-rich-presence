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
    # PyInstaller windowed builds have no console streams. Keep setup/repair
    # commands usable there by falling back to a small native dialog.
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


def _handle_update_command() -> Optional[int]:
    check_only = '--check-update' in sys.argv
    install = '--update' in sys.argv
    if not check_only and not install:
        return None

    from updater import UpdateError, check_for_update, install_update, update_summary

    try:
        info = check_for_update()
        if check_only or info is None:
            _setup_message(update_summary(info))
            return 0

        if not getattr(sys, 'frozen', False):
            raise UpdateError('Automatic installation is only available in packaged builds.')

        # Stop a separate tray/service instance before replacing the executable.
        # The Windows helper still waits for this updater process itself to exit.
        try:
            from runtime_state import RuntimeState
            runtime = RuntimeState()
            if runtime.read_active():
                runtime.terminate_active(timeout=5)
        except Exception:
            # Failing to find/stop a stale runtime record must not bypass checksum
            # verification; the platform-specific replace step remains fail-safe.
            pass

        result = install_update(info, restart_args=['--gui'])
        if result == 'scheduled':
            _setup_message(
                f'CYBREX {info.latest_version} verified. The update will finish after this process exits.'
            )
        else:
            _setup_message(
                f'CYBREX updated to {info.latest_version}. The new build is relaunching now.'
            )
        return 0
    except UpdateError as exc:
        _setup_message(f'Update failed: {exc}', error=True)
        return 1
    except Exception as exc:
        _setup_message(f'Unexpected update error: {exc}', error=True)
        return 1


def _handle_game_library_command() -> Optional[int]:
    if '--game-library' not in sys.argv:
        return None
    try:
        from config import Config
        from game_library_gui import GameLibraryWindow

        app = GameLibraryWindow(Config())
        app.mainloop()
        return 0
    except Exception as exc:
        _setup_message(f'Could not open Game Library: {exc}', error=True)
        return 1


def main() -> int:
    update_result = _handle_update_command()
    if update_result is not None:
        return update_result

    setup_result = _handle_cs2_setup_command()
    if setup_result is not None:
        return setup_result

    library_result = _handle_game_library_command()
    if library_result is not None:
        return library_result

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
