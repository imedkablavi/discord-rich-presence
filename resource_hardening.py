"""Runtime resource hardening for legacy loopback listeners.

The Browser Companion and CS2 GSI listeners historically subclassed
ThreadingHTTPServer directly. Their semaphore limited simultaneous requests but
still created a fresh OS thread for every request. On long-running Linux systems
that can grow RSS through thread-stack and allocator arena churn.

This module swaps those legacy server classes for fixed-worker equivalents
without changing their HTTP/API behavior. It is idempotent and intentionally
small so the older bridge implementations can be migrated cleanly later.
"""

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


def apply_resource_hardening() -> None:
    """Install fixed-worker server classes for legacy high-frequency bridges."""
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
        _APPLIED = True


def is_applied() -> bool:
    return _APPLIED
