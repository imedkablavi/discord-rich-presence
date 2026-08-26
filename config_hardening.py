"""Fail-soft validation for optional Rich Presence links.

A malformed optional URL must never make the entire CYBREX configuration
unloadable or prevent the service from starting. Core settings still use the
strict Config validator; only optional outbound link fields are sanitized.
"""

from __future__ import annotations

import logging
from typing import Any

from url_safety import public_https_url


LOGGER = logging.getLogger(__name__)
_APPLIED = False


def _clean_buttons(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in value[:2]:
        if not isinstance(item, dict):
            continue
        label = str(item.get('label', '') or '').strip()
        if not (1 <= len(label) <= 32):
            continue
        url = public_https_url(item.get('url'), 512)
        if not url:
            continue
        candidate = {'label': label, 'url': url}
        if candidate not in cleaned:
            cleaned.append(candidate)
    return cleaned


def sanitize_optional_links(data: Any) -> int:
    """Drop only malformed optional external links and return the drop count."""
    if not isinstance(data, dict):
        return 0
    dropped = 0

    discord = data.get('discord')
    if isinstance(discord, dict):
        before = discord.get('buttons', [])
        after = _clean_buttons(before)
        if before != after:
            dropped += max(1, len(before) - len(after)) if isinstance(before, list) else 1
            discord['buttons'] = after

    override = data.get('override')
    if isinstance(override, dict):
        before = override.get('buttons', [])
        after = _clean_buttons(before)
        if before != after:
            dropped += max(1, len(before) - len(after)) if isinstance(before, list) else 1
            override['buttons'] = after
        for key in ('details_url', 'state_url', 'large_url', 'small_url'):
            raw = override.get(key, '')
            if not str(raw or '').strip():
                override[key] = ''
                continue
            safe = public_https_url(raw, 256)
            if safe is None:
                override[key] = ''
                dropped += 1
            else:
                override[key] = safe

    images = data.get('images')
    if isinstance(images, dict):
        overrides = images.get('icon_overrides')
        if isinstance(overrides, dict):
            cleaned_overrides = {}
            for key, raw_value in list(overrides.items())[:256]:
                name = str(key or '').strip()
                value = str(raw_value or '').strip()
                if not name or not value:
                    dropped += 1
                    continue
                if value.lower().startswith(('http://', 'https://')):
                    safe = public_https_url(value, 300)
                    if not safe:
                        dropped += 1
                        continue
                    value = safe
                cleaned_overrides[name] = value[:300]
            images['icon_overrides'] = cleaned_overrides

    return dropped


def apply_config_hardening() -> None:
    """Wrap Config validation so optional bad links cannot brick startup."""
    global _APPLIED
    if _APPLIED:
        return

    from config import Config

    original_validate = Config._validate

    def hardened_validate(data):  # noqa: ANN001
        dropped = sanitize_optional_links(data)
        if dropped:
            LOGGER.warning(
                'Ignored %d invalid optional Rich Presence link field(s); core configuration remains usable',
                dropped,
            )
        return original_validate(data)

    Config._validate = staticmethod(hardened_validate)
    _APPLIED = True
