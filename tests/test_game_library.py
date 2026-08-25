from pathlib import Path
from types import SimpleNamespace

from config import Config
import game_library


def _config(tmp_path: Path) -> Config:
    return Config(tmp_path / 'config.yaml')


def test_game_toggle_uses_existing_blacklist_contract(tmp_path):
    config = _config(tmp_path)
    config.set('rules.blacklist.games', ['Other Game'])

    game_library.set_game_enabled(config, 'Elden Ring', False, save=False)
    assert not game_library.is_game_enabled(config, 'elden ring')
    assert game_library.is_game_enabled(config, 'Other Game') is False

    game_library.set_game_enabled(config, 'ELDEN RING', True, save=False)
    assert game_library.is_game_enabled(config, 'Elden Ring')
    assert config.get('rules.blacklist.games') == ['Other Game']


def test_gamer_mode_restores_detector_preferences(tmp_path):
    config = _config(tmp_path)
    config.set('rules.enabled_detectors.media', False)
    config.set('rules.enabled_detectors.browser', True)
    config.set('rules.enabled_detectors.coding', True)

    before = dict(config.get('rules.enabled_detectors'))
    game_library.set_gamer_mode(config, True, save=False)

    active = config.get('rules.enabled_detectors')
    assert active['gaming'] is True
    assert all(
        active[name] is False
        for name in ('media', 'terminal', 'coding', 'browser', 'application')
    )
    assert game_library.gamer_mode_enabled(config)

    game_library.set_gamer_mode(config, False, save=False)
    assert config.get('rules.enabled_detectors') == before
    assert not game_library.gamer_mode_enabled(config)


def test_gamer_mode_is_idempotent(tmp_path):
    config = _config(tmp_path)
    before = dict(config.get('rules.enabled_detectors'))
    game_library.set_gamer_mode(config, True, save=False)
    first_snapshot = dict(config.get('gaming.gamer_mode.previous_detectors'))
    game_library.set_gamer_mode(config, True, save=False)
    assert config.get('gaming.gamer_mode.previous_detectors') == first_snapshot
    game_library.set_gamer_mode(config, False, save=False)
    assert config.get('rules.enabled_detectors') == before


def test_gamer_and_companion_settings_survive_save_reload(tmp_path):
    path = tmp_path / 'config.yaml'
    config = Config(path)
    config.set('fivem.port', 32193)
    config.set('fivem.show_server_name', True)
    config.set('minecraft.port', 32194)
    config.set('minecraft.show_server_name', True)
    game_library.set_gamer_mode(config, True, save=False)
    config.save()

    reloaded = Config(path)
    assert reloaded.get('fivem.port') == 32193
    assert reloaded.get('fivem.show_server_name') is True
    assert reloaded.get('minecraft.port') == 32194
    assert reloaded.get('minecraft.show_server_name') is True
    assert reloaded.get('gaming.gamer_mode.enabled') is True
    assert reloaded.get('rules.enabled_detectors.gaming') is True
    assert reloaded.get('rules.enabled_detectors.browser') is False

    game_library.set_gamer_mode(reloaded, False, save=False)
    assert reloaded.get('rules.enabled_detectors.browser') is True
    assert reloaded.get('rules.enabled_detectors.media') is True


def test_discovery_returns_stable_keys_without_install_paths(monkeypatch):
    class FakeSteam:
        def __init__(self):
            self._games = [
                SimpleNamespace(name='Counter-Strike 2', appid=730, install_path=Path('/secret/cs2')),
                SimpleNamespace(name='Elden Ring', appid=1245620, install_path=Path('/secret/elden')),
            ]

        def refresh(self, force=False):
            return None

    class FakeEpic:
        def __init__(self):
            self._games = [
                SimpleNamespace(name='Fortnite', app_name='Fortnite', install_path=Path('/secret/fortnite')),
            ]

        def refresh(self, force=False):
            return None

    class FakeHeroic:
        def __init__(self):
            self._games = [
                SimpleNamespace(name='Hades', app_name='Min', install_path=Path('/secret/hades')),
            ]

        def refresh(self, force=False):
            return None

    monkeypatch.setattr(game_library, 'SteamGameCatalog', FakeSteam)
    monkeypatch.setattr(game_library, 'EpicGameCatalog', FakeEpic)
    monkeypatch.setattr(game_library, 'HeroicGameCatalog', FakeHeroic)

    entries = game_library.discover_games()
    assert {entry.key for entry in entries} == {
        'steam:730', 'steam:1245620', 'epic:fortnite', 'heroic:min'
    }
    cs2 = next(entry for entry in entries if entry.key == 'steam:730')
    assert cs2.enhanced is True
    assert not hasattr(cs2, 'install_path')
    assert all(entry.curated for entry in entries)


def test_library_counts():
    entries = [
        game_library.GameLibraryEntry('a', 'A', 'Steam', True),
        game_library.GameLibraryEntry('b', 'B', 'Steam', False),
        game_library.GameLibraryEntry('c', 'C', 'Epic Games', True),
    ]
    assert game_library.library_counts(entries) == (3, 2)
