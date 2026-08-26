from pathlib import Path

import pytest

from browser_companion import BrowserCompanionBridge
from config import Config


def _snapshot(browser: str, tab_id: str, **overrides):
    payload = {
        'version': 1,
        'browser': browser,
        'tab_id': tab_id,
        'url': 'https://example.com/page',
        'title': f'{browser} page',
        'service': '',
        'private': False,
        'focused': True,
        'visible': True,
        'media': {'playing': False},
    }
    payload.update(overrides)
    return payload


def _bridge(tmp_path: Path) -> BrowserCompanionBridge:
    cfg = Config(tmp_path / 'config.yaml')
    return BrowserCompanionBridge(cfg)


def test_same_tab_id_is_isolated_between_browsers(tmp_path: Path):
    bridge = _bridge(tmp_path)
    bridge.update(_snapshot('Brave', '42', service='YouTube'))
    bridge.update(_snapshot('Firefox', '42', service='GitHub'))

    bridge.update({
        'version': 1,
        'browser': 'Brave',
        'tab_id': '42',
        'removed': True,
    })

    assert bridge.latest('Brave') is None
    firefox = bridge.latest('Firefox')
    assert firefox is not None
    assert firefox['tab_id'] == '42'
    assert firefox['service'] == 'GitHub'


def test_removal_without_browser_fails_closed(tmp_path: Path):
    bridge = _bridge(tmp_path)
    bridge.update(_snapshot('Firefox', '7', service='ChatGPT'))

    with pytest.raises(ValueError, match='browser_required'):
        bridge.update({'version': 1, 'tab_id': '7', 'removed': True})

    assert bridge.latest('Firefox') is not None


@pytest.mark.parametrize('unsafe_url', [
    'https://user:secret@example.com/private',
    'https://example.com/path\nX-Fake-Header: yes',
    'https://example.com/path\rhidden',
    'https://example.com/path\tvalue',
])
def test_companion_drops_credential_or_control_character_urls(tmp_path: Path, unsafe_url: str):
    bridge = _bridge(tmp_path)
    bridge.update(_snapshot('Brave', '9', url=unsafe_url))

    latest = bridge.latest('Brave')
    assert latest is not None
    assert latest['url'] is None


def test_companion_keeps_normal_http_url(tmp_path: Path):
    bridge = _bridge(tmp_path)
    bridge.update(_snapshot('Firefox', '10', url='https://example.com/path?q=1'))

    latest = bridge.latest('Firefox')
    assert latest is not None
    assert latest['url'] == 'https://example.com/path?q=1'
