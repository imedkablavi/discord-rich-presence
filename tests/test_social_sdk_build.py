from pathlib import Path
import runpy

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "scripts" / "build_social_sdk_bridge.py"))
validate_sdk_root = MODULE["validate_sdk_root"]
platform_layout = MODULE["platform_layout"]
BRIDGE_SOURCE = ROOT / "native" / "discord_social_sdk_bridge" / "main.cpp"
BRIDGE_CMAKE = ROOT / "native" / "discord_social_sdk_bridge" / "CMakeLists.txt"


def _fake_sdk(tmp_path: Path, platform_name: str) -> Path:
    root = tmp_path / "discord_social_sdk"
    (root / "include").mkdir(parents=True)
    (root / "include" / "discordpp.h").write_text("// header\n", encoding="utf-8")
    (root / "include" / "cdiscord.h").write_text("// c header\n", encoding="utf-8")
    (root / "License-Notices.txt").write_text("notices\n", encoding="utf-8")

    _helper_name, runtime_relative = platform_layout(platform_name)
    runtime = root / runtime_relative
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_bytes(b"runtime")

    if platform_name == "windows":
        link = root / "lib" / "release" / "discord_partner_sdk.lib"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.write_bytes(b"import-library")
    return root


def test_validate_linux_social_sdk_layout(tmp_path):
    root = _fake_sdk(tmp_path, "linux")
    layout = validate_sdk_root(root, "linux")
    assert layout["runtime"].name == "libdiscord_partner_sdk.so"
    assert layout["helper_name"].name == "cybrex-discord-social-sdk"


def test_validate_windows_social_sdk_layout(tmp_path):
    root = _fake_sdk(tmp_path, "windows")
    layout = validate_sdk_root(root, "windows")
    assert layout["runtime"].name == "discord_partner_sdk.dll"
    assert layout["helper_name"].name == "cybrex-discord-social-sdk.exe"


def test_validate_sdk_layout_fails_closed_when_runtime_is_missing(tmp_path):
    root = _fake_sdk(tmp_path, "linux")
    (root / "lib" / "release" / "libdiscord_partner_sdk.so").unlink()
    with pytest.raises(FileNotFoundError):
        validate_sdk_root(root, "linux")


def test_bridge_tracks_current_social_sdk_cxx_requirement():
    cmake = BRIDGE_CMAKE.read_text(encoding="utf-8")
    assert "set(CMAKE_CXX_STANDARD 20)" in cmake
    assert "set(CMAKE_CXX_STANDARD_REQUIRED ON)" in cmake


def test_native_update_callback_does_not_capture_stack_state_by_reference():
    source = BRIDGE_SOURCE.read_text(encoding="utf-8")
    assert "struct UpdateCallbackState" in source
    assert "std::make_shared<UpdateCallbackState>()" in source
    assert "[callback_state](discordpp::ClientResult result)" in source
    assert "client->UpdateRichPresence(std::move(activity), [&]" not in source
