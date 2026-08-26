#!/usr/bin/env python3
"""Measure packaged CYBREX process-tree growth after warm-up."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil

MIB = 1024 * 1024


def tree_metrics(root_pid: int) -> tuple[int, int, int]:
    try:
        root = psutil.Process(root_pid)
        processes = [root, *root.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return 0, 0, 0

    rss = 0
    threads = 0
    fds = 0
    for process in processes:
        try:
            rss += int(process.memory_info().rss)
            threads += int(process.num_threads())
            if hasattr(process, "num_fds"):
                fds += int(process.num_fds())
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied, OSError):
            continue
    return rss, threads, fds


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        raise SystemExit("usage: qa_process_tree_soak.py <packaged-executable> [gui|tray]")
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        raise SystemExit(f"executable not found: {executable}")
    mode = sys.argv[2].strip().lower() if len(sys.argv) == 3 else "gui"
    if mode not in {"gui", "tray"}:
        raise SystemExit("mode must be gui or tray")

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
    samples: list[tuple[int, int, int]] = []
    try:
        # PyInstaller one-file extraction plus UI/tray/service initialization are
        # intentionally excluded from the growth measurement.
        warmup_deadline = time.monotonic() + warmup_seconds
        while time.monotonic() < warmup_deadline:
            if process.poll() is not None:
                raise RuntimeError(f"packaged {mode} exited during warm-up with {process.returncode}")
            time.sleep(0.5)

        baseline = tree_metrics(process.pid)
        if baseline[0] <= 0:
            raise RuntimeError(f"could not observe packaged {mode} process tree")

        deadline = time.monotonic() + soak_seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"packaged {mode} exited during soak with {process.returncode}")
            samples.append(tree_metrics(process.pid))
            time.sleep(1.0)

        final = samples[-1]
        peak = max(samples, key=lambda value: value[0])
        growth = final[0] - baseline[0]
        peak_growth = peak[0] - baseline[0]
        prefix = "CYBREX_GUI_SOAK" if mode == "gui" else "CYBREX_TRAY_SOAK"
        print(
            f"{prefix} "
            f"baseline={baseline[0] / MIB:.1f}MiB "
            f"final={final[0] / MIB:.1f}MiB "
            f"peak={peak[0] / MIB:.1f}MiB "
            f"growth={growth / MIB:.1f}MiB "
            f"peak_growth={peak_growth / MIB:.1f}MiB "
            f"threads={baseline[1]}->{final[1]} "
            f"fds={baseline[2]}->{final[2]}"
        )

        # These are slope guards after warm-up, not a cap on normal working set.
        if growth > 96 * MIB:
            raise RuntimeError(f"{mode} RSS grew more than 96 MiB after warm-up: {growth / MIB:.1f} MiB")
        if final[1] > baseline[1] + 8:
            raise RuntimeError(f"{mode} thread growth exceeded bound: {baseline[1]}->{final[1]}")
        if final[2] > baseline[2] + 20:
            raise RuntimeError(f"{mode} file descriptor growth exceeded bound: {baseline[2]}->{final[2]}")
    finally:
        if process.poll() is None:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
