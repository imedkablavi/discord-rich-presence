import json
import socket
import threading
import urllib.request

from browser_companion import BrowserCompanionBridge
from resource_hardening import apply_resource_hardening


def _free_loopback_port() -> int:
    """Reserve an ephemeral port briefly so parallel CI tests do not collide."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _Config:
    config_path = "/tmp/cybrex-test-config.yaml"

    def __init__(self, port: int):
        self.port = port

    def get(self, key, default=None):
        values = {
            "browser_companion.port": self.port,
            "browser_companion.ttl_secs": 15,
        }
        return values.get(key, default)


def test_browser_health_stress_keeps_fixed_worker_count():
    apply_resource_hardening()
    bridge = BrowserCompanionBridge(_Config(_free_loopback_port()))
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
