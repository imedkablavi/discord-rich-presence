import json
import os
import time

import psutil

from runtime_state import RuntimeState


def test_runtime_state_acquire_prevents_second_instance(tmp_path):
    first = RuntimeState(tmp_path)
    second = RuntimeState(tmp_path)

    assert first.acquire() is True
    try:
        assert second.acquire() is False
        status = second.read_active()
        assert status is not None
        assert status['pid'] == os.getpid()
    finally:
        first.release()


def test_runtime_state_updates_and_releases(tmp_path):
    runtime = RuntimeState(tmp_path)
    assert runtime.acquire() is True

    runtime.update(state='running', connected=True, presence_active=True, activity='Coding')
    status = runtime.read_active()
    assert status is not None
    assert status['state'] == 'running'
    assert status['connected'] is True
    assert status['presence_active'] is True
    assert status['activity'] == 'Coding'

    runtime.release()
    assert runtime.read_active() is None
    assert not runtime.lock_path.exists()
    assert not runtime.status_path.exists()


def test_runtime_state_recovers_stale_lock(tmp_path):
    runtime = RuntimeState(tmp_path)
    runtime.runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime.lock_path.write_text(
        json.dumps({'pid': 99999999, 'create_time': 1.0}),
        encoding='utf-8',
    )

    assert runtime.acquire() is True
    try:
        assert runtime.read_active() is not None
    finally:
        runtime.release()


def test_runtime_state_detects_pid_reuse_by_creation_time(tmp_path):
    runtime = RuntimeState(tmp_path)
    runtime.runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime.lock_path.write_text(
        json.dumps({
            'pid': os.getpid(),
            'create_time': psutil.Process(os.getpid()).create_time() - 60,
        }),
        encoding='utf-8',
    )

    assert runtime.acquire() is True
    runtime.release()


def test_runtime_status_has_fresh_heartbeat(tmp_path):
    runtime = RuntimeState(tmp_path)
    assert runtime.acquire() is True
    try:
        before = time.time()
        runtime.update(state='running')
        status = runtime.read_active()
        assert status is not None
        assert status['updated_at'] >= before
    finally:
        runtime.release()
