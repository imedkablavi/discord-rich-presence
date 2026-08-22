from rpc_contract import sanitize_rpc_payload


def test_one_character_optional_text_cannot_break_rpc():
    payload = sanitize_rpc_payload({
        'details': 'x',
        'state': 'ok',
        'large_image': 'x',
        'large_text': 'X',
        'small_image': 'c',
        'small_text': 'C',
    })
    assert 'details' not in payload
    assert payload['state'] == 'ok'
    assert payload['large_text'] == 'X.com'
    assert payload['small_text'] == 'C language'


def test_invalid_urls_buttons_and_timestamps_are_removed():
    payload = sanitize_rpc_payload({
        'details': 'Safe details',
        'details_url': 'file:///etc/passwd',
        'large_url': 'javascript:alert(1)',
        'buttons': [
            {'label': 'Bad', 'url': 'file:///tmp/nope'},
            {'label': 'Good', 'url': 'https://example.com'},
            {'label': 'Ignored third', 'url': 'https://third.example'},
        ],
        'start': -1,
        'end': 'not-a-number',
    })
    assert 'details_url' not in payload
    assert 'large_url' not in payload
    assert payload['buttons'] == [{'label': 'Good', 'url': 'https://example.com'}]
    assert 'start' not in payload
    assert 'end' not in payload


def test_activity_urls_longer_than_discord_limit_are_dropped():
    long_url = 'https://example.com/search?q=' + ('private-query-' * 30)
    assert len(long_url) > 256

    payload = sanitize_rpc_payload({
        'details': 'Browser page',
        'details_url': long_url,
        'state_url': long_url,
        'large_url': long_url,
        'small_url': long_url,
        # Button URLs have a separate, larger contract and should remain valid
        # only if they fit that contract.
        'buttons': [{'label': 'Open', 'url': long_url}],
    })

    assert 'details_url' not in payload
    assert 'state_url' not in payload
    assert 'large_url' not in payload
    assert 'small_url' not in payload
    if len(long_url) <= 512:
        assert payload['buttons'] == [{'label': 'Open', 'url': long_url}]
    else:
        assert 'buttons' not in payload


def test_activity_and_button_url_limits_are_exact():
    prefix = 'https://example.com/'
    activity_256 = prefix + ('a' * (256 - len(prefix)))
    activity_257 = prefix + ('a' * (257 - len(prefix)))
    button_512 = prefix + ('b' * (512 - len(prefix)))
    button_513 = prefix + ('b' * (513 - len(prefix)))

    allowed = sanitize_rpc_payload({
        'details': 'Bounds',
        'details_url': activity_256,
        'buttons': [{'label': 'Open', 'url': button_512}],
    })
    assert allowed['details_url'] == activity_256
    assert allowed['buttons'] == [{'label': 'Open', 'url': button_512}]

    rejected = sanitize_rpc_payload({
        'details': 'Bounds',
        'details_url': activity_257,
        'buttons': [{'label': 'Open', 'url': button_513}],
    })
    assert 'details_url' not in rejected
    assert 'buttons' not in rejected


def test_asset_and_party_bounds_are_enforced():
    payload = sanitize_rpc_payload({
        'large_image': 'a' * 301,
        'small_image': 'app',
        'party_id': 'p' * 129,
        'party_size': [5, 2],
    })
    assert 'large_image' not in payload
    assert payload['small_image'] == 'app'
    assert 'party_id' not in payload
    assert 'party_size' not in payload
