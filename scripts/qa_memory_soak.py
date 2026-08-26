#!/usr/bin/env python3
"""Deterministic long-running resource QA for CYBREX core paths.

This is intentionally synthetic/offline: it stresses the same bounded HTTP and
payload-building paths without requiring Discord, a browser, or a real game.
"""

from __future__ import annotations

import gc
import http.client
import json
import os
import socket
import tempfile
import threading
import time
from pathlib import Path

import psutil

from browser_companion import BrowserCompanionBridge
from config import Config
from memory_guard import _malloc_trim
from presence import PresenceBuilder
from resource_hardening import apply_resource_hardening

MIB = 1024 * 1024


def snapshot() -> tuple[int, int, int | None]:
    process = psutil.Process(os.getpid())
    rss = int(process.memory_info().rss)
    threads = int(process.num_threads())
    try:
        fds = int(process.num_fds()) if hasattr(process, "num_fds") else None
    except (psutil.Error, OSError):
        fds = None
    return rss, threads, fds


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def post_activity(port: int, index: int) -> None:
    payload = {
        "version": 1,
        "browser": "Brave",
        "tab_id": str(index % 180),
        "url": f"https://example.com/page/{index % 23}",
        "title": f"QA page {index % 97}",
        "service": "",
        "private": False,
        "focused": index % 7 == 0,
        "visible": True,
        "media": {"playing": False, "position": 0, "duration": 0},
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request(
            "POST",
            "/v1/activity",
            body=body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "X-CYBREX-Companion": "1",
                "Origin": "chrome-extension://cybrex-qa",
            },
        )
        response = conn.getresponse()
        response.read()
        if response.status != 200:
            raise RuntimeError(f"browser companion returned HTTP {response.status}")
    finally:
        conn.close()


def churn_presence(builder: PresenceBuilder, count: int) -> None:
    kinds = (
        lambda i: {"type": "application", "app_name": "org.kde.konsole", "window_title": f"Terminal {i % 20}"},
        lambda i: {"type": "browser", "browser_name": "Brave", "page_title": f"Page {i % 101}", "service": "YouTube" if i % 9 == 0 else "", "url": "https://example.com"},
        lambda i: {"type": "coding", "editor": "Visual Studio Code", "filename": f"file_{i % 71}.py", "language": "python", "project": f"project-{i % 13}"},
        lambda i: {"type": "gaming", "game_name": f"Synthetic Game {i % 31}", "launcher": "Steam", "game_source": "Steam"},
        lambda i: {"type": "media", "player": "Brave", "service": "YouTube", "title": f"Video {i % 83}", "is_playing": True, "position": i % 500, "duration": 600},
    )
    for i in range(count):
        builder.build(kinds[i % len(kinds)](i))


def main() -> int:
    apply_resource_hardening()
    with tempfile.TemporaryDirectory(prefix="cybrex-memory-qa-") as temp:
        config = Config(Path(temp) / "config.yaml")
        port = free_port()
        config.set("browser_companion.port", port)
        config.set("browser_companion.ttl_secs", 120)
        config.set("images.use_external_app_icons", True)

        builder = PresenceBuilder(config)
        # Warm imports/caches before the baseline so the assertion measures
        # growth, not one-time interpreter initialization.
        churn_presence(builder, 1000)
        gc.collect()
        _malloc_trim()
        baseline_rss, baseline_threads, baseline_fds = snapshot()

        bridge = BrowserCompanionBridge(config)
        if not bridge.start():
            raise RuntimeError("could not start Browser Companion on an ephemeral QA port")
        try:
            for index in range(5000):
                post_activity(bridge.port, index)
            status = bridge.status()
            if int(status.get("records", 0)) > 100:
                raise RuntimeError(f"browser record bound violated: {status}")
            churn_presence(builder, 30000)
        finally:
            bridge.stop()

        # Let fixed workers exit, then return free heap pages where glibc allows.
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if not any(t.name.startswith("cybrex-browser") for t in threading.enumerate()):
                break
            time.sleep(0.05)
        gc.collect()
        _malloc_trim()
        final_rss, final_threads, final_fds = snapshot()

        growth = final_rss - baseline_rss
        print(
            "CYBREX_MEMORY_QA "
            f"baseline_rss={baseline_rss / MIB:.1f}MiB "
            f"final_rss={final_rss / MIB:.1f}MiB "
            f"growth={growth / MIB:.1f}MiB "
            f"threads={baseline_threads}->{final_threads} "
            f"fds={baseline_fds}->{final_fds}"
        )

        if growth > 96 * MIB:
            raise RuntimeError(f"core RSS growth exceeded 96 MiB: {growth / MIB:.1f} MiB")
        if final_threads > baseline_threads + 3:
            raise RuntimeError(f"thread count did not return to bound: {baseline_threads}->{final_threads}")
        if baseline_fds is not None and final_fds is not None and final_fds > baseline_fds + 8:
            raise RuntimeError(f"file descriptor growth exceeded bound: {baseline_fds}->{final_fds}")
        if len(builder.activity_start_times) > 20:
            raise RuntimeError("activity start-time cache exceeded its bound")
        if len(builder.media_timelines) > 10:
            raise RuntimeError("media timeline cache exceeded its bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
