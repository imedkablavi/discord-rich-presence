from pathlib import Path

from pypresence.types import ActivityType

from config import Config
from presence import PresenceBuilder
from rpc_contract import sanitize_rpc_payload


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


def test_long_browser_url_cannot_break_final_discord_payload(tmp_path: Path):
    long_url = 'https://example.com/chat?' + ('conversation-part-' * 30)
    assert len(long_url) > 256

    built = _builder(tmp_path).build({
        'type': 'browser',
        'browser_name': 'Firefox',
        'is_private': False,
        'page_title': 'QA conversation',
        'service': '',
        'url': long_url,
    })
    payload = sanitize_rpc_payload(built)

    assert payload['details'] == 'QA conversation'
    assert payload['state'] == 'Firefox'
    assert 'details_url' not in payload
    assert 'large_url' not in payload
    # Button URLs have their own larger contract. If the original URL fits that
    # contract, it must remain complete rather than being silently truncated.
    if len(long_url) <= 512:
        assert payload['buttons'][0]['url'] == long_url


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
