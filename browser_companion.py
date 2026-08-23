"""Privacy-preserving loopback companion for browser extensions.

The companion never opens a non-loopback socket and never sends browser data
anywhere. Extensions authenticate with a random per-user bearer token. Exact
URLs are opt-in; private/incognito activity is always reduced to a private flag.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from config import Config


MAX_BODY_BYTES = 16 * 1024
ALLOWED_ORIGIN_SCHEMES = {"chrome-extension", "moz-extension"}


def default_companion_dir(config: Config) -> Path:
    path = getattr(config, "config_path", None)
    if path:
        return Path(path).parent / "companion"
    return Path.home() / ".config" / "discord-rich-presence" / "companion"


class BrowserCompanionState:
    """Thread-safe, short-lived browser state received from a local extension."""

    def __init__(self, config: Config):
        self.config = config
        self._lock = threading.Lock()
        self._state: Optional[Dict[str, Any]] = None

    def update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = time.monotonic()
        private = bool(payload.get("private", False))
        browser = str(payload.get("browser", "")).strip()[:64]
        service = str(payload.get("service", "")).strip()[:64]
        title = str(payload.get("title", "")).strip()[:256]
        url = str(payload.get("url", "")).strip()[:2048]

        if private:
            service = ""
            title = ""
            url = ""
        else:
            if not self.config.get("browser_companion.allow_titles", True):
                title = ""
            url = self._sanitize_url(url)

        state = {
            "browser": browser,
            "service": service,
            "title": title,
            "url": url or None,
            "private": private,
            "received_monotonic": now,
        }
        with self._lock:
            self._state = state
        return dict(state)

    def snapshot(self, browser: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            state = dict(self._state) if self._state else None
        if not state:
            return None
        ttl = float(self.config.get("browser_companion.ttl_secs", 15) or 15)
        age = time.monotonic() - float(state.get("received_monotonic", 0))
        if age < 0 or age > max(1.0, ttl):
            return None
        expected = str(browser or "").strip().lower()
        actual = str(state.get("browser") or "").strip().lower()
        if expected and actual and expected not in actual and actual not in expected:
            return None
        state.pop("received_monotonic", None)
        return state

    def _sanitize_url(self, value: str) -> Optional[str]:
        if not value:
            return None
        try:
            parsed = urllib.parse.urlsplit(value)
        except ValueError:
            return None
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        if self.config.get("browser_companion.allow_exact_url", False):
            return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
        if self.config.get("browser_companion.allow_origin", True):
            return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        return None


class _CompanionHTTPServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, handler, state: BrowserCompanionState, token: str):
        super().__init__(server_address, handler)
        self.state = state
        self.token = token


class _Handler(BaseHTTPRequestHandler):
    server: _CompanionHTTPServer

    def log_message(self, fmt: str, *args: Any) -> None:
        logging.getLogger(__name__).debug("Browser companion: " + fmt, *args)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/activity":
            self._json(404, {"error": "not_found"})
            return
        if not self._authorized():
            self._json(401, {"error": "unauthorized"})
            return
        if not self._origin_allowed():
            self._json(403, {"error": "origin_rejected"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid_length"})
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self._json(413, {"error": "payload_too_large"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "invalid_json"})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": "invalid_payload"})
            return
        state = self.server.state.update(payload)
        self._json(200, {"ok": True, "private": state["private"]})

    def _authorized(self) -> bool:
        prefix = "Bearer "
        value = self.headers.get("Authorization", "")
        if not value.startswith(prefix):
            return False
        return hmac.compare_digest(value[len(prefix):], self.server.token)

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin", "").strip()
        if not origin:
            return True
        try:
            return urllib.parse.urlsplit(origin).scheme in ALLOWED_ORIGIN_SCHEMES
        except ValueError:
            return False

    def _json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class BrowserCompanionServer:
    """Single-threaded loopback HTTP bridge with a stable background thread."""

    def __init__(self, config: Config):
        self.config = config
        self.state = BrowserCompanionState(config)
        self.logger = logging.getLogger(__name__)
        self._server: Optional[_CompanionHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.token_path = default_companion_dir(config) / "token"
        self.token = self._load_or_create_token()

    def start(self) -> None:
        if self._server:
            return
        port = int(self.config.get("browser_companion.port", 17653) or 17653)
        self._server = _CompanionHTTPServer(("127.0.0.1", port), _Handler, self.state, self.token)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="browser-companion",
            daemon=True,
        )
        self._thread.start()
        self.logger.info("Browser companion listening on 127.0.0.1:%s", port)

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        if server:
            server.shutdown()
            server.server_close()
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def snapshot(self, browser: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.state.snapshot(browser)

    def _load_or_create_token(self) -> str:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            token = self.token_path.read_text(encoding="utf-8").strip()
            if len(token) >= 32:
                return token
        except OSError:
            pass
        token = secrets.token_urlsafe(32)
        temp = self.token_path.with_suffix(".tmp")
        temp.write_text(token, encoding="utf-8")
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass
        os.replace(temp, self.token_path)
        try:
            os.chmod(self.token_path, 0o600)
        except OSError:
            pass
        return token
