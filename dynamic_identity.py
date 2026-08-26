"""Dynamic activity-name routing for Discord Social SDK with legacy fallback."""

from __future__ import annotations

from typing import Any, Dict

from pypresence import DiscordNotFound, InvalidID, InvalidPipe, Presence as LegacyPresence

from rpc_contract import sanitize_rpc_payload
from social_sdk_transport import SocialSDKError, SocialSDKPresence, social_sdk_available


_PATCHED = False


def _transport_mode(config) -> str:  # noqa: ANN001
    value = str(config.get("discord.transport", "auto") or "auto").strip().lower()
    return value if value in {"auto", "legacy", "social_sdk"} else "auto"


def activity_display_name(activity: Dict[str, Any]) -> str:
    """Return the actual foreground program/game identity for Discord's top line."""
    if not isinstance(activity, dict):
        return "CYBREX Activity"
    kind = str(activity.get("type") or "application").strip().lower()

    if kind == "gaming":
        value = activity.get("game_name") or activity.get("launcher") or "Game"
    elif kind == "coding":
        value = activity.get("editor") or "Code Editor"
    elif kind == "browser":
        value = activity.get("browser_name") or "Browser"
    elif kind == "media":
        value = activity.get("player") or activity.get("service") or "Media Player"
    elif kind == "terminal":
        value = activity.get("terminal_name") or activity.get("shell") or "Terminal"
    else:
        value = activity.get("app_name") or "Application"

    text = str(value or "CYBREX Activity").strip()
    friendly = {
        "org.kde.konsole": "Konsole",
        "org.kde.dolphin": "Dolphin",
        "org.kde.kate": "Kate",
        "org.kde.okular": "Okular",
        "org.kde.discover": "Discover",
        "org.kde.systemsettings": "System Settings",
        "code": "Visual Studio Code",
        "code oss": "VS Code OSS",
        "msedge": "Microsoft Edge",
        "google chrome": "Google Chrome",
    }
    mapped = friendly.get(text.lower())
    if mapped:
        return mapped[:128]
    if text.lower().startswith(("org.", "com.", "io.", "net.")) and "." in text:
        text = text.rsplit(".", 1)[-1]
    # Preserve punctuation in real product names (Counter-Strike, Battle.net,
    # etc.). Only normalize the common underscore process-name separator.
    text = text.replace("_", " ").strip()
    if text and text.islower():
        text = text.title()
    return (text or "CYBREX Activity")[:128]


def apply_dynamic_identity(service_cls, presence_builder_cls) -> None:  # noqa: ANN001
    """Patch current service classes without changing the legacy payload contract."""
    global _PATCHED
    if _PATCHED or getattr(service_cls, "_cybrex_dynamic_identity", False):
        return

    original_service_init = service_cls.__init__
    original_update_presence = service_cls.update_presence
    original_clear_presence = service_cls.clear_presence
    original_disconnect = service_cls.disconnect_discord
    original_builder_build = presence_builder_cls.build

    def service_init(self, *args, **kwargs):
        original_service_init(self, *args, **kwargs)
        self.rpc_transport = "legacy_rpc"
        self.current_activity_name = None

    def builder_build(self, activity):
        payload = original_builder_build(self, activity)
        if isinstance(payload, dict):
            payload["_cybrex_activity_name"] = activity_display_name(activity)
        return payload

    def connect_discord(self) -> bool:
        client_id = str(self.config.get("discord.client_id", "")).strip()
        if not client_id:
            self.logger.error("Discord client_id not configured")
            self._runtime_update(
                connected=False,
                state="configuration_error",
                last_error="Missing Discord client ID",
                transport="legacy_rpc",
            )
            return False

        requested = _transport_mode(self.config)
        helper_ready = social_sdk_available()
        attempted_social = requested == "social_sdk" or (requested == "auto" and helper_ready)

        if attempted_social:
            social = SocialSDKPresence(client_id)
            try:
                social.connect()
            except SocialSDKError as exc:
                try:
                    social.close()
                except Exception:
                    pass
                self.logger.warning("Discord Social SDK unavailable, using legacy RPC: %s", exc)
            else:
                self.rpc = social
                self.connected = True
                self.reconnect_delay = 5
                self.rpc_transport = "social_sdk"
                self.logger.info("Connected through Discord Social SDK dynamic-name transport")
                self._runtime_update(
                    connected=True,
                    state="running",
                    last_error=None,
                    transport="social_sdk",
                )
                return True

        try:
            rpc = LegacyPresence(client_id)
            rpc.connect()
            self.rpc = rpc
            self.connected = True
            self.reconnect_delay = 5
            self.rpc_transport = (
                "legacy_rpc_fallback" if attempted_social else "legacy_rpc"
            )
            self.logger.info("Connected to Discord legacy RPC")
            self._runtime_update(
                connected=True,
                state="running",
                last_error=None,
                transport=self.rpc_transport,
            )
            return True
        except (DiscordNotFound, InvalidID, InvalidPipe) as exc:
            self.logger.warning("Discord RPC unavailable: %s", exc)
            self._runtime_update(
                connected=False,
                state="discord_offline",
                last_error=str(exc)[:300],
                transport="legacy_rpc_fallback" if attempted_social else "legacy_rpc",
            )
        except Exception as exc:
            self.logger.error("Unexpected Discord connection error: %s", exc)
            self._runtime_update(
                connected=False,
                state="rpc_error",
                last_error=str(exc)[:300],
                transport="legacy_rpc_fallback" if attempted_social else "legacy_rpc",
            )
        self.connected = False
        self.rpc = None
        return False

    def update_presence(self, payload: Dict[str, Any]) -> bool:
        name = str(payload.get("_cybrex_activity_name") or "").strip()[:128]
        clean = sanitize_rpc_payload(payload)
        if not name:
            name = str(
                clean.get("large_text")
                or clean.get("state")
                or clean.get("details")
                or "CYBREX Activity"
            )[:128]
        self.current_activity_name = name
        transport = getattr(self, "rpc_transport", "legacy_rpc")

        if not self.dry_run and not self.connected:
            if not self.connect_discord():
                self._runtime_update(
                    activity_name=name,
                    transport=getattr(self, "rpc_transport", transport),
                )
                return False
        if isinstance(self.rpc, SocialSDKPresence):
            self.rpc.set_activity_name(name)

        active_rpc = self.rpc
        result = original_update_presence(self, payload)
        if not result and isinstance(active_rpc, SocialSDKPresence):
            try:
                active_rpc.close()
            except Exception:
                pass
        self._runtime_update(
            activity_name=name if result else None,
            transport=getattr(self, "rpc_transport", transport),
        )
        return result

    def clear_presence(self) -> bool:
        active_rpc = self.rpc
        result = original_clear_presence(self)
        if not result and isinstance(active_rpc, SocialSDKPresence):
            try:
                active_rpc.close()
            except Exception:
                pass
        if result:
            self.current_activity_name = None
            self._runtime_update(
                activity_name=None,
                transport=getattr(self, "rpc_transport", "legacy_rpc"),
            )
        return result

    def disconnect_discord(self):
        try:
            return original_disconnect(self)
        finally:
            self._runtime_update(
                transport=getattr(self, "rpc_transport", "legacy_rpc")
            )

    service_cls.__init__ = service_init
    service_cls.connect_discord = connect_discord
    service_cls.update_presence = update_presence
    service_cls.clear_presence = clear_presence
    service_cls.disconnect_discord = disconnect_discord
    service_cls._cybrex_dynamic_identity = True
    presence_builder_cls.build = builder_build
    presence_builder_cls._cybrex_dynamic_identity = True
    _PATCHED = True
