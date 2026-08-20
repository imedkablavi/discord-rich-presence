from pathlib import Path

from config import Config
from detectors.browser import BrowserDetector


def _detector(tmp_path: Path) -> BrowserDetector:
    return BrowserDetector(Config(tmp_path / 'config.yaml'))


def test_youtube_service_survives_title_cleanup(tmp_path: Path):
    activity = _detector(tmp_path).detect({
        'app_name': 'Chrome',
        'title': 'Example Video - YouTube - Chrome',
    })
    assert activity is not None
    assert activity['service'] == 'YouTube'
    assert activity['page_title'] == 'Example Video'
    assert 'youtube.com/results' in activity['url']


def test_private_window_never_generates_url(tmp_path: Path):
    activity = _detector(tmp_path).detect({
        'app_name': 'Firefox',
        'title': 'Private Browsing - Firefox',
    })
    assert activity is not None
    assert activity['is_private'] is True
    assert activity['url'] is None


def test_browser_detector_respects_disable_flag(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('rules.enabled_detectors.browser', False)
    detector = BrowserDetector(cfg)
    assert detector.detect({'app_name': 'Chrome', 'title': 'Example - Chrome'}) is None
