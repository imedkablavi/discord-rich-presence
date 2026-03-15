import logging
import re
from typing import Optional, Dict, Any
from config import Config
from core.activity_model import ActivityState
import time

class BrowserDetector:
    BROWSERS = {
        'firefox': 'Firefox',
        'chrome': 'Chrome',
        'chromium': 'Chromium',
        'brave': 'Brave',
        'edge': 'Edge',
        'msedge': 'Edge',
        'opera': 'Opera',
        'vivaldi': 'Vivaldi',
    }
    
    YOUTUBE_REGEX = re.compile(r'^(.*?)\s*-\s*YouTube$')
    GITHUB_REGEX = re.compile(r'^(.*?)\s*-\s*GitHub$')
    TWITCH_REGEX = re.compile(r'^(.*?)\s*-\s*Twitch$')
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.private_markers = config.get('rules.private_markers', ['Incognito', 'Private Browsing', 'InPrivate'])
        self._start_time = int(time.time())
        
    def detect(self, window_info: Dict[str, Any]) -> Optional[ActivityState]:
        if not self.config.get('rules.enabled_detectors.browser', True):
            return None
            
        app_name = window_info.get('app_name', '').lower()
        title = window_info.get('title', '')
        
        browser_name = None
        for key, name in self.BROWSERS.items():
            if key in app_name:
                browser_name = name
                break
                
        if not browser_name:
            return None
            
        # Private checking
        if any(marker.lower() in title.lower() for marker in self.private_markers) or '⧉' in title or '🕶' in title:
            return ActivityState(
                type="browser",
                details="Private Browsing",
                state=browser_name,
                large_image=self.config.get('images.browser', 'browser'),
                large_text=browser_name,
                start_time=self._start_time
            )
            
        # Clean title
        page_title = title
        separators = [f' - {browser_name}', f' — {browser_name}', f' – {browser_name}']
        for sep in separators:
            if title.endswith(sep):
                page_title = title[:-len(sep)]
                break

        # Confidence Scoring & Safe URLs
        # Never fabricate URLs based on search strings. Only provide a URL button if we are absolutely certain of the site.
        large_image = self.config.get('images.browser', 'browser')
        state = browser_name
        details = page_title
        url = None
        
        # YouTube
        yt_match = self.YOUTUBE_REGEX.match(page_title)
        if yt_match:
            details = f"Watching: {yt_match.group(1)}"
            large_image = self.config.get('images.sites.youtube', 'youtube')
            url = "https://www.youtube.com"
        
        # GitHub
        gh_match = self.GITHUB_REGEX.match(page_title)
        if gh_match:
            details = gh_match.group(1)
            large_image = self.config.get('images.sites.github', 'github')
            url = "https://github.com"
            
        # Twitch
        tw_match = self.TWITCH_REGEX.match(page_title)
        if tw_match:
            details = f"Watching {tw_match.group(1)}"
            large_image = self.config.get('images.sites.twitch', 'twitch')
            url = "https://twitch.tv"
            
        # Generic sites (fallback without URL)
        for site, img in (self.config.get('images.sites', {}) or {}).items():
            if site.lower() in page_title.lower() and url is None:
                large_image = img

        return ActivityState(
            type="browser",
            details=details,
            state=state,
            large_image=large_image,
            large_text=browser_name,
            start_time=self._start_time,
            url=url
        )
