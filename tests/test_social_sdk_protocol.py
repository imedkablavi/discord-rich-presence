import pytest

from social_sdk_protocol import (
    MAX_PROTOCOL_LINE_BYTES,
    activity_fields,
    decode_message,
    derive_display_name,
    encode_command,
    encode_update,
)


def test_protocol_round_trip_percent_encodes_tabs_unicode_and_urls():
    line = encode_command('UPDATE', {
        'name': 'Counter-Strike 2',
        'details': 'Mirage · CT\t8–6 T',
        'details_url': 'https://example.com/a?x=1&y=2',
    })
    op, fields = decode_message(line)
    assert op == 'UPDATE'
    assert fields['name'] == 'Counter-Strike 2'
    assert fields['details'] == 'Mirage · CT\t8–6 T'
    assert fields['details_url'] == 'https://example.com/a?x=1&y=2'


def test_protocol_rejects_unknown_fields_and_oversized_lines():
    with pytest.raises(ValueError, match='unsupported UPDATE field'):
        encode_command('UPDATE', {'raw_process_memory': 'nope'})

    with pytest.raises(ValueError, match='size limit'):
        encode_command('UPDATE', {'details': 'x' * MAX_PROTOCOL_LINE_BYTES})


def test_activity_fields_use_specific_large_text_as_dynamic_name():
    fields = activity_fields({
        'activity_type': 0,
        'details': 'Counter-Strike 2 · Competitive',
        'state': 'Mirage · Counter-Terrorists · 8–6',
        'large_image': 'https://example.com/cs2.png',
        'large_text': 'Counter-Strike 2',
        'buttons': [{'label': 'View on Steam', 'url': 'https://store.steampowered.com/app/730/'}],
    })
    assert fields['name'] == 'Counter-Strike 2'
    assert fields['details'] == 'Counter-Strike 2 · Competitive'
    assert fields['button1_label'] == 'View on Steam'
    assert fields['button1_url'].endswith('/730/')


def test_dynamic_name_fallback_is_bounded_and_never_one_character():
    assert derive_display_name({'large_text': 'X', 'state': 'Firefox'}) == 'Firefox'
    assert derive_display_name({'details': 'A'}) == 'CYBREX Activity'
    assert len(derive_display_name({'large_text': 'z' * 1000})) == 128


def test_encode_update_inherits_rpc_sanitizer_for_discord_url_limits():
    long_url = 'https://example.com/' + ('a' * 300)
    line = encode_update({
        'activity_type': 0,
        'details': 'Firefox',
        'state': 'Browsing',
        'large_text': 'Firefox',
        'details_url': long_url,
    })
    _, fields = decode_message(line)
    assert fields['name'] == 'Firefox'
    assert 'details_url' not in fields
