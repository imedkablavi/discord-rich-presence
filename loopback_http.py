"""Resource-bounded HTTP server for local companion integrations."""

from __future__ import annotations

from fixed_http import FixedWorkerLoopbackHTTPServer


class BoundedLoopbackHTTPServer(FixedWorkerLoopbackHTTPServer):
    """Loopback server with fixed workers, bounded backlog and socket timeouts."""

    request_queue_size = 8

    def __init__(
        self,
        server_address,
        request_handler_class,
        *,
        max_concurrent_requests: int = 8,
        client_timeout: float = 3.0,
    ):
        # Integrations are tiny local JSON endpoints. Four persistent workers are
        # enough for normal traffic and avoid the allocator/thread-stack churn of
        # spawning a fresh OS thread for every browser/game request.
        workers = max(1, min(4, int(max_concurrent_requests)))
        pending = max(workers, min(16, int(max_concurrent_requests)))
        super().__init__(
            server_address,
            request_handler_class,
            max_workers=workers,
            max_pending_requests=pending,
            client_timeout=client_timeout,
            thread_name_prefix="cybrex-loopback",
        )
