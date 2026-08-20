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
