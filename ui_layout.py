"""Responsive geometry for the desktop control panel.

This module intentionally does not import Tk so its calculations can be tested
on headless CI runners and reused before any widgets are created.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlPanelGeometry:
    width: int
    height: int
    x: int
    y: int
    min_width: int
    min_height: int


def control_panel_geometry(screen_width: int, screen_height: int) -> ControlPanelGeometry:
    """Choose a centered window and minimum size that fit common displays."""
    try:
        sw = max(320, int(screen_width))
    except (TypeError, ValueError, OverflowError):
        sw = 1366
    try:
        sh = max(240, int(screen_height))
    except (TypeError, ValueError, OverflowError):
        sh = 768

    min_width = min(1080, max(640, sw - 40))
    min_height = min(720, max(480, sh - 80))
    width = min(1320, max(min_width, int(sw * 0.92)))
    height = min(840, max(min_height, int(sh * 0.86)))
    # Integer rounding and minimum-size constraints should never push the
    # window outside the display bounds.
    width = min(sw, width)
    height = min(sh, height)
    min_width = min(min_width, width)
    min_height = min(min_height, height)
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    return ControlPanelGeometry(
        width=width,
        height=height,
        x=x,
        y=y,
        min_width=min_width,
        min_height=min_height,
    )



def sidebar_width_for_screen(screen_width: int) -> int:
    """Return a readable sidebar width for the display's available space."""
    try:
        width = max(320, int(screen_width))
    except (TypeError, ValueError, OverflowError):
        width = 1366
    if width < 720:
        return 156
    if width < 900:
        return 184
    if width < 1100:
        return 210
    return 252
