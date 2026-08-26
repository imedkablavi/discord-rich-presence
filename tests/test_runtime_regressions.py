from __future__ import annotations

import importlib

from config_hardening import sanitize_optional_links


def test_invalid_optional_links_are_dropped_without_touching_core_config():
    data = {
        'discord': {
            'buttons': [
                {'label': 'Bad', 'url': 'http://localhost:8080/private'},
                {'label': 'Good', 'url': 'https://github.com/imedkablavi'},
            ]
        },
        'override': {
            'details_url': 'not-a-url',
            'state_url': 'http://example.com/insecure',
            'large_url': 'https://example.com/public',
            'small_url': '',
            'buttons': [{'label': 'Local', 'url': 'https://127.0.0.1/private'}],
        },
        'images': {
            'icon_overrides': {
                'safe-asset': 'discord_asset_key',
                'unsafe-url': 'http://example.com/icon.png',
                'safe-url': 'https://example.com/icon.png',
            }
        },
        'update_interval_secs': 2,
    }

    dropped = sanitize_optional_links(data)

    assert dropped >= 4
    assert data['discord']['buttons'] == [
        {'label': 'Good', 'url': 'https://github.com/imedkablavi'}
    ]
    assert data['override']['details_url'] == ''
    assert data['override']['state_url'] == ''
    assert data['override']['large_url'] == 'https://example.com/public'
    assert data['override']['buttons'] == []
    assert data['images']['icon_overrides'] == {
        'safe-asset': 'discord_asset_key',
        'safe-url': 'https://example.com/icon.png',
    }
    assert data['update_interval_secs'] == 2


def test_hardened_config_validation_keeps_service_startable(tmp_path):
    import config
    import config_hardening

    # Reload so this test owns a fresh Config class before applying the wrapper.
    importlib.reload(config)
    importlib.reload(config_hardening)
    config_hardening.apply_config_hardening()

    cfg = config.Config(tmp_path / 'config.yaml')
    cfg.set('override.details_url', 'definitely not a URL')
    cfg.set('discord.buttons', [{'label': 'Broken', 'url': 'http://localhost/x'}])
    cfg.save()

    reloaded = config.Config(tmp_path / 'config.yaml')
    assert reloaded.get('override.details_url') == ''
    assert reloaded.get('discord.buttons') == []
    assert reloaded.get('discord.client_id')


def test_linux_media_detector_has_no_persistent_pydbus_proxy(monkeypatch):
    from detectors import media

    class DummyConfig:
        def get(self, _key, default=None):
            return default

    monkeypatch.setattr(media.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(media.shutil, 'which', lambda _name: None)
    monkeypatch.setattr(media, 'get_browser_companion', lambda *_args, **_kwargs: None)

    detector = media.MediaDetector(DummyConfig())

    assert detector.platform_name == 'linux'
    assert detector.playerctl_available is False
    assert not hasattr(detector, 'bus')
    assert not hasattr(detector, 'dbus_available')
    assert detector.detect({'app_name': 'Brave', 'title': 'Example'}) is None
