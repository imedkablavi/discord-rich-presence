"""Fail-closed regression tests for CS2 GSI auto-configuration."""

from unittest.mock import Mock

from config import Config
from cs2_gsi import CS2GSIBridge
import cs2_gsi as cs2_gsi_module
import detectors.gaming as gaming_module


def test_malformed_gsi_enabled_value_fails_closed(monkeypatch, tmp_path):
    config = Config(tmp_path / 'config.yaml')
    config.set('rules.enabled_detectors.gaming', True)
    config.set('cs2_gsi.enabled', 'false')

    get_bridge = Mock()
    monkeypatch.setattr(gaming_module, 'get_cs2_gsi', get_bridge)

    detector = gaming_module.GamingDetector(config)

    assert detector.cs2_gsi is None
    get_bridge.assert_not_called()


def test_malformed_auto_install_value_does_not_write_game_config(monkeypatch, tmp_path):
    config = Config(tmp_path / 'config.yaml')
    config.set('rules.enabled_detectors.gaming', True)
    config.set('cs2_gsi.enabled', True)
    config.set('cs2_gsi.auto_install', 'true')

    candidate = Mock()
    candidate.start.return_value = True
    monkeypatch.setattr(
        gaming_module,
        'get_cs2_gsi',
        lambda _config, start=False: candidate,
    )
    discover = Mock(return_value=[tmp_path / 'cfg'])
    install = Mock()
    monkeypatch.setattr(gaming_module, 'discover_cs2_cfg_dirs', discover)
    monkeypatch.setattr(gaming_module, 'install_gsi_config', install)

    detector = gaming_module.GamingDetector(config)

    assert detector.cs2_gsi is candidate
    candidate.start.assert_called_once_with()
    discover.assert_not_called()
    install.assert_not_called()


def test_auto_install_is_skipped_and_stale_cfg_removed_when_listener_cannot_bind(
    monkeypatch,
    tmp_path,
):
    config = Config(tmp_path / 'config.yaml')
    config.set('rules.enabled_detectors.gaming', True)
    config.set('cs2_gsi.enabled', True)
    config.set('cs2_gsi.auto_install', True)

    candidate = Mock()
    candidate.start.return_value = False
    monkeypatch.setattr(
        gaming_module,
        'get_cs2_gsi',
        lambda _config, start=False: candidate,
    )

    cfg_dir = tmp_path / 'game' / 'csgo' / 'cfg'
    cfg_dir.mkdir(parents=True)
    stale_cfg = cfg_dir / 'gamestate_integration_cybrex.cfg'
    stale_cfg.write_text('stale', encoding='utf-8')
    discover = Mock(return_value=[cfg_dir])
    install = Mock()
    monkeypatch.setattr(gaming_module, 'discover_cs2_cfg_dirs', discover)
    monkeypatch.setattr(gaming_module, 'install_gsi_config', install)

    detector = gaming_module.GamingDetector(config)

    assert detector.cs2_gsi is None
    candidate.start.assert_called_once_with()
    discover.assert_called_once_with()
    assert not stale_cfg.exists()
    install.assert_not_called()


def test_auto_install_only_runs_after_listener_ownership_is_verified(monkeypatch, tmp_path):
    config = Config(tmp_path / 'config.yaml')
    config.set('rules.enabled_detectors.gaming', True)
    config.set('cs2_gsi.enabled', True)
    config.set('cs2_gsi.auto_install', True)

    candidate = Mock()
    candidate.start.return_value = True
    monkeypatch.setattr(
        gaming_module,
        'get_cs2_gsi',
        lambda _config, start=False: candidate,
    )

    cfg_dir = tmp_path / 'game' / 'csgo' / 'cfg'
    cfg_dir.mkdir(parents=True)
    monkeypatch.setattr(gaming_module, 'discover_cs2_cfg_dirs', lambda: [cfg_dir])
    install = Mock(return_value=cfg_dir / 'gamestate_integration_cybrex.cfg')
    monkeypatch.setattr(gaming_module, 'install_gsi_config', install)

    detector = gaming_module.GamingDetector(config)

    assert detector.cs2_gsi is candidate
    candidate.start.assert_called_once_with()
    install.assert_called_once_with(config, cfg_dir)


def test_stale_gsi_snapshot_is_expired_and_removed(monkeypatch, tmp_path):
    config = Config(tmp_path / 'config.yaml')
    config.set('cs2_gsi.ttl_secs', 5)
    bridge = CS2GSIBridge(config)

    clock = [100.0]
    monkeypatch.setattr(cs2_gsi_module.time, 'monotonic', lambda: clock[0])
    bridge.update({
        'provider': {'appid': 730},
        'map': {'name': 'de_mirage', 'mode': 'competitive'},
        'player': {'team': 'CT', 'activity': 'playing'},
        'auth': {'token': bridge.token},
    })

    assert bridge.latest() is not None
    clock[0] = 106.0
    assert bridge.latest() is None
    assert bridge.status()['connected'] is False
