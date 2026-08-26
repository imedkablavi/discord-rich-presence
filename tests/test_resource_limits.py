import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler

from fixed_http import FixedWorkerLoopbackHTTPServer
from gui_instance import GUIInstanceLock
from resource_hardening import apply_resource_hardening, is_applied


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def do_GET(self):  # noqa: N802
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_fixed_http_reuses_small_worker_pool():
    server = FixedWorkerLoopbackHTTPServer(
        ("127.0.0.1", 0),
        _Handler,
        max_workers=2,
        max_pending_requests=4,
        client_timeout=1.0,
        thread_name_prefix="cybrex-test-http",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        for _ in range(120):
            with urllib.request.urlopen(url, timeout=2) as response:
                assert json.loads(response.read().decode("utf-8"))["ok"] is True

        workers = [
            item for item in threading.enumerate()
            if item.name.startswith("cybrex-test-http")
        ]
        assert 1 <= len(workers) <= 2
        assert server.worker_limit == 2
        assert server.pending_limit == 4
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if not any(
            item.name.startswith("cybrex-test-http") for item in threading.enumerate()
        ):
            break
        time.sleep(0.02)
    assert not any(
        item.name.startswith("cybrex-test-http") for item in threading.enumerate()
    )


def test_legacy_high_frequency_bridges_are_patched_to_fixed_workers():
    apply_resource_hardening()
    assert is_applied()

    import browser_companion
    import cs2_gsi

    assert issubclass(browser_companion._CompanionHTTPServer, FixedWorkerLoopbackHTTPServer)
    assert issubclass(cs2_gsi._CS2HTTPServer, FixedWorkerLoopbackHTTPServer)


def test_gui_single_instance_lock_blocks_duplicate_process(tmp_path):
    path = tmp_path / "gui.lock"
    first = GUIInstanceLock(path)
    second = GUIInstanceLock(path)

    assert first.acquire() is True
    try:
        assert second.acquire() is False
    finally:
        first.release()

    assert second.acquire() is True
    second.release()
