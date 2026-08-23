"""Loopback bridge for the optional CYBREX Minecraft Fabric companion."""

from __future__ import annotations

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional

from config import Config


_LOGGER = logging.getLogger(__name__)
_DEFAULT_PORT = 32194
_MAX_BODY_BYTES = 8 * 1024
_MAX_TEXT = 128
_COMPANION_HEADER = 'minecraft-fabric-1'
_ALLOWED_MODES = {'Singleplayer', 'Multiplayer'}


class MinecraftBridge:
    """Receive a deliberately small Minecraft state snapshot over loopback."""

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
            port = int(self.config.get('minecraft.port', _DEFAULT_PORT) or _DEFAULT_PORT)
        except (TypeError, ValueError):
            return _DEFAULT_PORT
        return port if 1024 <= port <= 65535 else _DEFAULT_PORT

    def _ttl(self) -> float:
        try:
            ttl = float(self.config.get('minecraft.ttl_secs', 15) or 15)
        except (TypeError, ValueError):
            return 15.0
        return min(60.0, max(5.0, ttl))

    @staticmethod
    def _clean_text(value: object) -> str:
        text = str(value or '').replace('\x00', '').replace('\r', ' ').replace('\n', ' ').strip()
        return ' '.join(text.split())[:_MAX_TEXT]

    @classmethod
    def _clean_mode(cls, value: object) -> str:
        text = cls._clean_text(value).title()
        return text if text in _ALLOWED_MODES else ''

    @classmethod
    def _clean_dimension(cls, value: object) -> str:
        text = cls._clean_text(value).lower()
        # Dimension identifiers are resource locations such as minecraft:overworld.
        # Keep the grammar intentionally narrow and never accept paths/URLs.
        if not text or len(text) > 128:
            return ''
        allowed = set('abcdefghijklmnopqrstuvwxyz0123456789_.:-/')
        if any(char not in allowed for char in text):
            return ''
        if '://' in text or text.startswith('/') or '..' in text:
            return ''
        return text

    @classmethod
    def normalize_payload(cls, payload: object) -> Optional[dict[str, str]]:
        if not isinstance(payload, dict):
            return None
        mode = cls._clean_mode(payload.get('mode'))
        dimension = cls._clean_dimension(payload.get('dimension'))
        server_name = cls._clean_text(payload.get('server_name'))
        if not mode:
            return None
        return {
            'mode': mode,
            'dimension': dimension,
            'server_name': server_name,
        }

    def ingest(self, payload: object, *, companion_header: object) -> bool:
        if str(companion_header or '').strip().lower() != _COMPANION_HEADER:
            return False
        normalized = self.normalize_payload(payload)
        if normalized is None:
            return False
        with self._lock:
            self._latest = normalized
            self._latest_at = time.monotonic()
        return True

    def latest(self) -> Optional[dict[str, str]]:
        with self._lock:
            if self._latest is None or time.monotonic() - self._latest_at > self._ttl():
                return None
            raw = dict(self._latest)

        result = {
            'mode': str(raw.get('mode') or ''),
            'dimension': str(raw.get('dimension') or ''),
        }
        if self._strict_bool(self.config, 'minecraft.show_server_name', False):
            server_name = str(raw.get('server_name') or '')
            if server_name:
                result['server_name'] = server_name
        return result

    def start(self) -> bool:
        if self._server is not None:
            return True
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'CYBREX-Minecraft/1'

            def log_message(self, _format: str, *_args: object) -> None:
                return

            def do_POST(self) -> None:  # noqa: N802
                if self.path != '/presence':
                    self.send_response(404)
                    self.end_headers()
                    return
                header = self.headers.get('X-CYBREX-Companion')
                if str(header or '').strip().lower() != _COMPANION_HEADER:
                    self.send_response(403)
                    self.end_headers()
                    return
                content_type = str(self.headers.get('Content-Type') or '').split(';', 1)[0].strip().lower()
                if content_type != 'application/json':
                    self.send_response(415)
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
                if not bridge.ingest(payload, companion_header=header):
                    self.send_response(400)
                    self.end_headers()
                    return
                self.send_response(204)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()

        try:
            server = ThreadingHTTPServer(('127.0.0.1', self._port()), Handler)
            server.daemon_threads = True
        except OSError as exc:
            _LOGGER.warning('Minecraft companion bridge unavailable on loopback: %s', exc)
            return False
        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever,
            name='CYBREX-Minecraft-Bridge',
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


_BRIDGE: Optional[MinecraftBridge] = None
_BRIDGE_LOCK = threading.Lock()


def get_minecraft_bridge(config: Config, *, start: bool = False) -> MinecraftBridge:
    global _BRIDGE
    with _BRIDGE_LOCK:
        if _BRIDGE is None:
            _BRIDGE = MinecraftBridge(config)
        else:
            _BRIDGE.config = config
        bridge = _BRIDGE
    if start:
        bridge.start()
    return bridge


def stop_minecraft_bridge() -> None:
    global _BRIDGE
    with _BRIDGE_LOCK:
        bridge = _BRIDGE
        _BRIDGE = None
    if bridge is not None:
        bridge.stop()
