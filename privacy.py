import re
import logging
from pathlib import Path
from typing import Dict, Any, List
from config import Config

class PrivacyRedactor:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.mode = config.get('privacy.mode', 'balanced')
        self.hide_home_paths = config.get('privacy.hide_home_paths', True)

    def redact_activity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mode = self.config.get('privacy.mode', 'balanced')
        p = payload.copy()
        
        if mode == 'strict':
            p.pop('buttons', None)
            p.pop('url', None)
            
            # Generalize all text fields
            if 'details' in p and p['details']:
                if 'Coding' in str(p['details']) or 'Editing' in str(p['details']):
                    p['details'] = 'Writing Code'
                elif 'Watching' in str(p['details']):
                    p['details'] = 'Consuming Media'
                else:
                    p['details'] = 'Active'
                    
            if 'state' in p and p['state']:
                # Hide project names, keep just the editor/app
                if '·' in str(p['state']):
                    p['state'] = str(p['state']).split('·')[0].strip()
            return p
            
        if mode == 'balanced':
            # Hide home paths, secrets, etc
            redacted = {}
            for k, v in payload.items():
                if isinstance(v, str):
                    redacted[k] = self._clean_string(v)
                else:
                    redacted[k] = v
            return redacted
            
        # mode == 'off'
        return payload

    def _clean_string(self, text: str) -> str:
        if not text: return text
        
        # Hide home
        if self.hide_home_paths:
            home = str(Path.home())
            text = text.replace(home, '~')
            
        # Basic secrets
        text = re.sub(r'([a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)', '[TOKEN]', text)
        text = re.sub(r'\b[A-Za-z0-9_-]{32,}\b', '[SECRET]', text)
        return text
