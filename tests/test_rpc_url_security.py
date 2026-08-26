import pytest

from rpc_contract import sanitize_rpc_payload


@pytest.mark.parametrize('url', [
    'https://user:secret@example.com/private',
    'https://example.com/path\nInjected: yes',
    'https://example.com/path\rhidden',
    'https://example.com/path\tvalue',
    'https://example.com:bad/path',
    'file:///tmp/private',
    'http://example.com/insecure',
    'https://localhost/private',
    'https://router.local/admin',
    'https://127.0.0.1:8443/private',
    'https://10.0.0.10/private',
    'https://169.254.10.20/private',
    'https://[::1]/private',
])
def test_rpc_drops_unsafe_activity_urls(url: str):
    payload = sanitize_rpc_payload({
        'details': 'Safe activity',
        'details_url': url,
        'large_url': url,
    })

    assert payload['details'] == 'Safe activity'
    assert 'details_url' not in payload
    assert 'large_url' not in payload


@pytest.mark.parametrize('url', [
    'https://user:secret@example.com/private',
    'https://example.com/path\nInjected: yes',
    'https://example.com:bad/path',
    'http://example.com/insecure',
    'https://192.168.1.1/admin',
])
def test_rpc_drops_unsafe_button_urls(url: str):
    payload = sanitize_rpc_payload({
        'details': 'Safe activity',
        'buttons': [{'label': 'Open', 'url': url}],
    })

    assert 'buttons' not in payload


@pytest.mark.parametrize('url', [
    'https://user:secret@example.com/icon.png',
    'https://example.com/icon.png\nInjected: yes',
    'https://example.com:bad/icon.png',
    'http://example.com/icon.png',
    'https://localhost/icon.png',
])
def test_rpc_drops_unsafe_external_artwork_urls(url: str):
    payload = sanitize_rpc_payload({
        'details': 'Safe activity',
        'large_image': url,
        'small_image': url,
    })

    assert 'large_image' not in payload
    assert 'small_image' not in payload


def test_rpc_keeps_asset_keys_and_safe_external_artwork():
    payload = sanitize_rpc_payload({
        'details': 'Safe activity',
        'large_image': 'counter_strike_2',
        'small_image': 'https://example.com/icon.png',
    })

    assert payload['large_image'] == 'counter_strike_2'
    assert payload['small_image'] == 'https://example.com/icon.png'


def test_rpc_normalizes_control_characters_in_display_text():
    payload = sanitize_rpc_payload({
        'details': 'Playing\nCounter-Strike 2',
        'state': 'Mirage\tCompetitive',
        'large_text': 'Counter-Strike 2\rLive',
    })

    assert payload['details'] == 'Playing Counter-Strike 2'
    assert payload['state'] == 'Mirage Competitive'
    assert payload['large_text'] == 'Counter-Strike 2 Live'


def test_rpc_keeps_normal_https_urls_within_field_limits():
    payload = sanitize_rpc_payload({
        'details': 'Safe activity',
        'details_url': 'https://example.com/path?q=1',
        'buttons': [{'label': 'Open', 'url': 'https://example.com/longer/path?q=1'}],
    })

    assert payload['details_url'] == 'https://example.com/path?q=1'
    assert payload['buttons'] == [
        {'label': 'Open', 'url': 'https://example.com/longer/path?q=1'}
    ]
