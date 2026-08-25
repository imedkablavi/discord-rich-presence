"""Fixed-worker HTTP server for CYBREX loopback integrations.

ThreadingHTTPServer creates a new Python/OS thread for every accepted request.
Even when concurrent requests are semaphore-bounded, long-running browser/game
traffic can churn thousands of threads and cause allocator/RSS growth on Linux.
This server keeps a small fixed worker pool for the lifetime of the listener and
bounds accepted-but-not-yet-finished requests as well.
"""

from __future__ import annotations

import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer


class FixedWorkerLoopbackHTTPServer(HTTPServer):
    """HTTPServer backed by a bounded, fixed-size worker pool."""

    allow_reuse_address = True
    request_queue_size = 16

    def __init__(
        self,
        server_address,
        request_handler_class,
        *,
        max_workers: int = 4,
        max_pending_requests: int | None = None,
        client_timeout: float = 3.0,
        thread_name_prefix: str = "cybrex-http",
    ):
        workers = max(1, min(16, int(max_workers)))
        pending = max(
            workers,
            min(64, int(max_pending_requests if max_pending_requests is not None else workers * 2)),
        )
        self._client_timeout = max(0.25, min(15.0, float(client_timeout)))
        self._request_slots = threading.BoundedSemaphore(pending)
        self._executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix=thread_name_prefix,
        )
        self._executor_closed = False
        self._workers = workers
        self._pending_limit = pending
        super().__init__(server_address, request_handler_class)

    @property
    def worker_limit(self) -> int:
        return self._workers

    @property
    def pending_limit(self) -> int:
        return self._pending_limit

    def get_request(self):
        request, client_address = super().get_request()
        try:
            request.settimeout(self._client_timeout)
        except (AttributeError, OSError):
            pass
        return request, client_address

    @staticmethod
    def _close_rejected(request) -> None:
        try:
            request.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            request.close()
        except OSError:
            pass

    def process_request(self, request, client_address) -> None:
        if not self._request_slots.acquire(blocking=False):
            self._close_rejected(request)
            return
        try:
            self._executor.submit(self._process_request_worker, request, client_address)
        except RuntimeError:
            self._request_slots.release()
            self._close_rejected(request)

    def _process_request_worker(self, request, client_address) -> None:
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            try:
                self.shutdown_request(request)
            finally:
                self._request_slots.release()

    def server_close(self) -> None:
        if self._executor_closed:
            return
        self._executor_closed = True
        try:
            super().server_close()
        finally:
            # shutdown() is called before server_close() by every CYBREX bridge,
            # so no new requests can arrive while the fixed workers drain.
            self._executor.shutdown(wait=True, cancel_futures=False)
