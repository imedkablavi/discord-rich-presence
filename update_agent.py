"""High-level signed update lifecycle used by the service and control panel."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

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


ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class UpdateStatus:
    current_version: str
    latest_version: Optional[str]
    available: bool
    asset: Optional[ReleaseAsset]
    message: str
    staged: bool = False


def check_for_update(config: Config) -> UpdateStatus:
    if not config.get('updates.enabled', False):
        return UpdateStatus(__version__, None, False, None, 'Update checks are off')
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
            f'Version {manifest.version} is available'
            if available
            else f'Version {__version__} is up to date'
        ),
    )


def stage_update(
    config: Config,
    *,
    wait_pids: Optional[Iterable[int]] = None,
    restart_args: Optional[list[str]] = None,
    progress: Optional[ProgressCallback] = None,
) -> UpdateStatus:
    """Verify, download, and schedule a user-approved portable self-update.

    The currently installed executable is left untouched until signature, size,
    and SHA-256 checks have all succeeded. The detached replacement helper keeps
    a rollback copy and restores it if the restarted build exits immediately.
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
            'An update is available, but source checkouts are not self-updated',
        )

    executable = Path(sys.executable).resolve()
    if not os.access(executable.parent, os.W_OK):
        return UpdateStatus(
            status.current_version,
            status.latest_version,
            True,
            status.asset,
            'An update is available. This installation must be updated with its package manager',
        )

    update_dir = _update_dir(config)
    update_dir.mkdir(parents=True, exist_ok=True)
    staged = update_dir / (status.asset.name + '.staged')
    download_verified_asset(status.asset, staged, progress=progress)

    pids = [int(pid) for pid in (wait_pids or [os.getpid()]) if int(pid) > 0]
    args = list(restart_args) if restart_args is not None else [
        arg for arg in sys.argv[1:] if arg != '--check-update'
    ]
    schedule_self_replace(executable, staged, pids, restart_args=args)
    return UpdateStatus(
        status.current_version,
        status.latest_version,
        True,
        status.asset,
        f'Version {status.latest_version} is verified and ready to install',
        staged=True,
    )


def auto_stage_update(
    config: Config,
    wait_pid: Optional[int] = None,
    progress: Optional[ProgressCallback] = None,
) -> UpdateStatus:
    """Prepare an update only when automatic update installation is enabled."""
    status = check_for_update(config)
    if not status.available or not status.asset:
        return status
    if not config.get('updates.auto_install', False):
        return UpdateStatus(
            status.current_version,
            status.latest_version,
            True,
            status.asset,
            'An update is available. Automatic installation is off',
        )
    return stage_update(
        config,
        wait_pids=[wait_pid or os.getpid()],
        progress=progress,
    )


def maybe_auto_stage(config: Config, wait_pid: Optional[int] = None) -> bool:
    """Run one startup update check when explicitly enabled; return True if staged."""
    if not config.get('updates.enabled', False) or not config.get('updates.auto_install', False):
        return False
    logger = logging.getLogger(__name__)
    try:
        status = auto_stage_update(config, wait_pid=wait_pid)
        logger.info('%s', status.message)
        return status.staged
    except (UpdateError, OSError, ValueError) as exc:
        logger.warning('Secure update check/install failed: %s', exc)
        return False
    except Exception as exc:
        logger.warning('Unexpected update error; current version kept: %s', exc)
        return False


def _update_dir(config: Config) -> Path:
    config_path = getattr(config, 'config_path', None)
    if config_path:
        return Path(config_path).parent / 'updates'
    return Path.home() / '.cache' / 'discord-rich-presence' / 'updates'
