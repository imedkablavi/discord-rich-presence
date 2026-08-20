from pathlib import Path

from config import Config
from privacy import PrivacyRedactor


def test_off_mode_preserves_activity(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('privacy.mode', 'off')
    redactor = PrivacyRedactor(cfg)
    original = {'type': 'browser', 'page_title': 'token=abc', 'url': 'https://example.com'}
    assert redactor.redact_activity(original) == original


def test_balanced_redacts_sensitive_command(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    redactor = PrivacyRedactor(cfg)
    activity = redactor.redact_activity({
        'type': 'terminal',
        'command': 'curl --token=supersecretvalue /home/test/file.txt',
        'directory': '/home/test/project',
    })
    assert '[REDACTED]' in activity['command']
    assert '/home/test/file.txt' not in activity['command']


def test_strict_browser_drops_url_and_title(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('privacy.mode', 'strict')
    redactor = PrivacyRedactor(cfg)
    activity = redactor.redact_activity({
        'type': 'browser', 'browser_name': 'Chrome', 'page_title': 'Secret page',
        'service': 'GitHub', 'url': 'https://github.com/private', 'is_private': False,
    })
    assert activity['page_title'] == 'Browsing'
    assert activity['url'] is None
    assert activity['service'] == ''


def test_reload_refreshes_cached_privacy_options(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    redactor = PrivacyRedactor(cfg)
    cfg.set('privacy.hide_home_paths', False)
    redactor.reload()
    assert redactor.hide_home_paths is False
