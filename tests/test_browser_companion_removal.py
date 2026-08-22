from pathlib import Path

import pytest

from browser_companion import BrowserCompanionBridge
from config import Config


def test_removed_tab_is_cleared_immediately(tmp_path: Path):
    bridge = BrowserCompanionBridge(Config(tmp_path / 'config.yaml'))
    bridge.update({
        'version': 1,
        'browser': 'Brave',
        'tab_id': '99',
        'url': 'https://www.youtube.com/watch?v=abc',
        'title': 'Video - YouTube',
        'service': 'YouTube',
        'focused': True,
        'visible': True,
        'media': {'playing': True, 'position': 5, 'duration': 100},
    })
    assert bridge.latest('Brave') is not None
    assert bridge.latest_media('Brave') is not None

    bridge.update({
        'version': 1,
        'browser': 'Brave',
        'tab_id': '99',
        'removed': True,
    })

    assert bridge.latest('Brave') is None
    assert bridge.latest_media('Brave') is None


def test_removal_is_scoped_to_browser_and_tab_id(tmp_path: Path):
    bridge = BrowserCompanionBridge(Config(tmp_path / 'config.yaml'))
    for browser in ('Brave', 'Chrome'):
        bridge.update({
            'version': 1,
            'browser': browser,
            'tab_id': '7',
            'url': 'https://example.com',
            'title': 'Example',
            'focused': False,
            'visible': True,
            'media': {'playing': False},
        })

    bridge.update({
        'version': 1,
        'browser': 'Brave',
        'tab_id': '7',
        'removed': True,
    })

    assert bridge.latest('Brave') is None
    assert bridge.latest('Chrome') is not None


def test_legacy_removal_without_browser_fails_closed(tmp_path: Path):
    bridge = BrowserCompanionBridge(Config(tmp_path / 'config.yaml'))
    bridge.update({
        'version': 1,
        'browser': 'Firefox',
        'tab_id': '7',
        'url': 'https://example.com',
        'title': 'Example',
        'focused': True,
        'visible': True,
        'media': {'playing': False},
    })

    with pytest.raises(ValueError, match='browser_required'):
        bridge.update({'version': 1, 'tab_id': '7', 'removed': True})

    assert bridge.latest('Firefox') is not None
