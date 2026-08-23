from pathlib import Path

import startup


def test_linux_autostart_create_and_remove(monkeypatch, tmp_path: Path):
    target = tmp_path / 'autostart' / 'discord-rich-presence.desktop'
    monkeypatch.setattr(startup.sys, 'platform', 'linux')
    monkeypatch.setattr(startup, '_linux_autostart_path', lambda: target)
    monkeypatch.setattr(startup, 'startup_command', lambda: ['/opt/drp/DiscordRichPresence', '--tray'])

    startup.set_enabled(True)
    assert startup.is_enabled() is True
    text = target.read_text(encoding='utf-8')
    assert 'Exec=/opt/drp/DiscordRichPresence --tray' in text
    assert 'X-GNOME-Autostart-enabled=true' in text

    startup.set_enabled(False)
    assert startup.is_enabled() is False
    assert not target.exists()
