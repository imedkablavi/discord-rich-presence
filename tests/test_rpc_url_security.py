import pytest

from rpc_contract import sanitize_rpc_payload


@pytest.mark.parametrize('url', [
    'https://user:secret@example.com/private',
    'https://example.com/path\nInjected: yes',
    'https://example.com/path\rhidden',
    'https://example.com/path\tvalue',
    'https://example.com:bad/path',
    'file:///tmp/private',
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
])
def test_rpc_drops_unsafe_button_urls(url: str):
    payload = sanitize_rpc_payload({
        'details': 'Safe activity',
        'buttons': [{'label': 'Open', 'url': url}],
    })

    assert 'buttons' not in payload


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
