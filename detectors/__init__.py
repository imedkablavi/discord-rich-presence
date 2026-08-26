"""
Activity detectors for Discord Rich Presence
"""

from .window import WindowDetector
from .browser import BrowserDetector
from .terminal import TerminalDetector
from .coding import CodingDetector
from .media import MediaDetector
from . import gaming as _gaming_module
from .gaming_hardened import GamingDetector
from .git_helper import GitHelper

# Keep direct imports such as ``from detectors.gaming import GamingDetector`` on
# the same hardened implementation as package imports. This avoids two detector
# behaviors between the service and regression tests while the release branch
# carries the accuracy hardening as a small, reviewable layer.
_gaming_module.GamingDetector = GamingDetector

__all__ = [
    'WindowDetector',
    'BrowserDetector',
    'TerminalDetector',
    'CodingDetector',
    'MediaDetector',
    'GamingDetector',
    'GitHelper',
]
