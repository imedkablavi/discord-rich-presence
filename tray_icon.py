"""System tray controls for Discord Rich Presence."""

import logging
from typing import Optional, Callable


class TrayIcon:
    def __init__(self, on_exit: Optional[Callable] = None, on_toggle_privacy: Optional[Callable] = None, on_open_panel: Optional[Callable] = None, get_privacy_mode: Optional[Callable] = None):
        self.logger = logging.getLogger(__name__)
        self.on_exit = on_exit
        self.on_toggle_privacy = on_toggle_privacy
        self.on_open_panel = on_open_panel
        self.get_privacy_mode = get_privacy_mode or (lambda: 'balanced')
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

    def _create_menu(self):
        return self.pystray.Menu(
            self.pystray.MenuItem('Discord Rich Presence', lambda: None, enabled=False),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem('Open Control Panel', lambda: self._open_panel()),
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
        if self.icon:
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def _open_panel(self):
        if self.on_open_panel:
            self.on_open_panel()

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

    def on_exit():
        if stop_func:
            stop_func()

    def on_open_panel():
        try:
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable, '--gui'])
                return
            script_dir = os.path.dirname(os.path.abspath(__file__))
            gui_script = os.path.join(script_dir, 'gui_modern.py')
            subprocess.Popen([sys.executable, gui_script], cwd=script_dir)
        except Exception as e:
            logging.error('Failed to open control panel: %s', e)

    tray = TrayIcon(
        on_exit=on_exit,
        on_toggle_privacy=on_toggle_privacy,
        on_open_panel=on_open_panel,
        get_privacy_mode=lambda: config.get('privacy.mode', 'balanced'),
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
