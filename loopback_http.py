"""Resource-bounded HTTP server for local companion integrations."""

from __future__ import annotations

import socket
import threading
from http.server import ThreadingHTTPServer


class BoundedLoopbackHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer with bounded request concurrency and socket timeouts."""

    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 8
    block_on_close = False

    def __init__(
        self,
        server_address,
        request_handler_class,
        *,
        max_concurrent_requests: int = 8,
        client_timeout: float = 3.0,
    ):
        super().__init__(server_address, request_handler_class)
        self._request_slots = threading.BoundedSemaphore(max(1, int(max_concurrent_requests)))
        self._client_timeout = max(0.25, float(client_timeout))

    def get_request(self):
        request, client_address = super().get_request()
        try:
            request.settimeout(self._client_timeout)
        except (AttributeError, OSError):
            pass
        return request, client_address

    def process_request(self, request, client_address) -> None:
        if not self._request_slots.acquire(blocking=False):
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                request.close()
            except OSError:
                pass
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()
