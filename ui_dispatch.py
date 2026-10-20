"""Thread-safe handoff from background work to the desktop UI event loop."""

from __future__ import annotations

import queue
from collections.abc import Callable


class UIThreadDispatcher:
    """Thread-safe callback queue. Callbacks run only when the UI thread drains it."""

    def __init__(self) -> None:
        self._callbacks: queue.SimpleQueue[Callable[[], object]] = queue.SimpleQueue()

    def post(self, callback: Callable[[], object]) -> None:
        if not callable(callback):
            raise TypeError("UI callback must be callable")
        self._callbacks.put(callback)

    def take_pending(self, *, limit: int = 64) -> list[Callable[[], object]]:
        """Return queued callbacks without executing them on the calling thread."""
        requested_limit = int(limit)
        if requested_limit <= 0:
            return []
        bounded_limit = min(requested_limit, 256)
        pending: list[Callable[[], object]] = []
        while len(pending) < bounded_limit:
            try:
                pending.append(self._callbacks.get_nowait())
            except queue.Empty:
                break
        return pending
