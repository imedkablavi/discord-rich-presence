#!/usr/bin/env python3
"""Discord Rich Presence service."""

import argparse
import logging
import os
import sys
import threading
import time
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from pypresence import DiscordNotFound, InvalidID, InvalidPipe, Presence

from activity_priority import ActivityPriorityEngine
from config import Config
from detectors.browser import BrowserDetector
from detectors.coding import CodingDetector
from detectors.gaming import GamingDetector
from detectors.media import MediaDetector
from detectors.terminal import TerminalDetector
from detectors.window import WindowDetector
from presence import PresenceBuilder
from runtime_state import RuntimeState
from tray_icon import run_with_tray


class DiscordRichPresenceService:
    """Detect activity and keep Discord RPC synchronized with the current state."""

    LOCK_SCREEN_APPS = {
        'lockapp', 'logonui', 'credentialuibroker',
        'kscreenlocker_greet', 'swaylock', 'i3lock', 'xsecurelock',
        'light-locker', 'xscreensaver',
    }

    def __init__(
        self,
        config: Config,
        dry_run: bool = False,
        once: bool = False,
        runtime: Optional[RuntimeState] = None,
        privacy_override: Optional[str] = None,
    ):
        self.config = config
        self.dry_run = dry_run
        self.once = once
        self.runtime = runtime
        self.privacy_override = privacy_override
        self.rpc: Optional[Presence] = None
        self.connected = False
        self.presence_active = False
        self.last_payload: Optional[Dict[str, Any]] = None
        self.reconnect_delay = 5
        self.max_reconnect_delay = 300
        self._stop_event = threading.Event()
        self._last_config_mtime: Optional[float] = None
        self.logger = logging.getLogger(__name__)

        self.window_detector = WindowDetector()
        self.browser_detector = BrowserDetector(config)
        self.terminal_detector = TerminalDetector(config)
        self.coding_detector = CodingDetector(config)
        self.media_detector = MediaDetector(config)
        self.gaming_detector = GamingDetector(config)
        self.priority_engine = ActivityPriorityEngine(config)
        self.presence_builder = PresenceBuilder(config)

    def _runtime_update(self, **fields: Any):
        runtime = getattr(self, 'runtime', None)
        if runtime:
            try:
                runtime.update(**fields)
            except Exception as e:
                self.logger.debug('Could not update runtime status: %s', e)

    def _wait(self, timeout: float) -> bool:
        """Wait interruptibly and honor GUI/runtime graceful-stop requests."""
        deadline = time.monotonic() + max(0.0, timeout)
        while not self._stop_event.is_set():
            runtime = getattr(self, 'runtime', None)
            if runtime:
                try:
                    if runtime.stop_requested():
                        self.logger.info('Graceful stop requested')
                        self._stop_event.set()
                        break
                except Exception as e:
                    self.logger.debug('Could not read runtime stop request: %s', e)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._stop_event.wait(min(0.25, remaining))
        return self._stop_event.is_set()

    @staticmethod
    def _activity_summary(payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if not payload:
            return None
        details = str(payload.get('details') or '').strip()
        state = str(payload.get('state') or '').strip()
        if details and state:
            return f'{details} — {state}'[:240]
        return details or state or None

    @classmethod
    def _is_lock_screen_window(cls, window_info: Dict[str, Any]) -> bool:
        app_name = str(window_info.get('app_name', '')).lower().replace('.exe', '').strip()
        compact = app_name.replace(' ', '').replace('_', '').replace('-', '')
        if any(name.replace('_', '').replace('-', '') in compact for name in cls.LOCK_SCREEN_APPS):
            return True
        title = str(window_info.get('title', '')).lower()
        return any(marker in title for marker in (
            'windows default lock screen', 'lock screen', 'screen locked'
        ))

    def connect_discord(self) -> bool:
        try:
            client_id = str(self.config.get('discord.client_id', '')).strip()
            if not client_id:
                self.logger.error('Discord client_id not configured')
                self._runtime_update(
                    connected=False,
                    state='configuration_error',
                    last_error='Missing Discord client ID',
                )
                return False
            self.rpc = Presence(client_id)
            self.rpc.connect()
            self.connected = True
            self.reconnect_delay = 5
            self.logger.info('Connected to Discord RPC')
            self._runtime_update(connected=True, state='running', last_error=None)
            return True
        except (DiscordNotFound, InvalidID, InvalidPipe) as e:
            self.logger.warning('Discord RPC unavailable: %s', e)
            self._runtime_update(
                connected=False,
                state='discord_offline',
                last_error=str(e)[:300],
            )
        except Exception as e:
            self.logger.error('Unexpected Discord connection error: %s', e)
            self.logger.debug(traceback.format_exc())
            self._runtime_update(
                connected=False,
                state='rpc_error',
                last_error=str(e)[:300],
            )
        self.connected = False
        self.rpc = None
        return False

    def disconnect_discord(self):
        if self.rpc and self.connected:
            try:
                self.rpc.close()
            except Exception as e:
                self.logger.debug('Error while closing Discord RPC: %s', e)
        self.connected = False
        self.rpc = None
        self._runtime_update(connected=False)

    def update_presence(self, payload: Dict[str, Any]) -> bool:
        clean_payload = {key: value for key, value in payload.items() if value is not None}
        if self.dry_run:
            self.logger.info('[DRY RUN] update: %s', clean_payload)
            self.last_payload = clean_payload
            self.presence_active = True
            self._runtime_update(
                connected=False,
                presence_active=True,
                state='dry_run',
                activity=self._activity_summary(clean_payload),
                last_error=None,
            )
            return True

        if not self.connected and not self.connect_discord():
            return False
        try:
            assert self.rpc is not None
            self.rpc.update(**clean_payload)
            self.last_payload = clean_payload
            self.presence_active = True
            self.logger.debug('Updated presence: %s', clean_payload)
            self._runtime_update(
                connected=True,
                presence_active=True,
                state='running',
                activity=self._activity_summary(clean_payload),
                last_error=None,
            )
            return True
        except Exception as e:
            self.logger.error('Failed to update presence: %s', e)
            self.logger.debug(traceback.format_exc())
            self.connected = False
            self.rpc = None
            self._runtime_update(
                connected=False,
                state='rpc_error',
                last_error=str(e)[:300],
            )
            return False

    def clear_presence(self) -> bool:
        """Clear Discord when activity disappears, is blocked, or privacy requires it."""
        if not self.presence_active:
            self._runtime_update(presence_active=False, activity=None)
            return True
        if self.dry_run:
            self.logger.info('[DRY RUN] clear presence')
            self.last_payload = None
            self.presence_active = False
            self._runtime_update(presence_active=False, activity=None, state='dry_run')
            return True
        if not self.connected and not self.connect_discord():
            return False
        try:
            assert self.rpc is not None
            self.rpc.clear()
            self.last_payload = None
            self.presence_active = False
            self.logger.debug('Cleared Discord presence')
            self._runtime_update(
                connected=True,
                presence_active=False,
                activity=None,
                state='running',
            )
            return True
        except Exception as e:
            self.logger.error('Failed to clear Discord presence: %s', e)
            self.connected = False
            self.rpc = None
            self._runtime_update(
                connected=False,
                state='rpc_error',
                last_error=str(e)[:300],
            )
            return False

    def _reset_rpc_for_client_id_change(self, old_client_id: str, new_client_id: str):
        """Detach the old Discord application before the next payload reconnects."""
        if old_client_id == new_client_id:
            return

        self.logger.info('Discord Client ID changed; resetting RPC connection')
        if self.presence_active:
            if self.dry_run:
                self.logger.info('[DRY RUN] clear presence for Client ID change')
            elif self.rpc and self.connected:
                try:
                    self.rpc.clear()
                except Exception as e:
                    self.logger.debug('Could not clear old Client ID presence: %s', e)

        self.last_payload = None
        self.presence_active = False
        self.disconnect_discord()
        self.reconnect_delay = 5
        self._runtime_update(
            connected=False,
            presence_active=False,
            activity=None,
            state='reconnecting',
            last_error=None,
        )

    def _reload_config_if_changed(self):
        path = getattr(self.config, 'config_path', None)
        if not path or not path.exists():
            return
        try:
            current_mtime = path.stat().st_mtime
            if self._last_config_mtime is None:
                self._last_config_mtime = current_mtime
                return
            if current_mtime == self._last_config_mtime:
                return

            old_client_id = str(self.config.get('discord.client_id', '')).strip()
            self.config.load(path)
            if self.privacy_override:
                self.config.set('privacy.mode', self.privacy_override)
            new_client_id = str(self.config.get('discord.client_id', '')).strip()

            self.presence_builder.reload()
            self._reset_rpc_for_client_id_change(old_client_id, new_client_id)
            self._last_config_mtime = current_mtime
            self.logger.info('Configuration reloaded')
            self._runtime_update(last_config_reload=time.time(), last_error=None)
        except Exception as e:
            self.logger.error('Config hot reload rejected; keeping previous config: %s', e)
            self._runtime_update(last_error=f'Config reload: {e}'[:300])

    def detect_activity(self) -> Optional[Dict[str, Any]]:
        self._reload_config_if_changed()

        if self.config.get('override.enabled', False):
            override = self.config.get('override', {}) or {}
            payload: Dict[str, Any] = {
                'details': str(override.get('details', ''))[:128],
                'state': str(override.get('state', ''))[:128],
                'large_image': override.get('large_image_key') or self.config.get('images.app', 'app'),
                'large_text': override.get('large_text') or None,
                'small_image': override.get('small_image_key') or None,
                'small_text': override.get('small_text') or None,
                'details_url': override.get('details_url') or None,
                'state_url': override.get('state_url') or None,
                'large_url': override.get('large_url') or None,
                'small_url': override.get('small_url') or None,
            }
            buttons = override.get('buttons') or []
            if isinstance(buttons, list):
                payload['buttons'] = [
                    {
                        'label': str(button.get('label', '')).strip()[:32],
                        'url': str(button.get('url', '')).strip()[:512],
                    }
                    for button in buttons[:2]
                    if isinstance(button, dict)
                    and button.get('label')
                    and str(button.get('url', '')).startswith(('http://', 'https://'))
                ]
            if override.get('use_start_timestamp'):
                payload['start'] = int(time.time() * 1000)

            party_id = override.get('party_id') or None
            try:
                party_current = int(override.get('party_current') or 0)
                party_max = int(override.get('party_max') or 0)
            except (TypeError, ValueError):
                party_current = party_max = 0
            if party_id:
                payload['party_id'] = str(party_id)
            if party_current > 0 and party_max >= party_current:
                payload['party_size'] = [party_current, party_max]

            if self.config.get('privacy.mode', 'balanced') == 'strict':
                payload.pop('buttons', None)
                for key in ('details_url', 'state_url', 'large_url', 'small_url'):
                    payload.pop(key, None)
            return payload

        window_info = self.window_detector.get_active_window()
        if not window_info:
            return None
        if self.config.get('rules.clear_on_lock_screen', True) and self._is_lock_screen_window(window_info):
            self.logger.debug('Lock screen detected; suppressing presence')
            return None

        app_name = str(window_info.get('app_name', '')).lower()
        if not self._is_app_allowed(app_name):
            return None

        candidates: Dict[str, Dict[str, Any]] = {}

        gaming = self.gaming_detector.detect(window_info)
        if gaming and gaming.get('is_game'):
            game_name = str(gaming.get('game_name') or '').lower()
            if not self._is_game_allowed(game_name):
                return None
            candidates['gaming'] = gaming

        media = self.media_detector.detect(window_info)
        if media and media.get('is_playing'):
            candidates['media'] = media

        terminal = self.terminal_detector.detect(window_info)
        if terminal and terminal.get('has_command'):
            candidates['terminal'] = terminal

        coding = self.coding_detector.detect(window_info)
        if coding:
            candidates['coding'] = coding

        browser = self.browser_detector.detect(window_info)
        if browser:
            searchable = ' '.join(str(value or '') for value in (
                browser.get('service'), browser.get('page_title'), browser.get('url')
            )).strip()
            if not self._is_site_allowed(searchable):
                return None
            candidates['browser'] = browser

        if self.config.get('rules.enabled_detectors.application', True):
            candidates['application'] = {
                'type': 'application',
                'app_name': window_info.get('app_name', 'Unknown'),
                'window_title': window_info.get('title', ''),
            }

        selected = self.priority_engine.choose(window_info, candidates)
        return self.presence_builder.build(selected) if selected else None

    def _is_game_allowed(self, game_name: str) -> bool:
        whitelist = [str(value).lower() for value in (self.config.get('rules.whitelist.games', []) or [])]
        blacklist = [str(value).lower() for value in (self.config.get('rules.blacklist.games', []) or [])]
        if game_name in blacklist:
            return False
        return not whitelist or game_name in whitelist

    def _is_app_allowed(self, app_name: str) -> bool:
        whitelist = [str(value).lower() for value in (self.config.get('rules.whitelist.apps', []) or [])]
        blacklist = [str(value).lower() for value in (self.config.get('rules.blacklist.apps', []) or [])]
        if app_name in blacklist:
            return False
        return not whitelist or app_name in whitelist

    def _is_site_allowed(self, title: str) -> bool:
        whitelist = [str(value).lower() for value in (self.config.get('rules.whitelist.sites', []) or [])]
        blacklist = [str(value).lower() for value in (self.config.get('rules.blacklist.sites', []) or [])]
        title_lower = str(title).lower()
        if any(keyword and keyword in title_lower for keyword in blacklist):
            return False
        return not whitelist or any(keyword and keyword in title_lower for keyword in whitelist)

    def should_update(self, new_payload: Optional[Dict[str, Any]]) -> bool:
        if new_payload is None:
            return False
        normalized = {key: value for key, value in new_payload.items() if value is not None}
        return not self.presence_active or normalized != (self.last_payload or {})

    def _handle_rpc_failure(self):
        self._runtime_update(retry_in_seconds=self.reconnect_delay)
        self._wait(self.reconnect_delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

    def run(self):
        self.logger.info('Starting Discord Rich Presence Service')
        self._runtime_update(
            state='starting',
            connected=False,
            presence_active=False,
            activity=None,
            last_error=None,
        )
        if not self.dry_run and not self.connect_discord():
            self.logger.warning('Discord is not available yet; service will retry')

        try:
            while not self._stop_event.is_set():
                try:
                    payload = self.detect_activity()
                    success = True
                    if payload is None:
                        if self.presence_active:
                            success = self.clear_presence()
                        else:
                            self._runtime_update(presence_active=False, activity=None)
                    elif self.should_update(payload):
                        success = self.update_presence(payload)

                    if not success:
                        self._handle_rpc_failure()
                        continue

                    self.reconnect_delay = 5
                    self._runtime_update(
                        state='dry_run' if self.dry_run else 'running',
                        connected=self.connected,
                        presence_active=self.presence_active,
                        retry_in_seconds=None,
                    )
                    if self.once:
                        break
                    interval = float(self.config.get('update_interval_secs', 2))
                    self._wait(max(1.0, interval))
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error('Error in main loop: %s', e, exc_info=True)
                    self._runtime_update(state='loop_error', last_error=str(e)[:300])
                    self._wait(max(1.0, float(self.config.get('update_interval_secs', 2))))
        except KeyboardInterrupt:
            self.logger.info('Received interrupt signal')
        finally:
            self._runtime_update(state='stopping')
            try:
                self.clear_presence()
            finally:
                self.disconnect_discord()
            self.logger.info('Discord Rich Presence Service stopped')

    def stop(self):
        self._stop_event.set()


def _default_log_path() -> Path:
    if sys.platform == 'win32':
        base = os.environ.get('LOCALAPPDATA')
        root = Path(base) if base else Path.home() / 'AppData' / 'Local'
        return root / 'discord-rich-presence' / 'logs' / 'app.log'
    return Path.home() / '.local' / 'state' / 'discord-rich-presence' / 'app.log'


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root = logging.getLogger()
    root.setLevel(level)

    if not any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, RotatingFileHandler)
        for handler in root.handlers
    ):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

    try:
        log_path = _default_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not any(
            isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename) == log_path
            for handler in root.handlers
        ):
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=2 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8',
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
    except Exception:
        root.exception('Could not initialize file logging')


def main():
    parser = argparse.ArgumentParser(description='Discord Rich Presence Service')
    parser.add_argument('--config', type=Path, default=None, help='Path to configuration file')
    parser.add_argument(
        '--privacy',
        choices=['off', 'balanced', 'strict'],
        help='Override privacy mode',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show RPC operations without sending them',
    )
    parser.add_argument('--once', action='store_true', help='Perform one detection cycle and exit')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--tray', action='store_true', help='Show the system tray control')
    args = parser.parse_args()

    setup_logging(args.verbose)
    runtime = RuntimeState()
    if not runtime.acquire():
        logging.warning('Another Discord Rich Presence service instance is already running')
        return

    try:
        try:
            config = Config(args.config)
            if args.privacy:
                config.set('privacy.mode', args.privacy)
        except Exception as e:
            logging.error('Failed to load configuration: %s', e)
            runtime.update(state='configuration_error', last_error=str(e)[:300])
            return

        service = DiscordRichPresenceService(
            config,
            dry_run=args.dry_run,
            once=args.once,
            runtime=runtime,
            privacy_override=args.privacy,
        )
        if args.tray or config.get('system.start_minimized', False):
            run_with_tray(service.run, config, service.stop)
        else:
            service.run()
    finally:
        runtime.release()


if __name__ == '__main__':
    main()
