import json
from pathlib import Path
from types import SimpleNamespace

from config import Config
from detectors.gaming import GamingDetector
from epic_catalog import EpicGameCatalog
from heroic_catalog import HeroicGameCatalog
import epic_catalog
import heroic_catalog


def test_epic_manifest_resolves_foreground_game_by_install_path(monkeypatch, tmp_path: Path):
    manifests = tmp_path / 'ProgramData/Epic/EpicGamesLauncher/Data/Manifests'
    manifests.mkdir(parents=True)
    install = tmp_path / 'Games/Fortnite'
    exe = install / 'FortniteGame/Binaries/Win64/FortniteClient-Win64-Shipping.exe'
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b'')
    (manifests / 'fortnite.item').write_text(json.dumps({
        'AppName': 'Fortnite',
        'DisplayName': 'Fortnite',
        'InstallLocation': str(install),
    }), encoding='utf-8')

    monkeypatch.setattr(epic_catalog, '_manifest_dirs', lambda: [manifests])
    catalog = EpicGameCatalog()
    monkeypatch.setattr(epic_catalog, '_process_path', lambda pid: exe)

    game = catalog.resolve({'app_name': 'FortniteClient-Win64-Shipping', 'pid': 42})
    assert game is not None
    assert game.name == 'Fortnite'
    assert game.app_name == 'Fortnite'


def test_epic_catalog_filters_engine_manifests(monkeypatch, tmp_path: Path):
    manifests = tmp_path / 'Manifests'
    manifests.mkdir()
    engine = tmp_path / 'Epic/UE_5.8'
    engine.mkdir(parents=True)
    (manifests / 'engine.item').write_text(json.dumps({
        'AppName': 'UE_5.8',
        'DisplayName': 'Unreal Engine 5.8',
        'InstallLocation': str(engine),
    }), encoding='utf-8')

    monkeypatch.setattr(epic_catalog, '_manifest_dirs', lambda: [manifests])
    catalog = EpicGameCatalog()
    assert catalog._games == []


def test_epic_catalog_rejects_filesystem_root_install_location(monkeypatch, tmp_path: Path):
    manifests = tmp_path / 'Manifests'
    manifests.mkdir()
    root = Path(tmp_path.anchor or '/')
    (manifests / 'bad.item').write_text(json.dumps({
        'AppName': 'BadRoot',
        'DisplayName': 'Bad Root Game',
        'InstallLocation': str(root),
    }), encoding='utf-8')

    monkeypatch.setattr(epic_catalog, '_manifest_dirs', lambda: [manifests])
    catalog = EpicGameCatalog()
    assert catalog._games == []


def test_heroic_legendary_installed_json_resolves_executable_name(monkeypatch, tmp_path: Path):
    install = tmp_path / 'Games/HeroicExample'
    install.mkdir(parents=True)
    installed = tmp_path / 'legendary/installed.json'
    installed.parent.mkdir(parents=True)
    installed.write_text(json.dumps({
        'HeroicExample': {
            'app_name': 'HeroicExample',
            'title': 'A Heroic Game',
            'install_path': str(install),
            'executable': 'Game/Binaries/HeroicExample-Win64-Shipping.exe',
            'is_dlc': False,
        }
    }), encoding='utf-8')

    monkeypatch.setattr(heroic_catalog, '_installed_json_paths', lambda: [installed])
    catalog = HeroicGameCatalog()
    game = catalog.resolve({
        'app_name': 'HeroicExample-Win64-Shipping.exe',
        'pid': None,
    })
    assert game is not None
    assert game.name == 'A Heroic Game'
    assert game.app_name == 'HeroicExample'


def test_heroic_catalog_ignores_dlc(monkeypatch, tmp_path: Path):
    install = tmp_path / 'Games/Base'
    install.mkdir(parents=True)
    installed = tmp_path / 'installed.json'
    installed.write_text(json.dumps({
        'DLC': {
            'app_name': 'DLC',
            'title': 'Expansion DLC',
            'install_path': str(install),
            'executable': 'dlc.exe',
            'is_dlc': True,
        }
    }), encoding='utf-8')

    monkeypatch.setattr(heroic_catalog, '_installed_json_paths', lambda: [installed])
    catalog = HeroicGameCatalog()
    assert catalog._games == []


def test_heroic_catalog_rejects_filesystem_root_install_path(monkeypatch, tmp_path: Path):
    installed = tmp_path / 'installed.json'
    root = Path(tmp_path.anchor or '/')
    installed.write_text(json.dumps({
        'BadRoot': {
            'app_name': 'BadRoot',
            'title': 'Bad Root Game',
            'install_path': str(root),
            'executable': 'game.exe',
            'is_dlc': False,
        }
    }), encoding='utf-8')

    monkeypatch.setattr(heroic_catalog, '_installed_json_paths', lambda: [installed])
    catalog = HeroicGameCatalog()
    assert catalog._games == []


def test_gaming_detector_prefers_epic_and_heroic_catalogs_before_aliases(tmp_path: Path):
    config = Config(tmp_path / 'config.yaml')
    config.set('cs2_gsi.enabled', False)
    detector = GamingDetector(config)
    detector.steam_catalog = SimpleNamespace(resolve=lambda info: None)

    epic_game = SimpleNamespace(app_name='EpicInternal', name='Epic Catalog Game')
    detector.epic_catalog = SimpleNamespace(resolve=lambda info: epic_game)
    detector.heroic_catalog = SimpleNamespace(resolve=lambda info: None)
    activity = detector.detect({'app_name': 'unknown.exe', 'pid': 1, 'title': ''})
    assert activity is not None
    assert activity['game_name'] == 'Epic Catalog Game'
    assert activity['game_source'] == 'Epic Games'

    detector.epic_catalog = SimpleNamespace(resolve=lambda info: None)
    heroic_game = SimpleNamespace(app_name='HeroicInternal', name='Heroic Catalog Game')
    detector.heroic_catalog = SimpleNamespace(resolve=lambda info: heroic_game)
    activity = detector.detect({'app_name': 'unknown.exe', 'pid': 2, 'title': ''})
    assert activity is not None
    assert activity['game_name'] == 'Heroic Catalog Game'
    assert activity['game_source'] == 'Heroic'
