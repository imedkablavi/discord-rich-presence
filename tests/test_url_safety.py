import pytest

from url_safety import is_public_hostname, public_https_url


@pytest.mark.parametrize('hostname', [
    'example.com',
    'sub.example.com',
    'xn--bcher-kva.example',
    '8.8.8.8',
])
def test_public_hostname_accepts_public_names_and_ips(hostname: str):
    assert is_public_hostname(hostname) is True


@pytest.mark.parametrize('hostname', [
    'localhost',
    'api.localhost',
    'printer.local',
    'service.internal',
    'intranet',
    '127.0.0.1',
    '10.0.0.1',
    '172.16.1.1',
    '192.168.1.1',
    '169.254.1.1',
    '::1',
    'fe80::1',
    'exa mple.com',
    '-bad.example.com',
    'bad-.example.com',
])
def test_public_hostname_rejects_local_private_and_malformed_names(hostname: str):
    assert is_public_hostname(hostname) is False


@pytest.mark.parametrize('url', [
    'https://example.com',
    'https://example.com/path?q=1#section',
    'https://example.com:443/path',
])
def test_public_https_url_accepts_normal_public_https(url: str):
    assert public_https_url(url, 512) == url


@pytest.mark.parametrize('url', [
    'http://example.com',
    'https://user:secret@example.com',
    'https://localhost/private',
    'https://192.168.1.1/admin',
    'https://example.com:8443/admin',
    'https://exa mple.com/path',
    'https://example.com/path\nInjected: yes',
    'file:///tmp/private',
])
def test_public_https_url_rejects_non_public_destinations(url: str):
    assert public_https_url(url, 512) is None


def test_public_https_url_honors_field_length_limit():
    value = 'https://example.com/' + ('x' * 100)
    assert public_https_url(value, 32) is None
