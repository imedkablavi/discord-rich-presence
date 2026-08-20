import json
import subprocess

from detectors.window import WindowDetector


def test_kde_wayland_uses_kdotool(monkeypatch):
    monkeypatch.setenv('XDG_SESSION_TYPE', 'wayland')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'KDE')
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('shutil.which', lambda command: '/usr/bin/kdotool' if command == 'kdotool' else None)

    payload = {
        'window_id': '{abc-def}',
        'app_name': 'org.kde.konsole',
        'title': 'cybrex@CybrexTech: ~/discord-rich-presence',
        'pid': 4242,
    }

    def fake_run(args, **kwargs):
        assert args[0:3] == ['kdotool', 'kwinscript', '--inline']
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(payload) + '\n', stderr='')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    detector = WindowDetector()

    assert detector.get_active_window() == payload


def test_kde_wayland_without_kdotool_returns_none(monkeypatch):
    monkeypatch.setenv('XDG_SESSION_TYPE', 'wayland')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'KDE')
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('shutil.which', lambda command: None)

    detector = WindowDetector()

    assert detector.get_active_window() is None
