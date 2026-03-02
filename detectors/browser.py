"""
Browser activity detection
"""

import logging
from typing import Optional, Dict, Any
from config import Config


class BrowserDetector:
    """Detects browser activity and private browsing mode"""
    
    BROWSERS = {
        'firefox': 'Firefox',
        'chrome': 'Chrome',
        'chromium': 'Chromium',
        'brave': 'Brave',
        'edge': 'Edge',
        'opera': 'Opera',
        'vivaldi': 'Vivaldi',
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.private_markers = config.get('rules.private_markers', [])
        self.youtube_domains = config.get('rules.youtube_domains', [])
    
    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect if window is a browser and extract activity"""
        if not window_info:
            return None
        
        app_name = window_info.get('app_name', '').lower()
        title = window_info.get('title', '')
        
        # Check if it's a browser
        browser_name = None
        for key, name in self.BROWSERS.items():
            if key in app_name:
                browser_name = name
                break
        
        if not browser_name:
            return None
        
        # Check for private browsing
        is_private = self._is_private_browsing(title, app_name)
        
        if is_private:
            return {
                'type': 'browser',
                'browser_name': browser_name,
                'is_private': True,
                'page_title': ''
            }
        
        # Extract page title
        page_title = self._extract_page_title(title, browser_name)
        
        # Try to infer URL (Basic inference based on title)
        url = self._generate_url(page_title)
        
        return {
            'type': 'browser',
            'browser_name': browser_name,
            'is_private': False,
            'page_title': page_title,
            'url': url
        }
    
    def _generate_url(self, title: str) -> Optional[str]:
        """Generate a valid URL or search link based on content"""
        if not title:
            return None
            
        import urllib.parse
        encoded = urllib.parse.quote(title)
        
        # SoundCloud
        if 'SoundCloud' in title:
            # "Song Title by Artist - SoundCloud" -> remove suffix
            clean = title.replace(' - SoundCloud', '').replace(' | SoundCloud', '')
            return f"https://soundcloud.com/search?q={urllib.parse.quote(clean)}"
            
        # Netflix
        elif 'Netflix' in title:
            # "Movie Title - Netflix"
            clean = title.replace(' - Netflix', '')
            return f"https://www.netflix.com/search?q={urllib.parse.quote(clean)}"
            
        # YouTube
        elif 'YouTube' in title:
            clean = title.replace(' - YouTube', '')
            return f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean)}"
            
        # Twitch
        elif 'Twitch' in title:
            # "Streamer - Twitch"
            clean = title.replace(' - Twitch', '')
            # If it looks like a channel name (no spaces), link directly
            if ' ' not in clean:
                return f"https://www.twitch.tv/{clean}"
            return f"https://www.twitch.tv/search?term={urllib.parse.quote(clean)}"
            
        # Spotify (Web)
        elif 'Spotify' in title:
            clean = title.replace(' - Spotify', '')
            return f"https://open.spotify.com/search/{urllib.parse.quote(clean)}"
            
        # GitHub
        elif 'GitHub' in title:
            return "https://github.com"
            
        # Disney+
        elif 'Disney+' in title:
             return "https://www.disneyplus.com"
             
        # Hulu
        elif 'Hulu' in title:
            return "https://www.hulu.com"
            
        # Prime Video
        elif 'Prime Video' in title:
            clean = title.replace(' - Prime Video', '')
            return f"https://www.amazon.com/s?k={urllib.parse.quote(clean)}&i=instant-video"
            
        return None
    
    def _is_private_browsing(self, title: str, app_name: str) -> bool:
        """Check if browser is in private/incognito mode"""
        # Check title for private markers
        for marker in self.private_markers:
            if marker.lower() in title.lower():
                return True
        
        # Check for incognito indicator (⧉ symbol)
        if '⧉' in title or '🕶' in title:
            return True
        
        return False
    
    def _extract_page_title(self, title: str, browser_name: str) -> str:
        """Extract clean page title from window title"""
        if not title:
            return ''
        
        # Remove browser name suffix
        # Most browsers use format: "Page Title - Browser Name"
        separators = [' - ', ' — ', ' – ']
        
        for sep in separators:
            if sep + browser_name in title:
                parts = title.rsplit(sep + browser_name, 1)
                title = parts[0]
                break
        
        # Handle YouTube titles
        for domain in self.youtube_domains:
            if domain in title:
                # YouTube format: "Video Title - YouTube"
                parts = title.split(' - ' + domain)
                if len(parts) > 0:
                    title = parts[0]
                break
        
        # Handle Netflix, Prime Video, etc.
        streaming_services = ['Netflix', 'Prime Video', 'Disney+', 'Hulu', 'SoundCloud', 'Spotify', 'Twitch']
        for service in streaming_services:
            if service in title:
                # Handle " | " or " - " separators
                for sep in [' - ', ' | ']:
                    if sep + service in title:
                        parts = title.split(sep + service)
                        if len(parts) > 0:
                            title = parts[0]
                        break
                break
        
        return title.strip()
