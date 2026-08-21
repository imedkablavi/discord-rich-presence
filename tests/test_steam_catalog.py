from pathlib import Path
from types import SimpleNamespace

from config import Config
from detectors.gaming import GamingDetector
from steam_catalog import SteamGameCatalog
import steam_catalog


def _write_manifest(steamapps: Path, appid: int, name: str, installdir: str) -> Path:
    steamapps.mkdir(parents=True, exist_ok=True)
    manifest = steamapps / f'appmanifest_{appid}.acf'
    manifest.write_text(
        '"AppState"\n'
        '{\n'
        f'    "appid" "{appid}"\n'
        f'    "name" "{name}"\n'
        f'    "installdir" "{installdir}"\n'
        '}\n',
        encoding='utf-8',
    )
    (steamapps / 'common' / installdir).mkdir(parents=True, exist_ok=True)
    return manifest


def test_catalog_resolves_any_installed_steam_app_class(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    _write_manifest(steamapps, 999001, 'A Game Not Hardcoded Anywhere', 'UnknownGame')

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    catalog = SteamGameCatalog()

    game = catalog.resolve({'app_name': 'steam_app_999001', 'pid': None})
    assert game is not None
    assert game.appid == 999001
    assert game.name == 'A Game Not Hardcoded Anywhere'
    assert game.install_path == steamapps / 'common' / 'UnknownGame'
    assert game.artwork_url.endswith('/steam/apps/999001/header.jpg')


def test_catalog_resolves_windows_style_foreground_exe_by_install_path(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    _write_manifest(steamapps, 888002, 'Path Matched Game', 'PathGame')
    exe = steamapps / 'common' / 'PathGame' / 'bin' / 'game.exe'
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_bytes(b'')

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    catalog = SteamGameCatalog()
    monkeypatch.setattr(catalog, '_process_path', lambda pid: exe)
    monkeypatch.setattr(catalog, '_appid_from_process_tree', lambda pid: None)

    game = catalog.resolve({'app_name': 'game', 'pid': 1234})
    assert game is not None
    assert game.appid == 888002
    assert game.name == 'Path Matched Game'


def test_catalog_filters_steam_runtime_tools(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    _write_manifest(steamapps, 123, 'Proton Experimental', 'Proton Experimental')
    _write_manifest(steamapps, 124, 'Steamworks Common Redistributables', 'Steamworks Shared')

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    catalog = SteamGameCatalog()

    assert catalog.by_appid(123) is None
    assert catalog.by_appid(124) is None


def test_gaming_detector_uses_generic_steam_catalog_metadata(tmp_path: Path):
    config = Config(tmp_path / 'config.yaml')
    config.set('cs2_gsi.enabled', False)
    detector = GamingDetector(config)
    game = SimpleNamespace(
        appid=424242,
        name='Generic Steam Game',
        artwork_url='https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/424242/header.jpg',
    )
    detector.steam_catalog = SimpleNamespace(resolve=lambda info: game)

    activity = detector.detect({'app_name': 'totally_unknown_process', 'title': '', 'pid': 99})
    assert activity is not None
    assert activity['game_name'] == 'Generic Steam Game'
    assert activity['steam_appid'] == 424242
    assert activity['game_source'] == 'Steam'
    assert activity['launcher'] == 'Steam'
    assert activity['store_url'] == 'https://store.steampowered.com/app/424242/'


def test_csgo_title_fallback_normalizes_to_counter_strike_2():
    assert GamingDetector._extract_game_from_title('CS GO Steam') == 'Counter-Strike 2'
    assert GamingDetector._extract_game_from_title('Counter-Strike 2 - Steam') == 'Counter-Strike 2'
    assert GamingDetector._extract_game_from_title('Library - Steam') is None
