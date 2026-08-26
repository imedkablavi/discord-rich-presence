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
    if '/' not in installdir and '\\' not in installdir and installdir not in {'.', '..'}:
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


def test_linux_wayland_missing_pid_recovers_one_exact_game_process(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    _write_manifest(steamapps, 393380, 'Squad', 'Squad')

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    monkeypatch.setattr(steam_catalog.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(
        steam_catalog.psutil,
        'process_iter',
        lambda attrs: [SimpleNamespace(info={'pid': 4242, 'name': 'SquadGame.exe'})],
    )
    catalog = SteamGameCatalog()
    monkeypatch.setattr(catalog, '_appid_from_process_tree', lambda pid: 393380 if pid == 4242 else None)

    game = catalog.resolve({'app_name': 'SquadGame.exe', 'pid': None})
    assert game is not None
    assert game.appid == 393380
    assert game.name == 'Squad'


def test_linux_wayland_missing_pid_fails_closed_on_duplicate_process_names(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    _write_manifest(steamapps, 393380, 'Squad', 'Squad')

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    monkeypatch.setattr(steam_catalog.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(
        steam_catalog.psutil,
        'process_iter',
        lambda attrs: [
            SimpleNamespace(info={'pid': 4242, 'name': 'SquadGame.exe'}),
            SimpleNamespace(info={'pid': 4243, 'name': 'SquadGame.exe'}),
        ],
    )
    catalog = SteamGameCatalog()
    calls = {'count': 0}

    def ancestry(_pid):
        calls['count'] += 1
        return 393380

    monkeypatch.setattr(catalog, '_appid_from_process_tree', ancestry)
    assert catalog.resolve({'app_name': 'SquadGame.exe', 'pid': None}) is None
    assert calls['count'] == 0


def test_linux_wayland_missing_pid_never_scans_generic_host_as_game(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    _write_manifest(steamapps, 123456, 'A Browser-Like Game', 'BrowserGame')
    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    monkeypatch.setattr(steam_catalog.platform, 'system', lambda: 'Linux')

    called = {'value': False}

    def process_iter(_attrs):
        called['value'] = True
        return []

    monkeypatch.setattr(steam_catalog.psutil, 'process_iter', process_iter)
    catalog = SteamGameCatalog()
    assert catalog.resolve({'app_name': 'chrome', 'pid': None}) is None
    assert called['value'] is False


def test_catalog_filters_steam_runtime_tools(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    _write_manifest(steamapps, 123, 'Proton Experimental', 'Proton Experimental')
    _write_manifest(steamapps, 124, 'Steamworks Common Redistributables', 'Steamworks Shared')

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    catalog = SteamGameCatalog()

    assert catalog.by_appid(123) is None
    assert catalog.by_appid(124) is None


def test_catalog_rejects_manifest_installdir_traversal(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    outside = tmp_path / 'outside'
    outside.mkdir()
    _write_manifest(steamapps, 991001, 'Traversal Game', '../outside')

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    catalog = SteamGameCatalog()

    assert catalog.by_appid(991001) is None


def test_catalog_rejects_nested_or_absolute_installdir(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    _write_manifest(steamapps, 991002, 'Nested Game', 'nested/game')
    absolute = tmp_path / 'absolute-game'
    absolute.mkdir()
    _write_manifest(steamapps, 991003, 'Absolute Game', str(absolute))

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    catalog = SteamGameCatalog()

    assert catalog.by_appid(991002) is None
    assert catalog.by_appid(991003) is None


def test_catalog_ignores_missing_install_directory(monkeypatch, tmp_path: Path):
    root = tmp_path / 'Steam'
    steamapps = root / 'steamapps'
    steamapps.mkdir(parents=True)
    manifest = steamapps / 'appmanifest_991004.acf'
    manifest.write_text(
        '"AppState"\n{\n'
        '    "appid" "991004"\n'
        '    "name" "Missing Game"\n'
        '    "installdir" "NoLongerInstalled"\n'
        '}\n',
        encoding='utf-8',
    )

    monkeypatch.setattr(steam_catalog, '_steamapps_locations', lambda: [(root, steamapps)])
    catalog = SteamGameCatalog()

    assert catalog.by_appid(991004) is None


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
