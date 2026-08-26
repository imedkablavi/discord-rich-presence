from pathlib import Path

import pytest

from config import Config
from detectors.browser import BrowserDetector
from presence import PresenceBuilder


class _FakeCompanion:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def latest(self, browser_name):
        return dict(self.snapshot)


def _detector(tmp_path: Path) -> tuple[BrowserDetector, Config]:
    config = Config(tmp_path / 'config.yaml')
    config.set('browser_companion.enabled', False)
    detector = BrowserDetector(config)
    return detector, config


@pytest.mark.parametrize(
    ('url', 'service'),
    [
        ('https://web.whatsapp.com/', 'WhatsApp'),
        ('https://www.facebook.com/', 'Facebook'),
        ('https://www.facebook.com/messages/t/123456', 'Messenger'),
        ('https://www.messenger.com/t/123456', 'Messenger'),
        ('https://www.instagram.com/direct/t/123456/', 'Instagram'),
        ('https://www.linkedin.com/messaging/thread/abc/', 'LinkedIn'),
        ('https://www.threads.com/@someone/post/abc', 'Threads'),
        ('https://www.tiktok.com/@someone/video/123', 'TikTok'),
        ('https://web.telegram.org/a/#123456', 'Telegram'),
        ('https://web.snapchat.com/', 'Snapchat'),
        ('https://discord.com/channels/123/456', 'Discord Web'),
        ('https://www.pinterest.com/someone/board/', 'Pinterest'),
        ('https://bsky.app/profile/example.test/post/abc', 'Bluesky'),
        ('https://x.com/someone/status/123', 'X'),
        ('https://www.reddit.com/r/example/comments/abc/private_title/', 'Reddit'),
    ],
)
def test_social_domains_are_structurally_detected(tmp_path: Path, url: str, service: str):
    detector, _ = _detector(tmp_path)
    assert detector._detect_service_from_url(url) == service


def test_social_detection_ignores_domains_hidden_in_query_text(tmp_path: Path):
    detector, _ = _detector(tmp_path)
    assert detector._detect_service_from_url(
        'https://example.com/redirect?next=https://www.instagram.com/direct/t/123'
    ) is None
    assert detector._detect_service_from_url(
        'https://example.com/?next=https://web.whatsapp.com/'
    ) is None


@pytest.mark.parametrize(
    ('url', 'title', 'service', 'homepage'),
    [
        (
            'https://web.whatsapp.com/',
            'Alice Family Group (12) - WhatsApp',
            'WhatsApp',
            'https://web.whatsapp.com',
        ),
        (
            'https://www.facebook.com/messages/t/123456',
            'Alice Smith | Messenger',
            'Messenger',
            'https://www.messenger.com',
        ),
        (
            'https://www.instagram.com/direct/t/123456/?hl=en',
            'Alice (@alice) • Instagram photos and videos',
            'Instagram',
            'https://www.instagram.com',
        ),
        (
            'https://www.linkedin.com/messaging/thread/abc/?trk=secret',
            'Alice Smith | LinkedIn',
            'LinkedIn',
            'https://www.linkedin.com',
        ),
        (
            'https://discord.com/channels/123456/789012',
            '#private-team | Secret Server | Discord',
            'Discord Web',
            'https://discord.com/app',
        ),
    ],
)
def test_social_companion_discards_private_titles_and_deep_links(
    tmp_path: Path,
    url: str,
    title: str,
    service: str,
    homepage: str,
):
    detector, config = _detector(tmp_path)
    config.set('privacy.browser_url_mode', 'full')
    detector.companion = _FakeCompanion({
        'title': title,
        'url': url,
        'service': service,
        'private': False,
        'media': {'playing': True, 'title': 'private media title'},
    })

    activity = detector._from_companion('Firefox')
    assert activity is not None
    assert activity['social'] is True
    assert activity['service'] == service
    assert activity['page_title'] == f'Using {service}'
    assert activity['url'] == homepage
    assert activity['url_is_exact'] is False
    assert activity['media'] == {}

    payload = PresenceBuilder(config).build(activity)
    rendered = repr(payload)
    assert title not in rendered
    assert url not in rendered
    assert '123456' not in rendered
    assert '789012' not in rendered
    assert 'private media title' not in rendered
    assert payload['details'] == f'Using {service}'
    assert payload['state'] == f'{service} · Firefox'
    assert payload['details_url'] == homepage
    assert payload['large_url'] == homepage
    assert any(button.get('url') == homepage for button in payload.get('buttons', []))


def test_social_window_title_fallback_is_generic(tmp_path: Path):
    detector, _ = _detector(tmp_path)
    detector.companion = None

    activity = detector.detect({
        'app_name': 'firefox',
        'title': 'Alice Smith | LinkedIn — Firefox',
    })

    assert activity is not None
    assert activity['service'] == 'LinkedIn'
    assert activity['page_title'] == 'Using LinkedIn'
    assert 'Alice Smith' not in repr(activity)
    assert activity['url'] == 'https://www.linkedin.com'
