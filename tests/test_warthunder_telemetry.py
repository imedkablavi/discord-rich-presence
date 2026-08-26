import warthunder_telemetry
from warthunder_telemetry import WarThunderTelemetryReader, read_warthunder_snapshot


def test_valid_ground_snapshot_uses_only_safe_presence_fields(monkeypatch):
    def fake(path):
        if path == '/indicators':
            return {
                'valid': True,
                'army': 'tank',
                'type': 'tankModels/ussr_t_80bvm',
                'speed': 42.0,
                'crew_current': 3,
            }
        return {'status': 'running', 'objectives': ['sensitive-ish tactical data']}

    monkeypatch.setattr(warthunder_telemetry, '_request_json', fake)
    snapshot = read_warthunder_snapshot()
    assert snapshot == {
        'warthunder_telemetry': True,
        'branch': 'Ground',
        'vehicle': 'T 80bvm',
        'vehicle_id': 'ussr_t_80bvm',
        'mission_status': 'running',
    }
    serialized = repr(snapshot).lower()
    assert 'speed' not in serialized
    assert 'crew' not in serialized
    assert 'objective' not in serialized
    assert 'server' not in serialized
    assert 'map' not in serialized


def test_invalid_indicators_fail_soft_without_querying_mission(monkeypatch):
    paths = []

    def fake(path):
        paths.append(path)
        return {'valid': False}

    monkeypatch.setattr(warthunder_telemetry, '_request_json', fake)
    assert read_warthunder_snapshot() == {}
    assert paths == ['/indicators']


def test_aircraft_without_army_gets_conservative_air_label(monkeypatch):
    monkeypatch.setattr(
        warthunder_telemetry,
        '_request_json',
        lambda path: {'valid': True, 'type': 'so_4050_vautour_2a_iaf'} if path == '/indicators' else {},
    )
    snapshot = read_warthunder_snapshot()
    assert snapshot['branch'] == 'Air'
    assert snapshot['vehicle'] == 'So 4050 Vautour 2A IAF'


def test_reader_caches_short_interval(monkeypatch):
    calls = {'count': 0}

    def fake():
        calls['count'] += 1
        return {'warthunder_telemetry': True, 'branch': 'Ground'}

    monkeypatch.setattr(warthunder_telemetry, 'read_warthunder_snapshot', fake)
    reader = WarThunderTelemetryReader()
    assert reader.snapshot()['branch'] == 'Ground'
    assert reader.snapshot()['branch'] == 'Ground'
    assert calls['count'] == 1


def test_request_json_rejects_unknown_endpoint():
    assert warthunder_telemetry._request_json('/gamechat') is None
    assert warthunder_telemetry._request_json('/map_obj.json') is None
    assert warthunder_telemetry._request_json('/hudmsg') is None
