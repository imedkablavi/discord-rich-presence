import sys

import launcher


def test_packaged_source_style_service_argument_becomes_tray(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'argv', ['DiscordRichPresence.exe', r'C:\temp\main.py'])

    launcher._normalize_packaged_args()

    assert sys.argv == ['DiscordRichPresence.exe', '--tray']


def test_packaged_explicit_arguments_are_preserved(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'argv', ['DiscordRichPresence.exe', '--dry-run', '--once'])

    launcher._normalize_packaged_args()

    assert sys.argv == ['DiscordRichPresence.exe', '--dry-run', '--once']


def test_source_launcher_does_not_rewrite_arguments(monkeypatch):
    monkeypatch.delattr(sys, 'frozen', raising=False)
    monkeypatch.setattr(sys, 'argv', ['launcher.py', 'main.py'])

    launcher._normalize_packaged_args()

    assert sys.argv == ['launcher.py', 'main.py']



def test_update_service_stop_allows_update_when_no_service_is_active():
    class InactiveRuntime:
        def read_active(self):
            return None

        def terminate_active(self, timeout=5):
            raise AssertionError("inactive service must not be terminated")

    assert launcher._stop_active_service_for_update(InactiveRuntime) is True


def test_update_service_stop_requires_success_for_an_active_service():
    class ActiveRuntime:
        def __init__(self, stop_result):
            self.stop_result = stop_result

        def read_active(self):
            return {"pid": 12345, "state": "running"}

        def terminate_active(self, timeout=5):
            assert timeout == 5
            return self.stop_result

    assert launcher._stop_active_service_for_update(lambda: ActiveRuntime(True)) is True
    assert launcher._stop_active_service_for_update(lambda: ActiveRuntime(False)) is False


def test_update_service_stop_fails_closed_when_runtime_state_is_unavailable():
    def broken_runtime():
        raise OSError("runtime directory is not accessible")

    assert launcher._stop_active_service_for_update(broken_runtime) is False



def test_update_refuses_to_proceed_with_corrupt_runtime_lock(tmp_path):
    class RuntimeWithCorruptLock:
        def __init__(self):
            self.lock_path = tmp_path / "instance.lock"
            self.lock_path.write_text("{not-json", encoding="utf-8")

        def read_active(self):
            return None

        @staticmethod
        def _read_json(_path):
            return None

        @staticmethod
        def _same_process(_record):
            raise AssertionError("corrupt records must be rejected before process checks")

    assert launcher._stop_active_service_for_update(RuntimeWithCorruptLock) is False


def test_update_allows_a_parseable_but_stale_runtime_lock(tmp_path):
    import json

    class RuntimeWithStaleLock:
        def __init__(self):
            self.lock_path = tmp_path / "instance.lock"
            self.lock_path.write_text(
                json.dumps({"pid": 2_000_000_000, "create_time": 1.0}),
                encoding="utf-8",
            )

        def read_active(self):
            return None

        @staticmethod
        def _read_json(path):
            try:
                import json as _json
                return _json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None

        @staticmethod
        def _same_process(_record):
            return False

    assert launcher._stop_active_service_for_update(RuntimeWithStaleLock) is True
