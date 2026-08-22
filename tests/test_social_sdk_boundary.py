from pathlib import Path

import pytest

from social_sdk_transport import SocialSDKError, discover_social_sdk_helper, social_sdk_available


ROOT = Path(__file__).resolve().parents[1]
NATIVE_SOURCE = ROOT / 'native' / 'discord_social_sdk_bridge' / 'main.cpp'


def test_native_social_sdk_bridge_stays_direct_presence_only():
    text = NATIVE_SOURCE.read_text(encoding='utf-8')
    forbidden = (
        'UpdateToken(',
        'GetTokenFromDevice(',
        'Authorize(',
        'GetDefaultPresenceScopes(',
        'GetDefaultCommunicationScopes(',
        '.Connect(',
        '->Connect(',
        'socket(',
        'bind(',
        'listen(',
        'accept(',
        'user_token',
        'access_token',
        'refresh_token',
    )
    for marker in forbidden:
        assert marker not in text

    assert 'SetApplicationId(' in text
    assert 'SetName(' in text
    assert 'UpdateRichPresence(' in text
    assert 'ClearRichPresence(' in text


def test_social_sdk_discovery_accepts_only_existing_local_helper(tmp_path, monkeypatch):
    missing = tmp_path / 'missing-helper'
    monkeypatch.setenv('CYBREX_DISCORD_SOCIAL_SDK_HELPER', str(missing))
    assert discover_social_sdk_helper() is None
    assert social_sdk_available() is False

    helper = tmp_path / 'cybrex-discord-social-sdk'
    helper.write_bytes(b'not executed by this test')
    monkeypatch.setenv('CYBREX_DISCORD_SOCIAL_SDK_HELPER', str(helper))
    assert discover_social_sdk_helper() == helper
    assert social_sdk_available() is True


def test_social_sdk_transport_rejects_invalid_application_id():
    from social_sdk_transport import SocialSDKPresence

    with pytest.raises(SocialSDKError, match='application ID'):
        SocialSDKPresence('not-a-number')
