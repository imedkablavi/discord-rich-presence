import json
import threading
import urllib.request

from browser_companion import BrowserCompanionBridge
from resource_hardening import apply_resource_hardening


class _Config:
    config_path = "/tmp/cybrex-test-config.yaml"

    def get(self, key, default=None):
        values = {
            "browser_companion.port": 0,
            "browser_companion.ttl_secs": 15,
        }
        return values.get(key, default)


def test_browser_health_stress_keeps_fixed_worker_count():
    apply_resource_hardening()
    bridge = BrowserCompanionBridge(_Config())
    assert bridge.start() is True
    try:
        url = f"http://127.0.0.1:{bridge.port}/v1/health"
        for _ in range(250):
            with urllib.request.urlopen(url, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
                assert payload["ok"] is True

        workers = [
            item for item in threading.enumerate()
            if item.name.startswith("cybrex-browser")
        ]
        assert 1 <= len(workers) <= 4
    finally:
        bridge.stop()

    assert not any(
        item.name.startswith("cybrex-browser") for item in threading.enumerate()
    )
