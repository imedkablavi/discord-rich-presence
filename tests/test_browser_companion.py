import json
import urllib.error
import urllib.request
from pathlib import Path

from browser_companion import BrowserCompanionServer, BrowserCompanionState
from config import Config


def _config(tmp_path: Path) -> Config:
    cfg = Config(tmp_path / "config.yaml")
    cfg.set("browser_companion.port", 0)
    return cfg


def test_private_payload_is_always_redacted(tmp_path: Path):
    state = BrowserCompanionState(_config(tmp_path))
    state.update({
        "browser": "Firefox",
        "title": "Secret tab",
        "service": "Example",
        "url": "https://example.com/private?token=abc",
        "private": True,
    })
    snap = state.snapshot("Firefox")
    assert snap is not None
    assert snap["private"] is True
    assert snap["title"] == ""
    assert snap["service"] == ""
    assert snap["url"] is None


def test_default_url_policy_keeps_origin_only(tmp_path: Path):
    state = BrowserCompanionState(_config(tmp_path))
    state.update({
        "browser": "Chrome",
        "url": "https://example.com/account/42?token=secret#fragment",
    })
    assert state.snapshot("Chrome")["url"] == "https://example.com"


def test_exact_url_is_explicit_opt_in_and_fragment_is_removed(tmp_path: Path):
    cfg = _config(tmp_path)
    cfg.set("browser_companion.allow_exact_url", True)
    state = BrowserCompanionState(cfg)
    state.update({"browser": "Chrome", "url": "https://example.com/watch?v=42#token"})
    assert state.snapshot("Chrome")["url"] == "https://example.com/watch?v=42"


def test_loopback_server_rejects_bad_token(tmp_path: Path):
    cfg = _config(tmp_path)
    server = BrowserCompanionServer(cfg)
    server.start()
    try:
        port = server._server.server_address[1]
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/activity",
            data=json.dumps({"browser": "Firefox", "title": "Example"}).encode(),
            headers={"Authorization": "Bearer wrong", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=2)
            assert False, "request should fail"
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
    finally:
        server.stop()
