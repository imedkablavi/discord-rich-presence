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
    if getattr(sys, 'frozen', False):
        try:
            from tkinter import messagebox
            if error:
                messagebox.showerror('CYBREX Rich Presence', message)
            else:
                messagebox.showinfo('CYBREX Rich Presence', message)
        except Exception:
            pass


def _tk_support_hint() -> str:
    """Explain how to add Tk to a Linux Python interpreter."""
    return (
        "CYBREX's source GUI requires Tk support in the selected Python interpreter.\n\n"
        "Install the operating-system Tk package (it is not a pip dependency):\n"
        "  Fedora / Nobara: sudo dnf install python3-tkinter\n"
        "  Bazzite / Fedora Atomic: rpm-ostree install python3-tkinter, then reboot\n"
        "  Debian / Ubuntu: sudo apt install python3-tk\n\n"
        "Verify Tk with: python -m tkinter\n"
        "Linuxbrew/Homebrew Python may be built without _tkinter. Create the "
        "virtual environment with your distribution's Python (for example "
        "/usr/bin/python3), then reinstall requirements.txt."
    )


def _handle_missing_tk(exc: ModuleNotFoundError) -> bool:
    """Show actionable setup guidance only for a missing Tk runtime."""
    if exc.name not in {"tkinter", "_tkinter"}:
        return False
    _setup_message(_tk_support_hint(), error=True)
    return True


def _handle_cs2_setup_command() -> Optional[int]:
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


def _stop_active_service_for_update(runtime_state_factory=None) -> bool:
    """Stop the currently running service before replacing its executable.

    A failed/indeterminate stop must block self-update: continuing could leave
    an old service process running after the executable on disk has changed.
    The injectable factory keeps this lifecycle boundary testable without
    touching a real user session.
    """
    try:
        if runtime_state_factory is None:
            from runtime_state import RuntimeState

            runtime_state_factory = RuntimeState
        runtime = runtime_state_factory()
        if runtime.read_active():
            return runtime.terminate_active(timeout=5) is True

        # read_active() intentionally returns None for both an absent lock and
        # an invalid/stale runtime record. Do not mistake an unreadable lock for
        # proof that no service is running: it could hide a live older process.
        lock_path = getattr(runtime, "lock_path", None)
        if lock_path is None:
            # Lightweight injected test doubles may only model the public
            # read_active/terminate_active contract.
            return True
        try:
            lock_path = Path(lock_path)
            try:
                lock_path.stat()
            except FileNotFoundError:
                return True
            except OSError:
                return False

            lock_record = runtime._read_json(lock_path)
            if not isinstance(lock_record, dict):
                return False
            try:
                pid = int(lock_record["pid"])
                create_time = float(lock_record["create_time"])
            except (KeyError, TypeError, ValueError):
                return False
            if pid <= 0 or create_time <= 0:
                return False

            # A parseable record that no longer matches a live process is a
            # stale PID lock, not an active service. A live/indeterminate match
            # means we must refuse update because read_active() was inconclusive.
            return runtime._same_process(lock_record) is False
        except Exception:
            return False
    except Exception:
        return False


def _handle_update_command() -> Optional[int]:
    check_only = '--check-update' in sys.argv
    install = '--update' in sys.argv
    if not check_only and not install:
        return None

    from config import Config
    from update_manager import check_for_update, configured_update_channel
    from updater import UpdateError, install_update, update_summary

    try:
        config = Config()
        channel = configured_update_channel(config)
        info = check_for_update(channel=channel)
        if check_only or info is None:
            summary = update_summary(info)
            _setup_message(f'{summary}\nUpdate channel: {channel.title()}')
            return 0

        if not getattr(sys, 'frozen', False):
            raise UpdateError('Automatic installation is only available in packaged builds.')

        if not _stop_active_service_for_update():
            raise UpdateError(
                'Could not safely stop the running CYBREX service. '
                'Close the current CYBREX session and try the update again.'
            )

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
    except ModuleNotFoundError as exc:
        if _handle_missing_tk(exc):
            return 1
        _setup_message(f'Could not open Game Library: {exc}', error=True)
        return 1
    except Exception as exc:
        _setup_message(f'Could not open Game Library: {exc}', error=True)
        return 1


def main() -> int:
    from config_hardening import apply_config_hardening
    apply_config_hardening()

    from memory_guard import start_memory_guard
    start_memory_guard()

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
        from gui_instance import GUIInstanceLock
        try:
            from gui_modern_v4 import ModernControlPanel
        except ModuleNotFoundError as exc:
            if _handle_missing_tk(exc):
                return 1
            raise

        gui_lock = GUIInstanceLock()
        if not gui_lock.acquire():
            _setup_message('CYBREX control panel is already running.')
            return 0
        try:
            app = ModernControlPanel(Config())
            app.mainloop()
        finally:
            gui_lock.release()
        return 0

    _normalize_packaged_args()

    from resource_hardening import apply_resource_hardening
    apply_resource_hardening()
    from main import main as service_main
    service_main()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
