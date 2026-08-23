import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import updater
from updater import (
    UpdateError,
    _powershell_literal,
    atomic_replace_with_rollback,
    is_newer_version,
    parse_manifest,
    schedule_self_replace,
    select_asset,
    verify_manifest,
)


def _signed_manifest():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    raw = {
        "version": "2.1.0",
        "assets": [
            {
                "name": "DiscordRichPresence.exe",
                "url": "https://example.invalid/DiscordRichPresence.exe",
                "sha256": "a" * 64,
                "size": 1234,
                "platform": "windows",
                "arch": "x86_64",
                "kind": "portable",
            }
        ],
    }
    payload = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
    raw["signature"] = base64.b64encode(private.sign(payload)).decode()
    return json.dumps(raw).encode(), base64.b64encode(public).decode()


def test_manifest_signature_is_required_and_verified():
    data, public = _signed_manifest()
    manifest = parse_manifest(data)
    verify_manifest(manifest, public)
    assert select_asset(manifest, "windows", "x86_64").name == "DiscordRichPresence.exe"


def test_manifest_tampering_fails_closed():
    data, public = _signed_manifest()
    raw = json.loads(data)
    raw["assets"][0]["size"] = 9999
    manifest = parse_manifest(json.dumps(raw).encode())
    with pytest.raises(UpdateError, match="signature"):
        verify_manifest(manifest, public)


def test_manifest_rejects_non_https_assets():
    data, _ = _signed_manifest()
    raw = json.loads(data)
    raw["assets"][0]["url"] = "http://example.invalid/app.exe"
    with pytest.raises(UpdateError, match="HTTPS"):
        parse_manifest(json.dumps(raw).encode())


def test_version_comparison_handles_prerelease():
    assert is_newer_version("2.1.0", "2.0.0")
    assert is_newer_version("2.1.0", "2.1.0-rc1")
    assert not is_newer_version("2.1.0-rc1", "2.1.0")


def test_atomic_replace_keeps_rollback(tmp_path: Path):
    current = tmp_path / "app.bin"
    staged = tmp_path / "app.new"
    current.write_bytes(b"old")
    staged.write_bytes(b"new")
    backup = atomic_replace_with_rollback(current, staged)
    assert current.read_bytes() == b"new"
    assert backup.read_bytes() == b"old"


def test_powershell_literal_escapes_single_quotes():
    assert _powershell_literal("C:\\Users\\O'Brien\\app.exe") == "'C:\\Users\\O''Brien\\app.exe'"


def test_windows_helper_contains_restart_health_rollback(monkeypatch, tmp_path: Path):
    current = tmp_path / "O'Brien" / "DiscordRichPresence.exe"
    staged = tmp_path / "stage.exe"
    current.parent.mkdir()
    current.write_bytes(b"old")
    staged.write_bytes(b"new")
    calls = []

    monkeypatch.setattr(updater.sys, "platform", "win32")
    monkeypatch.setattr(updater.subprocess, "Popen", lambda args, **kwargs: calls.append((args, kwargs)))

    helper = schedule_self_replace(current, staged, [123], ["--tray"])
    text = helper.read_text(encoding="utf-8")
    assert "O''Brien" in text
    assert "Start-Sleep -Seconds 3" in text
    assert "if($child.HasExited)" in text
    assert "Move-Item -Force $backup $current" in text
    assert calls and calls[0][0][0] == "powershell.exe"


def test_linux_helper_contains_restart_health_rollback(monkeypatch, tmp_path: Path):
    current = tmp_path / "Discord Rich Presence"
    staged = tmp_path / "stage"
    current.write_bytes(b"old")
    staged.write_bytes(b"new")
    calls = []

    monkeypatch.setattr(updater.sys, "platform", "linux")
    monkeypatch.setattr(updater.subprocess, "Popen", lambda args, **kwargs: calls.append((args, kwargs)))

    helper = schedule_self_replace(current, staged, [456], ["--tray"])
    text = helper.read_text(encoding="utf-8")
    assert "while kill -0 456" in text
    assert "sleep 3" in text
    assert "if ! kill -0 \"$child\"" in text
    assert "mv \"$backup\" \"$current\"" in text
    assert calls and calls[0][0][0] == "sh"
