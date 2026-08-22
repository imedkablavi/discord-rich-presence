"""Final validation/sanitization for payloads sent to Discord RPC."""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlsplit

from pypresence.types import ActivityType


_TEXT_ALIASES = {'x': 'X.com', 'c': 'C language'}
_TEXT_KEYS = ('details', 'state', 'large_text', 'small_text')
_URL_KEYS = ('details_url', 'state_url', 'large_url', 'small_url')
_ASSET_KEYS = ('large_image', 'small_image')
_DISCORD_URL_MAX = 256
_BUTTON_URL_MAX = 512
_ASSET_MAX = 300
_ALLOWED_KEYS = {
    'activity_type',
    'state', 'state_url',
    'details', 'details_url',
    'start', 'end',
    'large_image', 'large_text', 'large_url',
    'small_image', 'small_text', 'small_url',
    'party_id', 'party_size',
    'buttons',
}


def _contains_controls(text: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in text)


def _clean_text(value: Any, limit: int) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    # Discord text fields do not need embedded control characters. Normalize
    # them to spaces so malformed page titles/custom labels cannot trip schema
    # validation while preserving readable text.
    text = ''.join(' ' if ord(char) < 32 or ord(char) == 127 else char for char in text)
    text = ' '.join(text.split())
    return text[:limit] or None


def _http_url(value: Any, limit: int) -> str | None:
    text = str(value or '').strip().strip('`')
    if not text or len(text) > limit or _contains_controls(text):
        return None
    try:
        parsed = urlsplit(text)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {'https', 'http'} or not hostname:
        return None
    # Rich Presence links never need URL userinfo. Reject it instead of risking
    # accidental publication of credentials embedded in a browser/custom URL.
    if parsed.username is not None or parsed.password is not None:
        return None
    return text


def sanitize_rpc_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a payload that stays inside pypresence/legacy Discord RPC contracts.

    Only fields that this application intentionally supports are allowed through.
    Detector metadata must never accidentally become a keyword argument to
    ``Presence.update`` and tear down the service loop.
    """
    raw = dict(payload or {})
    result = {
        key: value
        for key, value in raw.items()
        if key in _ALLOWED_KEYS and value is not None
    }

    activity_type = result.get('activity_type')
    if activity_type is not None and not isinstance(activity_type, ActivityType):
        result.pop('activity_type', None)

    for key in _TEXT_KEYS:
        if key not in result:
            continue
        text = _clean_text(result[key], 128)
        if text is None:
            result.pop(key, None)
            continue
        if key in {'large_text', 'small_text'}:
            text = _TEXT_ALIASES.get(text.lower(), text)
        if len(text) < 2:
            result.pop(key, None)
        else:
            result[key] = text

    for key in _ASSET_KEYS:
        if key not in result:
            continue
        value = str(result[key]).strip()
        if not (1 <= len(value) <= _ASSET_MAX) or _contains_controls(value):
            result.pop(key, None)
            continue
        if value.lower().startswith(('http://', 'https://')):
            safe_url = _http_url(value, _ASSET_MAX)
            if safe_url is None:
                result.pop(key, None)
            else:
                result[key] = safe_url
        else:
            result[key] = value

    for key in _URL_KEYS:
        if key not in result:
            continue
        url = _http_url(result[key], _DISCORD_URL_MAX)
        if url is None:
            result.pop(key, None)
        else:
            result[key] = url

    buttons = result.get('buttons')
    if buttons is not None:
        safe_buttons = []
        if isinstance(buttons, list):
            for button in buttons[:2]:
                if not isinstance(button, dict):
                    continue
                label = _clean_text(button.get('label', ''), 32)
                url = _http_url(button.get('url'), _BUTTON_URL_MAX)
                if label and 1 <= len(label) <= 32 and url:
                    candidate = {'label': label, 'url': url}
                    if candidate not in safe_buttons:
                        safe_buttons.append(candidate)
        if safe_buttons:
            result['buttons'] = safe_buttons
        else:
            result.pop('buttons', None)

    for key in ('start', 'end'):
        if key not in result:
            continue
        value = result[key]
        if isinstance(value, bool):
            result.pop(key, None)
            continue
        try:
            timestamp = int(value)
        except (TypeError, ValueError, OverflowError):
            result.pop(key, None)
            continue
        if timestamp <= 0:
            result.pop(key, None)
        else:
            result[key] = timestamp
    if 'start' in result and 'end' in result and result['end'] <= result['start']:
        result.pop('end', None)

    if 'party_id' in result:
        party_id = _clean_text(result['party_id'], 128)
        if party_id is None:
            result.pop('party_id', None)
        else:
            result['party_id'] = party_id

    if 'party_size' in result:
        party_size = result['party_size']
        valid = False
        if isinstance(party_size, (list, tuple)) and len(party_size) == 2:
            try:
                current = int(party_size[0])
                maximum = int(party_size[1])
                valid = current > 0 and maximum >= current
            except (TypeError, ValueError, OverflowError):
                valid = False
            if valid:
                result['party_size'] = [current, maximum]
        if not valid:
            result.pop('party_size', None)

    return result
