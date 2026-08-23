"""High-level signed update lifecycle used by the service and control panel."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config import Config
from updater import (
    ReleaseAsset,
    UpdateError,
    download_verified_asset,
    fetch_signed_manifest,
    is_newer_version,
    schedule_self_replace,
    select_asset,
)
from version import __version__


@dataclass(frozen=True)
class UpdateStatus:
    current_version: str
    latest_version: Optional[str]
    available: bool
    asset: Optional[ReleaseAsset]
    message: str


def check_for_update(config: Config) -> UpdateStatus:
    if not config.get('updates.enabled', False):
        return UpdateStatus(__version__, None, False, None, 'Updates are disabled')
    manifest_url = str(config.get('updates.manifest_url', '')).strip()
    public_key = str(config.get('updates.public_key', '')).strip()
    manifest = fetch_signed_manifest(manifest_url, public_key)
    available = is_newer_version(manifest.version, __version__)
    asset = select_asset(manifest) if available else None
    return UpdateStatus(
        current_version=__version__,
        latest_version=manifest.version,
        available=available,
        asset=asset,
        message=(
            f'Update {manifest.version} is available'
            if available
            else f'{__version__} is up to date'
        ),
    )


def auto_stage_update(config: Config, wait_pid: Optional[int] = None) -> UpdateStatus:
    """Verify, download, and schedule a portable self-update.

    This never weakens verification: if signing, HTTPS, size, checksum, or write
    permissions fail, the current executable is left untouched.
    """
    status = check_for_update(config)
    if not status.available or not status.asset:
        return status
    if not getattr(sys, 'frozen', False):
        return UpdateStatus(
            status.current_version,
            status.latest_version,
            True,
            status.asset,
            'Update verified, but source checkouts are never self-replaced',
        )
    if not config.get('updates.auto_install', False):
        return UpdateStatus(
            status.current_version,
            status.latest_version,
            True,
            status.asset,
            'Update verified; automatic installation is disabled',
        )

    executable = Path(sys.executable).resolve()
    update_dir = _update_dir(config)
    update_dir.mkdir(parents=True, exist_ok=True)
    staged = update_dir / (status.asset.name + '.staged')
    download_verified_asset(status.asset, staged)
    restart_args = [arg for arg in sys.argv[1:] if arg != '--check-update']
    schedule_self_replace(
        executable,
        staged,
        [wait_pid or os.getpid()],
        restart_args=restart_args,
    )
    return UpdateStatus(
        status.current_version,
        status.latest_version,
        True,
        status.asset,
        f'Update {status.latest_version} verified and staged; restart scheduled',
    )


def maybe_auto_stage(config: Config, wait_pid: Optional[int] = None) -> bool:
    """Run one startup update check when explicitly enabled; return True if staged."""
    if not config.get('updates.enabled', False) or not config.get('updates.auto_install', False):
        return False
    logger = logging.getLogger(__name__)
    try:
        status = auto_stage_update(config, wait_pid=wait_pid)
        logger.info('%s', status.message)
        return bool(status.available and 'restart scheduled' in status.message)
    except (UpdateError, OSError, ValueError) as exc:
        logger.warning('Secure update check/install failed closed: %s', exc)
        return False
    except Exception as exc:
        logger.warning('Unexpected update error; current version kept: %s', exc)
        return False


def _update_dir(config: Config) -> Path:
    config_path = getattr(config, 'config_path', None)
    if config_path:
        return Path(config_path).parent / 'updates'
    return Path.home() / '.cache' / 'discord-rich-presence' / 'updates'
