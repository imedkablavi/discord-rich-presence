import json
import urllib.error
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


def _post_companion_activity(bridge, payload, *, origin, companion_header=True):
    headers = {
        "Origin": origin,
        "Content-Type": "application/json",
    }
    if companion_header:
        headers["X-CYBREX-Companion"] = "1"
    request = urllib.request.Request(
        f"http://127.0.0.1:{bridge.port}/v1/activity",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()



def test_companion_rejects_web_origin_for_activity_post(tmp_path):
    bridge = BrowserCompanionBridge(Config(tmp_path / "config.yaml"))
    bridge.port = 0
    assert bridge.start() is True
    try:
        status, headers, body = _post_companion_activity(
            bridge,
            _snapshot("web-origin"),
            origin="https://attacker.example",
        )

        assert status == 403
        assert json.loads(body)["error"] == "origin_not_allowed"
        assert headers.get("Access-Control-Allow-Origin") is None
        assert bridge.status()["records"] == 0
    finally:
        bridge.stop()


def test_companion_requires_its_protocol_header_even_for_extension_origins(tmp_path):
    bridge = BrowserCompanionBridge(Config(tmp_path / "config.yaml"))
    bridge.port = 0
    assert bridge.start() is True
    try:
        status, _headers, body = _post_companion_activity(
            bridge,
            _snapshot("missing-marker"),
            origin="chrome-extension://cybrex-test",
            companion_header=False,
        )

        assert status == 403
        assert json.loads(body)["error"] == "missing_companion_header"
        assert bridge.status()["records"] == 0
    finally:
        bridge.stop()


def test_companion_accepts_extension_origin_with_protocol_header(tmp_path):
    bridge = BrowserCompanionBridge(Config(tmp_path / "config.yaml"))
    bridge.port = 0
    assert bridge.start() is True
    origin = "chrome-extension://cybrex-test"
    try:
        status, headers, body = _post_companion_activity(
            bridge,
            _snapshot("valid-extension"),
            origin=origin,
        )

        assert status == 200
        assert json.loads(body)["ok"] is True
        assert headers.get("Access-Control-Allow-Origin") == origin
        assert bridge.status()["records"] == 1
    finally:
        bridge.stop()


def test_companion_rejects_oversized_activity_payload_before_parsing(tmp_path):
    bridge = BrowserCompanionBridge(Config(tmp_path / "config.yaml"))
    bridge.port = 0
    assert bridge.start() is True
    try:
        payload = _snapshot("oversized")
        payload["title"] = "x" * 40_000
        status, _headers, body = _post_companion_activity(
            bridge,
            payload,
            origin="moz-extension://cybrex-test",
        )

        assert status == 413
        assert json.loads(body)["error"] == "invalid_size"
        assert bridge.status()["records"] == 0
    finally:
        bridge.stop()
