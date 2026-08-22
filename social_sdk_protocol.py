"""Small bounded protocol shared with the optional Discord Social SDK helper.

The native Social SDK is distributed as a C/C++ SDK, while the main service is
Python. Keep the boundary deliberately tiny: one tab-separated command per line
with percent-encoded values. The helper never needs to parse arbitrary JSON and
the Python process never exposes a socket or network listener for it.
"""

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote, unquote

from rpc_contract import sanitize_rpc_payload


MAX_PROTOCOL_LINE_BYTES = 16 * 1024
MAX_DYNAMIC_NAME = 128

_ALLOWED_UPDATE_FIELDS = {
    'name',
    'activity_type',
    'details',
    'state',
    'details_url',
    'state_url',
    'large_image',
    'large_text',
    'large_url',
    'small_image',
    'small_text',
    'small_url',
    'start',
    'end',
    'button1_label',
    'button1_url',
    'button2_label',
    'button2_url',
}


def _encode(value: object) -> str:
    return quote(str(value), safe='')


def _decode(value: str) -> str:
    return unquote(value)


def encode_command(command: str, fields: Mapping[str, object] | None = None) -> str:
    """Encode one bounded helper command with an explicit field allowlist."""
    op = str(command or '').strip().upper()
    if op not in {'PING', 'SET_APP', 'UPDATE', 'CLEAR', 'QUIT'}:
        raise ValueError(f'unsupported Social SDK command: {op or "<empty>"}')

    parts = [op]
    for key, value in sorted((fields or {}).items()):
        clean_key = str(key or '').strip()
        if op == 'SET_APP':
            if clean_key != 'application_id':
                raise ValueError(f'unsupported SET_APP field: {clean_key}')
        elif op == 'UPDATE':
            if clean_key not in _ALLOWED_UPDATE_FIELDS:
                raise ValueError(f'unsupported UPDATE field: {clean_key}')
        elif fields:
            raise ValueError(f'{op} does not accept fields')
        if value is None:
            continue
        parts.append(f'{clean_key}={_encode(value)}')

    line = '\t'.join(parts) + '\n'
    if len(line.encode('utf-8')) > MAX_PROTOCOL_LINE_BYTES:
        raise ValueError('Social SDK helper command exceeds protocol size limit')
    return line


def decode_message(line: str) -> tuple[str, dict[str, str]]:
    """Decode one response/command line for tests and helper diagnostics."""
    if not isinstance(line, str):
        raise TypeError('protocol line must be text')
    if len(line.encode('utf-8')) > MAX_PROTOCOL_LINE_BYTES:
        raise ValueError('Social SDK helper line exceeds protocol size limit')

    raw = line.rstrip('\r\n')
    if not raw:
        raise ValueError('empty Social SDK helper line')
    parts = raw.split('\t')
    op = parts[0].strip().upper()
    fields: dict[str, str] = {}
    for part in parts[1:]:
        if '=' not in part:
            raise ValueError('malformed Social SDK helper field')
        key, encoded = part.split('=', 1)
        key = key.strip()
        if not key or key in fields:
            raise ValueError('invalid or duplicate Social SDK helper field')
        fields[key] = _decode(encoded)
    return op, fields


def derive_display_name(payload: Mapping[str, Any]) -> str:
    """Choose the top-line name for a Social SDK activity."""
    for key in ('large_text', 'state', 'details'):
        value = str(payload.get(key) or '').strip()
        if len(value) >= 2:
            return value[:MAX_DYNAMIC_NAME]
    return 'CYBREX Activity'


def _activity_type_value(value: object) -> int:
    raw = getattr(value, 'value', value)
    try:
        result = int(raw)
    except (TypeError, ValueError, OverflowError):
        return 0
    return result if 0 <= result <= 6 else 0


def activity_fields(payload: Mapping[str, Any], *, name: str | None = None) -> dict[str, object]:
    """Convert a legacy-compatible payload to Social SDK helper fields."""
    clean = sanitize_rpc_payload(dict(payload or {}))
    explicit_name = str(name or '').strip()
    fields: dict[str, object] = {
        'name': explicit_name[:MAX_DYNAMIC_NAME] if len(explicit_name) >= 2 else derive_display_name(clean),
    }

    for key in (
        'details', 'state', 'details_url', 'state_url',
        'large_image', 'large_text', 'large_url', 'small_image', 'small_text',
        'small_url', 'start', 'end',
    ):
        if key in clean:
            fields[key] = clean[key]
    if 'activity_type' in clean:
        fields['activity_type'] = _activity_type_value(clean['activity_type'])

    buttons = clean.get('buttons')
    if isinstance(buttons, list):
        for index, button in enumerate(buttons[:2], start=1):
            if not isinstance(button, dict):
                continue
            label = button.get('label')
            url = button.get('url')
            if label and url:
                fields[f'button{index}_label'] = label
                fields[f'button{index}_url'] = url
    return fields


def encode_update(payload: Mapping[str, Any], *, name: str | None = None) -> str:
    return encode_command('UPDATE', activity_fields(payload, name=name))
