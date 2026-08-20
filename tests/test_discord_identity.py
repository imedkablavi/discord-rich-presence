from pathlib import Path

import pytest
import yaml

from config import BUILTIN_DISCORD_APPLICATION_ID, Config


def test_default_config_uses_built_in_discord_application_id(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')

    assert 'client_id' not in cfg.data['discord']
    assert cfg.get('discord.client_id') == BUILTIN_DISCORD_APPLICATION_ID
    assert cfg.get('discord.application_id_override') == ''


def test_legacy_built_in_client_id_is_removed_on_load(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        yaml.safe_dump({'discord': {'client_id': BUILTIN_DISCORD_APPLICATION_ID}}),
        encoding='utf-8',
    )

    cfg = Config(path)

    assert 'client_id' not in cfg.data['discord']
    assert cfg.get('discord.application_id_override') == ''
    assert cfg.get('discord.client_id') == BUILTIN_DISCORD_APPLICATION_ID


def test_legacy_custom_client_id_migrates_to_advanced_override(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    custom_id = '123456789012345678'
    path.write_text(
        yaml.safe_dump({'discord': {'client_id': custom_id}}),
        encoding='utf-8',
    )

    cfg = Config(path)

    assert 'client_id' not in cfg.data['discord']
    assert cfg.get('discord.application_id_override') == custom_id
    assert cfg.get('discord.client_id') == custom_id


def test_application_id_override_must_be_numeric_when_set(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        yaml.safe_dump({'discord': {'application_id_override': 'not-an-id'}}),
        encoding='utf-8',
    )

    with pytest.raises(ValueError, match='application_id_override'):
        Config(path)
