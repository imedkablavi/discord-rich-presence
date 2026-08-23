#!/usr/bin/env python3
"""Long-running resource-leak soak harness for the service loop."""

from __future__ import annotations

import argparse
import tempfile
import threading
import time
from pathlib import Path

import psutil

from config import Config
from main import DiscordRichPresenceService


class StableWindowDetector:
    def get_active_window(self):
        return {"app_name": "soak-test-app", "title": "Soak Test", "pid": None}


class NoopDetector:
    def detect(self, _window_info):
        return None


def metric_handles(process: psutil.Process) -> int:
    if hasattr(process, "num_fds"):
        return int(process.num_fds())
    if hasattr(process, "num_handles"):
        return int(process.num_handles())
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--max-rss-growth-mb", type=float, default=32.0)
    parser.add_argument("--max-handle-growth", type=int, default=8)
    parser.add_argument("--max-thread-growth", type=int, default=3)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        cfg = Config(Path(temp_dir) / "config.yaml")
        cfg.set("update_interval_secs", 1)
        service = DiscordRichPresenceService(cfg, dry_run=True)
        service.window_detector = StableWindowDetector()
        service.browser_detector.close()
        service.browser_detector = NoopDetector()
        service.terminal_detector = NoopDetector()
        service.coding_detector = NoopDetector()
        service.media_detector = NoopDetector()
        service.gaming_detector = NoopDetector()

        worker = threading.Thread(target=service.run, name="soak-service", daemon=True)
        worker.start()
        time.sleep(min(2.0, max(0.2, args.duration / 10)))

        process = psutil.Process()
        baseline_rss = process.memory_info().rss
        baseline_handles = metric_handles(process)
        baseline_threads = process.num_threads()
        deadline = time.monotonic() + max(1.0, args.duration)
        peak_rss = baseline_rss
        peak_handles = baseline_handles
        peak_threads = baseline_threads

        while time.monotonic() < deadline:
            peak_rss = max(peak_rss, process.memory_info().rss)
            peak_handles = max(peak_handles, metric_handles(process))
            peak_threads = max(peak_threads, process.num_threads())
            time.sleep(0.5)

        service.stop()
        worker.join(timeout=10)
        if worker.is_alive():
            raise SystemExit("service thread did not stop cleanly")

        rss_growth_mb = (peak_rss - baseline_rss) / (1024 * 1024)
        handle_growth = peak_handles - baseline_handles
        thread_growth = peak_threads - baseline_threads
        print(
            f"soak: rss_growth={rss_growth_mb:.2f}MiB "
            f"handle_growth={handle_growth} thread_growth={thread_growth}"
        )
        if rss_growth_mb > args.max_rss_growth_mb:
            raise SystemExit("RSS growth exceeded threshold")
        if handle_growth > args.max_handle_growth:
            raise SystemExit("FD/handle growth exceeded threshold")
        if thread_growth > args.max_thread_growth:
            raise SystemExit("thread growth exceeded threshold")


if __name__ == "__main__":
    main()
