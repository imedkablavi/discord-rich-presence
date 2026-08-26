"""Read-only local Squad activity enrichment.

Squad does not expose a stable unauthenticated player API for the current client
session.  This module therefore reads only the game's own local log and returns
high-confidence, non-sensitive match metadata.  It never injects into the game,
reads game memory, captures packets, authenticates to EOS, or uses RCON.
"""

from __future__ import annotations

import os
import platform
import re
import time
from pathlib import Path
from typing import Any, Iterable, Optional


SQUAD_STEAM_APPID = 393380
_MAX_LOG_TAIL_BYTES = 2 * 1024 * 1024
_CACHE_SECONDS = 1.5
_MAX_TEXT = 120

_LAYER_PATTERNS = (
    re.compile(r"(?im)StartLoadingDestination\s+to:\s*([^\r\n?]+)"),
    re.compile(r"(?im)\b(?:CurrentLayer|LayerName|Layer)_(?:s|str)\s*[=:]\s*[\"']?([^\"'\r\n,}]+)"),
    re.compile(r"(?im)\b(?:CurrentLayer|LayerName)\s*[=:]\s*[\"']?([^\"'\r\n,}]+)"),
)
_SERVER_PATTERNS = (
    re.compile(r"(?im)\b(?:ServerName|SERVERNAME|SessionName|SESSIONNAME)_(?:s|str)\s*[=:]\s*[\"']([^\"'\r\n]{2,120})"),
    re.compile(r"(?im)\b(?:ServerName|SERVERNAME)\s*[=:]\s*[\"']([^\"'\r\n]{2,120})"),
)
_PLAYER_PATTERNS = (
    re.compile(r"(?im)\b(?:PlayerCount|PLAYERS|NumPlayers)_(?:l|i|int)\s*[=:]\s*(\d{1,3})\b"),
    re.compile(r"(?im)\b(?:PlayerCount|NumPlayers)\s*[=:]\s*(\d{1,3})\b"),
)
_MAX_PLAYER_PATTERNS = (
    re.compile(r"(?im)\b(?:MaxPlayers|MAXPLAYERS)_(?:l|i|int)\s*[=:]\s*(\d{1,3})\b"),
    re.compile(r"(?im)\bMaxPlayers\s*[=:]\s*(\d{1,3})\b"),
)
_QUEUE_PATTERNS = (
    re.compile(r"(?im)\b(?:Queue|QueueCount|PublicQueue)_(?:l|i|int)\s*[=:]\s*(\d{1,3})\b"),
    re.compile(r"(?im)\b(?:Queue|QueueCount)\s*[=:]\s*(\d{1,3})\b"),
)
_GAME_MODE_PATTERNS = (
    re.compile(r"(?im)\b(?:GameMode|GAMEMODE)_(?:s|str)\s*[=:]\s*[\"']?([^\"'\r\n,}]+)"),
    re.compile(r"(?im)\bGameMode\s*[=:]\s*[\"']?([^\"'\r\n,}]+)"),
)
_MAP_PATTERNS = (
    re.compile(r"(?im)\b(?:MapName|MAPNAME)_(?:s|str)\s*[=:]\s*[\"']?([^\"'\r\n,}]+)"),
    re.compile(r"(?im)\bMapName\s*[=:]\s*[\"']?([^\"'\r\n,}]+)"),
)

# Session markers are deliberately narrow.  Server browser search results can
# contain many server names; we only publish a server name when the tail also
# contains evidence that the local client is joining/connected/loading a match.
_SESSION_MARKERS = (
    "joinsession",
    "startloadingdestination to:",
    "connected to server",
    "welcomed by server",
    "pendingnetgame",
    "clienttravel",
)
_DISCONNECT_MARKERS = (
    "disconnecting from server",
    "disconnected from server",
    "connection lost",
    "network failure",
    "return to main menu",
)
_MENU_MARKERS = (
    "/game/maps/entry",
    "/game/_main/maps/mainmenu",
    "/game/maps/mainmenu",
)

_MODE_ALIASES = (
    ("territorycontrol", "Territory Control"),
    ("territory_control", "Territory Control"),
    ("insurgency", "Insurgency"),
    ("destruction", "Destruction"),
    ("invasion", "Invasion"),
    ("skirmish", "Skirmish"),
    ("training", "Training"),
    ("jensensrange", "Training"),
    ("jensen", "Training"),
    ("seed", "Seeding"),
    ("raas", "RAAS"),
    ("aas", "AAS"),
    ("tc", "Territory Control"),
)

# Common internal map spellings. Unknown maps are still converted safely by the
# generic CamelCase/underscore formatter, so this list does not age-gate support.
_MAP_ALIASES = {
    "albasrah": "Al Basrah",
    "anvil": "Anvil",
    "belaya": "Belaya",
    "blackcoast": "Black Coast",
    "chora": "Chora",
    "fallujah": "Fallujah",
    "foolsroad": "Fool's Road",
    "gorodok": "Gorodok",
    "harju": "Harju",
    "jensensrange": "Jensen's Range",
    "kamdesh": "Kamdesh Highlands",
    "kohat": "Kohat Toi",
    "kokan": "Kokan",
    "lashkar": "Lashkar Valley",
    "logar": "Logar Valley",
    "manic": "Manicouagan",
    "mestia": "Mestia",
    "mutaha": "Mutaha",
    "narva": "Narva",
    "pacificprovinggrounds": "Pacific Proving Grounds",
    "sanxian": "Sanxian Islands",
    "sanxianislands": "Sanxian Islands",
    "skorpo": "Skorpo",
    "sumari": "Sumari Bala",
    "tallil": "Tallil Outskirts",
    "talliloutskirts": "Tallil Outskirts",
    "yehorivka": "Yehorivka",
}


def _clean_text(value: object, limit: int = _MAX_TEXT) -> str:
    text = str(value or "").replace("\x00", " ").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split()).strip(" \"'[]{}")
    return text[:limit]


def _last_match(patterns: Iterable[re.Pattern[str]], text: str) -> tuple[int, str]:
    best_pos = -1
    best_value = ""
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = _clean_text(match.group(1))
            if value and match.start() >= best_pos:
                best_pos = match.start()
                best_value = value
    return best_pos, best_value


def _last_marker(text_lower: str, markers: Iterable[str]) -> int:
    return max((text_lower.rfind(marker) for marker in markers), default=-1)


def _basename_from_destination(value: str) -> str:
    raw = _clean_text(value, 180).split("?", 1)[0].rstrip("/")
    if not raw:
        return ""
    leaf = raw.rsplit("/", 1)[-1]
    if "." in leaf:
        leaf = leaf.split(".", 1)[0]
    return leaf.strip()


def _friendly_words(value: str) -> str:
    raw = _clean_text(value).replace("-", "_")
    if not raw:
        return ""
    raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw)
    raw = raw.replace("_", " ")
    return " ".join(raw.split()).title()[:_MAX_TEXT]


def _mode_from_layer(layer: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "", layer.lower())
    for token, label in _MODE_ALIASES:
        if token in lowered:
            return label
    return ""


def _map_from_layer(layer: str) -> str:
    leaf = _basename_from_destination(layer)
    if not leaf:
        return ""

    # Strip common layer/version suffixes such as Yehorivka_RAAS_v2.
    lowered = leaf.lower()
    split_at = len(leaf)
    for marker in (
        "_raas", "_aas", "_invasion", "_seed", "_skirmish", "_tc",
        "_territorycontrol", "_insurgency", "_destruction", "_training",
    ):
        pos = lowered.find(marker)
        if pos > 0:
            split_at = min(split_at, pos)
    candidate = leaf[:split_at]
    key = re.sub(r"[^a-z0-9]+", "", candidate.lower())
    if key in _MAP_ALIASES:
        return _MAP_ALIASES[key]
    return _friendly_words(candidate)


def _bounded_count(value: str) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if 0 <= parsed <= 256 else None


def parse_squad_log_tail(text: str) -> dict[str, Any]:
    """Parse recent Squad client-log text into a fail-closed activity snapshot."""
    if not isinstance(text, str) or not text:
        return {}

    # Keep parser work bounded even when tests/callers pass a large decoded file.
    if len(text.encode("utf-8", errors="ignore")) > _MAX_LOG_TAIL_BYTES:
        text = text[-_MAX_LOG_TAIL_BYTES:]
    lower = text.lower()

    layer_pos, raw_layer = _last_match(_LAYER_PATTERNS, text)
    session_pos = _last_marker(lower, _SESSION_MARKERS)
    disconnect_pos = _last_marker(lower, _DISCONNECT_MARKERS)
    menu_pos = _last_marker(lower, _MENU_MARKERS)

    # A disconnect/main-menu event newer than the last match destination invalidates
    # previous telemetry so Presence cannot show a stale server/map in the menu.
    latest_match_evidence = max(layer_pos, session_pos)
    if latest_match_evidence < 0 or max(disconnect_pos, menu_pos) > latest_match_evidence:
        return {}

    layer = _basename_from_destination(raw_layer)
    if layer.lower() in {"entry", "mainmenu", "transition", "transitionmap"}:
        layer = ""

    map_pos, raw_map = _last_match(_MAP_PATTERNS, text)
    mode_pos, raw_mode = _last_match(_GAME_MODE_PATTERNS, text)
    map_name = _clean_text(raw_map) if map_pos >= layer_pos and raw_map else _map_from_layer(layer)
    mode = _clean_text(raw_mode) if mode_pos >= layer_pos and raw_mode else _mode_from_layer(layer)
    if map_name:
        map_name = _MAP_ALIASES.get(re.sub(r"[^a-z0-9]+", "", map_name.lower()), _friendly_words(map_name))

    result: dict[str, Any] = {"squad_telemetry": True}
    if layer:
        result["layer"] = layer
    if map_name:
        result["map"] = map_name
    if mode:
        result["mode"] = mode

    # Only consider server/session fields in a bounded neighborhood around the
    # latest join/loading evidence. This rejects unrelated server-browser rows.
    if session_pos >= 0:
        left = max(0, session_pos - 96 * 1024)
        right = min(len(text), max(session_pos, layer_pos) + 96 * 1024)
        session_text = text[left:right]
        _server_pos, server_name = _last_match(_SERVER_PATTERNS, session_text)
        if server_name and not re.search(r"(?i)browser|search result|session search", server_name):
            result["server_name"] = server_name

        _player_pos, raw_players = _last_match(_PLAYER_PATTERNS, session_text)
        _max_pos, raw_max = _last_match(_MAX_PLAYER_PATTERNS, session_text)
        _queue_pos, raw_queue = _last_match(_QUEUE_PATTERNS, session_text)
        players = _bounded_count(raw_players)
        maximum = _bounded_count(raw_max)
        queue = _bounded_count(raw_queue)
        if players is not None:
            result["player_count"] = players
        if maximum is not None and maximum > 0:
            result["max_players"] = maximum
        if queue is not None:
            result["queue"] = queue

    return result if len(result) > 1 else {}


def _windows_log_paths() -> Iterable[Path]:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        yield Path(local) / "SquadGame" / "Saved" / "Logs" / "SquadGame.log"


def _linux_steam_roots() -> Iterable[Path]:
    home = Path.home()
    roots = [
        home / ".local/share/Steam",
        home / ".steam/steam",
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    steam_env = os.environ.get("STEAM_PATH")
    if steam_env:
        roots.insert(0, Path(steam_env))
    seen: set[str] = set()
    for root in roots:
        key = os.path.normcase(str(root.expanduser()))
        if key not in seen:
            seen.add(key)
            yield root.expanduser()


def _proton_logs_from_steamapps(steamapps: Path) -> Iterable[Path]:
    users = steamapps / "compatdata" / str(SQUAD_STEAM_APPID) / "pfx" / "drive_c" / "users"
    try:
        candidates = list(users.iterdir())[:16]
    except OSError:
        return
    for user_dir in candidates:
        yield user_dir / "AppData" / "Local" / "SquadGame" / "Saved" / "Logs" / "SquadGame.log"


def discover_squad_log_paths(steam_game: object | None = None) -> tuple[Path, ...]:
    """Return plausible local Squad client log paths without scanning the machine."""
    paths: list[Path] = []
    if platform.system().lower() == "windows":
        paths.extend(_windows_log_paths())
    else:
        install_path = getattr(steam_game, "install_path", None)
        if install_path:
            try:
                steamapps = Path(install_path).resolve(strict=False).parent.parent
                paths.extend(_proton_logs_from_steamapps(steamapps))
            except (OSError, RuntimeError, ValueError):
                pass
        for root in _linux_steam_roots():
            paths.extend(_proton_logs_from_steamapps(root / "steamapps"))

    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = os.path.normcase(os.path.abspath(str(path)))
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return tuple(unique)


def _read_tail(path: Path) -> str:
    try:
        size = path.stat().st_size
        if size <= 0:
            return ""
        with path.open("rb") as handle:
            if size > _MAX_LOG_TAIL_BYTES:
                handle.seek(size - _MAX_LOG_TAIL_BYTES)
                handle.readline()  # drop a partial first line
            raw = handle.read(_MAX_LOG_TAIL_BYTES)
    except OSError:
        return ""
    return raw.decode("utf-8", errors="ignore")


class SquadTelemetryReader:
    """Small cached reader used only while Squad is the foreground game."""

    def __init__(self) -> None:
        self._cache_until = 0.0
        self._cache_key: tuple[str, int, int] | None = None
        self._cache_value: dict[str, Any] = {}

    def snapshot(self, steam_game: object | None = None) -> dict[str, Any]:
        now = time.monotonic()
        for path in discover_squad_log_paths(steam_game):
            try:
                stat = path.stat()
            except OSError:
                continue
            key = (str(path), int(stat.st_mtime_ns), int(stat.st_size))
            if now < self._cache_until and key == self._cache_key:
                return dict(self._cache_value)
            value = parse_squad_log_tail(_read_tail(path))
            self._cache_key = key
            self._cache_value = value
            self._cache_until = now + _CACHE_SECONDS
            return dict(value)
        self._cache_key = None
        self._cache_value = {}
        self._cache_until = now + _CACHE_SECONDS
        return {}
