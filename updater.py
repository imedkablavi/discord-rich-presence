"""Signed release manifest verification and staged self-update helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


MAX_ASSET_BYTES = 300 * 1024 * 1024
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-.]?(?:rc|beta|alpha|dev)[.-]?(\d+)?)?$", re.I)


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str
    sha256: str
    size: int
    platform: str
    arch: str
    kind: str = "portable"


@dataclass(frozen=True)
class SignedManifest:
    version: str
    assets: tuple[ReleaseAsset, ...]
    signature: str
    raw: Dict[str, Any]

    @property
    def signed_payload(self) -> bytes:
        payload = dict(self.raw)
        payload.pop("signature", None)
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def parse_manifest(data: bytes) -> SignedManifest:
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("Update manifest is not valid UTF-8 JSON") from exc
    if not isinstance(raw, dict):
        raise UpdateError("Update manifest must be an object")
    version = str(raw.get("version", "")).strip()
    signature = str(raw.get("signature", "")).strip()
    if not version or not signature:
        raise UpdateError("Update manifest is missing version/signature")
    assets_value = raw.get("assets")
    if not isinstance(assets_value, list) or not assets_value:
        raise UpdateError("Update manifest has no assets")
    assets = []
    for item in assets_value:
        if not isinstance(item, dict):
            raise UpdateError("Update asset entry must be an object")
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        digest = str(item.get("sha256", "")).strip().lower()
        asset_platform = str(item.get("platform", "")).strip().lower()
        arch = str(item.get("arch", "")).strip().lower()
        kind = str(item.get("kind", "portable")).strip().lower() or "portable"
        try:
            size = int(item.get("size", 0))
        except (TypeError, ValueError) as exc:
            raise UpdateError(f"Invalid size for update asset {name!r}") from exc
        if not name or Path(name).name != name:
            raise UpdateError("Update asset name must be a basename")
        if not url.startswith("https://"):
            raise UpdateError(f"Update asset {name!r} must use HTTPS")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise UpdateError(f"Update asset {name!r} has an invalid SHA-256")
        if size <= 0 or size > MAX_ASSET_BYTES:
            raise UpdateError(f"Update asset {name!r} has an invalid size")
        assets.append(ReleaseAsset(name, url, digest, size, asset_platform, arch, kind))
    return SignedManifest(version, tuple(assets), signature, raw)


def verify_manifest(manifest: SignedManifest, public_key_b64: str) -> None:
    if not public_key_b64:
        raise UpdateError("Update signing public key is not configured")
    try:
        public_key_raw = base64.b64decode(public_key_b64, validate=True)
        signature = base64.b64decode(manifest.signature, validate=True)
        key = Ed25519PublicKey.from_public_bytes(public_key_raw)
        key.verify(signature, manifest.signed_payload)
    except (ValueError, InvalidSignature) as exc:
        raise UpdateError("Update manifest signature verification failed") from exc


def fetch_signed_manifest(url: str, public_key_b64: str, timeout: float = 10.0) -> SignedManifest:
    if not url.startswith("https://"):
        raise UpdateError("Update manifest URL must use HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "DiscordRichPresence-Updater/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if int(getattr(response, "status", 200)) != 200:
            raise UpdateError(f"Update manifest request failed with HTTP {response.status}")
        data = response.read(512 * 1024 + 1)
    if len(data) > 512 * 1024:
        raise UpdateError("Update manifest is unexpectedly large")
    manifest = parse_manifest(data)
    verify_manifest(manifest, public_key_b64)
    return manifest


def normalized_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    return sys.platform.lower()


def normalized_arch() -> str:
    machine = platform.machine().lower()
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86-64": "x86_64",
        "aarch64": "arm64",
    }
    return aliases.get(machine, machine)


def select_asset(
    manifest: SignedManifest,
    target_platform: Optional[str] = None,
    arch: Optional[str] = None,
    preferred_kinds: Iterable[str] = ("portable", "binary"),
) -> ReleaseAsset:
    target_platform = (target_platform or normalized_platform()).lower()
    arch = (arch or normalized_arch()).lower()
    matches = [a for a in manifest.assets if a.platform == target_platform and a.arch == arch]
    for kind in preferred_kinds:
        for asset in matches:
            if asset.kind == kind:
                return asset
    if matches:
        return matches[0]
    raise UpdateError(f"No update asset for {target_platform}/{arch}")


def version_tuple(value: str) -> tuple[int, int, int, int, int]:
    clean = value.strip().lstrip("v")
    match = _VERSION_RE.fullmatch(clean)
    if not match:
        raise UpdateError(f"Unsupported version format: {value!r}")
    major, minor, patch = (int(match.group(i)) for i in range(1, 4))
    lower = clean.lower()
    prerelease_rank = 1
    prerelease_number = 0
    if any(marker in lower for marker in ("rc", "beta", "alpha", "dev")):
        prerelease_rank = 0
        prerelease_number = int(match.group(4) or 0)
    return major, minor, patch, prerelease_rank, prerelease_number


def is_newer_version(candidate: str, current: str) -> bool:
    return version_tuple(candidate) > version_tuple(current)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_verified_asset(asset: ReleaseAsset, destination: Path, timeout: float = 30.0) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(asset.url, headers={"User-Agent": "DiscordRichPresence-Updater/1"})
    total = 0
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, temp.open("wb") as out:
            if int(getattr(response, "status", 200)) != 200:
                raise UpdateError(f"Update asset request failed with HTTP {response.status}")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > asset.size or total > MAX_ASSET_BYTES:
                    raise UpdateError("Update asset exceeded signed size")
                digest.update(chunk)
                out.write(chunk)
        if total != asset.size:
            raise UpdateError(f"Update asset size mismatch: expected {asset.size}, got {total}")
        if not hmac_safe_equal(digest.hexdigest(), asset.sha256):
            raise UpdateError("Update asset SHA-256 verification failed")
        os.replace(temp, destination)
        return destination
    except Exception:
        try:
            temp.unlink()
        except OSError:
            pass
        raise


def hmac_safe_equal(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a, b)


def atomic_replace_with_rollback(current: Path, staged: Path, backup: Optional[Path] = None) -> Path:
    """Replace a non-running target and restore it immediately if replacement fails."""
    current = Path(current)
    staged = Path(staged)
    backup = Path(backup) if backup else current.with_suffix(current.suffix + ".rollback")
    if not staged.is_file():
        raise UpdateError("Staged update does not exist")
    if not os.access(current.parent, os.W_OK):
        raise UpdateError("Install directory is not writable; use the system package manager")
    try:
        if backup.exists():
            backup.unlink()
        os.replace(current, backup)
        os.replace(staged, current)
    except Exception as exc:
        if not current.exists() and backup.exists():
            os.replace(backup, current)
        raise UpdateError("Failed to replace application; rollback restored the previous version") from exc
    return backup


def schedule_self_replace(
    current: Path,
    staged: Path,
    wait_pids: Iterable[int],
    restart_args: Optional[list[str]] = None,
) -> Path:
    """Launch a detached helper that replaces a running portable build."""
    current = Path(current).resolve()
    staged = Path(staged).resolve()
    if not staged.is_file():
        raise UpdateError("Staged update does not exist")
    if not os.access(current.parent, os.W_OK):
        raise UpdateError("Install directory is not writable; use the system package manager")
    pids = [int(pid) for pid in wait_pids if int(pid) > 0]
    restart_args = list(restart_args or [])
    helper_dir = Path(tempfile.mkdtemp(prefix="drp-update-"))
    backup = current.with_suffix(current.suffix + ".rollback")

    if sys.platform == "win32":
        helper = helper_dir / "apply-update.ps1"
        quoted_args = ",".join('"' + arg.replace('"', '`"') + '"' for arg in restart_args)
        helper.write_text(
            "param()\n"
            "$ErrorActionPreference='Stop'\n"
            f"$pids=@({','.join(str(pid) for pid in pids)})\n"
            "foreach($p in $pids){ try { Wait-Process -Id $p -Timeout 60 -ErrorAction SilentlyContinue } catch {} }\n"
            f"$current='{str(current).replace("'", "''")}'\n"
            f"$staged='{str(staged).replace("'", "''")}'\n"
            f"$backup='{str(backup).replace("'", "''")}'\n"
            "try {\n"
            "  if(Test-Path $backup){ Remove-Item -Force $backup }\n"
            "  Move-Item -Force $current $backup\n"
            "  Move-Item -Force $staged $current\n"
            f"  Start-Process -FilePath $current -ArgumentList @({quoted_args})\n"
            "} catch {\n"
            "  if((-not (Test-Path $current)) -and (Test-Path $backup)){ Move-Item -Force $backup $current }\n"
            "  exit 1\n"
            "}\n",
            encoding="utf-8",
        )
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper)],
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0),
            close_fds=True,
        )
    else:
        helper = helper_dir / "apply-update.sh"
        import shlex
        helper.write_text(
            "#!/bin/sh\nset -eu\n"
            + " ".join(f"while kill -0 {pid} 2>/dev/null; do sleep 1; done;" for pid in pids)
            + "\n"
            + f"current={shlex.quote(str(current))}\n"
            + f"staged={shlex.quote(str(staged))}\n"
            + f"backup={shlex.quote(str(backup))}\n"
            + "rm -f \"$backup\"\n"
            + "mv \"$current\" \"$backup\"\n"
            + "if ! mv \"$staged\" \"$current\"; then mv \"$backup\" \"$current\"; exit 1; fi\n"
            + "chmod +x \"$current\" || true\n"
            + f"if ! \"$current\" {' '.join(shlex.quote(a) for a in restart_args)} >/dev/null 2>&1 & then mv -f \"$backup\" \"$current\"; exit 1; fi\n",
            encoding="utf-8",
        )
        helper.chmod(0o700)
        subprocess.Popen(["sh", str(helper)], start_new_session=True, close_fds=True)
    return helper
