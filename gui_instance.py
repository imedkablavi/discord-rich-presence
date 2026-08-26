"""Per-user single-instance guard for the CYBREX control panel."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psutil

from runtime_state import default_runtime_dir


class GUIInstanceLock:
    """Prevent accidental duplicate GUI processes from multiplying RAM use."""

    def __init__(self, lock_path: Path | None = None):
        self.lock_path = Path(lock_path) if lock_path else default_runtime_dir() / "gui.lock"
        self.pid = os.getpid()
        self.create_time = float(psutil.Process(self.pid).create_time())
        self.acquired = False

    @staticmethod
    def _read(path: Path) -> dict | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, ValueError, TypeError):
            return None

    @staticmethod
    def _is_live(record: dict | None) -> bool:
        if not record:
            return False
        try:
            pid = int(record["pid"])
            create_time = float(record["create_time"])
        except (KeyError, TypeError, ValueError):
            return False
        if pid <= 0 or not psutil.pid_exists(pid):
            return False
        try:
            return abs(float(psutil.Process(pid).create_time()) - create_time) < 1.0
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return False
        except psutil.AccessDenied:
            return True

    def acquire(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix":
            try:
                os.chmod(self.lock_path.parent, 0o700)
            except OSError:
                pass

        payload = json.dumps({"pid": self.pid, "create_time": self.create_time}).encode("utf-8")
        for _ in range(2):
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                existing = self._read(self.lock_path)
                if self._is_live(existing):
                    return False
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    return False
                continue

            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            if os.name == "posix":
                try:
                    os.chmod(self.lock_path, 0o600)
                except OSError:
                    pass
            self.acquired = True
            return True
        return False

    def release(self) -> None:
        if not self.acquired:
            return
        self.acquired = False
        record = self._read(self.lock_path)
        try:
            if record and int(record.get("pid", -1)) != self.pid:
                return
        except (TypeError, ValueError):
            return
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
