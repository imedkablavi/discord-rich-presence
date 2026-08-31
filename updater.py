"""Verified GitHub Release updater for packaged CYBREX builds."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import ssl
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import certifi

from app_version import APP_VERSION


REPOSITORY = "imedkablavi/discord-rich-presence"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
_API_MAX_BYTES = 2 * 1024 * 1024
_CHECKSUM_MAX_BYTES = 16 * 1024
_BINARY_MAX_BYTES = 256 * 1024 * 1024
_HTTP_TIMEOUT = 12.0
_ALLOWED_DOWNLOAD_HOSTS = {
    "api.github.com",
    "github.com",
}


class UpdateError(RuntimeError):
    """Raised when an update cannot be verified or installed safely."""


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str
    size: int
    digest: Optional[str] = None


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    tag_name: str
    release_url: str
    binary: ReleaseAsset
    checksum: ReleaseAsset


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        _validate_github_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate_github_url(url: str) -> None:
    try:
        parsed = urllib.parse.urlsplit(str(url or ""))
        port = parsed.port
    except ValueError as exc:
        raise UpdateError("Malformed update URL") from exc
    host = (parsed.hostname or "").lower()
    allowed = (
        host in _ALLOWED_DOWNLOAD_HOSTS
        or host.endswith(".githubusercontent.com")
        or host.endswith(".github.com")
    )
    if (
        parsed.scheme != "https"
        or not allowed
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
    ):
        raise UpdateError(f"Refusing non-GitHub update URL: {host or 'unknown'}")


def _ssl_context() -> ssl.SSLContext:
    """Return host trust plus the CA bundle embedded in packaged builds."""
    try:
        context = ssl.create_default_context()
        context.load_verify_locations(cafile=certifi.where())
    except (OSError, ssl.SSLError) as exc:
        raise UpdateError("Could not initialize the HTTPS certificate store") from exc
    return context


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        _SafeRedirectHandler(),
        urllib.request.HTTPSHandler(context=_ssl_context()),
    )


def _request(url: str) -> urllib.request.Request:
    _validate_github_url(url)
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": f"CYBREX-Rich-Presence/{APP_VERSION}",
        },
    )


def _read_limited(url: str, max_bytes: int) -> bytes:
    try:
        with _opener().open(_request(url), timeout=_HTTP_TIMEOUT) as response:
            _validate_github_url(response.geturl())
            length = response.headers.get("Content-Length")
            if length:
                try:
                    if int(length) > max_bytes:
                        raise UpdateError("Update response is unexpectedly large")
                except ValueError:
                    pass
            data = response.read(max_bytes + 1)
    except UpdateError:
        raise
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise UpdateError(f"Could not contact GitHub: {exc}") from exc
    if len(data) > max_bytes:
        raise UpdateError("Update response exceeded the safety limit")
    return data


def _version_tuple(value: str) -> tuple[int, int, int, int]:
    """Return a precedence key where a stable build outranks its prerelease."""
    text = str(value or "").strip()
    match = re.fullmatch(
        r"v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?",
        text,
    )
    if not match:
        raise UpdateError(f"Unsupported release version: {text or 'empty'}")
    major, minor, patch = (int(match.group(index)) for index in range(1, 4))
    stable_rank = 0 if match.group(4) else 1
    return major, minor, patch, stable_rank


def _normalized_version(value: str) -> str:
    return str(value or "").strip().lstrip("v")


def _platform_asset_names() -> tuple[str, str]:
    machine = platform.machine().lower()
    if machine not in {"x86_64", "amd64"}:
        raise UpdateError(f"Automatic updates are not available for {machine or 'this architecture'}")
    if sys.platform == "win32":
        binary = "DiscordRichPresence.exe"
    elif sys.platform.startswith("linux"):
        binary = "CYBREX-DiscordRichPresence-linux-x86_64"
    else:
        raise UpdateError(f"Automatic updates are not available on {sys.platform}")
    return binary, f"{binary}.sha256"


def _release_asset(raw: Any, expected_name: str, max_bytes: int) -> ReleaseAsset:
    if not isinstance(raw, list):
        raise UpdateError("GitHub release assets are missing")
    for item in raw:
        if not isinstance(item, dict) or item.get("name") != expected_name:
            continue
        url = str(item.get("browser_download_url") or "")
        _validate_github_url(url)
        try:
            size = int(item.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if size <= 0 or size > max_bytes:
            raise UpdateError(f"Release asset {expected_name} has an invalid size")
        digest = str(item.get("digest") or "").strip() or None
        return ReleaseAsset(expected_name, url, size, digest)
    raise UpdateError(f"Release is missing required asset: {expected_name}")


def check_for_update(current_version: str = APP_VERSION) -> Optional[UpdateInfo]:
    """Return verified release metadata when a newer stable release exists."""
    raw = _read_limited(LATEST_RELEASE_API, _API_MAX_BYTES)
    try:
        release = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("GitHub returned invalid release metadata") from exc
    if not isinstance(release, dict):
        raise UpdateError("GitHub returned invalid release metadata")
    if bool(release.get("draft")) or bool(release.get("prerelease")):
        raise UpdateError("Latest release is not a stable published build")

    tag = str(release.get("tag_name") or "").strip()
    latest = _normalized_version(tag)
    latest_tuple = _version_tuple(latest)

    current_text = _normalized_version(current_version)
    current_tuple = _version_tuple(current_text)
    if latest_tuple <= current_tuple:
        return None

    binary_name, checksum_name = _platform_asset_names()
    assets = release.get("assets")
    binary = _release_asset(assets, binary_name, _BINARY_MAX_BYTES)
    checksum = _release_asset(assets, checksum_name, _CHECKSUM_MAX_BYTES)
    release_url = str(release.get("html_url") or "")
    _validate_github_url(release_url)
    return UpdateInfo(
        current_version=current_text,
        latest_version=latest,
        tag_name=tag,
        release_url=release_url,
        binary=binary,
        checksum=checksum,
    )


def _expected_checksum(info: UpdateInfo) -> str:
    text = _read_limited(info.checksum.url, _CHECKSUM_MAX_BYTES).decode("ascii", errors="strict")
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        digest = parts[0].lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            continue
        if len(parts) >= 2:
            filename = parts[-1].lstrip("*")
            if filename != info.binary.name:
                continue
        return digest
    raise UpdateError("Release checksum file is invalid")


def _download_verified_binary(info: UpdateInfo, destination: Path) -> str:
    expected = _expected_checksum(info)
    digest = hashlib.sha256()
    received = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _opener().open(_request(info.binary.url), timeout=_HTTP_TIMEOUT) as response:
            _validate_github_url(response.geturl())
            with open(destination, "wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > _BINARY_MAX_BYTES:
                        raise UpdateError("Downloaded update exceeded the safety limit")
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
    except Exception:
        try:
            destination.unlink()
        except OSError:
            pass
        raise

    if received != info.binary.size:
        try:
            destination.unlink()
        except OSError:
            pass
        raise UpdateError("Downloaded update size does not match GitHub metadata")

    actual = digest.hexdigest().lower()
    api_digest = str(info.binary.digest or "").lower()
    if api_digest.startswith("sha256:") and api_digest[7:] != actual:
        try:
            destination.unlink()
        except OSError:
            pass
        raise UpdateError("GitHub asset digest verification failed")
    if actual != expected:
        try:
            destination.unlink()
        except OSError:
            pass
        raise UpdateError("SHA-256 verification failed")
    return actual


def _install_linux(target: Path, staged: Path, *, keep_backup: bool = False) -> Optional[Path]:
    try:
        mode = stat.S_IMODE(target.stat().st_mode)
    except OSError:
        mode = 0o755
    os.chmod(staged, mode | stat.S_IXUSR)
    backup = target.with_name(target.name + ".old")
    try:
        backup.unlink(missing_ok=True)
    except OSError:
        pass
    os.replace(target, backup)
    try:
        os.replace(staged, target)
        os.chmod(target, mode | stat.S_IXUSR)
    except Exception:
        try:
            os.replace(backup, target)
        except OSError:
            pass
        raise
    if keep_backup:
        return backup
    try:
        backup.unlink()
    except OSError:
        pass
    return None


def _relaunch_linux(
    target: Path,
    restart_args: list[str],
    *,
    rollback_path: Optional[Path] = None,
) -> None:
    if not restart_args:
        if rollback_path is not None:
            try:
                rollback_path.unlink(missing_ok=True)
            except OSError:
                pass
        return
    process = subprocess.Popen(
        [str(target), *restart_args],
        close_fds=True,
        start_new_session=True,
    )
    if rollback_path is None:
        return
    try:
        process.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        try:
            rollback_path.unlink(missing_ok=True)
        except OSError:
            pass
        return

    try:
        target.unlink(missing_ok=True)
        os.replace(rollback_path, target)
        subprocess.Popen(
            [str(target), *restart_args],
            close_fds=True,
            start_new_session=True,
        )
    except OSError as exc:
        raise UpdateError("Updated Linux build exited immediately and rollback failed") from exc
    raise UpdateError("Updated Linux build exited immediately; rollback restored the previous version")


def _schedule_windows_replace(target: Path, staged: Path, restart_args: list[str]) -> None:
    script_fd, script_name = tempfile.mkstemp(prefix="cybrex-update-", suffix=".ps1")
    os.close(script_fd)
    script = Path(script_name)
    powershell = "\n".join([
        "param([int]$WaitPid,[string]$Target,[string]$Staged,[string]$RestartJson)",
        "$ErrorActionPreference = 'Stop'",
        "for ($i = 0; $i -lt 240; $i++) {",
        "  if (-not (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue)) { break }",
        "  Start-Sleep -Milliseconds 250",
        "}",
        "if (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue) { exit 20 }",
        "$Backup = $Target + '.old'",
        "Remove-Item $Backup -Force -ErrorAction SilentlyContinue",
        "Move-Item -LiteralPath $Target -Destination $Backup -Force",
        "try {",
        "  Move-Item -LiteralPath $Staged -Destination $Target -Force",
        "} catch {",
        "  Move-Item -LiteralPath $Backup -Destination $Target -Force -ErrorAction SilentlyContinue",
        "  exit 21",
        "}",
        "$ArgsList = ConvertFrom-Json $RestartJson",
        "if ($null -ne $ArgsList -and $ArgsList.Count -gt 0) {",
        "  $Child = Start-Process -FilePath $Target -ArgumentList $ArgsList -PassThru",
        "  Start-Sleep -Seconds 3",
        "  if ($Child.HasExited) {",
        "    Remove-Item -LiteralPath $Target -Force -ErrorAction SilentlyContinue",
        "    Move-Item -LiteralPath $Backup -Destination $Target -Force",
        "    Start-Process -FilePath $Target -ArgumentList $ArgsList | Out-Null",
        "    Remove-Item $PSCommandPath -Force -ErrorAction SilentlyContinue",
        "    exit 22",
        "  }",
        "}",
        "Remove-Item $Backup -Force -ErrorAction SilentlyContinue",
        "Remove-Item $PSCommandPath -Force -ErrorAction SilentlyContinue",
        "",
    ])
    script.write_text(powershell, encoding="utf-8")
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            str(os.getpid()),
            str(target),
            str(staged),
            json.dumps(restart_args),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )


def install_update(
    info: UpdateInfo,
    *,
    target_path: Optional[Path] = None,
    restart_args: Optional[list[str]] = None,
) -> str:
    """Download, verify and install a release over the packaged executable.

    Windows schedules replacement after the updater process exits because a
    running PE file cannot be replaced reliably. Linux uses an atomic rename and
    keeps a rollback copy until the relaunched build survives its startup check.
    """
    if target_path is None:
        if not getattr(sys, "frozen", False):
            raise UpdateError("Self-update is only available in packaged builds")
        target = Path(sys.executable).resolve()
    else:
        target = Path(target_path).resolve()
    if not target.exists() or not target.is_file():
        raise UpdateError("Current executable could not be located")

    staged = target.with_name(f".{target.name}.{info.latest_version}.new")
    try:
        staged.unlink(missing_ok=True)
    except OSError:
        pass
    _download_verified_binary(info, staged)

    args = list(restart_args or [])
    if sys.platform == "win32" and target_path is None:
        _schedule_windows_replace(target, staged, args)
        return "scheduled"
    try:
        rollback = _install_linux(target, staged, keep_backup=target_path is None)
        if target_path is None:
            _relaunch_linux(target, args, rollback_path=rollback)
    except Exception as exc:
        try:
            staged.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, UpdateError):
            raise
        raise UpdateError(f"Could not replace the current executable: {exc}") from exc
    return "installed"


def update_summary(info: Optional[UpdateInfo]) -> str:
    if info is None:
        return f"CYBREX Rich Presence {APP_VERSION} is up to date."
    return (
        f"CYBREX Rich Presence {info.latest_version} is available "
        f"(current: {info.current_version})."
    )
