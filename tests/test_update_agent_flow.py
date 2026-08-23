from pathlib import Path

import update_agent
from updater import ReleaseAsset


class FakeConfig:
    config_path = None

    def get(self, key, default=None):
        values = {
            'updates.enabled': True,
            'updates.auto_install': False,
        }
        return values.get(key, default)


def available_status():
    asset = ReleaseAsset(
        name='DiscordRichPresence-test.bin',
        url='https://example.invalid/app.bin',
        sha256='a' * 64,
        size=12,
        platform='linux',
        arch='x86_64',
        kind='binary',
    )
    return update_agent.UpdateStatus('1.0.0', '1.1.0', True, asset, 'Version 1.1.0 is available')


def test_manual_stage_reports_progress_and_schedules_restart(monkeypatch, tmp_path):
    executable = tmp_path / 'DiscordRichPresence'
    executable.write_bytes(b'old')
    monkeypatch.setattr(update_agent.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(update_agent.sys, 'executable', str(executable))
    monkeypatch.setattr(update_agent, 'check_for_update', lambda _config: available_status())
    monkeypatch.setattr(update_agent, '_update_dir', lambda _config: tmp_path / 'updates')

    progress_values = []
    scheduled = {}

    def fake_download(asset, destination, progress=None):
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_bytes(b'new')
        if progress:
            progress(0, asset.size)
            progress(asset.size, asset.size)
        return Path(destination)

    def fake_schedule(current, staged, wait_pids, restart_args=None):
        scheduled['current'] = Path(current)
        scheduled['staged'] = Path(staged)
        scheduled['pids'] = list(wait_pids)
        scheduled['args'] = list(restart_args or [])
        return tmp_path / 'helper'

    monkeypatch.setattr(update_agent, 'download_verified_asset', fake_download)
    monkeypatch.setattr(update_agent, 'schedule_self_replace', fake_schedule)

    result = update_agent.stage_update(
        FakeConfig(),
        wait_pids=[123, 456],
        restart_args=['--gui'],
        progress=lambda done, total: progress_values.append((done, total)),
    )

    assert result.staged is True
    assert result.latest_version == '1.1.0'
    assert progress_values == [(0, 12), (12, 12)]
    assert scheduled['current'] == executable.resolve()
    assert scheduled['pids'] == [123, 456]
    assert scheduled['args'] == ['--gui']
    assert scheduled['staged'].read_bytes() == b'new'


def test_source_checkout_never_self_replaces(monkeypatch):
    monkeypatch.setattr(update_agent.sys, 'frozen', False, raising=False)
    monkeypatch.setattr(update_agent, 'check_for_update', lambda _config: available_status())

    result = update_agent.stage_update(FakeConfig())

    assert result.available is True
    assert result.staged is False
    assert 'source checkouts' in result.message


def test_auto_stage_requires_explicit_auto_install(monkeypatch):
    monkeypatch.setattr(update_agent, 'check_for_update', lambda _config: available_status())

    result = update_agent.auto_stage_update(FakeConfig())

    assert result.available is True
    assert result.staged is False
    assert 'Automatic installation is off' in result.message
