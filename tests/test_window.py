import subprocess

from detectors.window import WindowDetector


def test_kde_wayland_uses_supported_kdotool_commands(monkeypatch):
    monkeypatch.setenv('XDG_SESSION_TYPE', 'wayland')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'KDE')
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('shutil.which', lambda command: '/usr/bin/kdotool' if command == 'kdotool' else None)

    def fake_run(args, **kwargs):
        assert args == [
            'kdotool',
            'getactivewindow',
            'getwindowclassname',
            'getwindowname',
            'getwindowpid',
        ]
        return subprocess.CompletedProcess(
            args,
            0,
            stdout='org.kde.konsole\ndiscord-rich-presence : bash — Konsole\n8975\n',
            stderr='',
        )

    monkeypatch.setattr(subprocess, 'run', fake_run)
    detector = WindowDetector()

    assert detector.get_active_window() == {
        'app_name': 'org.kde.konsole',
        'title': 'discord-rich-presence : bash — Konsole',
        'pid': 8975,
    }


def test_kde_wayland_without_kdotool_returns_none(monkeypatch):
    monkeypatch.setenv('XDG_SESSION_TYPE', 'wayland')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'KDE')
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('shutil.which', lambda command: None)

    detector = WindowDetector()

    assert detector.get_active_window() is None
