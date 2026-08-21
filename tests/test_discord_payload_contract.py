from pathlib import Path

from config import Config
from presence import PresenceBuilder
from rpc_contract import sanitize_rpc_payload


def test_x_service_uses_valid_asset_tooltip(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'browser',
        'browser_name': 'Brave',
        'is_private': False,
        'page_title': 'Timeline',
        'service': 'X',
        'url': 'https://x.com/home',
    })

    assert 'name' not in payload
    assert payload['state'] == 'X · Brave'
    assert payload['large_text'] == 'X.com'
    assert payload['large_image'] == 'https://www.google.com/s2/favicons?domain=x.com&sz=256'


def test_one_character_custom_service_cannot_break_rpc_tooltip(tmp_path: Path):
    payload = PresenceBuilder(Config(tmp_path / 'config.yaml')).build({
        'type': 'browser',
        'browser_name': 'Firefox',
        'is_private': False,
        'page_title': 'Internal tool',
        'service': 'Q',
        'url': 'https://q.example.test/',
    })

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

    assert payload['small_image'] == 'c'
    assert payload['small_text'] == 'C language'


def test_legacy_rpc_drops_dynamic_name_instead_of_promising_app_name_override():
    payload = sanitize_rpc_payload({
        'name': 'Counter-Strike 2',
        'details': 'Counter-Strike 2',
        'state': 'Mirage',
    })

    assert 'name' not in payload
    assert payload['details'] == 'Counter-Strike 2'
    assert payload['state'] == 'Mirage'


def test_clickable_activity_urls_over_discord_limit_are_dropped():
    long_url = 'https://example.test/' + ('a' * 240)
    assert len(long_url) > 256

    payload = sanitize_rpc_payload({
        'details': 'A valid details field',
        'state': 'A valid state field',
        'details_url': long_url,
        'state_url': long_url,
        'large_url': long_url,
        'small_url': long_url,
        'large_image': 'app',
    })

    assert 'details_url' not in payload
    assert 'state_url' not in payload
    assert 'large_url' not in payload
    assert 'small_url' not in payload
    assert payload['details'] == 'A valid details field'
    assert payload['state'] == 'A valid state field'


def test_button_url_keeps_separate_512_character_allowance():
    url = 'https://example.test/' + ('a' * 300)
    assert 256 < len(url) <= 512

    payload = sanitize_rpc_payload({
        'details': 'Example',
        'buttons': [{'label': 'Open', 'url': url}],
    })

    assert payload['buttons'] == [{'label': 'Open', 'url': url}]


def test_steam_game_card_prefers_game_artwork_and_store_button(tmp_path: Path):
    config = Config(tmp_path / 'config.yaml')
    payload = PresenceBuilder(config).build({
        'type': 'gaming',
        'game_name': 'Example Steam Game',
        'launcher': 'Steam',
        'game_source': 'Steam',
        'steam_appid': 12345,
        'artwork_url': 'https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/12345/header.jpg',
        'store_url': 'https://store.steampowered.com/app/12345/',
        'is_game': True,
    })

    assert payload['details'] == 'Example Steam Game'
    assert payload['state'] == 'Steam'
    assert payload['large_image'].endswith('/steam/apps/12345/header.jpg')
    assert payload['small_text'] == 'Steam'
    assert payload['buttons'] == [
        {'label': 'View on Steam', 'url': 'https://store.steampowered.com/app/12345/'}
    ]


def test_one_character_optional_text_is_dropped_instead_of_rejected(tmp_path: Path):
    builder = PresenceBuilder(Config(tmp_path / 'config.yaml'))
    payload = builder._sanitize_discord_fields({
        'details': 'A',
        'state': 'B',
        'large_text': 'Q',
        'small_text': 'Z',
        'large_image': 'app',
    })

    assert 'details' not in payload
    assert 'state' not in payload
    assert 'large_text' not in payload
    assert 'small_text' not in payload
    assert payload['large_image'] == 'app'
