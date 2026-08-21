"""Fail-closed regression tests for CS2 GSI auto-configuration."""

from unittest.mock import Mock

from config import Config
import detectors.gaming as gaming_module


def test_auto_install_is_skipped_when_gsi_listener_cannot_bind(monkeypatch, tmp_path):
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

    discover = Mock(return_value=[tmp_path / 'fake-cs2-cfg'])
    install = Mock()
    monkeypatch.setattr(gaming_module, 'discover_cs2_cfg_dirs', discover)
    monkeypatch.setattr(gaming_module, 'install_gsi_config', install)

    detector = gaming_module.GamingDetector(config)

    assert detector.cs2_gsi is None
    candidate.start.assert_called_once_with()
    discover.assert_not_called()
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
