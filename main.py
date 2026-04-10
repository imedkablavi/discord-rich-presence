#!/usr/bin/env python3
"""
Discord Rich Presence Service
Automatically updates Discord Rich Presence based on current activity
"""

import sys
import time
import logging
import argparse
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

from pypresence import Presence, DiscordNotFound, InvalidID, InvalidPipe

from config import Config
from presence import PresenceBuilder
from tray_icon import run_with_tray
from detectors.window import WindowDetector
from detectors.browser import BrowserDetector
from detectors.terminal import TerminalDetector
from detectors.coding import CodingDetector
from detectors.media import MediaDetector
from detectors.gaming import GamingDetector
from detectors.plugin_loader import PluginDetectorManager


class DiscordRichPresenceService:
    """Main service class for Discord Rich Presence updates"""
    
    def __init__(self, config: Config, dry_run: bool = False, once: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.once = once
        self.rpc: Optional[Presence] = None
        self.connected = False
        self.last_payload: Optional[Dict[str, Any]] = None
        self.reconnect_delay = 5
        self.max_reconnect_delay = 300
        
        # Initialize detectors
        self.window_detector = WindowDetector()
        self.browser_detector = BrowserDetector(config)
        self.terminal_detector = TerminalDetector(config)
        self.coding_detector = CodingDetector(config)
        self.media_detector = MediaDetector(config)
        self.gaming_detector = GamingDetector(config)
        self.plugin_detector = PluginDetectorManager(config)
        self.presence_builder = PresenceBuilder(config)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def connect_discord(self) -> bool:
        """Connect to Discord RPC with error handling"""
        user_client_id = str(self.config.get('discord.client_id', '') or '').strip()
        fallback_ids = [
            str(x).strip()
            for x in (self.config.get('discord.fallback_client_ids', []) or [])
            if str(x).strip()
        ]
        candidates = []
        for cid in [user_client_id, *fallback_ids, '1437867564762923028']:
            if cid and cid not in candidates:
                candidates.append(cid)

        if not candidates:
            self.logger.error("No Discord client IDs available")
            return False

        for client_id in candidates:
            try:
                self.rpc = Presence(client_id)
                self.rpc.connect()
                self.connected = True
                self.reconnect_delay = 5
                if user_client_id and client_id == user_client_id:
                    self.logger.info("Connected to Discord RPC")
                else:
                    self.logger.info(f"Connected to Discord RPC using fallback client ID: {client_id}")
                return True
            except (DiscordNotFound, InvalidID, InvalidPipe) as e:
                self.logger.warning(f"Discord connection failed with client ID {client_id}: {e}")
                self.logger.debug(traceback.format_exc())
            except Exception as e:
                self.logger.warning(f"Unexpected Discord connection error with client ID {client_id}: {e}")
                self.logger.debug(traceback.format_exc())

        self.connected = False
        return False
    
    def disconnect_discord(self):
        """Safely disconnect from Discord RPC"""
        if self.rpc and self.connected:
            try:
                self.rpc.close()
                self.logger.info("Disconnected from Discord RPC")
            except Exception as e:
                self.logger.warning(f"Error during disconnect: {e}")
            finally:
                self.connected = False
    
    def update_presence(self, payload: Dict[str, Any]) -> bool:
        """Update Discord presence with given payload"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would send: {payload}")
            return True
        
        if not self.connected:
            if not self.connect_discord():
                return False
        
        try:
            # Remove None values
            clean_payload = {k: v for k, v in payload.items() if v is not None}
            
            self.rpc.update(**clean_payload)
            self.last_payload = payload
            self.logger.debug(f"Updated presence: {clean_payload}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update presence: {e}")
            self.logger.debug(traceback.format_exc())
            self.connected = False
            return False
    
    def detect_activity(self) -> Optional[Dict[str, Any]]:
        """Detect current activity and build presence payload"""
        try:
            if hasattr(self.config, 'config_path') and self.config.config_path and self.config.config_path.exists():
                # Check modification time to avoid unnecessary reloads
                current_mtime = self.config.config_path.stat().st_mtime
                if not hasattr(self, '_last_config_mtime') or current_mtime != self._last_config_mtime:
                    self.config.load(self.config.config_path)
                    self._last_config_mtime = current_mtime
                    self.plugin_detector.reload()
        except Exception:
            pass
        
        # Manual override
        if self.config.get('override.enabled', False):
            override = self.config.get('override', {}) or {}
            payload = {
                'details': str(override.get('details', ''))[:128],
                'state': str(override.get('state', ''))[:128],
                'large_image': (override.get('large_image_key') or self.config.get('images.app', 'app')),
                'large_text': override.get('large_text') or None,
                'small_image': (override.get('small_image_key') or None),
                'small_text': override.get('small_text') or None,
                'details_url': override.get('details_url') or None,
                'state_url': override.get('state_url') or None,
                'large_url': override.get('large_url') or None,
                'small_url': override.get('small_url') or None,
            }
            buttons = override.get('buttons') or []
            if isinstance(buttons, list) and len(buttons) > 0:
                payload['buttons'] = [
                    {'label': str(b.get('label','')).strip(), 'url': str(b.get('url','')).strip()}
                    for b in buttons[:2]
                    if b.get('label') and b.get('url')
                ]
            if override.get('use_start_timestamp'):
                payload['start'] = int(time.time())
            # Party info
            party_id = override.get('party_id') or None
            party_cur = override.get('party_current') or 0
            party_max = override.get('party_max') or 0
            if party_id:
                payload['party_id'] = party_id
            if party_max and party_cur and int(party_max) >= int(party_cur):
                payload['party_size'] = [int(party_cur), int(party_max)]
            if self.config.get('privacy.mode','balanced') == 'strict':
                payload.pop('buttons', None)
            return payload

        # Get active window info
        window_info = self.window_detector.get_active_window()
        if not window_info:
            return None
        app_name_norm = window_info.get('app_name', '').lower()
        if not self._is_app_allowed(app_name_norm):
            return None

        # Priority 1: Gaming
        gaming_activity = self.gaming_detector.detect(window_info)
        if gaming_activity:
            # Optional gaming whitelist/blacklist
            gname = str(gaming_activity.get('game_name') or '').lower()
            if not self._is_game_allowed(gname):
                return None
            return self.presence_builder.build(gaming_activity)

        # Priority 2: Media playback (MPRIS)
        media_activity = self.media_detector.detect(window_info)
        if media_activity and media_activity.get('is_playing'):
            return self.presence_builder.build(media_activity)
        
        # Priority 3: Terminal with active command
        terminal_activity = self.terminal_detector.detect(window_info)
        if terminal_activity and terminal_activity.get('has_command'):
            return self.presence_builder.build(terminal_activity)
        
        # Priority 4: Code editor
        coding_activity = self.coding_detector.detect(window_info)
        if coding_activity:
            return self.presence_builder.build(coding_activity)
        
        # Priority 5: Browser
        browser_activity = self.browser_detector.detect(window_info)
        if browser_activity:
            page_title = browser_activity.get('page_title', '')
            if self._is_site_allowed(page_title):
                return self.presence_builder.build(browser_activity)
            else:
                return None

        # Priority 6: Community plugins
        plugin_activity = self.plugin_detector.detect(window_info)
        if plugin_activity:
            return self.presence_builder.build(plugin_activity)
        
        # Priority 7: Generic application
        generic_activity = {
            'type': 'application',
            'app_name': window_info.get('app_name', 'Unknown'),
            'window_title': window_info.get('title', '')
        }
        return self.presence_builder.build(generic_activity)

    def _is_game_allowed(self, game_name: str) -> bool:
        wl = [str(x).lower() for x in (self.config.get('rules.whitelist.games', []) or [])]
        bl = [str(x).lower() for x in (self.config.get('rules.blacklist.games', []) or [])]
        if game_name in bl:
            return False
        if wl and game_name not in wl:
            return False
        return True

    def _is_app_allowed(self, app_name: str) -> bool:
        wl = [str(x).lower() for x in (self.config.get('rules.whitelist.apps', []) or [])]
        bl = [str(x).lower() for x in (self.config.get('rules.blacklist.apps', []) or [])]
        if app_name in bl:
            return False
        if wl and app_name not in wl:
            return False
        return True

    def _is_site_allowed(self, title: str) -> bool:
        wl = [str(x).lower() for x in (self.config.get('rules.whitelist.sites', []) or [])]
        bl = [str(x).lower() for x in (self.config.get('rules.blacklist.sites', []) or [])]
        title_l = str(title).lower()
        for kw in bl:
            if kw and kw in title_l:
                return False
        if wl:
            return any(kw in title_l for kw in wl if kw)
        return True
    
    def should_update(self, new_payload: Optional[Dict[str, Any]]) -> bool:
        """Check if presence should be updated"""
        if new_payload is None:
            return False
        
        if self.last_payload is None:
            return True
        
        # Compare key fields to avoid unnecessary updates
        key_fields = ['details', 'state', 'large_image', 'small_image']
        for field in key_fields:
            if new_payload.get(field) != self.last_payload.get(field):
                return True
        
        return False
    
    def run(self):
        """Main service loop"""
        self.logger.info("Starting Discord Rich Presence Service")
        
        if not self.dry_run:
            if not self.connect_discord():
                self.logger.error("Failed to connect to Discord. Retrying...")
        
        update_interval = max(1.0, float(self.config.get('update_interval_secs', 2)))
        
        import threading
        if not hasattr(self, '_stop_event'):
            self._stop_event = threading.Event()
        try:
            while not self._stop_event.is_set():
                try:
                    # Detect current activity
                    payload = self.detect_activity()
                    
                    # Update if changed
                    if self.should_update(payload):
                        if self.update_presence(payload):
                            self.reconnect_delay = 5
                        else:
                            # Exponential backoff on failure
                            self.reconnect_delay = min(
                                self.reconnect_delay * 2,
                                self.max_reconnect_delay
                            )
                            if self._stop_event.wait(self.reconnect_delay):
                                break
                            continue
                    
                    # Exit if --once flag is set
                    if self.once:
                        self.logger.info("Single update completed, exiting")
                        break
                    
                    # Wait for next update
                    if self._stop_event.wait(update_interval):
                        break
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}", exc_info=True)
                    if self._stop_event.wait(update_interval):
                        break
        
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down")
        finally:
            self.disconnect_discord()

    def stop(self):
        try:
            if hasattr(self, '_stop_event'):
                self._stop_event.set()
        except Exception:
            pass


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(
        description='Discord Rich Presence Service - Auto-update based on activity'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=None,  # Will use platform-specific default in Config class
        help='Path to configuration file'
    )
    parser.add_argument(
        '--privacy',
        choices=['off', 'balanced', 'strict'],
        help='Override privacy mode'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be sent without actually sending'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Update once and exit'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--tray',
        action='store_true',
        help='Show system tray for privacy and control'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    try:
        config = Config(args.config)
        
        # Override privacy mode if specified
        if args.privacy:
            config.set('privacy.mode', args.privacy)
        
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Run service
    service = DiscordRichPresenceService(
        config=config,
        dry_run=args.dry_run,
        once=args.once
    )
    if args.tray or config.get('system.start_minimized', False):
        run_with_tray(service.run, config, service.stop)
    else:
        service.run()


if __name__ == '__main__':
    main()
