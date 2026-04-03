"""
Activity detectors for Discord Rich Presence
"""

from .window import WindowDetector
from .browser import BrowserDetector
from .terminal import TerminalDetector
from .coding import CodingDetector
from .media import MediaDetector
from .gaming import GamingDetector
from .git_helper import GitHelper

__all__ = [
    'WindowDetector',
    'BrowserDetector',
    'TerminalDetector',
    'CodingDetector',
    'MediaDetector',
    'GamingDetector',
    'GitHelper',
]
