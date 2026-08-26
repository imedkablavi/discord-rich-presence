"""Update-channel selection layered on top of the verified package updater."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app_version import APP_VERSION
from updater import (
    REPOSITORY,
    UpdateError,
    UpdateInfo,
    _API_MAX_BYTES,
    _BINARY_MAX_BYTES,
    _CHECKSUM_MAX_BYTES,
    _normalized_version,
    _platform_asset_names,
    _read_limited,
    _release_asset,
    _validate_github_url,
    check_for_update as check_for_stable_update,
)

_RELEASES_API = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=30"
_SEMVER_RE = re.compile(
    r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)
_IDENTIFIER_RE = re.compile(r"[A-Za-z-]+|\d+")


def normalize_channel(value: object) -> str:
    channel = str(value or "stable").strip().lower()
    if channel not in {"stable", "preview"}:
        raise UpdateError("Update channel must be stable or preview")
    return channel


def configured_update_channel(config, current_version: str = APP_VERSION) -> str:  # noqa: ANN001
    """Return the saved channel, defaulting RC builds to Preview and stable builds to Stable."""
    fallback = "preview" if "-" in _normalized_version(current_version) else "stable"
    value = config.get("updates.channel", fallback)
    try:
        return normalize_channel(value)
    except UpdateError:
        return fallback


def _version_key(value: str) -> tuple[int, int, int, int, tuple[tuple[int, object], ...]]:
    """Comparable SemVer-style key with stable > prerelease for equal core versions."""
    text = str(value or "").strip()
    match = _SEMVER_RE.fullmatch(text)
    if not match:
        raise UpdateError(f"Unsupported release version: {text or 'empty'}")

    major, minor, patch = (int(match.group(index)) for index in range(1, 4))
    prerelease = match.group(4)
    if not prerelease:
        return major, minor, patch, 1, ()

    identifiers: list[tuple[int, object]] = []
    for token in prerelease.split("."):
        parts = _IDENTIFIER_RE.findall(token)
        if not parts:
            parts = [token]
        for part in parts:
            if part.isdigit():
                identifiers.append((0, int(part)))
            else:
                identifiers.append((1, part.casefold()))
    return major, minor, patch, 0, tuple(identifiers)


def _parse_release_list(raw: bytes) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("GitHub returned invalid release metadata") from exc
    if not isinstance(payload, list):
        raise UpdateError("GitHub returned invalid release metadata")
    return [item for item in payload if isinstance(item, dict)]


def _preview_update(current_version: str) -> Optional[UpdateInfo]:
    releases = _parse_release_list(_read_limited(_RELEASES_API, _API_MAX_BYTES))
    current_text = _normalized_version(current_version)
    current_key = _version_key(current_text)

    candidates: list[tuple[tuple[int, int, int, int, tuple[tuple[int, object], ...]], dict[str, Any]]] = []
    for release in releases:
        if bool(release.get("draft")):
            continue
        tag = str(release.get("tag_name") or "").strip()
        try:
            key = _version_key(tag)
        except UpdateError:
            continue
        if key > current_key:
            candidates.append((key, release))

    if not candidates:
        return None

    _, release = max(candidates, key=lambda pair: pair[0])
    tag = str(release.get("tag_name") or "").strip()
    latest = _normalized_version(tag)
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


def check_for_update(
    current_version: str = APP_VERSION,
    *,
    channel: str = "stable",
) -> Optional[UpdateInfo]:
    """Check the selected update channel without weakening package verification."""
    selected = normalize_channel(channel)
    if selected == "stable":
        return check_for_stable_update(current_version)
    return _preview_update(current_version)
