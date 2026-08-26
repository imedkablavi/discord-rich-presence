"""Bounded, read-only War Thunder local telemetry for Rich Presence.

War Thunder exposes a game-local HTTP service on 127.0.0.1:8111 while it is
running. CYBREX intentionally reads only the minimal high-confidence endpoints
needed for Presence and never consumes tactical objects, chat, damage events or
other player-sensitive data.
"""

from __future__ import annotations

import http.client
import json
import re
import time
from typing import Any, Optional


WAR_THUNDER_STEAM_APPID = 236390
_HOST = "127.0.0.1"
_PORT = 8111
_TIMEOUT_SECS = 0.45
_CACHE_SECONDS = 3.0
_MAX_JSON_BYTES = 64 * 1024
_MAX_TEXT = 96

_BRANCHES = {
    "tank": "Ground",
    "ground": "Ground",
    "air": "Air",
    "aircraft": "Air",
    "plane": "Air",
    "aviation": "Air",
    "ship": "Naval",
    "naval": "Naval",
    "boat": "Naval",
    "helicopter": "Helicopter",
    "heli": "Helicopter",
}

_COUNTRY_PREFIXES = {
    "ussr", "usa", "us", "uk", "germ", "germany", "ger", "jp", "japan",
    "fr", "france", "it", "italy", "cn", "china", "sw", "sweden", "il",
    "israel",
}


def _clean_text(value: object, maximum: int = _MAX_TEXT) -> str:
    text = str(value or "").replace("\x00", " ").replace("\r", " ").replace("\n", " ")
    return " ".join(text.split())[:maximum]


def _friendly_vehicle(raw: object) -> tuple[str, str]:
    """Return a conservative display label plus bounded internal model id."""
    value = _clean_text(raw, 160).replace("\\", "/")
    if not value:
        return "", ""
    model_id = value.rsplit("/", 1)[-1][:96]
    tokens = [token for token in re.split(r"[_\-]+", model_id) if token]
    if tokens and tokens[0].lower() in _COUNTRY_PREFIXES:
        tokens = tokens[1:]
    if not tokens:
        return "", model_id

    display_parts: list[str] = []
    for token in tokens[:10]:
        if token.isdigit():
            display_parts.append(token)
            continue
        upper = token.upper()
        if len(token) <= 4 and any(ch.isdigit() for ch in token):
            display_parts.append(upper)
        elif token.lower() in {"mk", "f", "bf", "fw", "mig", "su", "yak", "t", "m", "p", "a"}:
            display_parts.append(upper)
        else:
            display_parts.append(token.upper() if len(token) <= 3 else token.capitalize())
    return " ".join(display_parts)[:80], model_id


def _branch_label(raw: object, vehicle_id: str) -> str:
    key = _clean_text(raw, 32).lower()
    if key in _BRANCHES:
        return _BRANCHES[key]
    lowered = vehicle_id.lower()
    if lowered.startswith(("tank", "ussr_t_", "us_m", "germ_")):
        return "Ground"
    if any(marker in lowered for marker in ("ship", "boat", "destroyer", "cruiser")):
        return "Naval"
    if any(marker in lowered for marker in ("heli", "helicopter")):
        return "Helicopter"
    return "Air" if vehicle_id else ""


def _request_json(path: str) -> Optional[dict[str, Any]]:
    """Read one fixed loopback endpoint with strict size/time bounds."""
    if path not in {"/indicators", "/mission.json"}:
        return None
    connection = http.client.HTTPConnection(_HOST, _PORT, timeout=_TIMEOUT_SECS)
    try:
        connection.request(
            "GET",
            path,
            headers={
                "Accept": "application/json",
                "Connection": "close",
                "User-Agent": "CYBREX-Presence/WarThunder",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            return None
        raw = response.read(_MAX_JSON_BYTES + 1)
        if len(raw) > _MAX_JSON_BYTES:
            return None
        try:
            payload = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None
    except (OSError, TimeoutError, http.client.HTTPException):
        return None
    finally:
        try:
            connection.close()
        except OSError:
            pass


def read_warthunder_snapshot() -> dict[str, Any]:
    indicators = _request_json("/indicators")
    if not indicators or indicators.get("valid") is not True:
        return {}

    vehicle, vehicle_id = _friendly_vehicle(indicators.get("type"))
    branch = _branch_label(indicators.get("army"), vehicle_id)
    if not vehicle_id and not branch:
        return {}

    result: dict[str, Any] = {"warthunder_telemetry": True}
    if branch:
        result["branch"] = branch
    if vehicle:
        result["vehicle"] = vehicle
    if vehicle_id:
        result["vehicle_id"] = vehicle_id

    mission = _request_json("/mission.json") or {}
    status = _clean_text(mission.get("status"), 32).lower()
    if status in {"running", "active", "started", "in_progress", "in progress"}:
        result["mission_status"] = "running"
    elif status in {"briefing", "loading", "preparing"}:
        result["mission_status"] = "loading"
    return result


class WarThunderTelemetryReader:
    """Small cache so the 2-second main loop never hammers port 8111."""

    def __init__(self) -> None:
        self._cache_until = 0.0
        self._cache: dict[str, Any] = {}

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        if now < self._cache_until:
            return dict(self._cache)
        self._cache = read_warthunder_snapshot()
        self._cache_until = now + _CACHE_SECONDS
        return dict(self._cache)
