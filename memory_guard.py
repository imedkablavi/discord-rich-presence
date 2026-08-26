"""Low-overhead long-running memory pressure diagnostics for CYBREX."""

from __future__ import annotations

import ctypes
import gc
import logging
import os
import sys
import threading

import psutil


LOGGER = logging.getLogger(__name__)
_STARTED = False
_START_LOCK = threading.Lock()
_INTERVAL_SECS = 30.0
_WARN_RSS_BYTES = 384 * 1024 * 1024
_GROWTH_BYTES = 96 * 1024 * 1024


def _malloc_trim() -> bool:
    """Ask glibc to return unused heap pages to the OS when available."""
    if not sys.platform.startswith('linux'):
        return False
    try:
        libc = ctypes.CDLL('libc.so.6')
        trim = libc.malloc_trim
        trim.argtypes = [ctypes.c_size_t]
        trim.restype = ctypes.c_int
        return bool(trim(0))
    except Exception:
        return False


def _resource_snapshot(process: psutil.Process) -> tuple[int, int, int | None]:
    rss = int(process.memory_info().rss)
    threads = int(process.num_threads())
    fds = None
    if hasattr(process, 'num_fds'):
        try:
            fds = int(process.num_fds())
        except (psutil.Error, OSError):
            fds = None
    return rss, threads, fds


def _guard_loop() -> None:
    process = psutil.Process(os.getpid())
    try:
        baseline_rss, _, _ = _resource_snapshot(process)
    except (psutil.Error, OSError):
        return
    last_trim_rss = baseline_rss

    while True:
        threading.Event().wait(_INTERVAL_SECS)
        try:
            rss, threads, fds = _resource_snapshot(process)
        except (psutil.Error, OSError):
            return

        growth = rss - baseline_rss
        since_trim = rss - last_trim_rss
        if rss < _WARN_RSS_BYTES and growth < _GROWTH_BYTES:
            continue
        if since_trim < _GROWTH_BYTES // 2 and rss < _WARN_RSS_BYTES * 2:
            continue

        before = rss
        gc.collect()
        trimmed = _malloc_trim()
        try:
            after, threads_after, fds_after = _resource_snapshot(process)
        except (psutil.Error, OSError):
            after, threads_after, fds_after = before, threads, fds

        LOGGER.warning(
            'Memory pressure: rss_before=%.1fMiB rss_after=%.1fMiB baseline=%.1fMiB '
            'threads=%d fds=%s malloc_trim=%s',
            before / (1024 * 1024),
            after / (1024 * 1024),
            baseline_rss / (1024 * 1024),
            threads_after,
            fds_after if fds_after is not None else 'n/a',
            trimmed,
        )
        last_trim_rss = after


def start_memory_guard() -> None:
    """Start one daemon guard per CYBREX process."""
    global _STARTED
    if _STARTED:
        return
    with _START_LOCK:
        if _STARTED:
            return
        thread = threading.Thread(
            target=_guard_loop,
            name='cybrex-memory-guard',
            daemon=True,
        )
        thread.start()
        _STARTED = True
