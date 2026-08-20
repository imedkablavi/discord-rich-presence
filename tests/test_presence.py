from pathlib import Path

from pypresence.types import ActivityType

from config import Config
from presence import PresenceBuilder


def _builder(tmp_path: Path) -> PresenceBuilder:
    return PresenceBuilder(Config(tmp_path / 'config.yaml'))


def test_activity_start_timestamp_is_milliseconds(tmp_path: Path):
    payload = _builder(tmp_path).build({
        'type': 'coding',
        'editor': 'VS Code',
        'filename': 'main.py',
        'language': 'python',
        'project': 'demo',
    })
    assert payload['start'] > 1_000_000_000_000


def test_spotify_uses_listening_activity_type(tmp_path: Path):
    payload = _builder(tmp_path).build({
        'type': 'media',
        'player': 'Spotify',
        'title': 'Track',
        'is_playing': True,
        'position': 10,
        'duration': 100,
    })
    assert payload['activity_type'] == ActivityType.LISTENING
    assert payload['end'] > payload['start']


def test_media_timeline_stays_stable_during_normal_playback(tmp_path: Path, monkeypatch):
    builder = _builder(tmp_path)
    clock = {'now': 1_800_000_000}
    monkeypatch.setattr('presence.time.time', lambda: clock['now'])

    first = builder.build({
        'type': 'media', 'player': 'Spotify', 'title': 'Track',
        'is_playing': True, 'position': 10, 'duration': 100,
    })
    clock['now'] += 5
    second = builder.build({
        'type': 'media', 'player': 'Spotify', 'title': 'Track',
        'is_playing': True, 'position': 15, 'duration': 100,
    })

    assert second['start'] == first['start']
    assert second['end'] == first['end']


def test_media_timeline_resets_after_seek(tmp_path: Path, monkeypatch):
    builder = _builder(tmp_path)
    clock = {'now': 1_800_000_000}
    monkeypatch.setattr('presence.time.time', lambda: clock['now'])

    first = builder.build({
        'type': 'media', 'player': 'Spotify', 'title': 'Track',
        'is_playing': True, 'position': 10, 'duration': 100,
    })
    clock['now'] += 5
    sought = builder.build({
        'type': 'media', 'player': 'Spotify', 'title': 'Track',
        'is_playing': True, 'position': 50, 'duration': 100,
    })

    assert sought['start'] != first['start']
    assert sought['end'] != first['end']


def test_browser_url_reaches_clickable_payload_and_button(tmp_path: Path):
    payload = _builder(tmp_path).build({
        'type': 'browser',
        'browser_name': 'Chrome',
        'is_private': False,
        'page_title': 'Video',
        'service': 'YouTube',
        'url': 'https://www.youtube.com/results?search_query=Video',
    })
    assert payload['details_url'].startswith('https://www.youtube.com/')
    assert payload['large_url'] == payload['details_url']
    assert payload['buttons'][0]['url'] == payload['details_url']


def test_strict_browser_does_not_emit_urls_or_buttons(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('privacy.mode', 'strict')
    payload = PresenceBuilder(cfg).build({
        'type': 'browser',
        'browser_name': 'Chrome',
        'is_private': False,
        'page_title': 'Secret',
        'service': 'GitHub',
        'url': 'https://github.com/private',
    })
    assert 'details_url' not in payload
    assert 'large_url' not in payload
    assert 'buttons' not in payload
