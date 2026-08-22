"""Local, privacy-conscious bridge for the optional browser companion extension."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from config import Config


LOGGER = logging.getLogger(__name__)
_ALLOWED_ORIGIN_PREFIXES = ('chrome-extension://', 'moz-extension://', 'safari-web-extension://')
_MAX_BODY_BYTES = 32 * 1024
_MAX_RECORDS = 100
_MAX_CONCURRENT_REQUESTS = 8
_CLIENT_TIMEOUT_SECS = 3.0
_SUPPORTED_VERSION = 1


class _CompanionHTTPServer(ThreadingHTTPServer):
    """Small loopback HTTP server with bounded thread/socket behavior."""

    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 16
    block_on_close = False

    def __init__(self, server_address, request_handler_class):
        super().__init__(server_address, request_handler_class)
        self._request_slots = threading.BoundedSemaphore(_MAX_CONCURRENT_REQUESTS)

    def process_request(self, request, client_address) -> None:
        # ThreadingMixIn normally creates one worker per accepted connection.
        # Keep that bounded even on loopback so a buggy extension/local process
        # cannot grow request threads without limit.
        if not self._request_slots.acquire(blocking=False):
            try:
                request.close()
            except OSError:
                pass
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


class BrowserCompanionBridge:
    """Keep recent browser snapshots in memory and expose a loopback-only HTTP endpoint."""

    def __init__(self, config: Config):
        self.config = config
        self.host = '127.0.0.1'
        self.port = int(config.get('browser_companion.port', 32191) or 32191)
        self.ttl_secs = float(config.get('browser_companion.ttl_secs', 15) or 15)
        self._records: Dict[tuple[str, str], tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.RLock()
        self._server: Optional[_CompanionHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        server = self._server
        if server is not None:
            return True

        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'CYBREXBrowserCompanion/1'

            def setup(self) -> None:
                super().setup()
                try:
                    self.connection.settimeout(_CLIENT_TIMEOUT_SECS)
                except OSError:
                    pass

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                # A healthy extension posts snapshots frequently. Do not flood
                # verbose logs with routine 200/204 requests; unexpected status
                # codes remain visible for troubleshooting.
                status = 0
                if len(args) >= 2:
                    try:
                        status = int(args[1])
                    except (TypeError, ValueError):
                        status = 0
                if status in {200, 204}:
                    return
                LOGGER.debug('Browser companion: ' + format, *args)

            def _origin_allowed(self) -> bool:
                origin = (self.headers.get('Origin') or '').strip().lower()
                # Empty Origin is kept for local diagnostics/tools. Browser pages
                # send their real http(s) Origin and are rejected by CORS here.
                # This endpoint is not a security boundary against another process
                # already running as the same OS user.
                return not origin or origin.startswith(_ALLOWED_ORIGIN_PREFIXES)

            def _send(self, status: int, payload: Dict[str, Any]) -> None:
                body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
                try:
                    self.send_response(status)
                    origin = (self.headers.get('Origin') or '').strip()
                    if origin.lower().startswith(_ALLOWED_ORIGIN_PREFIXES):
                        self.send_header('Access-Control-Allow-Origin', origin)
                        self.send_header('Vary', 'Origin')
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError, socket.timeout, OSError):
                    # Client tabs/service workers can disappear between request and
                    # response. Never keep a server thread alive just to log that.
                    return

            def do_OPTIONS(self) -> None:  # noqa: N802
                if not self._origin_allowed():
                    self._send(403, {'ok': False, 'error': 'origin_not_allowed'})
                    return
                try:
                    self.send_response(204)
                    origin = (self.headers.get('Origin') or '').strip()
                    if origin:
                        self.send_header('Access-Control-Allow-Origin', origin)
                        self.send_header('Vary', 'Origin')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-CYBREX-Companion')
                    self.send_header('Access-Control-Max-Age', '600')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                except (BrokenPipeError, ConnectionResetError, socket.timeout, OSError):
                    return

            def do_GET(self) -> None:  # noqa: N802
                if self.path == '/v1/health':
                    self._send(200, {'ok': True, 'version': _SUPPORTED_VERSION})
                    return
                if self.path == '/v1/status':
                    self._send(200, bridge.status())
                    return
                self._send(404, {'ok': False})

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
                content_type = (self.headers.get('Content-Type') or '').split(';', 1)[0].strip().lower()
                if content_type != 'application/json':
                    self._send(415, {'ok': False, 'error': 'content_type_required'})
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
                except (socket.timeout, TimeoutError):
                    self._send(408, {'ok': False, 'error': 'request_timeout'})
                    return
                except OSError:
                    return
                if len(raw) != length:
                    self._send(400, {'ok': False, 'error': 'truncated_body'})
                    return
                try:
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
            server = _CompanionHTTPServer((self.host, self.port), Handler)
            # Port 0 is useful for tests and diagnostics; persist the actual bound
            # port so callers can connect to it and stop/rebind deterministically.
            self.port = int(server.server_address[1])
            thread = threading.Thread(
                target=server.serve_forever,
                name='browser-companion',
                daemon=True,
            )
            self._server = server
            self._thread = thread
            thread.start()
            LOGGER.info('Browser companion listening on http://%s:%d', self.host, self.port)
            return True
        except OSError as exc:
            self._server = None
            self._thread = None
            LOGGER.warning('Browser companion could not bind 127.0.0.1:%d: %s', self.port, exc)
            return False

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        if server is not None:
            try:
                server.shutdown()
            except OSError:
                pass
            try:
                server.server_close()
            except OSError:
                pass
        if (
            thread is not None
            and thread is not threading.current_thread()
            and thread.is_alive()
        ):
            thread.join(timeout=2.0)
        # Exact URLs/titles exist only in memory. Remove them immediately when
        # the service stops rather than waiting for process teardown or TTL.
        with self._lock:
            self._records.clear()

    def update(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ValueError('payload_must_be_object')
        try:
            version = int(payload.get('version', 0))
        except (TypeError, ValueError):
            version = 0
        if version != _SUPPORTED_VERSION:
            raise ValueError('unsupported_version')

        tab_id = self._clean_text(payload.get('tab_id'), 80)
        if not tab_id:
            raise ValueError('tab_id_required')

        # Browser is part of the record identity. Tab IDs are scoped to one
        # browser profile and can collide across Brave/Firefox/Chrome. Requiring
        # it for removals prevents closing tab 42 in one browser from deleting
        # tab 42 snapshots belonging to another browser.
        browser = self._clean_text(payload.get('browser'), 40)
        if not browser:
            raise ValueError('browser_required')

        if bool(payload.get('removed')):
            with self._lock:
                self._records.pop((browser.lower(), tab_id), None)
            return

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

    def status(self) -> Dict[str, Any]:
        """Return privacy-safe diagnostics without exposing URLs, titles, or tab IDs."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            if not self._records:
                return {
                    'ok': True,
                    'version': _SUPPORTED_VERSION,
                    'records': 0,
                    'connected': False,
                    'latest': None,
                }
            seen, record = max(self._records.values(), key=lambda item: item[0])
            media = record.get('media') or {}
            return {
                'ok': True,
                'version': _SUPPORTED_VERSION,
                'records': len(self._records),
                'connected': True,
                'latest': {
                    'browser': record.get('browser') or '',
                    'service': record.get('service') or '',
                    'focused': bool(record.get('focused')),
                    'visible': bool(record.get('visible')),
                    'media_playing': bool(media.get('playing')),
                    'age_ms': max(0, int((now - seen) * 1000)),
                },
            }

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
            _, selected = max(
                candidates,
                key=lambda item: (bool(item[1].get('focused')), item[0]),
            )
            return dict(selected)

    def _prune(self, now: float) -> None:
        expired = [key for key, (seen, _) in self._records.items() if now - seen > self.ttl_secs]
        for key in expired:
            self._records.pop(key, None)
        if len(self._records) > _MAX_RECORDS:
            oldest = sorted(self._records.items(), key=lambda item: item[1][0])[:-_MAX_RECORDS]
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
        if number != number or number in (float('inf'), float('-inf')):
            return 0.0
        return max(0.0, min(number, 7 * 24 * 3600.0))

    @staticmethod
    def _clean_url(value: Any) -> Optional[str]:
        raw = str(value or '').strip()
        if not raw or len(raw) > 2048:
            return None
        # Control characters can confuse downstream URL parsers/logging and
        # should never be part of an activity URL.
        if any(ord(char) < 32 or ord(char) == 127 for char in raw):
            return None
        try:
            parsed = urlsplit(raw)
            # Accessing hostname/port validates malformed bracketed hosts/ports.
            hostname = parsed.hostname
            _ = parsed.port
        except ValueError:
            return None
        if parsed.scheme.lower() not in {'http', 'https'} or not hostname:
            return None
        # Userinfo can contain credentials. Rich Presence never needs it.
        if parsed.username is not None or parsed.password is not None:
            return None
        return raw


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


def stop_browser_companions() -> None:
    """Stop and forget all shared local bridges owned by this process."""
    with _BRIDGES_LOCK:
        bridges = list(_BRIDGES.values())
        _BRIDGES.clear()
    for bridge in bridges:
        try:
            bridge.stop()
        except Exception as exc:
            LOGGER.debug('Could not stop browser companion cleanly: %s', exc)
