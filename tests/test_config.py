from pathlib import Path

import pytest

from config import Config, DEFAULT_CONFIG


def test_config_instances_do_not_share_nested_state(tmp_path: Path):
    a = Config(tmp_path / 'a.yaml')
    b = Config(tmp_path / 'b.yaml')
    a.set('privacy.mode', 'strict')
    assert b.get('privacy.mode') == DEFAULT_CONFIG['privacy']['mode']


def test_reload_rebuilds_from_defaults(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text('privacy:\n  mode: strict\n', encoding='utf-8')
    cfg = Config(path)
    assert cfg.get('privacy.mode') == 'strict'

    path.write_text('{}\n', encoding='utf-8')
    cfg.load(path)
    assert cfg.get('privacy.mode') == 'balanced'


def test_invalid_interval_is_rejected(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text('update_interval_secs: banana\n', encoding='utf-8')
    with pytest.raises(ValueError, match='update_interval_secs'):
        Config(path)


def test_button_limits_are_validated(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        'discord:\n'
        '  buttons:\n'
        '    - label: "This label is definitely longer than thirty two characters"\n'
        '      url: "https://example.com"\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='1-32'):
        Config(path)


def test_invalid_privacy_regex_is_rejected(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        'privacy:\n'
        '  redactions:\n'
        '    - regex: "[unterminated"\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='Invalid privacy regex'):
        Config(path)


def test_detector_flags_must_be_boolean(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        'rules:\n'
        '  enabled_detectors:\n'
        '    application: yes-please\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='enabled_detectors.application'):
        Config(path)


def test_terminal_ttl_range_is_validated(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        'rules:\n'
        '  terminal_command_ttl_secs: 999999999\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='terminal_command_ttl_secs'):
        Config(path)


def test_override_urls_must_be_http_or_https(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        'override:\n'
        '  details_url: "file:///etc/passwd"\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='override.details_url'):
        Config(path)


def test_party_current_cannot_exceed_party_max(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        'override:\n'
        '  party_current: 5\n'
        '  party_max: 2\n',
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='party_current'):
        Config(path)
