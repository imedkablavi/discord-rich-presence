from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_social_sdk_bridge_has_no_oauth_token_or_network_listener_primitives():
    paths = (
        ROOT / "social_sdk_transport.py",
        ROOT / "social_sdk_protocol.py",
        ROOT / "native" / "discord_social_sdk_bridge" / "main.cpp",
    )
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in paths)

    forbidden = (
        "access_token",
        "refresh_token",
        "oauth2",
        "create_server",
        "bind(",
        "listen(",
        "accept(",
    )
    for marker in forbidden:
        assert marker not in combined


def test_native_bridge_uses_dynamic_activity_name_api():
    source = (
        ROOT / "native" / "discord_social_sdk_bridge" / "main.cpp"
    ).read_text(encoding="utf-8")
    assert "activity.SetName(*name)" in source
    assert "UpdateRichPresence" in source
