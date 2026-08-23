from detectors.window import WindowDetector


def test_gnome_wayland_never_guesses_foreground_app(monkeypatch):
    monkeypatch.setenv('XDG_SESSION_TYPE', 'wayland')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'GNOME')
    monkeypatch.delenv('SWAYSOCK', raising=False)
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('shutil.which', lambda command: None)

    detector = WindowDetector()
    capability = detector.capability()

    assert capability['supported'] is False
    assert capability['backend'] == 'unavailable'
    assert 'does not expose' in capability['reason']
    assert detector.get_active_window() is None


def test_installed_swaymsg_is_not_used_outside_sway(monkeypatch):
    monkeypatch.setenv('XDG_SESSION_TYPE', 'wayland')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'GNOME')
    monkeypatch.delenv('SWAYSOCK', raising=False)
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('shutil.which', lambda command: '/usr/bin/swaymsg' if command == 'swaymsg' else None)

    detector = WindowDetector()
    assert detector.capability()['supported'] is False
    assert detector.get_active_window() is None
