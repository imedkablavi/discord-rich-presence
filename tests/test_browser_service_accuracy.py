from pathlib import Path

from config import Config
from detectors.browser import BrowserDetector


class _FakeCompanion:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def latest(self, browser_name):
        return dict(self.snapshot)


def _detector(tmp_path: Path) -> BrowserDetector:
    config = Config(tmp_path / 'config.yaml')
    config.set('browser_companion.enabled', False)
    return BrowserDetector(config)


def test_single_letter_x_is_never_inferred_from_arbitrary_page_title(tmp_path: Path):
    detector = _detector(tmp_path)
    assert detector._detect_service('فحص شامل QA — Mozilla Firefox') is None
    assert detector._detect_service('Example documentation — Mozilla Firefox') is None


def test_x_requires_explicit_url_or_twitter_marker(tmp_path: Path):
    detector = _detector(tmp_path)
    assert detector._detect_service('https://x.com/home') == 'X'
    assert detector._detect_service('Twitter / Home') == 'X'


def test_service_url_markers_only_match_hostname_and_expected_path(tmp_path: Path):
    detector = _detector(tmp_path)
    assert detector._detect_service_from_url('https://www.youtube.com/watch?v=abc') == 'YouTube'
    assert detector._detect_service_from_url('https://music.youtube.com/watch?v=abc') == 'YouTube Music'
    assert detector._detect_service_from_url('https://www.amazon.com/gp/video/storefront') == 'Prime Video'
    assert detector._detect_service_from_url('https://example.com/?next=https://x.com/home') is None
    assert detector._detect_service_from_url('https://example.com/youtube.com/watch') is None
    assert detector._detect_service_from_url('https://amazon.com/not-video?next=/gp/video') is None


def test_exact_companion_url_ignores_service_names_inside_query(tmp_path: Path):
    detector = _detector(tmp_path)
    detector.companion = _FakeCompanion({
        'title': 'Redirect helper — Mozilla Firefox',
        'url': 'https://example.com/redirect?next=https://x.com/home',
        'service': 'X',
        'private': False,
        'media': {},
    })

    activity = detector._from_companion('Firefox')
    assert activity is not None
    assert activity['service'] == ''
    assert activity['url'] == 'https://example.com/redirect?next=https://x.com/home'


def test_exact_companion_url_overrides_stale_service_label(tmp_path: Path):
    detector = _detector(tmp_path)
    detector.companion = _FakeCompanion({
        'title': 'فحص شامل QA — Mozilla Firefox',
        'url': 'https://chatgpt.com/c/example',
        'service': 'X',
        'private': False,
        'media': {},
    })

    activity = detector._from_companion('Firefox')
    assert activity is not None
    assert activity['service'] == 'ChatGPT'
    assert activity['url'] == 'https://chatgpt.com/c/example'


def test_exact_unknown_domain_does_not_reuse_stale_known_service(tmp_path: Path):
    detector = _detector(tmp_path)
    detector.companion = _FakeCompanion({
        'title': 'Internal Dashboard — Mozilla Firefox',
        'url': 'https://dashboard.example.test/home',
        'service': 'YouTube',
        'private': False,
        'media': {},
    })

    activity = detector._from_companion('Firefox')
    assert activity is not None
    assert activity['service'] == ''
    assert activity['url'] == 'https://dashboard.example.test/home'
