from pathlib import Path

from config import Config
from presence import PresenceBuilder


def _builder(tmp_path: Path) -> PresenceBuilder:
    return PresenceBuilder(Config(tmp_path / 'config.yaml'))


def test_generic_game_does_not_invent_map_or_server(tmp_path: Path):
    payload = _builder(tmp_path).build({
        'type': 'gaming',
        'game_name': 'ELDEN RING',
        'launcher': 'Steam',
        'game_source': 'Steam',
        'steam_appid': 1245620,
    })
    assert payload['details'] == 'ELDEN RING'
    assert payload['state'] == 'Steam'
    serialized = repr(payload).lower()
    assert 'server' not in serialized
    assert 'map' not in serialized


def test_cs2_gsi_formats_verified_match_context(tmp_path: Path):
    payload = _builder(tmp_path).build({
        'type': 'gaming',
        'game_name': 'Counter-Strike 2',
        'launcher': 'Steam',
        'game_source': 'Steam',
        'steam_appid': 730,
        'gsi': True,
        'mode': 'Competitive',
        'mode_key': 'competitive',
        'map': 'Mirage',
        'team_name': 'Counter-Terrorists',
        'ct_score': 7,
        't_score': 5,
    })
    assert payload['details'] == 'Counter-Strike 2 · Competitive'
    assert payload['state'] == 'Mirage · Counter-Terrorists · 7–5'


def test_league_live_context_stays_in_state_without_fake_server(tmp_path: Path):
    payload = _builder(tmp_path).build({
        'type': 'gaming',
        'game_name': 'League of Legends',
        'launcher': 'Riot Client',
        'game_source': 'Ahri · MIDDLE · CLASSIC',
        'league_live': True,
    })
    assert payload['details'] == 'League of Legends'
    assert payload['state'] == 'Ahri · MIDDLE · CLASSIC'
    assert 'server' not in repr(payload).lower()


def test_fivem_companion_context_is_not_reinterpreted(tmp_path: Path):
    payload = _builder(tmp_path).build({
        'type': 'gaming',
        'game_name': 'FiveM',
        'launcher': 'FiveM',
        'game_source': 'Example RP · 64/128 players',
        'fivem_companion': True,
    })
    assert payload['details'] == 'FiveM'
    assert payload['state'] == 'Example RP · 64/128 players'


def test_minecraft_companion_context_is_not_reinterpreted(tmp_path: Path):
    payload = _builder(tmp_path).build({
        'type': 'gaming',
        'game_name': 'Minecraft',
        'launcher': 'Minecraft Launcher',
        'game_source': 'Multiplayer · Nether · Community World',
        'minecraft_companion': True,
    })
    assert payload['details'] == 'Minecraft'
    assert payload['state'] == 'Multiplayer · Nether · Community World'


def test_squad_without_current_local_evidence_falls_back_to_game_identity(tmp_path: Path, monkeypatch):
    builder = _builder(tmp_path)
    monkeypatch.setattr(builder.squad_telemetry, 'snapshot', lambda: {})
    payload = builder.build({
        'type': 'gaming',
        'game_name': 'Squad',
        'launcher': 'Steam',
        'game_source': 'Steam',
        'steam_appid': 393380,
    })
    assert payload['details'] == 'Squad'
    assert payload['state'] == 'Steam'
