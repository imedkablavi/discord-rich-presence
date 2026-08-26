from pathlib import Path

from config import BUILTIN_DISCORD_APPLICATION_ID, Config


def test_nested_get_set_contract(tmp_path: Path):
    config = Config(tmp_path / 'config.yaml')
    assert config.get('rules.enabled_detectors.gaming') is True
    assert config.get('missing.value', 'fallback') == 'fallback'

    config.set('rules.blacklist.games', ['Example Game'])
    config.set('fivem.show_server_name', True)

    assert config.get('rules.blacklist.games') == ['Example Game']
    assert config.get('fivem.show_server_name') is True


def test_save_reload_preserves_runtime_settings(tmp_path: Path):
    path = tmp_path / 'config.yaml'
    config = Config(path)
    config.set('minecraft.show_server_name', True)
    config.set('rules.blacklist.games', ['Example Game'])
    config.save()

    reloaded = Config(path)
    assert reloaded.get('minecraft.show_server_name') is True
    assert reloaded.get('rules.blacklist.games') == ['Example Game']


def test_legacy_client_id_read_uses_builtin_or_override(tmp_path: Path):
    config = Config(tmp_path / 'config.yaml')
    assert config.get('discord.client_id') == BUILTIN_DISCORD_APPLICATION_ID

    config.set('discord.application_id_override', '12345678901234567')
    assert config.get('discord.client_id') == '12345678901234567'
