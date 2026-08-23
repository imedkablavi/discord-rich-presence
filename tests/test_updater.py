import hashlib
import json
from pathlib import Path

import pytest

import updater
from updater import ReleaseAsset, UpdateError, UpdateInfo


def _release(version: str = '1.2.3') -> bytes:
    binary_name, checksum_name = 'binary.bin', 'binary.bin.sha256'
    return json.dumps({
        'tag_name': f'v{version}',
        'html_url': f'https://github.com/imedkablavi/discord-rich-presence/releases/tag/v{version}',
        'draft': False,
        'prerelease': False,
        'assets': [
            {
                'name': binary_name,
                'browser_download_url': f'https://github.com/imedkablavi/discord-rich-presence/releases/download/v{version}/{binary_name}',
                'size': 12,
                'digest': 'sha256:' + ('a' * 64),
            },
            {
                'name': checksum_name,
                'browser_download_url': f'https://github.com/imedkablavi/discord-rich-presence/releases/download/v{version}/{checksum_name}',
                'size': 90,
            },
        ],
    }).encode('utf-8')


def test_version_parser_orders_stable_versions():
    assert updater._version_tuple('v1.2.3') == (1, 2, 3)
    assert updater._version_tuple('2.0.0') > updater._version_tuple('1.99.99')
    with pytest.raises(UpdateError):
        updater._version_tuple('latest')


def test_update_urls_are_https_and_github_only():
    updater._validate_github_url('https://api.github.com/repos/a/b/releases/latest')
    updater._validate_github_url('https://release-assets.githubusercontent.com/example')
    with pytest.raises(UpdateError):
        updater._validate_github_url('http://github.com/example')
    with pytest.raises(UpdateError):
        updater._validate_github_url('https://example.com/update.exe')


def test_check_for_update_requires_expected_platform_assets(monkeypatch):
    monkeypatch.setattr(updater, '_read_limited', lambda *_: _release('1.2.3'))
    monkeypatch.setattr(updater, '_platform_asset_names', lambda: ('binary.bin', 'binary.bin.sha256'))
    info = updater.check_for_update('1.0.0')
    assert info is not None
    assert info.latest_version == '1.2.3'
    assert info.binary.name == 'binary.bin'
    assert info.checksum.name == 'binary.bin.sha256'


def test_check_for_update_never_downgrades(monkeypatch):
    monkeypatch.setattr(updater, '_read_limited', lambda *_: _release('1.2.3'))
    monkeypatch.setattr(updater, '_platform_asset_names', lambda: ('binary.bin', 'binary.bin.sha256'))
    assert updater.check_for_update('1.2.3') is None
    assert updater.check_for_update('2.0.0') is None


def test_release_rejects_missing_checksum(monkeypatch):
    raw = json.loads(_release('1.2.3').decode('utf-8'))
    raw['assets'] = raw['assets'][:1]
    monkeypatch.setattr(updater, '_read_limited', lambda *_: json.dumps(raw).encode())
    monkeypatch.setattr(updater, '_platform_asset_names', lambda: ('binary.bin', 'binary.bin.sha256'))
    with pytest.raises(UpdateError, match='missing required asset'):
        updater.check_for_update('1.0.0')


def test_checksum_sidecar_must_name_the_binary(monkeypatch):
    info = UpdateInfo(
        current_version='1.0.0',
        latest_version='1.2.3',
        tag_name='v1.2.3',
        release_url='https://github.com/imedkablavi/discord-rich-presence/releases/tag/v1.2.3',
        binary=ReleaseAsset('binary.bin', 'https://github.com/a', 4),
        checksum=ReleaseAsset('binary.bin.sha256', 'https://github.com/b', 80),
    )
    digest = hashlib.sha256(b'data').hexdigest()
    monkeypatch.setattr(
        updater,
        '_read_limited',
        lambda *_: f'{digest}  other.bin\n'.encode('ascii'),
    )
    with pytest.raises(UpdateError, match='checksum file is invalid'):
        updater._expected_checksum(info)


def test_linux_atomic_replace_keeps_new_payload(tmp_path: Path):
    target = tmp_path / 'CYBREX'
    staged = tmp_path / '.CYBREX.2.0.0.new'
    target.write_bytes(b'old')
    staged.write_bytes(b'new')
    updater._install_linux(target, staged)
    assert target.read_bytes() == b'new'
    assert not staged.exists()
    assert not (tmp_path / 'CYBREX.old').exists()


def test_linux_relaunch_uses_verified_replacement(monkeypatch, tmp_path: Path):
    target = tmp_path / 'CYBREX'
    target.write_bytes(b'new')
    launched = []

    def fake_popen(command, **kwargs):
        launched.append((command, kwargs))
        return object()

    monkeypatch.setattr(updater.subprocess, 'Popen', fake_popen)
    updater._relaunch_linux(target, ['--gui'])

    assert launched[0][0] == [str(target), '--gui']
    assert launched[0][1]['close_fds'] is True
    assert launched[0][1]['start_new_session'] is True


def test_linux_relaunch_is_noop_without_restart_args(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        updater.subprocess,
        'Popen',
        lambda *_args, **_kwargs: pytest.fail('Popen should not be called'),
    )
    updater._relaunch_linux(tmp_path / 'CYBREX', [])
