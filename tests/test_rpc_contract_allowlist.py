from pypresence.types import ActivityType

from rpc_contract import sanitize_rpc_payload


def test_unknown_detector_metadata_never_reaches_presence_update():
    payload = sanitize_rpc_payload({
        'activity_type': ActivityType.PLAYING,
        'details': 'Working',
        'state': 'Project',
        'source': 'browser-companion',
        'raw_url': 'https://example.com/private',
        'debug': {'secret': 'value'},
        'unexpected_kwarg': True,
    })

    assert payload == {
        'activity_type': ActivityType.PLAYING,
        'details': 'Working',
        'state': 'Project',
    }


def test_invalid_activity_type_is_dropped_before_pypresence():
    payload = sanitize_rpc_payload({
        'activity_type': 'PLAYING',
        'details': 'Working',
    })

    assert 'activity_type' not in payload
    assert payload['details'] == 'Working'
