import time
from pathlib import Path

from config import Config
from detectors.gaming import GamingDetector
from fivem_bridge import FiveMBridge


def _config(tmp_path: Path) -> Config:
    return Config(tmp_path / 'config.yaml')


def test_fivem_payload_is_minimal_and_bounded():
    payload = FiveMBridge.normalize_payload({
        'server_name': '  Example\nRoleplay  ',
        'player_count': 999,
        'max_players': 128,
        'join_url': 'https://cfx.re/join/AbC123',
        'player_identifier': 'license:should-never-be-kept',
        'job': 'police',
        'coords': [1, 2, 3],
    })
    assert payload == {
        'server_name': 'Example Roleplay',
        'player_count': 128,
        'max_players': 128,
        'join_url': 'https://cfx.re/join/AbC123',
    }


def test_fivem_bridge_rejects_non_nui_origin(tmp_path):
    bridge = FiveMBridge(_config(tmp_path))
    assert not bridge.ingest({'server_name': 'Example'}, origin='https://evil.example')
    assert bridge.latest() is None


def test_fivem_privacy_defaults_hide_server_and_join(tmp_path):
    config = _config(tmp_path)
    bridge = FiveMBridge(config)
    assert bridge.ingest(
        {
            'server_name': 'Private RP Server',
            'player_count': 42,
            'max_players': 128,
            'join_url': 'https://cfx.re/join/test42',
        },
        origin='https://cfx-nui-cybrex_presence',
    )
    assert bridge.latest() == {'player_count': 42, 'max_players': 128}


def test_fivem_privacy_can_opt_into_server_and_join(tmp_path):
    config = _config(tmp_path)
    config.set('fivem.show_server_name', True)
    config.set('fivem.allow_join_button', True)
    bridge = FiveMBridge(config)
    assert bridge.ingest(
        {
            'server_name': 'Public RP',
            'player_count': 10,
            'max_players': 64,
            'join_url': 'https://cfx.re/join/Public_1',
        },
        origin='https://cfx-nui-cybrex_presence',
    )
    assert bridge.latest() == {
        'server_name': 'Public RP',
        'player_count': 10,
        'max_players': 64,
        'join_url': 'https://cfx.re/join/Public_1',
    }


def test_fivem_snapshot_expires(tmp_path, monkeypatch):
    config = _config(tmp_path)
    bridge = FiveMBridge(config)
    now = [100.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    assert bridge.ingest({'player_count': 1, 'max_players': 10}, origin='https://cfx-nui-cybrex_presence')
    assert bridge.latest() is not None
    now[0] += 16
    assert bridge.latest() is None


def test_fivem_process_detection_preempts_gta_labeling():
    assert GamingDetector._is_fivem_process('FiveM_b3258_GTAProcess')
    assert GamingDetector._is_fivem_process('CitizenFX_SubProcess')
    assert not GamingDetector._is_fivem_process('GTA5')


def test_fivem_enrichment_builds_privacy_filtered_state(tmp_path):
    class FakeBridge:
        def __init__(self):
            self.config = None
            self.started = False

        def start(self):
            self.started = True
            return True

        def latest(self):
            return {
                'server_name': 'Public RP',
                'player_count': 20,
                'max_players': 100,
                'join_url': 'https://cfx.re/join/public1',
            }

    detector = object.__new__(GamingDetector)
    detector.config = _config(tmp_path)
    detector.fivem_bridge = FakeBridge()
    activity = {'type': 'gaming', 'game_name': 'FiveM', 'is_game': True}
    detector._enrich_fivem(activity)
    assert detector.fivem_bridge.started is True
    assert activity['launcher'] == 'FiveM'
    assert activity['game_source'] == 'Public RP · 20/100 players'
    assert activity['store_url'] == 'https://cfx.re/join/public1'
