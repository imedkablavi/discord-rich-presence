import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from config import Config
from cs2_gsi import CS2GSIBridge, install_gsi_config, render_gsi_config
from detectors.gaming import GamingDetector
from presence import PresenceBuilder


VALID_TEST_TOKEN = 'A' * 43


def _config(tmp_path: Path) -> Config:
    config = Config(tmp_path / 'config.yaml')
    config.set('cs2_gsi.enabled', False)
    return config


def _payload(token: str) -> dict:
    return {
        'provider': {
            'name': 'Counter-Strike 2',
            'appid': 730,
            'steamid': '76561198000000000',
        },
        'map': {
            'mode': 'competitive',
            'name': 'de_mirage',
            'phase': 'live',
            'round': 14,
            'team_ct': {'score': 8, 'name': 'Secret CT Name'},
            'team_t': {'score': 6, 'name': 'Secret T Name'},
        },
        'round': {'phase': 'live'},
        'player': {
            'steamid': '76561198000000001',
            'name': 'Private Player Name',
            'team': 'CT',
            'activity': 'playing',
            'state': {'health': 73, 'money': 4200},
            'weapons': {'weapon_0': {'name': 'weapon_ak47'}},
        },
        'allplayers': {
            '76561198000000002': {'name': 'Other Player', 'position': '1,2,3'},
        },
        'phase_countdowns': {'phase': 'live', 'phase_ends_in': '73.1'},
        'auth': {'token': token},
    }


def test_cs2_gsi_rejects_wrong_token_and_retains_only_presence_fields(tmp_path):
    config = _config(tmp_path)
    bridge = CS2GSIBridge(config)

    bad = _payload('wrong-token')
    with pytest.raises(PermissionError):
        bridge.update(bad)

    bridge.update(_payload(bridge.token))
    snapshot = bridge.latest()
    assert snapshot == {
        'map': 'de_mirage',
        'mode': 'competitive',
        'map_phase': 'live',
        'round': 14,
        'round_phase': 'live',
        'countdown_phase': 'live',
        'team': 'CT',
        'player_activity': 'playing',
        'ct_score': 8,
        't_score': 6,
    }
    serialized = repr(snapshot)
    assert '765611' not in serialized
    assert 'Private Player Name' not in serialized
    assert 'weapon_ak47' not in serialized
    assert 'Secret CT Name' not in serialized


def test_cs2_gsi_requires_counter_strike_appid(tmp_path):
    config = _config(tmp_path)
    bridge = CS2GSIBridge(config)
    payload = _payload(bridge.token)
    payload['provider']['appid'] = 570
    with pytest.raises(ValueError, match='unexpected_appid'):
        bridge.update(payload)


def test_cs2_gsi_config_requests_only_minimum_match_context():
    rendered = render_gsi_config(32192, VALID_TEST_TOKEN)
    assert 'http://127.0.0.1:32192/v1/cs2' in rendered
    assert '"map" "1"' in rendered
    assert '"round" "1"' in rendered
    assert '"player_id" "1"' in rendered
    assert '"phase_countdowns" "1"' in rendered
    assert 'allplayers' not in rendered
    assert 'player_state' not in rendered
    assert 'player_weapons' not in rendered


def test_cs2_gsi_rejects_cfg_token_injection():
    with pytest.raises(ValueError, match='authentication token'):
        render_gsi_config(32192, 'bad-token"\n"allplayers" "1"')


def test_cs2_installer_writes_authenticated_cfg_and_private_token(tmp_path):
    config = _config(tmp_path)
    cfg_dir = tmp_path / 'game' / 'csgo' / 'cfg'
    cfg_dir.mkdir(parents=True)

    target = install_gsi_config(config, cfg_dir)
    text = target.read_text(encoding='utf-8')
    token_path = tmp_path / 'cs2_gsi_token'
    token = token_path.read_text(encoding='utf-8').strip()
    assert target.name == 'gamestate_integration_cybrex.cfg'
    assert token
    assert token in text
    assert 'allplayers' not in text
    if os.name == 'posix':
        assert target.stat().st_mode & 0o777 == 0o600
        assert token_path.stat().st_mode & 0o777 == 0o600


def test_cs2_gaming_detector_formats_mode_map_team_and_score(tmp_path):
    config = _config(tmp_path)
    detector = GamingDetector(config)
    detector.cs2_gsi = SimpleNamespace(latest=lambda: {
        'map': 'de_mirage',
        'mode': 'competitive',
        'map_phase': 'live',
        'round': 14,
        'round_phase': 'live',
        'countdown_phase': 'live',
        'team': 'CT',
        'player_activity': 'playing',
        'ct_score': 8,
        't_score': 6,
    })

    activity = detector.detect({'app_name': 'cs2', 'title': 'Counter-Strike 2'})
    assert activity is not None
    assert activity['game_name'] == 'Counter-Strike 2'
    assert activity['map'] == 'Mirage'
    assert activity['mode'] == 'Competitive'
    assert activity['team_name'] == 'Counter-Terrorists'
    assert activity['launcher'] == 'Competitive · Mirage · Counter-Terrorists · CT 8–6 T'

    payload = PresenceBuilder(config).build(activity)
    assert payload['details'] == 'Playing · Counter-Strike 2'
    assert payload['state'] == 'Competitive · Mirage · Counter-Terrorists · CT 8–6 T'
    assert payload['large_text'] == 'Counter-Strike 2'
