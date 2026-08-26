import json
from pathlib import Path

import pytest

from game_packs import GamePackRegistry, load_pack


def _write(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / 'pack.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path


def test_pack_uses_exact_process_matching(tmp_path):
    path = _write(tmp_path, {
        'schema': 1,
        'games': [{
            'name': 'Example Game',
            'launcher': 'Steam',
            'steam_appid': 123,
            'processes': ['ExampleGame.exe'],
        }],
    })
    registry = GamePackRegistry([path])
    assert registry.match('ExampleGame.exe').name == 'Example Game'
    assert registry.match('examplegame').name == 'Example Game'
    assert registry.match('ExampleGameHelper.exe') is None


def test_pack_builds_safe_steam_activity(tmp_path):
    path = _write(tmp_path, {
        'schema': 1,
        'games': [{
            'name': 'Example Game',
            'launcher': 'Steam',
            'steam_appid': 123,
            'processes': ['game'],
        }],
    })
    activity = GamePackRegistry([path]).activity('game.exe')
    assert activity['game_name'] == 'Example Game'
    assert activity['steam_appid'] == 123
    assert activity['store_url'] == 'https://store.steampowered.com/app/123/'
    assert activity['artwork_url'].endswith('/steam/apps/123/header.jpg')


def test_bundled_pack_detects_squad_game_process_exactly():
    registry = GamePackRegistry()
    activity = registry.activity('SquadGame.exe')
    assert activity is not None
    assert activity['game_name'] == 'Squad'
    assert activity['launcher'] == 'Steam'
    assert activity['steam_appid'] == 393380
    assert registry.activity('SquadGameServer.exe') is None


def test_invalid_schema_fails_closed(tmp_path):
    path = _write(tmp_path, {'schema': 99, 'games': []})
    with pytest.raises(ValueError, match='schema'):
        load_pack(path)


def test_ambiguous_process_collision_keeps_first_definition(tmp_path):
    path = _write(tmp_path, {
        'schema': 1,
        'games': [
            {'name': 'First', 'launcher': 'Gaming', 'processes': ['same', 'first']},
            {'name': 'Second', 'launcher': 'Gaming', 'processes': ['same', 'second']},
        ],
    })
    registry = GamePackRegistry([path])
    assert registry.match('same').name == 'First'
    assert registry.match('first').name == 'First'
    assert registry.match('second').name == 'Second'


def test_invalid_process_aliases_are_ignored(tmp_path):
    path = _write(tmp_path, {
        'schema': 1,
        'games': [{
            'name': 'Example',
            'launcher': 'Gaming',
            'processes': ['../../evil', 'https://example.com', 'valid-game'],
        }],
    })
    registry = GamePackRegistry([path])
    assert registry.match('valid-game').name == 'Example'
    assert registry.match('../../evil') is None


def test_pack_size_is_bounded(tmp_path):
    path = tmp_path / 'pack.json'
    path.write_bytes(b' ' * (256 * 1024 + 1))
    with pytest.raises(ValueError, match='too large'):
        load_pack(path)
