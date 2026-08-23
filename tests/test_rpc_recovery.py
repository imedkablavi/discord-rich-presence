import logging
import threading

from main import DiscordRichPresenceService


class BrokenRPC:
    def __init__(self):
        self.closed = 0

    def update(self, **_payload):
        raise OSError('pipe closed')

    def clear(self):
        raise OSError('pipe closed')

    def close(self):
        self.closed += 1


class RuntimeRecorder:
    def __init__(self):
        self.updates = []

    def update(self, **fields):
        self.updates.append(fields)

    def stop_requested(self):
        return False


def _service():
    service = DiscordRichPresenceService.__new__(DiscordRichPresenceService)
    service.dry_run = False
    service.connected = True
    service.rpc = BrokenRPC()
    service.presence_active = True
    service.last_payload = {'details': 'before'}
    service.runtime = RuntimeRecorder()
    service._stop_event = threading.Event()
    service.reconnect_delay = 5
    service.max_reconnect_delay = 300
    service.logger = logging.getLogger('rpc-recovery-test')
    return service


def test_update_failure_closes_broken_rpc_transport():
    service = _service()
    rpc = service.rpc

    assert service.update_presence({'details': 'after'}) is False
    assert rpc.closed == 1
    assert service.rpc is None
    assert service.connected is False
    assert any(update.get('state') == 'rpc_error' for update in service.runtime.updates)


def test_clear_failure_closes_broken_rpc_transport():
    service = _service()
    rpc = service.rpc

    assert service.clear_presence() is False
    assert rpc.closed == 1
    assert service.rpc is None
    assert service.connected is False


def test_backoff_is_capped_and_interruptible(monkeypatch):
    service = _service()
    service.reconnect_delay = 200
    waits = []
    monkeypatch.setattr(service, '_wait', lambda seconds: waits.append(seconds) or False)

    service._handle_rpc_failure()
    assert waits == [200]
    assert service.reconnect_delay == 300

    service._handle_rpc_failure()
    assert waits == [200, 300]
    assert service.reconnect_delay == 300
