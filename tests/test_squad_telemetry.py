from pathlib import Path

import squad_telemetry
from squad_telemetry import SquadTelemetryReader, discover_squad_log_paths, parse_squad_log_tail


def test_parses_current_layer_map_mode_and_joined_server():
    log = r'''
[2026.08.27-00.00.01:000][100]LogEOS: Session search result: ServerName_s="Wrong Browser Result"
[2026.08.27-00.00.05:000][101]LogOnlineSession: JoinSession complete
[2026.08.27-00.00.05:100][101]LogOnlineSession: ServerName_s="EU Tactical Server #1"
[2026.08.27-00.00.05:110][101]LogOnlineSession: PlayerCount_l=78 MaxPlayers_l=100 QueueCount_l=4
[2026.08.27-00.00.06:000][102]LogWorld: StartLoadingDestination to: Yehorivka_RAAS_v2
'''
    snapshot = parse_squad_log_tail(log)
    assert snapshot['squad_telemetry'] is True
    assert snapshot['layer'] == 'Yehorivka_RAAS_v2'
    assert snapshot['map'] == 'Yehorivka'
    assert snapshot['mode'] == 'RAAS'
    assert snapshot['server_name'] == 'EU Tactical Server #1'
    assert snapshot['player_count'] == 78
    assert snapshot['max_players'] == 100
    assert snapshot['queue'] == 4


def test_newer_disconnect_clears_stale_match_metadata():
    log = '''
LogOnlineSession: JoinSession complete
LogOnlineSession: ServerName_s="Example Server"
LogWorld: StartLoadingDestination to: AlBasrah_Invasion_v3
LogNet: Disconnected from server
'''
    assert parse_squad_log_tail(log) == {}


def test_main_menu_after_match_clears_old_layer():
    log = '''
LogOnlineSession: JoinSession complete
LogWorld: StartLoadingDestination to: TallilOutskirts_AAS_v1
LogWorld: StartLoadingDestination to: /Game/_Main/Maps/MainMenu
'''
    assert parse_squad_log_tail(log) == {}


def test_server_browser_result_alone_is_not_publishable_session():
    log = '''
LogEOS: Session search result ServerName_s="Random Server"
LogEOS: MapName_s="Gorodok" GameMode_s="RAAS"
'''
    assert parse_squad_log_tail(log) == {}


def test_parser_never_returns_network_or_account_identifiers():
    log = '''
LogOnlineSession: JoinSession complete
LogOnlineSession: ServerName_s="Community Server"
LogNet: RemoteAddr=203.0.113.22:7787 EOSID=aaaaaaaa SteamID=76561198000000000
LogWorld: StartLoadingDestination to: Sanxian_RAAS_v1
'''
    snapshot = parse_squad_log_tail(log)
    serialized = repr(snapshot)
    assert '203.0.113.22' not in serialized
    assert '76561198000000000' not in serialized
    assert 'aaaaaaaa' not in serialized
    assert snapshot['map'] == 'Sanxian Islands'


def test_windows_log_discovery_uses_localappdata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(squad_telemetry.platform, 'system', lambda: 'Windows')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    paths = discover_squad_log_paths()
    assert paths == (tmp_path / 'SquadGame' / 'Saved' / 'Logs' / 'SquadGame.log',)


def test_reader_caches_unchanged_log(monkeypatch, tmp_path: Path):
    log_path = tmp_path / 'SquadGame.log'
    log_path.write_text(
        'LogOnlineSession: JoinSession complete\n'
        'LogWorld: StartLoadingDestination to: Gorodok_AAS_v2\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(squad_telemetry, 'discover_squad_log_paths', lambda _game=None: (log_path,))

    calls = {'count': 0}
    original = squad_telemetry._read_tail

    def counted(path):
        calls['count'] += 1
        return original(path)

    monkeypatch.setattr(squad_telemetry, '_read_tail', counted)
    reader = SquadTelemetryReader()
    assert reader.snapshot()['map'] == 'Gorodok'
    assert reader.snapshot()['map'] == 'Gorodok'
    assert calls['count'] == 1
