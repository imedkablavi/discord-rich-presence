from pathlib import Path

import pytest

from browser_companion import BrowserCompanionBridge
from config import Config
from detectors.browser import BrowserDetector
from detectors.media import MediaDetector
from privacy import PrivacyRedactor


def _snapshot(**overrides):
    payload = {
        'version': 1,
        'browser': 'Brave',
        'tab_id': '42',
        'url': 'https://www.youtube.com/watch?v=abc123&t=10',
        'title': 'Example video - YouTube',
        'service': 'YouTube',
        'private': False,
        'focused': True,
        'visible': True,
        'media': {
            'playing': True,
            'position': 10,
            'duration': 240,
            'title': 'Example video',
            'artist': 'Example channel',
        },
    }
    payload.update(overrides)
    return payload


def test_bridge_prefers_focused_tab_over_background_media(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    bridge = BrowserCompanionBridge(cfg)
    bridge.update(_snapshot(tab_id='playing', focused=False, visible=False))
    bridge.update(_snapshot(
        tab_id='focused',
        focused=True,
        url='https://github.com/imedkablavi/discord-rich-presence',
        service='GitHub',
        media={'playing': False},
    ))

    latest = bridge.latest('Brave')
    assert latest is not None
    assert latest['tab_id'] == 'focused'
    assert latest['service'] == 'GitHub'

    playing = bridge.latest_media('Brave')
    assert playing is not None
    assert playing['tab_id'] == 'playing'
    assert playing['service'] == 'YouTube'


def test_companion_status_is_privacy_safe(tmp_path: Path):
    bridge = BrowserCompanionBridge(Config(tmp_path / 'config.yaml'))
    empty = bridge.status()
    assert empty == {
        'ok': True,
        'version': 1,
        'records': 0,
        'connected': False,
        'latest': None,
    }

    bridge.update(_snapshot())
    status = bridge.status()
    assert status['ok'] is True
    assert status['connected'] is True
    assert status['records'] == 1
    assert status['latest']['browser'] == 'Brave'
    assert status['latest']['service'] == 'YouTube'
    assert status['latest']['focused'] is True
    assert status['latest']['visible'] is True
    assert status['latest']['media_playing'] is True
    assert status['latest']['age_ms'] >= 0
    serialized = repr(status)
    assert 'abc123' not in serialized
    assert 'Example video' not in serialized
    assert '42' not in serialized


def test_bridge_rejects_wrong_protocol_version(tmp_path: Path):
    bridge = BrowserCompanionBridge(Config(tmp_path / 'config.yaml'))
    with pytest.raises(ValueError, match='unsupported_version'):
        bridge.update(_snapshot(version=2))


def test_browser_detector_prefers_exact_companion_metadata(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('browser_companion.enabled', False)
    detector = BrowserDetector(cfg)

    class FakeCompanion:
        def latest(self, _browser_name):
            return _snapshot()

    detector.companion = FakeCompanion()
    activity = detector.detect({
        'app_name': 'com.brave.Browser',
        'title': 'Unhelpful browser title — Brave',
    })

    assert activity is not None
    assert activity['source'] == 'companion'
    assert activity['service'] == 'YouTube'
    assert activity['page_title'] == 'Example video'
    assert activity['url'] == 'https://www.youtube.com/watch?v=abc123&t=10'
    assert activity['url_is_exact'] is True


def test_self_hosted_domain_mapping_requires_no_custom_javascript(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('browser_companion.enabled', False)
    cfg.set('browser_companion.domain_services', {
        'media.home.example': 'Jellyfin',
        '*.corp.example': 'Company Portal',
    })
    detector = BrowserDetector(cfg)

    class FakeCompanion:
        def __init__(self, url):
            self.url = url

        def latest(self, _browser_name):
            return _snapshot(
                url=self.url,
                title='Dashboard',
                service='',
                media={'playing': False},
            )

    detector.companion = FakeCompanion('https://media.home.example/web/index.html')
    exact = detector.detect({'app_name': 'brave', 'title': 'Dashboard — Brave'})
    assert exact is not None
    assert exact['service'] == 'Jellyfin'

    detector.companion = FakeCompanion('https://git.corp.example/projects')
    wildcard = detector.detect({'app_name': 'brave', 'title': 'Projects — Brave'})
    assert wildcard is not None
    assert wildcard['service'] == 'Company Portal'


def test_private_window_never_reuses_normal_companion_snapshot(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('browser_companion.enabled', False)
    detector = BrowserDetector(cfg)

    class FakeCompanion:
        def latest(self, _browser_name):
            return _snapshot()

    detector.companion = FakeCompanion()
    activity = detector.detect({
        'app_name': 'brave',
        'title': 'Private Browsing — Brave',
    })

    assert activity is not None
    assert activity['is_private'] is True
    assert activity['url'] is None
    assert activity['source'] == 'private'


def test_media_detector_uses_background_youtube_companion_snapshot(tmp_path: Path, monkeypatch):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('browser_companion.enabled', False)
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('shutil.which', lambda _command: None)
    detector = MediaDetector(cfg)

    class FakeCompanion:
        def latest_media(self):
            return _snapshot(focused=False, visible=False)

    detector.companion = FakeCompanion()
    activity = detector.detect({'app_name': 'org.kde.konsole', 'title': 'Konsole'})

    assert activity is not None
    assert activity['source'] == 'companion'
    assert activity['player'] == 'Brave'
    assert activity['service'] == 'YouTube'
    assert activity['title'] == 'Example channel - Example video'
    assert activity['position'] == 10
    assert activity['duration'] == 240
    assert activity['tab_focused'] is False


def test_balanced_privacy_reduces_exact_url_to_domain_by_default(tmp_path: Path):
    redactor = PrivacyRedactor(Config(tmp_path / 'config.yaml'))
    result = redactor.redact_activity({
        'type': 'browser',
        'browser_name': 'Brave',
        'page_title': 'Example',
        'service': 'YouTube',
        'url': 'https://www.youtube.com/watch?v=abc123&token=secret#oauth-token',
        'url_is_exact': True,
    })
    assert result['url'] == 'https://www.youtube.com'


def test_balanced_path_mode_drops_query_and_fragment(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('privacy.browser_url_mode', 'path')
    redactor = PrivacyRedactor(cfg)
    result = redactor.redact_activity({
        'type': 'browser',
        'page_title': 'Issue',
        'url': 'https://github.com/org/repo/issues/1?token=secret#comment',
        'url_is_exact': True,
    })
    assert result['url'] == 'https://github.com/org/repo/issues/1'


def test_balanced_full_mode_redacts_sensitive_query_and_drops_fragment(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('privacy.browser_url_mode', 'full')
    redactor = PrivacyRedactor(cfg)
    result = redactor.redact_activity({
        'type': 'browser',
        'page_title': 'Example',
        'url': 'https://example.com/watch?id=123&access_token=very-secret#session-token',
        'url_is_exact': True,
    })
    assert result['url'].startswith('https://example.com/watch?')
    assert 'id=123' in result['url']
    assert 'access_token=%5BREDACTED%5D' in result['url']
    assert '#' not in result['url']
    assert 'very-secret' not in result['url']
