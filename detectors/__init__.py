"""
Activity detectors for Discord Rich Presence
"""

from .window import WindowDetector
from .browser import BrowserDetector
from .terminal import TerminalDetector
from .coding import CodingDetector
from .media import MediaDetector

__all__ = [
    'WindowDetector',
    'BrowserDetector',
    'TerminalDetector',
    'CodingDetector',
    'MediaDetector',
]
