"""Small generated vector-style icon set for the desktop control panel.

Icons are drawn locally with Pillow so the UI does not depend on remote assets,
font glyph availability, or a heavyweight icon package.
"""

from __future__ import annotations

from functools import lru_cache

import customtkinter as ctk
from PIL import Image, ImageDraw


_CANVAS = 48


def _draw(name: str, color: str) -> Image.Image:
    image = Image.new("RGBA", (_CANVAS, _CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    w = 4

    if name == "overview":
        for x, y in ((8, 8), (27, 8), (8, 27), (27, 27)):
            draw.rounded_rectangle((x, y, x + 13, y + 13), radius=3, outline=color, width=w)
    elif name == "integrations":
        draw.rounded_rectangle((6, 17, 21, 31), radius=6, outline=color, width=w)
        draw.rounded_rectangle((27, 17, 42, 31), radius=6, outline=color, width=w)
        draw.line((20, 24, 28, 24), fill=color, width=w)
    elif name == "activity":
        draw.line((5, 26, 13, 26, 18, 13, 25, 36, 31, 20, 36, 26, 43, 26), fill=color, width=w, joint="curve")
    elif name == "privacy":
        draw.polygon(((24, 5), (39, 11), (36, 30), (24, 42), (12, 30), (9, 11)), outline=color)
        draw.line((17, 24, 22, 29, 32, 18), fill=color, width=w)
    elif name == "settings":
        draw.ellipse((14, 14, 34, 34), outline=color, width=w)
        draw.ellipse((21, 21, 27, 27), fill=color)
        for x1, y1, x2, y2 in ((24, 5, 24, 13), (24, 35, 24, 43), (5, 24, 13, 24), (35, 24, 43, 24), (10, 10, 16, 16), (32, 32, 38, 38), (32, 16, 38, 10), (10, 38, 16, 32)):
            draw.line((x1, y1, x2, y2), fill=color, width=w)
    elif name == "diagnostics":
        draw.rounded_rectangle((6, 8, 42, 40), radius=5, outline=color, width=w)
        draw.line((12, 18, 18, 24, 12, 30), fill=color, width=w)
        draw.line((23, 31, 34, 31), fill=color, width=w)
    elif name == "about":
        draw.ellipse((7, 7, 41, 41), outline=color, width=w)
        draw.ellipse((22, 13, 26, 17), fill=color)
        draw.line((24, 22, 24, 34), fill=color, width=w)
    elif name == "discord":
        draw.rounded_rectangle((7, 12, 41, 36), radius=10, outline=color, width=w)
        draw.ellipse((16, 21, 21, 26), fill=color)
        draw.ellipse((27, 21, 32, 26), fill=color)
        draw.arc((15, 20, 33, 33), 20, 160, fill=color, width=3)
    elif name == "browser":
        draw.ellipse((6, 6, 42, 42), outline=color, width=w)
        draw.ellipse((16, 6, 32, 42), outline=color, width=3)
        draw.line((7, 24, 41, 24), fill=color, width=3)
    elif name == "game":
        draw.ellipse((7, 7, 41, 41), outline=color, width=w)
        draw.line((24, 13, 24, 35), fill=color, width=3)
        draw.line((13, 24, 35, 24), fill=color, width=3)
        draw.ellipse((21, 21, 27, 27), fill=color)
    elif name == "app":
        draw.rounded_rectangle((6, 8, 42, 40), radius=5, outline=color, width=w)
        draw.line((7, 17, 41, 17), fill=color, width=3)
        draw.ellipse((11, 12, 14, 15), fill=color)
        draw.ellipse((17, 12, 20, 15), fill=color)
    elif name == "update":
        draw.arc((8, 8, 40, 40), 45, 300, fill=color, width=w)
        draw.polygon(((36, 7), (43, 15), (33, 16)), fill=color)
    else:
        draw.ellipse((10, 10, 38, 38), outline=color, width=w)
    return image


@lru_cache(maxsize=128)
def icon(name: str, size: int = 18) -> ctk.CTkImage:
    light = _draw(name, "#526173")
    dark = _draw(name, "#B7C4D4")
    return ctk.CTkImage(light_image=light, dark_image=dark, size=(size, size))
