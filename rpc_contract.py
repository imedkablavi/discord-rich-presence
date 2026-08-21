"""Final validation/sanitization for payloads sent to Discord RPC."""

from __future__ import annotations

from typing import Any, Dict


_TEXT_ALIASES = {'x': 'X.com', 'c': 'C language'}
_TEXT_KEYS = ('name', 'details', 'state', 'large_text', 'small_text')
_URL_KEYS = ('details_url', 'state_url', 'large_url', 'small_url')
_ASSET_KEYS = ('large_image', 'small_image')


def _http_url(value: Any, limit: int = 512) -> str | None:
    text = str(value or '').strip().strip('`')
    if not text or len(text) > limit:
        return None
    if not text.startswith(('https://', 'http://')):
        return None
    return text


def sanitize_rpc_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a payload that stays inside pypresence/Discord field contracts.

    This is intentionally a second line of defense after detector-specific
    builders. Manual overrides and future detectors must not be able to break
    the entire RPC session with one malformed optional field.
    """
    result = {key: value for key, value in dict(payload or {}).items() if value is not None}

    for key in _TEXT_KEYS:
        if key not in result:
            continue
        text = str(result[key]).strip()
        if key in {'name', 'large_text', 'small_text'}:
            text = _TEXT_ALIASES.get(text.lower(), text)
        if len(text) < 2:
            result.pop(key, None)
        else:
            result[key] = text[:128]

    for key in _ASSET_KEYS:
        if key not in result:
            continue
        value = str(result[key]).strip()
        if not (1 <= len(value) <= 300):
            result.pop(key, None)
        else:
            result[key] = value

    for key in _URL_KEYS:
        if key not in result:
            continue
        url = _http_url(result[key])
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
                label = str(button.get('label', '')).strip()
                url = _http_url(button.get('url'))
                if 1 <= len(label) <= 32 and url:
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
        party_id = str(result['party_id']).strip()
        if not party_id or len(party_id) > 128:
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
