"""System tray controls for Discord Rich Presence."""

import logging
from typing import Optional, Callable


class TrayIcon:
    def __init__(
        self,
        on_exit: Optional[Callable] = None,
        on_toggle_privacy: Optional[Callable] = None,
        on_toggle_gamer_mode: Optional[Callable] = None,
        on_open_panel: Optional[Callable] = None,
        on_open_game_library: Optional[Callable] = None,
        on_check_updates: Optional[Callable] = None,
        on_install_update: Optional[Callable] = None,
        get_privacy_mode: Optional[Callable] = None,
        get_gamer_mode: Optional[Callable] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.on_exit = on_exit
        self.on_toggle_privacy = on_toggle_privacy
        self.on_toggle_gamer_mode = on_toggle_gamer_mode
        self.on_open_panel = on_open_panel
        self.on_open_game_library = on_open_game_library
        self.on_check_updates = on_check_updates
        self.on_install_update = on_install_update
        self.get_privacy_mode = get_privacy_mode or (lambda: 'balanced')
        self.get_gamer_mode = get_gamer_mode or (lambda: False)
        self.icon = None
        self.available = False
        try:
            import pystray
            from PIL import Image, ImageDraw
            self.pystray = pystray
            self.Image = Image
            self.ImageDraw = ImageDraw
            self.available = True
        except ImportError:
            self.logger.warning("pystray/Pillow unavailable; tray icon disabled")

    def create_icon(self) -> None:
        if not self.available:
            return
        self.icon = self.pystray.Icon(
            'discord-rich-presence', self._create_image(),
            'Discord Rich Presence', self._create_menu()
        )

    def _create_image(self):
        image = self.Image.new('RGB', (64, 64), 'white')
        draw = self.ImageDraw.Draw(image)
        draw.ellipse([10, 10, 54, 54], fill='#5865F2', outline='#5865F2')
        draw.rectangle([32, 10, 54, 54], fill='white')
        draw.ellipse([20, 20, 44, 44], fill='white', outline='white')
        return image

    def _is_mode(self, mode: str) -> bool:
        try:
            return str(self.get_privacy_mode()) == mode
        except Exception:
            return False

    def _gamer_mode_enabled(self) -> bool:
        try:
            return bool(self.get_gamer_mode())
        except Exception:
            return False

    def _create_menu(self):
        return self.pystray.Menu(
            self.pystray.MenuItem('Discord Rich Presence', lambda: None, enabled=False),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem('Open Control Panel', lambda: self._open_panel()),
            self.pystray.MenuItem('Game Library', lambda: self._open_game_library()),
            self.pystray.MenuItem(
                'Gamer Mode (games only)',
                lambda: self._toggle_gamer_mode(),
                checked=lambda item: self._gamer_mode_enabled(),
            ),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem('Check for updates', lambda: self._check_updates()),
            self.pystray.MenuItem('Install latest update', lambda: self._install_update()),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem('Privacy: Off', lambda: self._toggle_privacy('off'), radio=True, checked=lambda item: self._is_mode('off')),
            self.pystray.MenuItem('Privacy: Balanced', lambda: self._toggle_privacy('balanced'), radio=True, checked=lambda item: self._is_mode('balanced')),
            self.pystray.MenuItem('Privacy: Strict', lambda: self._toggle_privacy('strict'), radio=True, checked=lambda item: self._is_mode('strict')),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem('Exit', self._on_exit_clicked),
        )

    def _toggle_privacy(self, mode: str):
        if self.on_toggle_privacy:
            self.on_toggle_privacy(mode)
        self._refresh_menu()

    def _toggle_gamer_mode(self):
        if self.on_toggle_gamer_mode:
            self.on_toggle_gamer_mode(not self._gamer_mode_enabled())
        self._refresh_menu()

    def _refresh_menu(self):
        if self.icon:
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def _open_panel(self):
        if self.on_open_panel:
            self.on_open_panel()

    def _open_game_library(self):
        if self.on_open_game_library:
            self.on_open_game_library()

    def _check_updates(self):
        if self.on_check_updates:
            self.on_check_updates()

    def _install_update(self):
        if self.on_install_update:
            self.on_install_update()

    def _on_exit_clicked(self, icon, item):
        if self.on_exit:
            self.on_exit()
        if self.icon:
            self.icon.stop()

    def run(self):
        if self.available and self.icon:
            self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()

    @staticmethod
    def is_available() -> bool:
        try:
            import pystray  # noqa: F401
            return True
        except ImportError:
            return False


def run_with_tray(service_run_func: Callable, config, stop_func: Optional[Callable] = None):
    import os
    import subprocess
    import sys
    import threading

    if not TrayIcon.is_available():
        service_run_func()
        return

    def on_toggle_privacy(mode: str):
        config.set('privacy.mode', mode)
        try:
            config.save()
        except Exception as e:
            logging.error('Failed to persist privacy mode: %s', e)
        logging.info('Privacy mode changed to: %s', mode)

    def on_toggle_gamer_mode(enabled: bool):
        try:
            from game_library import set_gamer_mode
            set_gamer_mode(config, enabled)
            logging.info('Gamer Mode %s', 'enabled' if enabled else 'disabled')
        except Exception as e:
            logging.error('Failed to change Gamer Mode: %s', e)

    def on_exit():
        if stop_func:
            stop_func()

    def _launcher_command(argument: str):
        if getattr(sys, 'frozen', False):
            return [sys.executable, argument]
        script_dir = os.path.dirname(os.path.abspath(__file__))
        launcher_script = os.path.join(script_dir, 'launcher.py')
        return [sys.executable, launcher_script, argument]

    def on_open_panel():
        try:
            # Always route through launcher.py so the control-panel single-instance
            # guard and resource-aware GUI are used in both source and packaged runs.
            subprocess.Popen(_launcher_command('--gui'))
        except Exception as e:
            logging.error('Failed to open control panel: %s', e)

    def on_open_game_library():
        try:
            subprocess.Popen(_launcher_command('--game-library'))
        except Exception as e:
            logging.error('Failed to open Game Library: %s', e)

    def on_check_updates():
        try:
            subprocess.Popen(_launcher_command('--check-update'))
        except Exception as e:
            logging.error('Failed to launch update check: %s', e)

    def on_install_update():
        try:
            subprocess.Popen(_launcher_command('--update'))
            # Let the updater child take over, then end this process cleanly so
            # Windows can replace the executable without force-killing the tray.
            if stop_func:
                stop_func()
            if tray.icon:
                tray.icon.stop()
        except Exception as e:
            logging.error('Failed to launch updater: %s', e)

    tray = TrayIcon(
        on_exit=on_exit,
        on_toggle_privacy=on_toggle_privacy,
        on_toggle_gamer_mode=on_toggle_gamer_mode,
        on_open_panel=on_open_panel,
        on_open_game_library=on_open_game_library,
        on_check_updates=on_check_updates,
        on_install_update=on_install_update,
        get_privacy_mode=lambda: config.get('privacy.mode', 'balanced'),
        get_gamer_mode=lambda: config.get('gaming.gamer_mode.enabled', False) is True,
    )
    tray.create_icon()
    service_thread = threading.Thread(target=service_run_func, daemon=False)
    service_thread.start()
    try:
        tray.run()
    finally:
        if stop_func:
            stop_func()
        service_thread.join(timeout=10)
