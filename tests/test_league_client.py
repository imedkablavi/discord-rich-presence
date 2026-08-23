from league_client import LeagueLiveClient


class FakeLeague(LeagueLiveClient):
    def __init__(self):
        super().__init__()
        self.responses = {
            '/gamestats': {
                'gameMode': 'CLASSIC',
                'gameTime': 321.9,
                'mapName': 'Map11',
            },
            '/activeplayername': 'Player One#EUW',
            '/playerlist': [
                {
                    'riotId': 'Enemy#EUW',
                    'championName': 'Zed',
                    'position': 'MIDDLE',
                    'scores': {'kills': 99},
                },
                {
                    'riotId': 'Player One#EUW',
                    'summonerName': 'legacy-name',
                    'championName': 'Ahri',
                    'position': 'MIDDLE',
                    'scores': {'kills': 7},
                    'items': [{'itemID': 1}],
                },
            ],
        }

    def _get_json(self, endpoint):
        return self.responses.get(endpoint)


def test_snapshot_keeps_only_display_safe_local_player_context():
    client = FakeLeague()
    snapshot = client.snapshot()
    assert snapshot == {
        'champion': 'Ahri',
        'position': 'Mid',
        'mode': "Summoner's Rift",
        'game_time': 321,
    }
    assert 'riotId' not in snapshot
    assert 'scores' not in snapshot
    assert 'items' not in snapshot
    assert 'Zed' not in snapshot.values()


def test_snapshot_fails_closed_when_local_player_cannot_be_identified():
    client = FakeLeague()
    client.responses['/activeplayername'] = 'Unknown#EUW'
    assert client.snapshot() is None


def test_endpoint_guard_rejects_non_relative_paths():
    client = LeagueLiveClient()
    assert client._get_json('https://example.com/') is None
    assert client._get_json('/../secret') is None
