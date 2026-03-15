import time
import logging
import threading
import traceback
from typing import Optional, Dict, Any
from pypresence import Presence, DiscordNotFound, InvalidID, InvalidPipe
from config import Config
from .detector_router import DetectorRouter
from platforms.window_reader_factory import WindowReaderFactory
from privacy import PrivacyRedactor

class PresenceService:
    def __init__(self, config: Config, dry_run: bool = False, once: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.once = once
        self.rpc = None
        self.connected = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 300
        
        self.logger = logging.getLogger(__name__)
        self.router = DetectorRouter(config)
        self.window_reader = WindowReaderFactory.create_reader()
        self.privacy = PrivacyRedactor(config)
        self._stop_event = threading.Event()
        
        self.last_payload = None
        self.last_window_signature = None
        
        # Adaptive polling
        self.base_poll_interval = 2.0
        self.idle_poll_interval = 5.0
        self.current_poll_interval = self.base_poll_interval
        
    def connect_discord(self) -> bool:
        try:
            client_id = self.config.get('discord.client_id', '')
            if not client_id:
                self.logger.error("No Discord Client ID configured. Please configure it in your settings.")
                self.connected = False
                return False
            
            self.rpc = Presence(client_id)
            self.rpc.connect()
            self.connected = True
            self.reconnect_delay = 5
            self.logger.info(f"Connected to Discord RPC with App ID {client_id}")
            return True
        except (DiscordNotFound, InvalidID, InvalidPipe, ConnectionRefusedError) as e:
            self.logger.debug(f"Discord not running or unavailable: {e}")
            self.connected = False
            return False
        except Exception as e:
            self.logger.debug(f"Error connecting: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.rpc and self.connected:
            try:
                self.rpc.close()
                self.logger.info("Disconnected from Discord RPC")
            except Exception:
                pass
            finally:
                self.connected = False

    def get_window_signature(self, window_info: Optional[Dict[str, Any]]) -> Optional[str]:
        if not window_info:
            return None
        return f"{window_info.get('window_id')}-{window_info.get('title')}-{window_info.get('cwd')}"

    def safe_detect(self) -> Optional[Dict[str, Any]]:
        try:
            # 1. Check window
            window_info = self.window_reader.get_active_window()
            
            # Simple adaptive polling: hash window state to determine if active checking needed
            current_signature = self.get_window_signature(window_info)
            if current_signature == self.last_window_signature and current_signature is not None:
                # Window didn't change, we can poll slightly slower
                self.current_poll_interval = self.idle_poll_interval
            else:
                self.current_poll_interval = self.base_poll_interval
                self.last_window_signature = current_signature

            # 2. Route activity
            activity_state = self.router.route(window_info)
            if not activity_state:
                return None
                
            # 3. Privacy Filter
            payload = activity_state.to_discord_payload()
            payload = self.privacy.redact_activity(payload)
            
            # 4. Buttons insertion
            self._add_buttons(payload)
            
            return payload
        except Exception as e:
            self.logger.error(f"Error in detection pipeline: {e}", exc_info=True)
            return None

    def _add_buttons(self, payload: dict):
        if self.config.get('privacy.mode', 'balanced') == 'strict':
            payload.pop('buttons', None)
            return
            
        buttons = []
        static_buttons = self.config.get('discord.buttons', [])
        for btn in static_buttons[:2]:
            if isinstance(btn, dict) and 'label' in btn and 'url' in btn:
                if str(btn['url']).startswith('http'):
                    buttons.append({'label': str(btn['label']), 'url': str(btn['url'])})
                    
        if len(buttons) < 2 and 'url' in payload and payload['url']:
            buttons.append({'label': 'View Page', 'url': payload['url']})
            payload.pop('url', None)
            
        if buttons:
            payload['buttons'] = buttons[:2]

    def update_presence(self, payload: Dict[str, Any]) -> bool:
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would send: {payload}")
            return True
            
        if not self.connected:
            return False
            
        try:
            if payload != self.last_payload:
                self.rpc.update(**payload)
                self.last_payload = payload
                self.logger.debug(f"Updated presence: {payload}")
            return True
        except Exception as e:
            self.logger.debug(f"RPC Update lost connection: {e}")
            self.connected = False
            return False

    def run(self):
        self.logger.info("Starting Discord Rich Presence Service")
        
        last_reconnect_attempt = 0
        
        try:
            while not self._stop_event.is_set():
                current_time = time.time()
                
                # Non-blocking reconnect
                if not self.connected and not self.dry_run:
                    if current_time - last_reconnect_attempt >= self.reconnect_delay:
                        last_reconnect_attempt = current_time
                        if self.connect_discord():
                            self.reconnect_delay = 5
                        else:
                            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                
                # Detection and update
                payload = self.safe_detect()
                
                if payload:
                    if self.connected or self.dry_run:
                        if not self.update_presence(payload):
                            # Connection dropped
                            pass
                else:
                    if self.connected and self.last_payload:
                        try:
                            self.rpc.clear()
                            self.last_payload = None
                            self.logger.debug("Cleared presence")
                        except Exception:
                            self.connected = False
                
                if self.once:
                    break
                    
                self._stop_event.wait(self.current_poll_interval)
                
        except Exception as e:
            self.logger.error(f"Fatal error in service: {e}", exc_info=True)
        finally:
            self.disconnect()

    def stop(self):
        self._stop_event.set()
