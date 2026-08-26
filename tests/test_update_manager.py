import json

import pytest

import update_manager


class DummyConfig:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)


def test_version_key_orders_release_candidates_and_stable():
    assert update_manager._version_key("2.1.0-rc3") < update_manager._version_key("2.1.0-rc4")
    assert update_manager._version_key("2.1.0-rc9") < update_manager._version_key("2.1.0-rc10")
    assert update_manager._version_key("2.1.0-rc10") < update_manager._version_key("2.1.0")
    assert update_manager._version_key("2.1.0") < update_manager._version_key("2.2.0-rc1")


def test_configured_channel_defaults_follow_build_type():
    assert update_manager.configured_update_channel(DummyConfig(), "2.1.0-rc4") == "preview"
    assert update_manager.configured_update_channel(DummyConfig(), "2.1.0-beta2") == "preview"
    assert update_manager.configured_update_channel(DummyConfig(), "2.1.0-alpha1") == "preview"
    assert update_manager.configured_update_channel(DummyConfig(), "2.1.0") == "stable"
    assert update_manager.configured_update_channel(DummyConfig(), "2.1.0-dev") == "stable"
    assert update_manager.configured_update_channel(DummyConfig(), "2.1.0-local") == "stable"
    assert (
        update_manager.configured_update_channel(
            DummyConfig({"updates.channel": "preview"}), "2.1.0-dev"
        )
        == "preview"
    )


def test_invalid_channel_is_rejected():
    with pytest.raises(update_manager.UpdateError):
        update_manager.normalize_channel("nightly")


def test_preview_selects_newer_rc(monkeypatch):
    binary_name = "CYBREX-DiscordRichPresence-linux-x86_64"
    checksum_name = f"{binary_name}.sha256"

    def asset(name, size):
        return {
            "name": name,
            "size": size,
            "browser_download_url": (
                "https://github.com/imedkablavi/discord-rich-presence/"
                f"releases/download/v2.1.0-rc5/{name}"
            ),
            "digest": "sha256:" + "a" * 64,
        }

    releases = [
        {
            "tag_name": "v2.1.0-rc5",
            "draft": False,
            "prerelease": True,
            "html_url": (
                "https://github.com/imedkablavi/discord-rich-presence/releases/tag/v2.1.0-rc5"
            ),
            "assets": [asset(binary_name, 100), asset(checksum_name, 90)],
        },
        {
            "tag_name": "v2.1.0-rc6",
            "draft": True,
            "prerelease": True,
            "html_url": (
                "https://github.com/imedkablavi/discord-rich-presence/releases/tag/v2.1.0-rc6"
            ),
            "assets": [asset(binary_name, 100), asset(checksum_name, 90)],
        },
    ]

    monkeypatch.setattr(
        update_manager,
        "_read_limited",
        lambda _url, _limit: json.dumps(releases).encode("utf-8"),
    )
    monkeypatch.setattr(
        update_manager,
        "_platform_asset_names",
        lambda: (binary_name, checksum_name),
    )

    info = update_manager.check_for_update("2.1.0-rc4", channel="preview")
    assert info is not None
    assert info.latest_version == "2.1.0-rc5"
    assert info.binary.name == binary_name


def test_preview_can_promote_rc_to_stable(monkeypatch):
    binary_name = "CYBREX-DiscordRichPresence-linux-x86_64"
    checksum_name = f"{binary_name}.sha256"
    assets = [
        {
            "name": binary_name,
            "size": 100,
            "browser_download_url": (
                "https://github.com/imedkablavi/discord-rich-presence/"
                f"releases/download/v2.1.0/{binary_name}"
            ),
        },
        {
            "name": checksum_name,
            "size": 90,
            "browser_download_url": (
                "https://github.com/imedkablavi/discord-rich-presence/"
                f"releases/download/v2.1.0/{checksum_name}"
            ),
        },
    ]
    releases = [
        {
            "tag_name": "v2.1.0",
            "draft": False,
            "prerelease": False,
            "html_url": (
                "https://github.com/imedkablavi/discord-rich-presence/releases/tag/v2.1.0"
            ),
            "assets": assets,
        }
    ]

    monkeypatch.setattr(
        update_manager,
        "_read_limited",
        lambda _url, _limit: json.dumps(releases).encode("utf-8"),
    )
    monkeypatch.setattr(
        update_manager,
        "_platform_asset_names",
        lambda: (binary_name, checksum_name),
    )

    info = update_manager.check_for_update("2.1.0-rc4", channel="preview")
    assert info is not None
    assert info.latest_version == "2.1.0"
