from pathlib import Path


def test_league_integration_stays_local_http_only_and_avoids_game_tampering():
    source = (Path(__file__).resolve().parents[1] / 'league_client.py').read_text(encoding='utf-8').lower()

    assert "https://127.0.0.1:2999/liveclientdata" in source
    for forbidden in (
        'readprocessmemory',
        'writeprocessmemory',
        'openprocess(',
        'createremotethread',
        'virtualallocex',
        'pymem',
        'frida',
        'dllinject',
        'sendinput',
        'pyautogui',
        'packet capture',
        'scapy',
    ):
        assert forbidden not in source


def test_league_snapshot_does_not_publish_identity_or_competitive_stats():
    source = (Path(__file__).resolve().parents[1] / 'league_client.py').read_text(encoding='utf-8')
    retained_block = source.split("snapshot = {", 1)[1].split("}", 1)[0]
    for forbidden in (
        'riotId', 'summonerName', 'kills', 'deaths', 'assists',
        'items', 'runes', 'enemy', 'scores',
    ):
        assert forbidden not in retained_block
