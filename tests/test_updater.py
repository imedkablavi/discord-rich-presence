import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from updater import (
    UpdateError,
    atomic_replace_with_rollback,
    is_newer_version,
    parse_manifest,
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
