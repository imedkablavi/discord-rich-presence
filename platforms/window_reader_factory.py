import sys
from .base_window_reader import BaseWindowReader

class WindowReaderFactory:
    @staticmethod
    def create_reader() -> BaseWindowReader:
        if sys.platform == 'win32':
            from .windows_window_reader import WindowsWindowReader
            return WindowsWindowReader()
        elif sys.platform == 'darwin':
            from .mac_window_reader import MacWindowReader
            return MacWindowReader()
        else:
            from .linux_window_reader import LinuxWindowReader
            return LinuxWindowReader()
