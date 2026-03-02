"""
Privacy and redaction layer for sensitive information
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List
from config import Config


class PrivacyRedactor:
    """Handles privacy modes and redaction of sensitive information"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.mode = config.get('privacy.mode', 'balanced')
        self.redaction_patterns = self._compile_redaction_patterns()
        self.hide_home_paths = config.get('privacy.hide_home_paths', True)
    
    def _compile_redaction_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for redaction"""
        patterns = []
        redactions = self.config.get('privacy.redactions', [])
        
        for redaction in redactions:
            if 'regex' in redaction:
                try:
                    pattern = re.compile(redaction['regex'])
                    patterns.append(pattern)
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern: {redaction['regex']}: {e}")
        
        return patterns
    
    def redact_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Apply privacy redaction to activity data"""
        mode = self.config.get('privacy.mode', 'balanced')
        activity_type = activity.get('type', 'application')
        
        if mode == 'off':
            # No redaction, but still apply basic filtering
            return self._apply_basic_filtering(activity)
        elif mode == 'strict':
            return self._apply_strict_mode(activity)
        else:  # balanced
            return self._apply_balanced_mode(activity)
    
    def _apply_basic_filtering(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Apply basic sensitive data filtering even in 'off' mode"""
        activity = activity.copy()
        
        # Redact sensitive patterns in all text fields
        for key, value in activity.items():
            if isinstance(value, str):
                activity[key] = self._redact_sensitive_patterns(value)
        
        return activity
    
    def _apply_balanced_mode(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Apply balanced privacy mode - hide full paths, show project names"""
        activity = activity.copy()
        activity_type = activity.get('type')
        
        if activity_type == 'terminal':
            # Hide full paths in commands
            if 'command' in activity:
                activity['command'] = self._redact_command_balanced(activity['command'])
            
            # Shorten directory paths
            if 'directory' in activity:
                activity['directory'] = self._shorten_path(activity['directory'])
        
        elif activity_type == 'coding':
            # Keep filename but remove path
            if 'filename' in activity and '/' in activity['filename']:
                activity['filename'] = Path(activity['filename']).name
            
            # Keep project name but remove full path
            if 'project' in activity:
                activity['project'] = self._shorten_path(activity['project'])
        
        elif activity_type == 'browser':
            # Keep page title but redact sensitive info
            if 'page_title' in activity:
                activity['page_title'] = self._redact_sensitive_patterns(activity['page_title'])
        
        # Apply sensitive pattern redaction to all fields
        for key, value in activity.items():
            if isinstance(value, str):
                activity[key] = self._redact_sensitive_patterns(value)
        
        return activity
    
    def _apply_strict_mode(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Apply strict privacy mode - show only generic descriptions"""
        activity_type = activity.get('type')
        
        if activity_type == 'terminal':
            return {
                'type': 'terminal',
                'terminal_name': activity.get('terminal_name', 'Terminal'),
                'command': '',
                'shell': activity.get('shell', 'Terminal'),
                'directory': '',
                'has_command': False
            }
        
        elif activity_type == 'coding':
            language = activity.get('language', '')
            editor = activity.get('editor', 'Code Editor')
            
            # Generic description
            if language:
                filename = f"Coding in {language.title()}"
            else:
                filename = "Coding"
            
            return {
                'type': 'coding',
                'editor': editor,
                'filename': filename,
                'language': language,
                'project': ''
            }
        
        elif activity_type == 'browser':
            if activity.get('is_private'):
                return activity  # Already says "Private browsing"
            
            return {
                'type': 'browser',
                'browser_name': activity.get('browser_name', 'Browser'),
                'is_private': False,
                'page_title': 'Browsing'
            }
        
        elif activity_type == 'media':
            # For media, keep the title but redact sensitive info
            return {
                'type': 'media',
                'player': activity.get('player', 'Media Player'),
                'title': self._redact_sensitive_patterns(activity.get('title', 'Media')),
                'is_playing': activity.get('is_playing', False),
                'position': activity.get('position', 0),
                'duration': activity.get('duration', 0)
            }
        
        else:  # application
            return {
                'type': 'application',
                'app_name': activity.get('app_name', 'Application'),
                'window_title': ''
            }
    
    def _redact_command_balanced(self, command: str) -> str:
        """Redact sensitive parts of command while keeping it readable"""
        if not command:
            return command
        
        # Split command into parts
        parts = command.split()
        if not parts:
            return command
        
        # Keep the base command (first part)
        base_cmd = parts[0]
        
        # Redact arguments that look like paths
        redacted_parts = [base_cmd]
        for part in parts[1:]:
            # Hide full paths
            if part.startswith('/') or part.startswith('~/'):
                # Keep just the filename
                redacted_parts.append(Path(part).name)
            # Hide long strings (potential tokens/hashes)
            elif len(part) > 32 and '=' not in part:
                redacted_parts.append('[...]')
            # Hide arguments with sensitive keywords
            elif any(kw in part.lower() for kw in ['password', 'token', 'secret', 'key', 'api']):
                redacted_parts.append('[REDACTED]')
            else:
                redacted_parts.append(part)
        
        return ' '.join(redacted_parts)
    
    def _redact_sensitive_patterns(self, text: str) -> str:
        """Redact text matching sensitive patterns"""
        if not text:
            return text
        
        redacted = text
        
        # Apply custom regex patterns
        for pattern in self.redaction_patterns:
            redacted = pattern.sub('[REDACTED]', redacted)
        
        # Hide home directory paths if enabled
        if self.hide_home_paths:
            home = str(Path.home())
            redacted = redacted.replace(home, '~')
        
        # Hide very long continuous strings (potential tokens)
        redacted = re.sub(r'\b[A-Za-z0-9_-]{40,}\b', '[TOKEN]', redacted)
        
        return redacted
    
    def _shorten_path(self, path: str) -> str:
        """Shorten path to just the last component or project name"""
        if not path:
            return path
        
        # Replace home directory
        if self.hide_home_paths:
            home = str(Path.home())
            path = path.replace(home, '~')
        
        # If it's a short path already, keep it
        if len(path) < 20:
            return path
        
        # Otherwise, keep just the last component
        path_obj = Path(path)
        return path_obj.name or str(path_obj)
    
    def _is_sensitive_branch_name(self, branch: str) -> bool:
        """Check if Git branch name contains sensitive keywords"""
        if not branch:
            return False
        
        sensitive_keywords = [
            'password', 'token', 'secret', 'key', 'api',
            'private', 'confidential', 'internal'
        ]
        
        branch_lower = branch.lower()
        return any(kw in branch_lower for kw in sensitive_keywords)
