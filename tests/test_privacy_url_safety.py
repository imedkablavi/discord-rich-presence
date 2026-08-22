from pathlib import Path

from config import Config
from privacy import PrivacyRedactor


def _redactor(tmp_path: Path, policy: str = 'full') -> PrivacyRedactor:
    config = Config(tmp_path / 'config.yaml')
    config.set('privacy.browser_url_mode', policy)
    return PrivacyRedactor(config)


def test_full_browser_url_rejects_malformed_port(tmp_path: Path):
    redactor = _redactor(tmp_path)
    assert redactor._sanitize_exact_browser_url('https://example.com:bad/path') is None


def test_full_browser_url_strips_userinfo(tmp_path: Path):
    redactor = _redactor(tmp_path)
    result = redactor._sanitize_exact_browser_url(
        'https://user:secret@example.com/account?view=1'
    )
    assert result == 'https://example.com/account?view=1'
    assert 'user' not in result
    assert 'secret' not in result


def test_full_browser_url_redacts_sensitive_query_and_fragment(tmp_path: Path):
    redactor = _redactor(tmp_path)
    result = redactor._sanitize_exact_browser_url(
        'https://example.com/account?access_token=secret-value&view=1#oauth-secret'
    )
    assert result is not None
    assert 'secret-value' not in result
    assert 'oauth-secret' not in result
    assert 'access_token=%5BREDACTED%5D' in result
    assert 'view=1' in result


def test_full_browser_url_redacts_long_token_in_path(tmp_path: Path):
    redactor = _redactor(tmp_path)
    token = 'A' * 48
    result = redactor._sanitize_exact_browser_url(
        f'https://example.com/reset/{token}/confirm'
    )
    assert result is not None
    assert token not in result
    assert '[TOKEN]' in result


def test_percent_encoded_path_token_is_redacted_after_decoding(tmp_path: Path):
    redactor = _redactor(tmp_path)
    token = 'B' * 48
    encoded = ''.join(f'%{ord(char):02X}' for char in token)
    result = redactor._sanitize_exact_browser_url(
        f'https://example.com/reset/{encoded}'
    )
    assert result is not None
    assert token not in result
    assert '[TOKEN]' in result


def test_domain_policy_never_includes_path_query_or_fragment(tmp_path: Path):
    redactor = _redactor(tmp_path, 'domain')
    result = redactor._sanitize_exact_browser_url(
        'https://example.com/private/path?token=secret#fragment'
    )
    assert result == 'https://example.com'
