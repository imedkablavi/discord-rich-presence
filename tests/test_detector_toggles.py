from main import DiscordRichPresenceService


class FakeConfig:
    def __init__(self, enabled):
        self.enabled = dict(enabled)

    def get(self, key, default=None):
        values = {
            'override.enabled': False,
            'rules.clear_on_lock_screen': False,
            'rules.enabled_detectors': self.enabled,
            'rules.whitelist.apps': [],
            'rules.blacklist.apps': [],
            'rules.whitelist.games': [],
            'rules.blacklist.games': [],
            'rules.whitelist.sites': [],
            'rules.blacklist.sites': [],
        }
        return values.get(key, default)


class Window:
    def get_active_window(self):
        return {'app_name': 'TestApp', 'title': 'Test window'}


class MustNotRun:
    def detect(self, _window):
        raise AssertionError('disabled detector was executed')


class Coding:
    def __init__(self):
        self.calls = 0

    def detect(self, _window):
        self.calls += 1
        return {'type': 'coding', 'app_name': 'Code', 'project': 'demo'}


class Builder:
    def build(self, activity):
        return {'details': f"Detected {activity['type']}"}


def service_for(enabled):
    service = DiscordRichPresenceService.__new__(DiscordRichPresenceService)
    service.config = FakeConfig(enabled)
    service.privacy_override = None
    service._last_config_mtime = None
    service.window_detector = Window()
    service.gaming_detector = MustNotRun()
    service.media_detector = MustNotRun()
    service.terminal_detector = MustNotRun()
    service.coding_detector = MustNotRun()
    service.browser_detector = MustNotRun()
    service.presence_builder = Builder()
    return service


def test_all_disabled_detectors_are_not_executed():
    service = service_for({
        'gaming': False,
        'media': False,
        'terminal': False,
        'coding': False,
        'browser': False,
        'application': False,
    })

    assert service.detect_activity() is None


def test_only_enabled_detector_is_executed():
    service = service_for({
        'gaming': False,
        'media': False,
        'terminal': False,
        'coding': True,
        'browser': False,
        'application': False,
    })
    coding = Coding()
    service.coding_detector = coding

    assert service.detect_activity() == {'details': 'Detected coding'}
    assert coding.calls == 1


def test_missing_detector_key_defaults_to_disabled():
    service = service_for({'application': False})

    assert service._detector_enabled('browser') is False
