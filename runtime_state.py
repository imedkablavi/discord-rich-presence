"""Runtime process state and single-instance coordination."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import psutil


def default_runtime_dir() -> Path:
    """Return the per-user runtime directory used by the service and GUI."""
    if sys.platform == 'win32':
        base = os.environ.get('LOCALAPPDATA')
        root = Path(base) if base else Path.home() / 'AppData' / 'Local'
        return root / 'discord-rich-presence' / 'runtime'
    return Path.home() / '.local' / 'state' / 'discord-rich-presence' / 'runtime'


class RuntimeState:
    """Coordinate one service process and expose a small local status record."""

    def __init__(self, runtime_dir: Optional[Path] = None):
        self.runtime_dir = Path(runtime_dir) if runtime_dir else default_runtime_dir()
        self.lock_path = self.runtime_dir / 'instance.lock'
        self.status_path = self.runtime_dir / 'status.json'
        self.pid = os.getpid()
        self.create_time = float(psutil.Process(self.pid).create_time())
        self.acquired = False

    @staticmethod
    def _read_json(path: Path) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else None
        except (OSError, ValueError, TypeError):
            return None

    @staticmethod
    def _same_process(record: Optional[Dict[str, Any]]) -> bool:
        if not record:
            return False
        try:
            pid = int(record['pid'])
            expected_create_time = float(record['create_time'])
        except (KeyError, TypeError, ValueError):
            return False
        if pid <= 0 or not psutil.pid_exists(pid):
            return False
        try:
            actual_create_time = float(psutil.Process(pid).create_time())
            return abs(actual_create_time - expected_create_time) < 1.0
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return False
        except psutil.AccessDenied:
            # Same-user services should normally be queryable. If the OS denies access,
            # prefer treating the PID as live rather than starting a competing instance.
            return True

    def _identity(self) -> Dict[str, Any]:
        return {'pid': self.pid, 'create_time': self.create_time}

    def _write_atomic(self, path: Path, data: Dict[str, Any]):
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding='utf-8')
        os.replace(temp, path)

    def acquire(self) -> bool:
        """Acquire the per-user service lock. Returns False if another instance is live."""
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        identity = self._identity()

        for _ in range(2):
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                existing = self._read_json(self.lock_path)
                if self._same_process(existing):
                    return False
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    return False
                continue

            try:
                os.write(fd, json.dumps(identity).encode('utf-8'))
            finally:
                os.close(fd)
            self.acquired = True
            now = time.time()
            self._write_atomic(self.status_path, {
                **identity,
                'started_at': now,
                'updated_at': now,
                'connected': False,
                'presence_active': False,
                'state': 'starting',
            })
            return True

        return False

    def update(self, **fields: Any):
        """Update status when this object owns the service lock."""
        if not self.acquired:
            return
        lock = self._read_json(self.lock_path)
        if not lock or int(lock.get('pid', -1)) != self.pid:
            self.acquired = False
            return
        current = self._read_json(self.status_path) or self._identity()
        current.update(fields)
        current.update(self._identity())
        current['updated_at'] = time.time()
        self._write_atomic(self.status_path, current)

    def release(self):
        """Remove status/lock files only when they still belong to this process."""
        if not self.acquired:
            return
        self.acquired = False
        for path in (self.status_path, self.lock_path):
            record = self._read_json(path)
            if record and int(record.get('pid', -1)) != self.pid:
                continue
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def read_active(self) -> Optional[Dict[str, Any]]:
        """Return the live service status, or None when no valid instance exists."""
        lock = self._read_json(self.lock_path)
        if not self._same_process(lock):
            return None
        status = self._read_json(self.status_path) or dict(lock or {})
        if not self._same_process(status):
            status = dict(lock or {})
        return status

    def terminate_active(self, timeout: float = 5.0) -> bool:
        """Terminate the live service identified by the lock file."""
        record = self.read_active()
        if not record:
            return False
        try:
            pid = int(record['pid'])
        except (KeyError, TypeError, ValueError):
            return False
        if pid == os.getpid():
            return False
        try:
            process = psutil.Process(pid)
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                process.kill()
                process.wait(timeout=timeout)
            return True
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return True
        except (psutil.AccessDenied, psutil.TimeoutExpired):
            return False
