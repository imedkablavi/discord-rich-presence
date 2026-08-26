import logging
import threading

from main import DiscordRichPresenceService


class FakeRPC:
    def __init__(self):
        self.updated = []
        self.closed = 0

    def update(self, **payload):
        self.updated.append(payload)

    def close(self):
        self.closed += 1


class DummyBuilder:
    def reload(self):
        return None


def _service(dry_run=False):
    service = DiscordRichPresenceService.__new__(DiscordRichPresenceService)
    service.dry_run = dry_run
    service.connected = True
    service.rpc = FakeRPC()
    service.presence_active = False
    service.last_payload = None
    service.runtime = None
    service._stop_event = threading.Event()
    service.reconnect_delay = 5
    service.max_reconnect_delay = 300
    service.logger = logging.getLogger('release-safety-test')
    return service


def test_final_rpc_guard_also_covers_manual_override_payloads():
    service = _service()
    assert service.update_presence({
        'details': 'x',
        'state': 'valid state',
        'large_image': 'app',
        'large_text': 'X',
        'details_url': 'file:///secret',
    }) is True

    sent = service.rpc.updated[-1]
    assert 'details' not in sent
    assert sent['state'] == 'valid state'
    assert sent['large_text'] == 'X.com'
    assert 'details_url' not in sent


def test_presence_debug_log_does_not_include_payload_values(caplog):
    service = _service()
    secret_title = 'SECRET-PAGE-TITLE-123'
    secret_url = 'https://example.com/?token=SECRET-TOKEN-456'
    with caplog.at_level(logging.DEBUG):
        assert service.update_presence({
            'details': secret_title,
            'state': 'Browser',
            'details_url': secret_url,
        }) is True

    text = caplog.text
    assert 'Updated presence:' in text
    assert secret_title not in text
    assert secret_url not in text
    assert 'SECRET-TOKEN-456' not in text


def test_should_update_compares_sanitized_payloads():
    service = _service()
    service.presence_active = True
    service.last_payload = {'state': 'valid state', 'large_text': 'X.com'}
    assert service.should_update({
        'details': 'x',
        'state': 'valid state',
        'large_text': 'X',
    }) is False
