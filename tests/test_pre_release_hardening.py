import subprocess
from pathlib import Path

from config import Config
from detectors.git_helper import GitHelper
from detectors.media import MediaDetector
from presence import PresenceBuilder


def test_default_detection_interval_is_responsive(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    assert cfg.get('update_interval_secs') == 2


def test_playing_media_payload_stays_stable_as_position_advances(tmp_path: Path, monkeypatch):
    builder = PresenceBuilder(Config(tmp_path / 'config.yaml'))
    clock = {'now': 1_800_000_000}
    monkeypatch.setattr('presence.time.time', lambda: clock['now'])

    first = builder.build({
        'type': 'media', 'player': 'Spotify', 'title': 'Artist - Track',
        'is_playing': True, 'position': 30, 'duration': 240,
    })
    clock['now'] += 2
    second = builder.build({
        'type': 'media', 'player': 'Spotify', 'title': 'Artist - Track',
        'is_playing': True, 'position': 32, 'duration': 240,
    })

    assert first == second
    assert first['state'] == 'Spotify'
    assert first['start'] < first['end']


def test_playerctl_backend_reads_playing_track_in_one_process(tmp_path: Path, monkeypatch):
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('shutil.which', lambda command: '/usr/bin/playerctl' if command == 'playerctl' else None)

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        sep = '\x1f'
        line = sep.join(('spotify', 'Playing', 'Artist', 'Track', '42000000', '240000000'))
        return subprocess.CompletedProcess(args, 0, stdout=line + '\n', stderr='')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    detector = MediaDetector(Config(tmp_path / 'config.yaml'))
    activity = detector.detect({})

    assert activity == {
        'type': 'media',
        'player': 'Spotify',
        'title': 'Artist - Track',
        'is_playing': True,
        'position': 42,
        'duration': 240,
    }
    assert len(calls) == 1
    assert calls[0][0:3] == ['playerctl', '--all-players', 'metadata']


def test_git_helper_parses_branch_status_with_two_queries(tmp_path: Path, monkeypatch):
    helper = GitHelper()
    calls = []

    def fake_run(path, *args):
        calls.append(args)
        if args == ('rev-parse', '--show-toplevel'):
            return str(tmp_path)
        if args == ('status', '--porcelain=v1', '--branch'):
            return '## main...origin/main [ahead 2, behind 1]\n M file.py\n?? new.txt'
        raise AssertionError(args)

    monkeypatch.setattr(helper, '_run', fake_run)
    info = helper.get_repo_info(str(tmp_path))

    assert info is not None
    assert info['branch'] == 'main'
    assert info['ahead'] == 2
    assert info['behind'] == 1
    assert info['uncommitted'] == 2
    assert info['is_dirty'] is True
    assert len(calls) == 2
