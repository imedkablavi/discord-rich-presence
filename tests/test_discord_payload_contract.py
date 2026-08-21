from pathlib import Path

from config import Config
from presence import PresenceBuilder


def test_x_service_uses_valid_asset_tooltip_and_activity_name(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'browser',
        'browser_name': 'Brave',
        'is_private': False,
        'page_title': 'Timeline',
        'service': 'X',
        'url': 'https://x.com/home',
    })

    assert payload['name'] == 'X.com'
    assert payload['state'] == 'X · Brave'
    assert payload['large_text'] == 'X.com'
    assert payload['large_image'] == 'https://www.google.com/s2/favicons?domain=x.com&sz=256'


def test_one_character_custom_service_falls_back_to_browser_activity_name(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'browser',
        'browser_name': 'Firefox',
        'is_private': False,
        'page_title': 'Internal tool',
        'service': 'Q',
        'url': 'https://q.example.test/',
    })

    assert payload['name'] == 'Firefox'
    assert payload['state'] == 'Q · Firefox'
    assert 'large_text' not in payload


def test_c_language_uses_valid_small_asset_tooltip(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'coding',
        'editor': 'VS Code',
        'filename': 'main.c',
        'language': 'c',
        'project': 'demo',
    })

    assert payload['name'] == 'VS Code'
    assert payload['small_image'] == 'c'
    assert payload['small_text'] == 'C language'


def test_game_name_replaces_builtin_application_name(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'gaming',
        'game_name': 'Counter-Strike 2',
        'launcher': 'Competitive · Mirage · Counter-Terrorists · CT 8–6 T',
        'is_game': True,
    })

    assert payload['name'] == 'Counter-Strike 2'
    assert payload['details'] == 'Playing · Counter-Strike 2'
    assert payload['state'] == 'Competitive · Mirage · Counter-Terrorists · CT 8–6 T'


def test_one_character_optional_text_is_dropped_instead_of_rejected(tmp_path: Path):
    builder = PresenceBuilder(Config(tmp_path / 'config.yaml'))
    payload = builder._sanitize_discord_fields({
        'name': 'A',
        'details': 'A',
        'state': 'B',
        'large_text': 'Q',
        'small_text': 'Z',
        'large_image': 'app',
    })

    assert 'name' not in payload
    assert 'details' not in payload
    assert 'state' not in payload
    assert 'large_text' not in payload
    assert 'small_text' not in payload
    assert payload['large_image'] == 'app'
