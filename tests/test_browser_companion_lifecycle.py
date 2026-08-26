import json
import urllib.request

from browser_companion import BrowserCompanionBridge
from config import Config


def _snapshot(tab_id: str):
    return {
        'version': 1,
        'browser': 'Brave',
        'tab_id': tab_id,
        'url': f'https://example.com/watch?id={tab_id}',
        'title': f'Example {tab_id}',
        'service': 'Example',
        'private': False,
        'focused': False,
        'visible': True,
        'media': {'playing': False, 'position': 0, 'duration': 0},
    }


def test_companion_record_memory_is_bounded(tmp_path):
    bridge = BrowserCompanionBridge(Config(tmp_path / 'config.yaml'))
    for index in range(500):
        bridge.update(_snapshot(str(index)))

    status = bridge.status()
    assert status['records'] == 100
    assert len(bridge._records) == 100

    bridge.stop()
    assert bridge.status()['records'] == 0


def test_companion_start_stop_joins_thread_and_releases_port(tmp_path):
    first = BrowserCompanionBridge(Config(tmp_path / 'config.yaml'))
    first.port = 0
    assert first.start() is True
    port = first.port
    thread = first._thread
    assert thread is not None and thread.is_alive()

    with urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/health', timeout=2) as response:
        payload = json.loads(response.read().decode('utf-8'))
    assert payload == {'ok': True, 'version': 1}

    first.update(_snapshot('one'))
    assert first.status()['connected'] is True
    first.stop()
    assert not thread.is_alive()
    assert first.status()['connected'] is False

    second = BrowserCompanionBridge(Config(tmp_path / 'config2.yaml'))
    second.port = port
    try:
        assert second.start() is True
    finally:
        second.stop()


def test_companion_rejects_non_finite_media_numbers(tmp_path):
    bridge = BrowserCompanionBridge(Config(tmp_path / 'config.yaml'))
    payload = _snapshot('bad-number')
    payload['media'] = {'playing': True, 'position': float('nan'), 'duration': float('inf')}
    bridge.update(payload)

    record = bridge.latest('Brave')
    assert record is not None
    assert record['media']['position'] == 0
    assert record['media']['duration'] == 0
