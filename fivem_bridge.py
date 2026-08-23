"""Loopback bridge for the optional CYBREX FiveM server resource."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import urlsplit

from config import Config


_LOGGER = logging.getLogger(__name__)
_DEFAULT_PORT = 32193
_MAX_BODY_BYTES = 8 * 1024
_MAX_TEXT = 128
_ALLOWED_ORIGINS = {
    'https://cfx-nui-cybrex_presence',
    'https://cfx-nui-cybrex-presence',
}
_JOIN_RE = re.compile(r'^https://cfx\.re/join/[A-Za-z0-9_-]{2,64}/?$')


class FiveMBridge:
    """Receive a minimal FiveM presence snapshot from local NUI only."""

    def __init__(self, config: Config):
        self.config = config
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._latest: Optional[dict[str, Any]] = None
        self._latest_at = 0.0

    @staticmethod
    def _strict_bool(config: Config, key: str, default: bool) -> bool:
        value = config.get(key, default)
        return value if isinstance(value, bool) else default

    def _port(self) -> int:
        try:
            port = int(self.config.get('fivem.port', _DEFAULT_PORT) or _DEFAULT_PORT)
        except (TypeError, ValueError):
            return _DEFAULT_PORT
        return port if 1024 <= port <= 65535 else _DEFAULT_PORT

    def _ttl(self) -> float:
        try:
            ttl = float(self.config.get('fivem.ttl_secs', 15) or 15)
        except (TypeError, ValueError):
            return 15.0
        return min(60.0, max(5.0, ttl))

    @staticmethod
    def _origin_allowed(origin: object) -> bool:
        return str(origin or '').strip().lower() in _ALLOWED_ORIGINS

    @staticmethod
    def _clean_text(value: object) -> str:
        text = str(value or '').replace('\x00', '').replace('\r', ' ').replace('\n', ' ').strip()
        return ' '.join(text.split())[:_MAX_TEXT]

    @staticmethod
    def _clean_count(value: object, maximum: int = 4096) -> int:
        if isinstance(value, bool):
            return 0
        try:
            number = int(value or 0)
        except (TypeError, ValueError, OverflowError):
            return 0
        return min(maximum, max(0, number))

    @classmethod
    def _clean_join_url(cls, value: object) -> str:
        url = str(value or '').strip()
        if not url or len(url) > 160 or not _JOIN_RE.fullmatch(url):
            return ''
        try:
            parsed = urlsplit(url)
        except ValueError:
            return ''
        if parsed.scheme != 'https' or parsed.hostname != 'cfx.re':
            return ''
        return url

    @classmethod
    def normalize_payload(cls, payload: object) -> Optional[dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        server_name = cls._clean_text(payload.get('server_name'))
        player_count = cls._clean_count(payload.get('player_count'))
        max_players = cls._clean_count(payload.get('max_players'))
        if max_players and player_count > max_players:
            player_count = max_players
        join_url = cls._clean_join_url(payload.get('join_url'))
        return {
            'server_name': server_name,
            'player_count': player_count,
            'max_players': max_players,
            'join_url': join_url,
        }

    def ingest(self, payload: object, *, origin: object) -> bool:
        if not self._origin_allowed(origin):
            return False
        normalized = self.normalize_payload(payload)
        if normalized is None:
            return False
        with self._lock:
            self._latest = normalized
            self._latest_at = time.monotonic()
        return True

    def latest(self) -> Optional[dict[str, Any]]:
        with self._lock:
            if self._latest is None or time.monotonic() - self._latest_at > self._ttl():
                return None
            raw = dict(self._latest)

        result: dict[str, Any] = {}
        if self._strict_bool(self.config, 'fivem.show_server_name', False):
            name = str(raw.get('server_name') or '')
            if name:
                result['server_name'] = name
        if self._strict_bool(self.config, 'fivem.show_player_count', True):
            result['player_count'] = int(raw.get('player_count', 0) or 0)
            result['max_players'] = int(raw.get('max_players', 0) or 0)
        if self._strict_bool(self.config, 'fivem.allow_join_button', False):
            join_url = str(raw.get('join_url') or '')
            if join_url:
                result['join_url'] = join_url
        return result

    def start(self) -> bool:
        if self._server is not None:
            return True
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'CYBREX-FiveM/1'

            def log_message(self, _format: str, *_args: object) -> None:
                return

            def _cors(self, origin: str) -> None:
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Vary', 'Origin')

            def do_OPTIONS(self) -> None:  # noqa: N802
                origin = str(self.headers.get('Origin') or '').strip().lower()
                if not bridge._origin_allowed(origin):
                    self.send_response(403)
                    self.end_headers()
                    return
                self.send_response(204)
                self._cors(origin)
                self.end_headers()

            def do_POST(self) -> None:  # noqa: N802
                origin = str(self.headers.get('Origin') or '').strip().lower()
                if self.path != '/presence' or not bridge._origin_allowed(origin):
                    self.send_response(403 if self.path == '/presence' else 404)
                    self.end_headers()
                    return
                try:
                    length = int(self.headers.get('Content-Length') or 0)
                except (TypeError, ValueError):
                    length = 0
                if length <= 0 or length > _MAX_BODY_BYTES:
                    self.send_response(413)
                    self.end_headers()
                    return
                try:
                    payload = json.loads(self.rfile.read(length).decode('utf-8'))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self.send_response(400)
                    self.end_headers()
                    return
                if not bridge.ingest(payload, origin=origin):
                    self.send_response(400)
                    self.end_headers()
                    return
                self.send_response(204)
                self._cors(origin)
                self.end_headers()

        try:
            server = ThreadingHTTPServer(('127.0.0.1', self._port()), Handler)
            server.daemon_threads = True
        except OSError as exc:
            _LOGGER.warning('FiveM companion bridge unavailable on loopback: %s', exc)
            return False
        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever,
            name='CYBREX-FiveM-Bridge',
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        server = self._server
        self._server = None
        if server is None:
            return
        try:
            server.shutdown()
            server.server_close()
        except OSError:
            pass
        thread = self._thread
        self._thread = None
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2.0)


_BRIDGE: Optional[FiveMBridge] = None
_BRIDGE_LOCK = threading.Lock()


def get_fivem_bridge(config: Config, *, start: bool = False) -> FiveMBridge:
    global _BRIDGE
    with _BRIDGE_LOCK:
        if _BRIDGE is None:
            _BRIDGE = FiveMBridge(config)
        else:
            _BRIDGE.config = config
        bridge = _BRIDGE
    if start:
        bridge.start()
    return bridge


def stop_fivem_bridge() -> None:
    global _BRIDGE
    with _BRIDGE_LOCK:
        bridge = _BRIDGE
        _BRIDGE = None
    if bridge is not None:
        bridge.stop()
