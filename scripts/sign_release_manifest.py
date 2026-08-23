#!/usr/bin/env python3
"""Build and Ed25519-sign the updater manifest for release assets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--private-key-b64", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--asset",
        action="append",
        nargs=4,
        metavar=("PATH", "PLATFORM", "ARCH", "KIND"),
        required=True,
    )
    args = parser.parse_args()

    assets = []
    for raw_path, target_platform, arch, kind in args.asset:
        path = Path(raw_path)
        if not path.is_file():
            raise SystemExit(f"Missing release asset: {path}")
        assets.append({
            "name": path.name,
            "url": args.base_url.rstrip("/") + "/" + path.name,
            "sha256": sha256(path),
            "size": path.stat().st_size,
            "platform": target_platform,
            "arch": arch,
            "kind": kind,
        })

    manifest = {"version": args.version.lstrip("v"), "assets": assets}
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    private = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(args.private_key_b64, validate=True)
    )
    manifest["signature"] = base64.b64encode(private.sign(payload)).decode("ascii")
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
