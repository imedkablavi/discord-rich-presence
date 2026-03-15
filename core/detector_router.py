import logging
from typing import Optional, Dict, Any
from config import Config
from .activity_model import ActivityState

class DetectorRouter:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._init_detectors()

    def _init_detectors(self):
        from detectors.gaming import GamingDetector
        from detectors.media import MediaDetector
        from detectors.terminal import TerminalDetector
        from detectors.coding import CodingDetector
        from detectors.browser import BrowserDetector
        
        # Priority order
        self.detectors = [
            GamingDetector(self.config),
            MediaDetector(self.config),
            TerminalDetector(self.config),
            CodingDetector(self.config),
            BrowserDetector(self.config)
        ]

    def route(self, window_info: Dict[str, Any]) -> Optional[ActivityState]:
        if not window_info:
            return None
            
        for detector in self.detectors:
            try:
                activity = detector.detect(window_info)
                if activity:
                    return activity
            except Exception as e:
                self.logger.error(f"Detector {detector.__class__.__name__} failed: {e}", exc_info=True)
                
        # Default fallback
        app_name = window_info.get('app_name', 'Unknown App')
        title = window_info.get('title', '')
        return ActivityState(
            type="application",
            details=f"Using {app_name}",
            state=title[:100],
            large_text=app_name,
            large_image=self.config.get(f'images.apps.{app_name.lower()}', 'app')
        )
