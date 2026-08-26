"""Runtime resource hardening for long-running CYBREX services."""

from __future__ import annotations

import threading

from fixed_http import FixedWorkerLoopbackHTTPServer


_APPLY_LOCK = threading.Lock()
_APPLIED = False


class _BrowserFixedServer(FixedWorkerLoopbackHTTPServer):
    request_queue_size = 16

    def __init__(self, server_address, request_handler_class):
        super().__init__(
            server_address,
            request_handler_class,
            max_workers=4,
            max_pending_requests=8,
            client_timeout=3.0,
            thread_name_prefix="cybrex-browser",
        )


class _CS2FixedServer(FixedWorkerLoopbackHTTPServer):
    request_queue_size = 8

    def __init__(self, server_address, request_handler_class):
        super().__init__(
            server_address,
            request_handler_class,
            max_workers=4,
            max_pending_requests=8,
            client_timeout=3.0,
            thread_name_prefix="cybrex-cs2",
        )


def _patch_pypresence_cleanup() -> None:
    """Ensure failed connect/update/clear paths close their IPC transport."""
    import pypresence

    original = pypresence.Presence
    if getattr(original, "_cybrex_resource_safe", False):
        return

    class ResourceSafePresence(original):
        _cybrex_resource_safe = True

        def _close_after_failure(self) -> None:
            try:
                super().close()
            except Exception:
                pass

        def connect(self, *args, **kwargs):
            try:
                return super().connect(*args, **kwargs)
            except Exception:
                self._close_after_failure()
                raise

        def update(self, *args, **kwargs):
            try:
                return super().update(*args, **kwargs)
            except Exception:
                self._close_after_failure()
                raise

        def clear(self, *args, **kwargs):
            try:
                return super().clear(*args, **kwargs)
            except Exception:
                self._close_after_failure()
                raise

    pypresence.Presence = ResourceSafePresence


def _patch_dynamic_discord_identity() -> None:
    """Enable Social SDK dynamic activity names while preserving legacy fallback."""
    from dynamic_identity import apply_dynamic_identity
    from main import DiscordRichPresenceService
    from presence import PresenceBuilder

    apply_dynamic_identity(DiscordRichPresenceService, PresenceBuilder)


def apply_resource_hardening() -> None:
    """Install bounded workers, RPC cleanup, and dynamic Discord identity routing."""
    global _APPLIED
    if _APPLIED:
        return
    with _APPLY_LOCK:
        if _APPLIED:
            return

        import browser_companion
        import cs2_gsi

        browser_companion._CompanionHTTPServer = _BrowserFixedServer
        cs2_gsi._CS2HTTPServer = _CS2FixedServer

        # Patch pypresence first so the legacy fallback used by dynamic_identity
        # inherits the resource-safe cleanup behavior.
        _patch_pypresence_cleanup()
        _patch_dynamic_discord_identity()
        _APPLIED = True


def is_applied() -> bool:
    return _APPLIED
