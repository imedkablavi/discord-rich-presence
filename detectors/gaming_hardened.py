"""Accuracy/privacy hardening layered on top of the stable game detector."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .gaming import GamingDetector as BaseGamingDetector
from warthunder_telemetry import WAR_THUNDER_STEAM_APPID, WarThunderTelemetryReader


class GamingDetector(BaseGamingDetector):
    """Game detector with strict launcher boundaries and safe deep telemetry."""

    WAR_THUNDER_PROCESSES = frozenset({"aces", "aces64"})

    def __init__(self, config):  # noqa: ANN001
        super().__init__(config)
        self.warthunder_telemetry = WarThunderTelemetryReader()

    def _strict_privacy(self) -> bool:
        return str(self.config.get("privacy.mode", "balanced") or "balanced").lower() == "strict"

    def _gsi_signature(self) -> tuple[bool, bool, bool, int, float]:
        gaming_enabled, gsi_enabled, auto_install, port, ttl = super()._gsi_signature()
        if self._strict_privacy():
            gsi_enabled = False
        return gaming_enabled, gsi_enabled, auto_install, port, ttl

    @staticmethod
    def _normalized_process(value: object) -> str:
        text = str(value or "").strip().lower().replace("\\", "/").rsplit("/", 1)[-1]
        return text[:-4] if text.endswith(".exe") else text

    @staticmethod
    def _is_minecraft_window(app_name: str, title: str) -> bool:
        app = GamingDetector._normalized_process(app_name)
        window = str(title or "").strip().lower()
        if app == "minecraft":
            return True
        if app == "minecraftlauncher":
            return False
        if app not in {"java", "javaw"}:
            return False
        return bool(re.match(r"^minecraft(?:\s|$|\*)", window))

    @staticmethod
    def _is_warthunder_activity(activity: Dict[str, Any]) -> bool:
        try:
            appid = int(activity.get("steam_appid", 0) or 0)
        except (TypeError, ValueError, OverflowError):
            appid = 0
        name = "".join(ch for ch in str(activity.get("game_name") or "").lower() if ch.isalnum())
        return appid == WAR_THUNDER_STEAM_APPID or name == "warthunder"

    def _enrich_league(self, activity: Dict[str, Any]) -> None:
        if self._strict_privacy():
            return
        super()._enrich_league(activity)

    def _enrich_fivem(self, activity: Dict[str, Any]) -> None:
        if self._strict_privacy():
            return
        super()._enrich_fivem(activity)

    def _enrich_minecraft(self, activity: Dict[str, Any]) -> None:
        if self._strict_privacy():
            return
        super()._enrich_minecraft(activity)

    def _enrich_cs2(self, activity: Dict[str, Any]) -> None:
        if self._strict_privacy():
            return
        super()._enrich_cs2(activity)

    def _enrich_warthunder(self, activity: Dict[str, Any]) -> None:
        if self._strict_privacy():
            return
        snapshot = self.warthunder_telemetry.snapshot()
        if not snapshot:
            return

        branch = str(snapshot.get("branch") or "").strip()
        vehicle = str(snapshot.get("vehicle") or "").strip()
        mission = str(snapshot.get("mission_status") or "").strip().lower()
        parts = [part for part in (branch, vehicle) if part]
        if mission == "running":
            parts.append("In Battle")
        elif mission == "loading":
            parts.append("Loading Battle")

        activity.update({
            "warthunder_local": True,
            "warthunder_branch": branch,
            "warthunder_vehicle": vehicle,
            "warthunder_mission_status": mission,
            "game_source": " · ".join(parts) or activity.get("game_source") or activity.get("launcher") or "War Thunder",
        })

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        app = self._normalized_process(window_info.get("app_name") if window_info else "")

        # MinecraftLauncher is a launcher, never evidence that Minecraft itself
        # is running. This exact boundary runs before legacy substring aliases.
        if app == "minecraftlauncher":
            if not window_info or not self.config.get("rules.enabled_detectors.gaming", False):
                return None
            return {
                "type": "gaming",
                "game_name": None,
                "launcher": "Minecraft Launcher",
                "is_game": False,
            }

        activity = super().detect(window_info)
        if activity and self._is_warthunder_activity(activity):
            activity["game_name"] = "War Thunder"
            self._enrich_warthunder(activity)
            return activity

        # Native/standalone and some Wayland sessions expose only the official
        # client process. Accept exact names only; never substring-match "aces".
        if activity is None and app in self.WAR_THUNDER_PROCESSES:
            activity = {
                "type": "gaming",
                "game_name": "War Thunder",
                "launcher": "War Thunder",
                "game_source": "War Thunder",
                "is_game": True,
            }
            self._enrich_warthunder(activity)
            return activity
        return activity
