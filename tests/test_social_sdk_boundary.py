from pathlib import Path

import social_sdk_transport


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


def test_native_bridge_resets_client_after_callback_timeout():
    source = (
        ROOT / "native" / "discord_social_sdk_bridge" / "main.cpp"
    ).read_text(encoding="utf-8")
    assert "ApplyResult::TimedOut" in source
    assert "client = make_client(*application_id)" in source
    assert 'print_error("update_timeout")' in source


def test_pyinstaller_runtime_helper_has_priority(monkeypatch, tmp_path):
    helper_name = social_sdk_transport._HELPER_NAME
    helper = tmp_path / helper_name
    helper.write_bytes(b"helper")

    monkeypatch.setattr(social_sdk_transport.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv("CYBREX_DISCORD_SOCIAL_SDK_HELPER", raising=False)
    monkeypatch.setattr(social_sdk_transport.shutil, "which", lambda _name: None)

    assert social_sdk_transport.discover_social_sdk_helper() == helper.resolve()


def test_pyinstaller_spec_supports_optional_embedded_social_sdk_bundle():
    source = (ROOT / "discord-rich-presence.spec").read_text(encoding="utf-8")
    assert "CYBREX_SOCIAL_SDK_BUNDLE_DIR" in source
    assert "cybrex-discord-social-sdk" in source
    assert "libdiscord_partner_sdk.so" in source
    assert "discord_partner_sdk.dll" in source
