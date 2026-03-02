"""
Discord Rich Presence payload builder
"""

import time
from typing import Dict, Any, Optional, List
from config import Config
from privacy import PrivacyRedactor


class PresenceBuilder:
    """Builds Discord Rich Presence payloads from activity data"""
    
    def __init__(self, config: Config):
        self.config = config
        self.redactor = PrivacyRedactor(config)
        self.activity_start_times: Dict[str, int] = {}
    
    def build(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Build presence payload from activity data"""
        activity_type = activity.get('type', 'application')
        
        # Apply privacy redaction
        activity = self.redactor.redact_activity(activity)
        
        # Build payload based on activity type
        if activity_type == 'media':
            return self._build_media(activity)
        elif activity_type == 'terminal':
            return self._build_terminal(activity)
        elif activity_type == 'coding':
            return self._build_coding(activity)
        elif activity_type == 'browser':
            return self._build_browser(activity)
        elif activity_type == 'gaming':
            return self._build_gaming(activity)
        else:
            return self._build_application(activity)
    
    def _build_media(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Build payload for media playback"""
        title = activity.get('title', 'Unknown')
        player = activity.get('player', 'Media Player')
        is_playing = activity.get('is_playing', False)
        position = activity.get('position', 0)
        duration = activity.get('duration', 0)
        
        details = f"{'Watching' if is_playing else 'Paused'} · {title}"
        
        # Format time
        state_parts = [player]
        if duration > 0:
            pos_str = self._format_time(position)
            dur_str = self._format_time(duration)
            state_parts.append(f"{pos_str}/{dur_str}")
        
        state = ' · '.join(state_parts)
        
        payload = {
            'details': details[:128],
            'state': state[:128],
            'large_image': self._resolve_media_image(player),
            'large_text': player,
        }
        
        # Add timestamp if playing
        if is_playing:
            now = int(time.time())
            
            # If duration is available, set both start and end for progress bar
            if duration > 0:
                # Calculate when the track started and when it will end based on current position
                # This makes the progress bar move correctly in Discord
                start_ts = now - position
                end_ts = now + (duration - position)
                
                payload['start'] = start_ts
                payload['end'] = end_ts
            else:
                # If no duration (livestream or unknown), just show elapsed time
                start_ts = now - position
                payload['start'] = start_ts
        
        self._add_buttons(payload)
        return payload
    
    def _build_terminal(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Build payload for terminal activity"""
        command = activity.get('command', '')
        shell = activity.get('shell', 'Terminal')
        directory = activity.get('directory', '')
        
        details = f"Terminal · {command}" if command else "Terminal"
        state = f"{shell} · {directory}" if directory else shell
        
        payload = {
            'details': details[:128],
            'state': state[:128],
            'large_image': self.config.get('images.terminal', 'terminal'),
            'large_text': shell,
            'start': self._get_activity_start('terminal', command or 'idle')
        }
        
        self._add_buttons(payload)
        return payload
    
    def _build_coding(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Build payload for coding activity"""
        filename = activity.get('filename', '')
        language = activity.get('language', '')
        editor = activity.get('editor', 'Code Editor')
        project = activity.get('project', '')
        
        details = f"Coding · {filename}" if filename else "Coding"
        state = f"{editor} · {project}" if project else editor
        
        payload = {
            'details': details[:128],
            'state': state[:128],
            'large_image': self.config.get('images.code', 'code'),
            'large_text': editor,
            'start': self._get_activity_start('coding', project or filename)
        }
        
        # Add language icon if available
        if language:
            lang_key = self.config.get(f'images.langs.{language.lower()}')
            if lang_key:
                payload['small_image'] = lang_key
                payload['small_text'] = language.title()
        
        self._add_buttons(payload)
        return payload
    
    def _build_browser(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Build payload for browser activity"""
        browser_name = activity.get('browser_name', 'Browser')
        is_private = activity.get('is_private', False)
        page_title = activity.get('page_title', '')
        
        if is_private:
            details = "Private browsing"
            state = browser_name
        else:
            details = page_title if page_title else "Browsing"
            state = browser_name
        
        payload = {
            'details': details[:128],
            'state': state[:128],
            'large_image': self._resolve_browser_image(page_title),
            'large_text': browser_name,
            'start': self._get_activity_start('browser', 'browsing')
        }
        
        self._add_buttons(payload)
        return payload
    
    def _build_application(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Build payload for generic application"""
        app_name = activity.get('app_name', 'Application')
        window_title = activity.get('window_title', '')
        
        details = f"{app_name} active"
        state = window_title[:100] if window_title else app_name
        
        app_key = app_name.lower()
        apps_map = self.config.get('images.apps', {}) or {}
        image_key = apps_map.get(app_key, self.config.get('images.app', 'app'))

        payload = {
            'details': details[:128],
            'state': state[:128],
            'large_image': image_key,
            'large_text': app_name,
            'start': self._get_activity_start('app', app_name)
        }
        
        self._add_buttons(payload)
        return payload

    def _build_gaming(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        game_name = activity.get('game_name') or activity.get('launcher') or 'Game'
        launcher = activity.get('launcher')
        details = f"Playing · {game_name}"
        state = launcher or 'Gaming'
        # resolve image: try images.apps or images.games
        key = self.config.get(f"images.apps.{str(game_name).lower()}") or \
              self.config.get(f"images.games.{str(game_name).lower()}") or \
              self.config.get('images.app', 'app')
        payload = {
            'details': details[:128],
            'state': state[:128],
            'large_image': key,
            'large_text': game_name,
            'start': self._get_activity_start('gaming', game_name)
        }
        self._add_buttons(payload)
        return payload
    
    def _add_buttons(self, payload: Dict[str, Any]):
        """Add buttons to payload if configured, dynamically based on activity"""
        if self.config.get('privacy.mode', 'balanced') == 'strict':
            return
        
        buttons = []
        
        # 1. Custom Buttons from Config (Static)
        config_buttons = self.config.get('discord.buttons', [])
        if config_buttons and isinstance(config_buttons, list):
            for btn in config_buttons[:2]:
                if isinstance(btn, dict) and 'label' in btn and 'url' in btn:
                    url = str(btn['url']).strip().strip('`')
                    label = str(btn['label']).strip()
                    if url and label and (url.startswith('http://') or url.startswith('https://')):
                        buttons.append({'label': label, 'url': url})
        
        # 2. Dynamic Buttons based on activity (if space allows)
        if len(buttons) < 2:
            details = str(payload.get('details', ''))
            state = str(payload.get('state', ''))
            large_image = str(payload.get('large_image', ''))
            
            # YouTube Detection
            if 'YouTube' in details or 'YouTube' in state or large_image == 'youtube':
                # Try to extract URL if detector provided it (BrowserDetector might not, but let's check payload)
                if payload.get('url'):
                    buttons.append({'label': 'Search on YouTube', 'url': payload.get('url')})
                else:
                    buttons.append({'label': 'Watch on YouTube', 'url': 'https://www.youtube.com'})
            
            # GitHub Detection
            elif 'GitHub' in details or 'GitHub' in state or large_image == 'github':
                if payload.get('url'):
                    buttons.append({'label': 'View on GitHub', 'url': payload.get('url')})
                else:
                    buttons.append({'label': 'Open GitHub', 'url': 'https://github.com'})
            
            # Generic URL support for other platforms
            elif payload.get('url'):
                # Extract domain or platform name
                import urllib.parse
                try:
                    domain = urllib.parse.urlparse(payload['url']).netloc.replace('www.', '')
                    platform = domain.split('.')[0].title()
                    buttons.append({'label': f'Open {platform}', 'url': payload['url']})
                except:
                    buttons.append({'label': 'Open Link', 'url': payload['url']})
                
        if buttons:
            payload['buttons'] = buttons[:2]
    
    def _get_activity_start(self, activity_type: str, activity_id: str) -> int:
        """Get or create start timestamp for activity"""
        key = f"{activity_type}:{activity_id}"
        
        if key not in self.activity_start_times:
            self.activity_start_times[key] = int(time.time())
        
        # Clean old entries (keep last 10)
        if len(self.activity_start_times) > 10:
            oldest_keys = sorted(
                self.activity_start_times.keys(),
                key=lambda k: self.activity_start_times[k]
            )[:-10]
            for old_key in oldest_keys:
                del self.activity_start_times[old_key]
        
        return self.activity_start_times[key]
    
    @staticmethod
    def _format_time(seconds: int) -> str:
        """Format seconds to mm:ss or hh:mm:ss"""
        if seconds < 0:
            seconds = 0
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"

    def _resolve_media_image(self, player: str) -> str:
        player_key = None
        if player:
            player_key = self.config.get(f'images.players.{str(player).lower()}')
        return player_key or self.config.get('images.video', 'video')

    def _resolve_browser_image(self, title: str) -> str:
        sites = self.config.get('images.sites', {}) or {}
        tl = str(title).lower()
        for key in sites.keys():
            if key and key.lower() in tl:
                return sites[key]
        return self.config.get('images.browser', 'browser')
