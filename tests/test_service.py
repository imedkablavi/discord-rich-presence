import logging
import threading

from main import DiscordRichPresenceService


class FakeRPC:
    def __init__(self):
        self.cleared = 0
        self.updated = []
        self.closed = 0

    def clear(self):
        self.cleared += 1

    def update(self, **payload):
        self.updated.append(payload)

    def close(self):
        self.closed += 1


class StopRuntime:
    def __init__(self, requested=False):
        self.requested = requested
        self.updates = []

    def stop_requested(self):
        return self.requested

    def update(self, **fields):
        self.updates.append(fields)


def _service():
    service = DiscordRichPresenceService.__new__(DiscordRichPresenceService)
    service.dry_run = False
    service.connected = True
    service.rpc = FakeRPC()
    service.presence_active = True
    service.last_payload = {'details': 'old', 'buttons': [{'label': 'A', 'url': 'https://a.test'}]}
    service.runtime = None
    service._stop_event = threading.Event()
    service.reconnect_delay = 60
    service.logger = logging.getLogger('test')
    return service


def test_clear_presence_removes_stale_activity():
    service = _service()
    assert service.clear_presence() is True
    assert service.rpc.cleared == 1
    assert service.presence_active is False
    assert service.last_payload is None


def test_payload_comparison_includes_buttons_and_urls():
    service = _service()
    changed_button = {'details': 'old', 'buttons': [{'label': 'B', 'url': 'https://b.test'}]}
    assert service.should_update(changed_button) is True


def test_identical_full_payload_does_not_update():
    service = _service()
    assert service.should_update(dict(service.last_payload)) is False


def test_wait_honors_runtime_graceful_stop_request():
    service = _service()
    service.runtime = StopRuntime(requested=True)

    assert service._wait(10) is True
    assert service._stop_event.is_set()


def test_client_id_change_clears_old_presence_and_disconnects():
    service = _service()
    rpc = service.rpc

    service._reset_rpc_for_client_id_change('111', '222')

    assert rpc.cleared == 1
    assert rpc.closed == 1
    assert service.rpc is None
    assert service.connected is False
    assert service.presence_active is False
    assert service.last_payload is None
    assert service.reconnect_delay == 5


def test_unchanged_client_id_keeps_current_rpc():
    service = _service()
    rpc = service.rpc

    service._reset_rpc_for_client_id_change('111', '111')

    assert service.rpc is rpc
    assert rpc.cleared == 0
    assert rpc.closed == 0
    assert service.connected is True


def test_windows_lock_app_is_detected():
    assert DiscordRichPresenceService._is_lock_screen_window({
        'app_name': 'LockApp.exe',
        'title': 'Windows Default Lock Screen',
    }) is True


def test_linux_screen_locker_is_detected():
    assert DiscordRichPresenceService._is_lock_screen_window({
        'app_name': 'kscreenlocker_greet',
        'title': '',
    }) is True


def test_normal_application_is_not_treated_as_lock_screen():
    assert DiscordRichPresenceService._is_lock_screen_window({
        'app_name': 'code',
        'title': 'main.py - Visual Studio Code',
    }) is False
