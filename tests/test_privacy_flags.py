from pathlib import Path

from config import Config
from privacy import PrivacyRedactor


def _redactor(tmp_path: Path) -> PrivacyRedactor:
    return PrivacyRedactor(Config(tmp_path / 'config.yaml'))


def test_balanced_redacts_value_after_token_flag(tmp_path: Path):
    redactor = _redactor(tmp_path)
    activity = redactor.redact_activity({
        'type': 'terminal',
        'command': 'tool --token abc123 --mode fast',
        'directory': '',
    })
    assert 'abc123' not in activity['command']
    assert '[REDACTED]' in activity['command']
    assert '--mode fast' in activity['command']


def test_balanced_redacts_password_assignment(tmp_path: Path):
    redactor = _redactor(tmp_path)
    activity = redactor.redact_activity({
        'type': 'terminal',
        'command': 'tool --password=hunter2 run',
        'directory': '',
    })
    assert 'hunter2' not in activity['command']
    assert '[REDACTED]' in activity['command']
    assert activity['command'].endswith(' run')


def test_balanced_redacts_authorization_value(tmp_path: Path):
    redactor = _redactor(tmp_path)
    activity = redactor.redact_activity({
        'type': 'terminal',
        'command': 'curl -H Authorization secretvalue https://example.com',
        'directory': '',
    })
    assert 'secretvalue' not in activity['command']
    assert 'https://example.com' in activity['command']


def test_balanced_drops_inferred_browser_url_when_title_is_redacted(tmp_path: Path):
    redactor = _redactor(tmp_path)
    activity = redactor.redact_activity({
        'type': 'browser',
        'browser_name': 'Firefox',
        'is_private': False,
        'page_title': 'token=abc123',
        'service': 'YouTube',
        'url': 'https://www.youtube.com/results?search_query=token%3Dabc123',
    })
    assert 'abc123' not in activity['page_title']
    assert activity['url'] is None
