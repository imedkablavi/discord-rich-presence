"""Unicode display helpers shared by desktop UI code and headless tests."""

from __future__ import annotations

import re

try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    _ARABIC_BIDI_AVAILABLE = True
except ImportError:  # pragma: no cover - source checkout without optional UI deps
    arabic_reshaper = None
    get_display = None
    _ARABIC_BIDI_AVAILABLE = False


_ARABIC_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
_MOJIBAKE_HINTS = ("Ø", "Ù", "Ã", "Â", "â€", "ï¿½")


def repair_utf8_mojibake(value: object) -> str:
    """Repair likely UTF-8 text that was decoded as Latin-1/CP1252."""

    text = str(value or "")
    if not text or not any(marker in text for marker in _MOJIBAKE_HINTS):
        return text

    original_arabic = len(_ARABIC_RE.findall(text))
    original_noise = sum(text.count(marker) for marker in _MOJIBAKE_HINTS)

    for source_encoding in ("cp1252", "latin1"):
        try:
            candidate = text.encode(source_encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

        candidate_arabic = len(_ARABIC_RE.findall(candidate))
        candidate_noise = sum(candidate.count(marker) for marker in _MOJIBAKE_HINTS)
        if candidate_arabic > original_arabic or candidate_noise < original_noise:
            return candidate

    return text


def display_text(value: object, *, base_dir: str = "L") -> str:
    """Return UI-safe text with mojibake repair and Arabic shaping/BiDi."""

    text = repair_utf8_mojibake(value)
    if not _ARABIC_RE.search(text) or not _ARABIC_BIDI_AVAILABLE:
        return text

    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped, base_dir=base_dir)
    except Exception:
        return text
