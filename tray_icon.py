"""
System tray icon for Discord Rich Presence Service
Optional GUI component for easy control
"""

import logging
import platform
from typing import Optional, Callable


class TrayIcon:
    """System tray icon with menu for service control"""
    
    def __init__(self, on_exit: Optional[Callable] = None, on_toggle_privacy: Optional[Callable] = None, on_open_panel: Optional[Callable] = None):
        self.logger = logging.getLogger(__name__)
        self.on_exit = on_exit
        self.on_toggle_privacy = on_toggle_privacy
        self.on_open_panel = on_open_panel
        self.icon = None
        self.available = False
        
        # Try to import platform-specific tray library
        try:
            import pystray
            from PIL import Image, ImageDraw
            self.pystray = pystray
            self.Image = Image
            self.ImageDraw = ImageDraw
            self.available = True
            self.logger.info("System tray support available")
        except ImportError:
            self.logger.warning("pystray not available, tray icon disabled")
            self.logger.warning("Install with: pip install pystray pillow")
    
    def create_icon(self) -> None:
        """Create the tray icon"""
        if not self.available:
            return
        
        # Create a simple icon image
        image = self._create_image()
        
        # Create menu
        menu = self._create_menu()
        
        # Create icon
        self.icon = self.pystray.Icon(
            "discord-rich-presence",
            image,
            "Discord Rich Presence",
            menu
        )
    
    def _create_image(self):
        """Create icon image"""
        # Create a simple Discord-like icon
        width = 64
        height = 64
        image = self.Image.new('RGB', (width, height), 'white')
        draw = self.ImageDraw.Draw(image)
        
        # Draw a simple "D" shape
        draw.ellipse([10, 10, 54, 54], fill='#5865F2', outline='#5865F2')
        draw.rectangle([32, 10, 54, 54], fill='white')
        draw.ellipse([20, 20, 44, 44], fill='white', outline='white')
        
        return image
    
    def _create_menu(self):
        """Create tray menu"""
        return self.pystray.Menu(
            self.pystray.MenuItem(
                "Discord Rich Presence",
                lambda: None,
                enabled=False
            ),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem(
                "فتح لوحة التحكم",
                lambda: self._open_panel()
            ),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem(
                "Privacy: Off",
                lambda: self._toggle_privacy('off'),
                radio=True
            ),
            self.pystray.MenuItem(
                "Privacy: Balanced",
                lambda: self._toggle_privacy('balanced'),
                radio=True,
                checked=lambda item: True  # Default
            ),
            self.pystray.MenuItem(
                "Privacy: Strict",
                lambda: self._toggle_privacy('strict'),
                radio=True
            ),
            self.pystray.Menu.SEPARATOR,
            self.pystray.MenuItem(
                "Exit",
                self._on_exit_clicked
            )
        )
    
    def _toggle_privacy(self, mode: str):
        """Toggle privacy mode"""
        if self.on_toggle_privacy:
            self.on_toggle_privacy(mode)

    def _open_panel(self):
        if self.on_open_panel:
            self.on_open_panel()
    
    def _on_exit_clicked(self, icon, item):
        """Handle exit menu click"""
        if self.on_exit:
            self.on_exit()
        if self.icon:
            self.icon.stop()
    
    def run(self):
        """Run the tray icon (blocking)"""
        if not self.available or not self.icon:
            return
        
        self.icon.run()
    
    def stop(self):
        """Stop the tray icon"""
        if self.icon:
            self.icon.stop()
    
    @staticmethod
    def is_available() -> bool:
        """Check if tray icon is available"""
        try:
            import pystray
            return True
        except ImportError:
            return False


def run_with_tray(service_run_func: Callable, config, stop_func: Optional[Callable] = None):
    """
    Run service with tray icon in separate thread
    
    Args:
        service_run_func: Function to run the service
        config: Configuration object
    """
    import threading
    
    if not TrayIcon.is_available():
        # No tray available, just run service
        service_run_func()
        return
    
    # Create tray icon
    def on_toggle_privacy(mode: str):
        config.set('privacy.mode', mode)
        logging.info(f"Privacy mode changed to: {mode}")
    
    def on_exit():
        logging.info("Exit requested from tray icon")
        try:
            if stop_func:
                stop_func()
        except Exception as e:
            logging.error(f"Failed to stop service: {e}")
    
    def on_open_panel():
        import subprocess
        import sys
        import os
        
        # Launch GUI in a separate process to avoid thread conflicts with tray icon
        try:
            # Get path to python interpreter
            python_exe = sys.executable
            
            # Get path to gui_modern.py
            script_dir = os.path.dirname(os.path.abspath(__file__))
            gui_script = os.path.join(script_dir, 'gui_modern.py')
            
            # Launch
            subprocess.Popen([python_exe, gui_script], cwd=script_dir)
            
        except Exception as e:
            logging.error(f"Failed to open control panel: {e}")
    tray = TrayIcon(on_exit=on_exit, on_toggle_privacy=on_toggle_privacy, on_open_panel=on_open_panel)
    tray.create_icon()
    
    # Run service in separate thread
    service_thread = threading.Thread(target=service_run_func, daemon=True)
    service_thread.start()
    
    # Run tray icon in main thread (blocking)
    tray.run()
