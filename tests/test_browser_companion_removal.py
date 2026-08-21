from pathlib import Path

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

    bridge.update({'version': 1, 'tab_id': '99', 'removed': True})

    assert bridge.latest('Brave') is None
    assert bridge.latest_media('Brave') is None


def test_removal_clears_same_tab_id_regardless_of_browser_label(tmp_path: Path):
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

    bridge.update({'version': 1, 'tab_id': '7', 'removed': True})

    assert bridge.latest('Brave') is None
    assert bridge.latest('Chrome') is None
