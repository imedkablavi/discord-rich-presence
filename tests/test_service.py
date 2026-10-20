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



def test_lock_screen_suppresses_override_presence_and_clears_terminal_cache():
    service = _service()
    service.config = type(
        "ConfigStub",
        (),
        {"get": lambda self, key, default=None: {
            "rules.clear_on_lock_screen": True,
            "override.enabled": True,
        }.get(key, default)},
    )()
    service._reload_config_if_changed = lambda: None
    service.window_detector = type(
        "WindowDetectorStub",
        (),
        {"get_active_window": lambda self: {
            "app_name": "LockApp.exe",
            "title": "Windows Default Lock Screen",
        }},
    )()

    class TerminalCacheStub:
        def __init__(self):
            self.cleared = 0
            self.cleaned = 0

        def clear_command_cache(self):
            self.cleared += 1

        def cleanup_command_cache(self):
            self.cleaned += 1

    service.terminal_detector = TerminalCacheStub()

    assert service.detect_activity() is None
    assert service.terminal_detector.cleared == 1
    assert service.terminal_detector.cleaned == 0


def test_missing_foreground_window_triggers_terminal_cache_cleanup():
    service = _service()
    service.config = type(
        "ConfigStub",
        (),
        {"get": lambda self, key, default=None: {
            "rules.clear_on_lock_screen": True,
            "override.enabled": False,
        }.get(key, default)},
    )()
    service._reload_config_if_changed = lambda: None
    service.window_detector = type(
        "WindowDetectorStub",
        (),
        {"get_active_window": lambda self: None},
    )()

    class TerminalCacheStub:
        def __init__(self):
            self.cleaned = 0

        def cleanup_command_cache(self):
            self.cleaned += 1

        def clear_command_cache(self):
            raise AssertionError("a missing window is not proof of a lock screen")

    service.terminal_detector = TerminalCacheStub()

    assert service.detect_activity() is None
    assert service.terminal_detector.cleaned == 1



def test_override_presence_still_clears_cache_when_terminal_tracking_is_disabled():
    service = _service()
    service.config = type(
        "ConfigStub",
        (),
        {"get": lambda self, key, default=None: {
            "rules.clear_on_lock_screen": True,
            "rules.enabled_detectors.terminal": False,
            "override.enabled": True,
            "override": {"details": "Manual presence"},
            "images.app": "app",
            "privacy.mode": "balanced",
        }.get(key, default)},
    )()
    service._reload_config_if_changed = lambda: None
    service.window_detector = type(
        "WindowDetectorStub",
        (),
        {"get_active_window": lambda self: {
            "app_name": "Firefox",
            "title": "news",
        }},
    )()

    class TerminalCacheStub:
        def __init__(self):
            self.cleared = 0
            self.cleaned = 0

        def clear_command_cache(self):
            self.cleared += 1

        def cleanup_command_cache(self):
            self.cleaned += 1

    service.terminal_detector = TerminalCacheStub()

    payload = service.detect_activity()

    assert payload is not None
    assert payload["details"] == "Manual presence"
    assert service.terminal_detector.cleared == 1
    assert service.terminal_detector.cleaned == 0
