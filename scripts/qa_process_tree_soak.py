#!/usr/bin/env python3
"""Measure packaged CYBREX process-tree growth after warm-up."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import psutil

MIB = 1024 * 1024


@dataclass(frozen=True)
class TreeMetrics:
    rss: int = 0
    rss_anon: int = 0
    rss_file: int = 0
    threads: int = 0
    fds: int = 0
    children: int = 0
    zombies: int = 0


def _status_rss(process: psutil.Process) -> tuple[int, int]:
    if not sys.platform.startswith("linux"):
        return 0, 0
    values: dict[str, int] = {}
    try:
        for line in Path(f"/proc/{process.pid}/status").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(":")
            if separator and key in {"RssAnon", "RssFile"}:
                values[key] = int(value.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return 0, 0
    return values.get("RssAnon", 0), values.get("RssFile", 0)


def tree_metrics(root_pid: int) -> TreeMetrics:
    try:
        root = psutil.Process(root_pid)
        processes = [root, *root.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return TreeMetrics()

    rss = 0
    threads = 0
    fds = 0
    rss_anon = 0
    rss_file = 0
    zombies = 0
    for process in processes:
        try:
            if process.status() == psutil.STATUS_ZOMBIE:
                zombies += 1
                continue
            rss += int(process.memory_info().rss)
            anon, file_backed = _status_rss(process)
            rss_anon += anon
            rss_file += file_backed
            threads += int(process.num_threads())
            if hasattr(process, "num_fds"):
                fds += int(process.num_fds())
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied, OSError):
            continue
    return TreeMetrics(rss, rss_anon, rss_file, threads, fds, max(0, len(processes) - 1), zombies)


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()
        process.wait(timeout=3)


def lifecycle_cycles(executable: Path, mode: str) -> int:
    arg = "--gui" if mode == "gui-cycle" else "--tray"
    for cycle in range(3):
        process = subprocess.Popen(
            [str(executable), arg],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=os.environ.copy(),
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + (12 if mode == "gui-cycle" else 20)
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"packaged {mode} exited in cycle {cycle + 1}: {process.returncode}")
                time.sleep(0.5)
            metrics = tree_metrics(process.pid)
            if metrics.rss <= 0 or metrics.zombies:
                raise RuntimeError(f"invalid {mode} metrics in cycle {cycle + 1}: {metrics}")
        finally:
            _terminate(process)
        if process.poll() is None:
            raise RuntimeError(f"packaged {mode} did not terminate in cycle {cycle + 1}")
    print(f"CYBREX_{mode.upper().replace('-', '_')} cycles=3 status=passed")
    return 0


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        raise SystemExit("usage: qa_process_tree_soak.py <packaged-executable> [gui|tray|gui-cycle|tray-cycle]")
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        raise SystemExit(f"executable not found: {executable}")
    mode = sys.argv[2].strip().lower() if len(sys.argv) == 3 else "gui"
    if mode not in {"gui", "tray", "gui-cycle", "tray-cycle"}:
        raise SystemExit("mode must be gui, tray, gui-cycle, or tray-cycle")
    if mode.endswith("-cycle"):
        return lifecycle_cycles(executable, mode)

    arg = "--gui" if mode == "gui" else "--tray"
    warmup_seconds = 12 if mode == "gui" else 20
    soak_seconds = 60 if mode == "gui" else 120
    process = subprocess.Popen(
        [str(executable), arg],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
        start_new_session=True,
    )
    samples: list[TreeMetrics] = []
    try:
        # PyInstaller one-file extraction plus UI/tray/service initialization are
        # intentionally excluded from the growth measurement.
        warmup_deadline = time.monotonic() + warmup_seconds
        while time.monotonic() < warmup_deadline:
            if process.poll() is not None:
                raise RuntimeError(f"packaged {mode} exited during warm-up with {process.returncode}")
            time.sleep(0.5)

        baseline = tree_metrics(process.pid)
        if baseline.rss <= 0:
            raise RuntimeError(f"could not observe packaged {mode} process tree")

        deadline = time.monotonic() + soak_seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"packaged {mode} exited during soak with {process.returncode}")
            samples.append(tree_metrics(process.pid))
            time.sleep(1.0)

        final = samples[-1]
        peak = max(samples, key=lambda value: value.rss)
        growth = final.rss - baseline.rss
        peak_growth = peak.rss - baseline.rss
        prefix = "CYBREX_GUI_SOAK" if mode == "gui" else "CYBREX_TRAY_SOAK"
        print(
            f"{prefix} "
            f"baseline={baseline.rss / MIB:.1f}MiB "
            f"final={final.rss / MIB:.1f}MiB "
            f"peak={peak.rss / MIB:.1f}MiB "
            f"growth={growth / MIB:.1f}MiB "
            f"peak_growth={peak_growth / MIB:.1f}MiB "
            f"rss_anon={baseline.rss_anon}->{final.rss_anon} "
            f"rss_file={baseline.rss_file}->{final.rss_file} "
            f"threads={baseline.threads}->{final.threads} "
            f"fds={baseline.fds}->{final.fds} "
            f"children={baseline.children}->{final.children} "
            f"zombies={baseline.zombies}->{final.zombies}"
        )

        # These are slope guards after warm-up, not a cap on normal working set.
        if growth > 96 * MIB:
            raise RuntimeError(f"{mode} RSS grew more than 96 MiB after warm-up: {growth / MIB:.1f} MiB")
        if final.threads > baseline.threads + 8:
            raise RuntimeError(f"{mode} thread growth exceeded bound: {baseline.threads}->{final.threads}")
        if final.fds > baseline.fds + 20:
            raise RuntimeError(f"{mode} file descriptor growth exceeded bound: {baseline.fds}->{final.fds}")
        if final.children > baseline.children + 2:
            raise RuntimeError(f"{mode} child-process growth exceeded bound: {baseline.children}->{final.children}")
        if final.zombies:
            raise RuntimeError(f"{mode} left zombie processes: {final.zombies}")
    finally:
        _terminate(process)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
