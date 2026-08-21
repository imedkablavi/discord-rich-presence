"""Counter-Strike 2 Game State Integration listener and installer.

The integration is deliberately read-only. CS2 sends a small, explicitly
requested subset of game state to a loopback HTTP endpoint. The bridge stores
only the fields needed for Rich Presence and discards the raw payload.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import platform
import re
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from config import Config


LOGGER = logging.getLogger(__name__)
_MAX_BODY_BYTES = 64 * 1024
_CLIENT_TIMEOUT_SECS = 3.0
_DEFAULT_PORT = 32192
_DEFAULT_TTL_SECS = 30.0
_APP_ID = 730
_TOKEN_PATTERN = re.compile(r'^[A-Za-z0-9_-]{32,128}$')


class _CS2HTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 8
    block_on_close = False


class CS2GSIBridge:
    """Receive authenticated CS2 GSI payloads on IPv4 loopback only."""

    def __init__(self, config: Config):
        self.config = config
        self.host = '127.0.0.1'
        self.port = _configured_port(config)
        self.ttl_secs = _configured_ttl(config)
        self.token_path = Path(config.config_path).parent / 'cs2_gsi_token'
        self.token = _load_or_create_token(self.token_path)
        self._snapshot: Optional[Dict[str, Any]] = None
        self._seen_at = 0.0
        self._lock = threading.RLock()
        self._server: Optional[_CS2HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        if self._server is not None:
            return True
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'CYBREXCS2GSI/1'

            def setup(self) -> None:
                super().setup()
                try:
                    self.connection.settimeout(_CLIENT_TIMEOUT_SECS)
                except OSError:
                    pass

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                LOGGER.debug('CS2 GSI: ' + format, *args)

            def _send(self, status: int, payload: Dict[str, Any]) -> None:
                body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
                try:
                    self.send_response(status)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError, socket.timeout, OSError):
                    return

            def do_GET(self) -> None:  # noqa: N802
                if self.path == '/v1/health':
                    self._send(200, {'ok': True, 'integration': 'cs2-gsi'})
                    return
                if self.path == '/v1/status':
                    self._send(200, bridge.status())
                    return
                self._send(404, {'ok': False})

            def do_POST(self) -> None:  # noqa: N802
                if self.path not in {'/', '/v1/cs2'}:
                    self._send(404, {'ok': False})
                    return
                content_type = (self.headers.get('Content-Type') or '').split(';', 1)[0].strip().lower()
                if content_type and content_type != 'application/json':
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
                except PermissionError:
                    self._send(403, {'ok': False, 'error': 'invalid_auth'})
                    return
                except ValueError as exc:
                    self._send(400, {'ok': False, 'error': str(exc)[:100]})
                    return
                self._send(200, {'ok': True})

        try:
            server = _CS2HTTPServer((self.host, self.port), Handler)
            self.port = int(server.server_address[1])
            thread = threading.Thread(
                target=server.serve_forever,
                name='cs2-gsi',
                daemon=True,
            )
            self._server = server
            self._thread = thread
            thread.start()
            LOGGER.info('CS2 GSI listening on http://%s:%d/v1/cs2', self.host, self.port)
            return True
        except OSError as exc:
            self._server = None
            self._thread = None
            LOGGER.warning('CS2 GSI could not bind %s:%d: %s', self.host, self.port, exc)
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
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._snapshot = None
            self._seen_at = 0.0

    def update(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ValueError('payload_must_be_object')
        auth = payload.get('auth') if isinstance(payload.get('auth'), dict) else {}
        supplied = str(auth.get('token', '') or '')
        if not supplied or not hmac.compare_digest(supplied, self.token):
            raise PermissionError('invalid_auth')

        provider = payload.get('provider') if isinstance(payload.get('provider'), dict) else {}
        appid = _clean_int(provider.get('appid'), maximum=10_000_000)
        # The generated integration always requests provider metadata. Requiring
        # appid 730 prevents an authenticated stale/misrouted Valve payload from
        # being interpreted as Counter-Strike 2 state.
        if appid != _APP_ID:
            raise ValueError('unexpected_appid')

        game_map = payload.get('map') if isinstance(payload.get('map'), dict) else {}
        player = payload.get('player') if isinstance(payload.get('player'), dict) else {}
        round_info = payload.get('round') if isinstance(payload.get('round'), dict) else {}
        countdown = payload.get('phase_countdowns') if isinstance(payload.get('phase_countdowns'), dict) else {}
        team_ct = game_map.get('team_ct') if isinstance(game_map.get('team_ct'), dict) else {}
        team_t = game_map.get('team_t') if isinstance(game_map.get('team_t'), dict) else {}

        # Never retain Steam IDs, player names, positions, weapons, health or the
        # rest of the raw GSI document. Rich Presence only needs these fields.
        snapshot = {
            'map': _clean_text(game_map.get('name'), 80),
            'mode': _clean_text(game_map.get('mode'), 48),
            'map_phase': _clean_text(game_map.get('phase'), 32),
            'round': _clean_int(game_map.get('round'), maximum=200),
            'round_phase': _clean_text(round_info.get('phase'), 32),
            'countdown_phase': _clean_text(countdown.get('phase'), 32),
            'team': _clean_team(player.get('team')),
            'player_activity': _clean_text(player.get('activity'), 24),
            'ct_score': _clean_int(team_ct.get('score'), maximum=99),
            't_score': _clean_int(team_t.get('score'), maximum=99),
        }
        with self._lock:
            self._snapshot = snapshot
            self._seen_at = time.monotonic()

    def latest(self) -> Optional[Dict[str, Any]]:
        now = time.monotonic()
        with self._lock:
            if not self._snapshot or now - self._seen_at > self.ttl_secs:
                self._snapshot = None
                self._seen_at = 0.0
                return None
            return dict(self._snapshot)

    def status(self) -> Dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            active = bool(self._snapshot and now - self._seen_at <= self.ttl_secs)
            snapshot = self._snapshot if active else None
            return {
                'ok': True,
                'connected': active,
                'age_ms': max(0, int((now - self._seen_at) * 1000)) if active else None,
                'map': (snapshot or {}).get('map') or '',
                'mode': (snapshot or {}).get('mode') or '',
                'team': (snapshot or {}).get('team') or '',
            }


def _configured_port(config: Config) -> int:
    try:
        value = int(config.get('cs2_gsi.port', _DEFAULT_PORT) or _DEFAULT_PORT)
    except (TypeError, ValueError):
        return _DEFAULT_PORT
    return value if 1024 <= value <= 65535 else _DEFAULT_PORT


def _configured_ttl(config: Config) -> float:
    try:
        value = float(config.get('cs2_gsi.ttl_secs', _DEFAULT_TTL_SECS) or _DEFAULT_TTL_SECS)
    except (TypeError, ValueError):
        return _DEFAULT_TTL_SECS
    return value if 5.0 <= value <= 300.0 else _DEFAULT_TTL_SECS


def _clean_text(value: Any, limit: int) -> str:
    text = str(value or '').replace('\x00', '').strip()
    text = re.sub(r'[\x01-\x1f\x7f]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()[:limit]


def _clean_int(value: Any, *, maximum: int) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, maximum))


def _clean_team(value: Any) -> str:
    team = str(value or '').strip().upper()
    return team if team in {'CT', 'T'} else ''


def _load_or_create_token(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == 'posix':
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
    try:
        token = path.read_text(encoding='utf-8').strip()
    except OSError:
        token = ''
    if _TOKEN_PATTERN.fullmatch(token):
        if os.name == 'posix':
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        return token

    token = secrets.token_urlsafe(32)
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write(token + '\n')
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    if os.name == 'posix':
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return token


def _windows_registry_steam_roots() -> Iterable[Path]:
    if platform.system().lower() != 'windows':
        return []
    try:
        import winreg
    except ImportError:
        return []

    roots: list[Path] = []
    locations = (
        (winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam'),
    )
    for hive, key_name in locations:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                for value_name in ('SteamPath', 'InstallPath'):
                    try:
                        raw, _ = winreg.QueryValueEx(key, value_name)
                    except OSError:
                        continue
                    if raw:
                        roots.append(Path(str(raw)))
                        break
        except OSError:
            continue
    return roots


def _steam_roots() -> Iterable[Path]:
    system = platform.system().lower()
    roots: list[Path] = []
    if system == 'windows':
        steam_env = os.environ.get('STEAM_PATH')
        if steam_env:
            roots.append(Path(steam_env))
        roots.extend(_windows_registry_steam_roots())
        for env_name in ('PROGRAMFILES(X86)', 'PROGRAMFILES'):
            base = os.environ.get(env_name)
            if base:
                roots.append(Path(base) / 'Steam')
    else:
        home = Path.home()
        roots.extend((
            home / '.local/share/Steam',
            home / '.steam/steam',
            home / '.var/app/com.valvesoftware.Steam/.local/share/Steam',
        ))

    seen: set[str] = set()
    for root in roots:
        try:
            normalized = root.expanduser()
        except (TypeError, ValueError):
            continue
        key = os.path.normcase(str(normalized))
        if key not in seen:
            seen.add(key)
            yield normalized


def _library_roots() -> Iterable[Path]:
    seen: set[str] = set()
    queue = list(_steam_roots())
    for steam_root in queue:
        candidates = [steam_root]
        library_file = steam_root / 'steamapps/libraryfolders.vdf'
        try:
            text = library_file.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            text = ''
        for match in re.finditer(r'"path"\s+"([^"]+)"', text, re.IGNORECASE):
            raw = match.group(1).replace('\\\\', '\\')
            candidates.append(Path(raw))
        for candidate in candidates:
            key = os.path.normcase(str(candidate))
            if key not in seen:
                seen.add(key)
                yield candidate


def discover_cs2_cfg_dirs() -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    for library in _library_roots():
        cfg = library / 'steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg'
        if cfg.is_dir():
            key = os.path.normcase(str(cfg.resolve()))
            if key not in seen:
                seen.add(key)
                found.append(cfg)
    return found


def render_gsi_config(port: int, token: str) -> str:
    """Render a least-data CS2 GSI configuration."""
    if not _TOKEN_PATTERN.fullmatch(str(token or '')):
        raise ValueError('Invalid CS2 GSI authentication token')
    port = int(port)
    if port < 1024 or port > 65535:
        raise ValueError('CS2 GSI port must be between 1024 and 65535')
    return f'''"CYBREX Discord Rich Presence"
{{
    "uri" "http://127.0.0.1:{port}/v1/cs2"
    "timeout" "5.0"
    "buffer" "0.1"
    "throttle" "0.2"
    "heartbeat" "10.0"
    "auth"
    {{
        "token" "{token}"
    }}
    "data"
    {{
        "provider" "1"
        "map" "1"
        "round" "1"
        "player_id" "1"
        "phase_countdowns" "1"
    }}
}}
'''


def install_gsi_config(config: Config, cfg_dir: Optional[Path] = None) -> Path:
    """Install the authenticated GSI cfg into an existing CS2 installation."""
    if cfg_dir is None:
        locations = discover_cs2_cfg_dirs()
        if not locations:
            raise FileNotFoundError(
                'Counter-Strike 2 cfg directory was not found automatically; '
                'provide the game/csgo/cfg directory explicitly'
            )
        cfg_dir = locations[0]
    cfg_dir = Path(cfg_dir).expanduser().resolve()
    if not cfg_dir.is_dir():
        raise FileNotFoundError(f'CS2 cfg directory does not exist: {cfg_dir}')

    token_path = Path(config.config_path).parent / 'cs2_gsi_token'
    token = _load_or_create_token(token_path)
    port = _configured_port(config)
    target = cfg_dir / 'gamestate_integration_cybrex.cfg'
    content = render_gsi_config(port, token)

    # Avoid changing the game config mtime on every service start when the
    # integration is already correct. On POSIX, keep the token-bearing cfg
    # private even if an older release created it with a permissive umask.
    try:
        if target.read_text(encoding='utf-8') == content:
            if os.name == 'posix':
                try:
                    os.chmod(target, 0o600)
                except OSError:
                    pass
            return target
    except OSError:
        pass

    tmp = target.with_name(f'.{target.name}.{os.getpid()}.tmp')
    fd = os.open(tmp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(content)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        if os.name == 'posix':
            try:
                os.chmod(tmp, 0o600)
            except OSError:
                pass
        os.replace(tmp, target)
        if os.name == 'posix':
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return target


_BRIDGES: Dict[int, CS2GSIBridge] = {}
_BRIDGES_LOCK = threading.Lock()


def get_cs2_gsi(config: Config, start: bool = True) -> Optional[CS2GSIBridge]:
    if not bool(config.get('cs2_gsi.enabled', True)):
        return None
    port = _configured_port(config)
    with _BRIDGES_LOCK:
        bridge = _BRIDGES.get(port)
        if bridge is None:
            bridge = CS2GSIBridge(config)
            _BRIDGES[port] = bridge
    if start:
        bridge.start()
    return bridge


def stop_cs2_gsi() -> None:
    with _BRIDGES_LOCK:
        bridges = list(_BRIDGES.values())
        _BRIDGES.clear()
    for bridge in bridges:
        try:
            bridge.stop()
        except Exception as exc:
            LOGGER.debug('Could not stop CS2 GSI cleanly: %s', exc)
