"""Local, privacy-conscious bridge for the optional browser companion extension."""

from __future__ import annotations

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from config import Config


LOGGER = logging.getLogger(__name__)
_ALLOWED_ORIGIN_PREFIXES = ('chrome-extension://', 'moz-extension://', 'safari-web-extension://')
_MAX_BODY_BYTES = 32 * 1024
_SUPPORTED_VERSION = 1


class BrowserCompanionBridge:
    """Keep recent browser snapshots in memory and expose a loopback-only HTTP endpoint."""

    def __init__(self, config: Config):
        self.config = config
        self.host = '127.0.0.1'
        self.port = int(config.get('browser_companion.port', 32191) or 32191)
        self.ttl_secs = float(config.get('browser_companion.ttl_secs', 15) or 15)
        self._records: Dict[tuple[str, str], tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.RLock()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        if self._server is not None:
            return True

        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'CYBREXBrowserCompanion/1'

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                LOGGER.debug('Browser companion: ' + format, *args)

            def _origin_allowed(self) -> bool:
                origin = (self.headers.get('Origin') or '').strip().lower()
                return not origin or origin.startswith(_ALLOWED_ORIGIN_PREFIXES)

            def _send(self, status: int, payload: Dict[str, Any]) -> None:
                body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
                self.send_response(status)
                origin = (self.headers.get('Origin') or '').strip()
                if origin.lower().startswith(_ALLOWED_ORIGIN_PREFIXES):
                    self.send_header('Access-Control-Allow-Origin', origin)
                    self.send_header('Vary', 'Origin')
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self) -> None:  # noqa: N802
                if not self._origin_allowed():
                    self._send(403, {'ok': False, 'error': 'origin_not_allowed'})
                    return
                self.send_response(204)
                origin = (self.headers.get('Origin') or '').strip()
                if origin:
                    self.send_header('Access-Control-Allow-Origin', origin)
                    self.send_header('Vary', 'Origin')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-CYBREX-Companion')
                self.send_header('Access-Control-Max-Age', '600')
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                if self.path != '/v1/health':
                    self._send(404, {'ok': False})
                    return
                self._send(200, {'ok': True, 'version': _SUPPORTED_VERSION})

            def do_POST(self) -> None:  # noqa: N802
                if self.path != '/v1/activity':
                    self._send(404, {'ok': False})
                    return
                if not self._origin_allowed():
                    self._send(403, {'ok': False, 'error': 'origin_not_allowed'})
                    return
                if self.headers.get('X-CYBREX-Companion') != '1':
                    self._send(403, {'ok': False, 'error': 'missing_companion_header'})
                    return
                try:
                    length = int(self.headers.get('Content-Length') or '0')
                except ValueError:
                    length = 0
                if length <= 0 or length > _MAX_BODY_BYTES:
                    self._send(413, {'ok': False, 'error': 'invalid_size'})
                    return
                try:
                    raw = self.rfile.read(length)
                    payload = json.loads(raw.decode('utf-8'))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send(400, {'ok': False, 'error': 'invalid_json'})
                    return
                try:
                    bridge.update(payload)
                except ValueError as exc:
                    self._send(400, {'ok': False, 'error': str(exc)[:120]})
                    return
                self._send(200, {'ok': True})

        try:
            self._server = ThreadingHTTPServer((self.host, self.port), Handler)
            self._server.daemon_threads = True
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                name='browser-companion',
                daemon=True,
            )
            self._thread.start()
            LOGGER.info('Browser companion listening on http://%s:%d', self.host, self.port)
            return True
        except OSError as exc:
            self._server = None
            self._thread = None
            LOGGER.warning('Browser companion could not bind 127.0.0.1:%d: %s', self.port, exc)
            return False

    def stop(self) -> None:
        server = self._server
        self._server = None
        if server is not None:
            server.shutdown()
            server.server_close()
        self._thread = None

    def update(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ValueError('payload_must_be_object')
        try:
            version = int(payload.get('version', 0))
        except (TypeError, ValueError):
            version = 0
        if version != _SUPPORTED_VERSION:
            raise ValueError('unsupported_version')

        browser = self._clean_text(payload.get('browser'), 40)
        tab_id = self._clean_text(payload.get('tab_id'), 80)
        if not browser or not tab_id:
            raise ValueError('browser_and_tab_id_required')

        url = self._clean_url(payload.get('url'))
        media = payload.get('media') if isinstance(payload.get('media'), dict) else {}
        record = {
            'version': _SUPPORTED_VERSION,
            'browser': browser,
            'tab_id': tab_id,
            'url': url,
            'title': self._clean_text(payload.get('title'), 300),
            'service': self._clean_text(payload.get('service'), 80),
            'private': bool(payload.get('private', False)),
            'focused': bool(payload.get('focused', False)),
            'visible': bool(payload.get('visible', False)),
            'media': {
                'playing': bool(media.get('playing', False)),
                'position': self._clean_number(media.get('position')),
                'duration': self._clean_number(media.get('duration')),
                'title': self._clean_text(media.get('title'), 300),
                'artist': self._clean_text(media.get('artist'), 200),
            },
        }
        now = time.monotonic()
        with self._lock:
            self._records[(browser.lower(), tab_id)] = (now, record)
            self._prune(now)

    def latest(self, browser_name: str = '') -> Optional[Dict[str, Any]]:
        """Return the best recent tab for foreground browser activity."""
        now = time.monotonic()
        browser = str(browser_name or '').strip().lower()
        with self._lock:
            self._prune(now)
            candidates = [
                (seen, data)
                for (record_browser, _), (seen, data) in self._records.items()
                if not browser or self._browser_matches(browser, record_browser)
            ]
            if not candidates:
                return None
            _, selected = max(
                candidates,
                key=lambda item: (
                    bool(item[1].get('focused')),
                    bool((item[1].get('media') or {}).get('playing')),
                    bool(item[1].get('visible')),
                    item[0],
                ),
            )
            return dict(selected)

    def latest_media(self, browser_name: str = '') -> Optional[Dict[str, Any]]:
        """Return the best recent tab that is actively playing media."""
        now = time.monotonic()
        browser = str(browser_name or '').strip().lower()
        with self._lock:
            self._prune(now)
            candidates = [
                (seen, data)
                for (record_browser, _), (seen, data) in self._records.items()
                if (not browser or self._browser_matches(browser, record_browser))
                and bool((data.get('media') or {}).get('playing'))
                and not bool(data.get('private'))
            ]
            if not candidates:
                return None
            # A playing tab that is currently focused is strongest. Otherwise
            # recency decides between multiple background players.
            _, selected = max(
                candidates,
                key=lambda item: (bool(item[1].get('focused')), item[0]),
            )
            return dict(selected)

    def _prune(self, now: float) -> None:
        expired = [key for key, (seen, _) in self._records.items() if now - seen > self.ttl_secs]
        for key in expired:
            self._records.pop(key, None)
        if len(self._records) > 100:
            oldest = sorted(self._records.items(), key=lambda item: item[1][0])[:-100]
            for key, _ in oldest:
                self._records.pop(key, None)

    @staticmethod
    def _browser_matches(expected: str, actual: str) -> bool:
        aliases = {
            'brave': ('brave',),
            'firefox': ('firefox',),
            'chrome': ('chrome', 'google chrome'),
            'chromium': ('chromium',),
            'edge': ('edge', 'msedge'),
            'opera': ('opera',),
            'vivaldi': ('vivaldi',),
        }
        expected_lower = expected.lower()
        actual_lower = actual.lower()
        for canonical, names in aliases.items():
            if any(name in expected_lower for name in names):
                return any(name in actual_lower for name in names) or canonical in actual_lower
        return expected_lower == actual_lower

    @staticmethod
    def _clean_text(value: Any, limit: int) -> str:
        return str(value or '').replace('\x00', '').strip()[:limit]

    @staticmethod
    def _clean_number(value: Any) -> float:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(number, 7 * 24 * 3600.0))

    @staticmethod
    def _clean_url(value: Any) -> Optional[str]:
        raw = str(value or '').strip()
        if not raw:
            return None
        try:
            parsed = urlparse(raw)
        except ValueError:
            return None
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            return None
        return raw[:2048]


_BRIDGES: Dict[tuple[str, int], BrowserCompanionBridge] = {}
_BRIDGES_LOCK = threading.Lock()


def get_browser_companion(config: Config, start: bool = True) -> Optional[BrowserCompanionBridge]:
    """Return the shared bridge when the optional companion feature is enabled."""
    if not bool(config.get('browser_companion.enabled', False)):
        return None
    port = int(config.get('browser_companion.port', 32191) or 32191)
    key = ('127.0.0.1', port)
    with _BRIDGES_LOCK:
        bridge = _BRIDGES.get(key)
        if bridge is None:
            bridge = BrowserCompanionBridge(config)
            _BRIDGES[key] = bridge
    if start:
        bridge.start()
    return bridge
