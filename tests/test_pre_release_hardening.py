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


def test_reverse_domain_kde_app_id_is_displayed_cleanly(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'application',
        'app_name': 'org.kde.dolphin',
        'window_title': 'Downloads — Dolphin',
    })
    assert payload['details'] == 'Dolphin active'
    assert payload['large_text'] == 'Dolphin'
    assert payload['large_image'] == 'https://www.google.com/s2/favicons?domain=kde.org&sz=256'


def test_browser_large_artwork_represents_browser_and_service_is_secondary(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'browser',
        'browser_name': 'Brave',
        'is_private': False,
        'page_title': 'Example video',
        'service': 'YouTube',
        'url': 'https://www.youtube.com/results?search_query=Example%20video',
    })
    assert payload['large_image'] == 'https://www.google.com/s2/favicons?domain=brave.com&sz=256'
    assert payload['large_text'] == 'Brave'
    assert payload['small_image'] == 'https://www.google.com/s2/favicons?domain=youtube.com&sz=256'
    assert payload['small_text'] == 'YouTube'


def test_browser_media_uses_actual_browser_icon(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'media',
        'player': 'brave',
        'title': 'Artist - Track',
        'is_playing': True,
        'position': 10,
        'duration': 321,
    })
    assert payload['large_image'] == 'https://www.google.com/s2/favicons?domain=brave.com&sz=256'
    assert payload['large_text'] == 'Brave'
    assert payload['state'] == 'Brave'


def test_coding_large_artwork_represents_editor(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'coding',
        'editor': 'VS Code',
        'filename': 'main.py',
        'language': 'python',
        'project': 'demo',
    })
    assert payload['large_image'] == 'https://www.google.com/s2/favicons?domain=code.visualstudio.com&sz=256'
    assert payload['large_text'] == 'VS Code'
    assert payload['small_image'] == 'py'


def test_terminal_large_artwork_represents_terminal_app(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'terminal',
        'terminal_name': 'Konsole',
        'shell': 'bash',
        'command': '',
        'directory': '',
    })
    assert payload['large_image'] == 'https://www.google.com/s2/favicons?domain=kde.org&sz=256'
    assert payload['large_text'] == 'Konsole'


def test_icon_override_wins_over_builtin_external_icon(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('images.icon_overrides', {'brave': 'my-brave-asset'})
    payload = PresenceBuilder(cfg).build({
        'type': 'application',
        'app_name': 'brave',
        'window_title': 'Brave',
    })
    assert payload['large_image'] == 'my-brave-asset'


def test_external_icons_can_be_disabled_for_developer_portal_assets(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('images.use_external_app_icons', False)
    payload = PresenceBuilder(cfg).build({
        'type': 'application',
        'app_name': 'brave',
        'window_title': 'Brave',
    })
    assert payload['large_image'] == 'brave'
