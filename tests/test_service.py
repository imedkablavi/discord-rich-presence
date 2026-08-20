import logging

from main import DiscordRichPresenceService


class FakeRPC:
    def __init__(self):
        self.cleared = 0
        self.updated = []

    def clear(self):
        self.cleared += 1

    def update(self, **payload):
        self.updated.append(payload)

    def close(self):
        pass


def _service():
    service = DiscordRichPresenceService.__new__(DiscordRichPresenceService)
    service.dry_run = False
    service.connected = True
    service.rpc = FakeRPC()
    service.presence_active = True
    service.last_payload = {'details': 'old', 'buttons': [{'label': 'A', 'url': 'https://a.test'}]}
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
