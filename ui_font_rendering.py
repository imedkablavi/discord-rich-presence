"""Choose scalable desktop fonts so Tk does not fall back to bitmap faces.

Some Linux Tk installations expose bitmap families as their default named fonts.
The custom panel uses both CustomTkinter fonts and Tk's built-in named fonts, so
fixing only the explicitly styled labels is insufficient.
"""

from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
from tkinter import font as tkfont
from typing import Iterable


_UI_CANDIDATES = (
    "DejaVu Sans",
    "Liberation Sans",
    "Cantarell",
    "Inter",
    "Noto Sans",
    "Ubuntu",
    "Segoe UI",
    "Arial",
    "Helvetica Neue",
)
_MONO_CANDIDATES = (
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Ubuntu Mono",
    "Noto Sans Mono",
    "Cascadia Mono",
    "Consolas",
    "Courier New",
)


def parse_scalable_font_families(output: str) -> set[str]:
    """Parse fc-list family/scalable output into case-folded family names."""
    families: set[str] = set()
    for line in output.splitlines():
        family_text, separator, scalable_text = line.partition("\t")
        if not separator or scalable_text.strip().casefold() not in {"true", "yes", "1"}:
            continue
        for family in family_text.split(","):
            normalized = family.strip().casefold()
            if normalized:
                families.add(normalized)
    return families


@lru_cache(maxsize=1)
def linux_scalable_font_families() -> set[str] | None:
    """Return installed scalable Fontconfig families, or None if unavailable."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        result = subprocess.run(
            ["fc-list", "--format=%{family}\t%{scalable}\n"],
            check=True,
            capture_output=True,
            text=True,
            timeout=1.5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    families = parse_scalable_font_families(result.stdout)
    # A malformed/unsupported fc-list format should fall back to Tk's family
    # list rather than make every family appear unusable.
    return families or None


def choose_font_family(
    available_families: Iterable[str],
    candidates: Iterable[str] = _UI_CANDIDATES,
    scalable_families: set[str] | None = None,
) -> str | None:
    """Select an actual Tk family, preferring a scalable outline font."""
    available = {str(name).strip().casefold(): str(name).strip() for name in available_families}
    scalable = {name.casefold() for name in scalable_families} if scalable_families is not None else None

    for candidate in candidates:
        actual = available.get(candidate.casefold())
        if actual and (scalable is None or actual.casefold() in scalable):
            return actual

    # Fontconfig aliases can differ from Tk's displayed family casing/naming.
    # If none of the preferred families matched, use any shared scalable face.
    if scalable is not None:
        for key in sorted(available):
            if key in scalable:
                return available[key]
    return None


def configure_tk_named_fonts(root) -> tuple[str, str]:
    """Apply scalable fonts to Tk named fonts before the first widgets exist."""
    try:
        available = tkfont.families(root)
    except Exception:
        available = ()

    scalable = linux_scalable_font_families()
    family = choose_font_family(available, _UI_CANDIDATES, scalable)
    mono_family = choose_font_family(available, _MONO_CANDIDATES, scalable)

    try:
        current_default = tkfont.nametofont("TkDefaultFont", root=root)
        fallback_family = str(current_default.cget("family") or "").strip()
    except Exception:
        fallback_family = ""

    family = family or fallback_family or "TkDefaultFont"
    mono_family = mono_family or family

    # These aliases are used by Tk itself and by third-party widgets which do
    # not pass an explicit CTkFont. Update them before the panel builds widgets.
    regular_aliases = (
        "TkDefaultFont",
        "TkTextFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont",
    )
    for alias in regular_aliases:
        try:
            named_font = tkfont.nametofont(alias, root=root)
            size = int(named_font.cget("size"))
            # A negative Tk font size is pixel-based. Convert it to a positive
            # point size so the font follows desktop DPI rather than staying a
            # fixed number of device pixels.
            if size < 0:
                try:
                    dpi = float(root.winfo_fpixels("1i"))
                except Exception:
                    dpi = 96.0
                size = max(8, round(abs(size) * 72.0 / max(72.0, dpi)))
            elif size == 0:
                size = 10
            named_font.configure(family=family, size=size)
        except Exception:
            # Tk versions vary in which named aliases they expose.
            continue

    try:
        fixed_font = tkfont.nametofont("TkFixedFont", root=root)
        size = int(fixed_font.cget("size"))
        if size < 0:
            try:
                dpi = float(root.winfo_fpixels("1i"))
            except Exception:
                dpi = 96.0
            size = max(8, round(abs(size) * 72.0 / max(72.0, dpi)))
        elif size == 0:
            size = 10
        fixed_font.configure(family=mono_family, size=size)
    except Exception:
        pass

    return family, mono_family
