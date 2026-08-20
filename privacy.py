"""Privacy and redaction layer for sensitive information."""

import logging
import re
import shlex
from pathlib import Path
from typing import Dict, Any, List

from config import Config


class PrivacyRedactor:
    """Apply the documented off/balanced/strict privacy contracts."""

    SENSITIVE_ARG_MARKERS = (
        'password', 'passwd', 'token', 'secret', 'api_key', 'api-key',
        'apikey', 'auth', 'authorization', 'access_key', 'access-key',
        'private_key', 'private-key',
    )

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.redaction_patterns: List[re.Pattern] = []
        self.hide_home_paths = True
        self.reload()

    def reload(self):
        self.redaction_patterns = self._compile_redaction_patterns()
        self.hide_home_paths = bool(self.config.get('privacy.hide_home_paths', True))

    def _compile_redaction_patterns(self) -> List[re.Pattern]:
        patterns = []
        for redaction in self.config.get('privacy.redactions', []) or []:
            if not isinstance(redaction, dict) or 'regex' not in redaction:
                continue
            try:
                patterns.append(re.compile(str(redaction['regex'])))
            except re.error as e:
                self.logger.warning("Invalid privacy regex %r: %s", redaction.get('regex'), e)
        return patterns

    def redact_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        mode = self.config.get('privacy.mode', 'balanced')
        if mode == 'off':
            return activity.copy()
        if mode == 'strict':
            return self._apply_strict_mode(activity)
        return self._apply_balanced_mode(activity)

    def _apply_balanced_mode(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        result = activity.copy()
        activity_type = result.get('type')

        if activity_type == 'terminal':
            if 'command' in result:
                result['command'] = self._redact_command_balanced(str(result.get('command', '')))
            if 'directory' in result:
                result['directory'] = self._shorten_path(str(result.get('directory', '') or ''))
        elif activity_type == 'coding':
            if 'filename' in result:
                result['filename'] = self._basename(str(result.get('filename', '')))
            if 'project' in result:
                result['project'] = self._shorten_path(str(result.get('project', '') or ''))
        elif activity_type == 'browser':
            raw_title = str(result.get('page_title', '') or '')
            safe_title = self._redact_sensitive_patterns(raw_title)
            result['page_title'] = safe_title
            if safe_title != raw_title:
                result['url'] = None

        for key, value in list(result.items()):
            if isinstance(value, str):
                result[key] = self._redact_sensitive_patterns(value)
        return result

    def _apply_strict_mode(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        activity_type = activity.get('type')
        if activity_type == 'terminal':
            return {
                'type': 'terminal', 'terminal_name': 'Terminal', 'command': '',
                'shell': 'Terminal', 'directory': '', 'has_command': False
            }
        if activity_type == 'coding':
            return {
                'type': 'coding', 'editor': 'Code Editor', 'filename': 'Coding',
                'language': '', 'project': ''
            }
        if activity_type == 'browser':
            return {
                'type': 'browser', 'browser_name': 'Browser',
                'is_private': bool(activity.get('is_private')), 'page_title': 'Browsing',
                'service': '', 'url': None
            }
        if activity_type == 'media':
            return {
                'type': 'media', 'player': 'Media Player', 'title': 'Media playback',
                'is_playing': bool(activity.get('is_playing')), 'position': 0, 'duration': 0
            }
        if activity_type == 'gaming':
            return {
                'type': 'gaming', 'game_name': 'Game', 'launcher': 'Gaming', 'is_game': True
            }
        return {'type': 'application', 'app_name': 'Application', 'window_title': ''}

    @staticmethod
    def _split_command(command: str) -> List[str]:
        try:
            # posix=False preserves quoted Windows/PowerShell-looking tokens while
            # still keeping a quoted multi-word value as one token.
            return shlex.split(command, posix=False)
        except ValueError:
            # Never fail activity processing because a shell line contains an
            # unmatched quote; the conservative whitespace fallback still lets
            # the pattern redactor run.
            return command.split()

    def _redact_command_balanced(self, command: str) -> str:
        if not command:
            return command
        parts = self._split_command(command)
        if not parts:
            return command

        redacted = [parts[0]]
        redact_next = False
        for part in parts[1:]:
            if redact_next:
                redacted.append('[REDACTED]')
                redact_next = False
                continue

            lower = part.lower()
            normalized = lower.lstrip('-/').replace('.', '_')
            sensitive = any(marker in normalized for marker in self.SENSITIVE_ARG_MARKERS)
            if sensitive:
                if '=' in part or (':' in part and not part.startswith(('http://', 'https://'))):
                    name = re.split(r'[=:]', part, maxsplit=1)[0]
                    redacted.append(f'{name}=[REDACTED]')
                else:
                    redacted.append(part if part.startswith('-') else '[REDACTED]')
                    redact_next = True
                continue

            if self._looks_like_path(part):
                redacted.append(self._basename(part))
            elif len(part) > 32 and '=' not in part:
                redacted.append('[...]')
            else:
                redacted.append(self._redact_sensitive_patterns(part))
        return ' '.join(redacted)

    def _redact_sensitive_patterns(self, text: str) -> str:
        if not text:
            return text
        redacted = text
        for pattern in self.redaction_patterns:
            redacted = pattern.sub('[REDACTED]', redacted)
        if self.hide_home_paths:
            home = str(Path.home())
            redacted = redacted.replace(home, '~')
            redacted = redacted.replace(home.replace('/', '\\'), '~')
        return re.sub(r'\b[A-Za-z0-9_-]{40,}\b', '[TOKEN]', redacted)

    def _shorten_path(self, path: str) -> str:
        if not path:
            return path
        path = self._redact_sensitive_patterns(path)
        if len(path) < 20 and not self._looks_like_path(path):
            return path
        return self._basename(path) or path

    @staticmethod
    def _basename(value: str) -> str:
        if not value:
            return value
        normalized = value.rstrip('/\\')
        return re.split(r'[/\\]', normalized)[-1]

    @staticmethod
    def _looks_like_path(value: str) -> bool:
        return (
            value.startswith(('/', '~/', '.\\', '..\\'))
            or '\\' in value
            or bool(re.match(r'^[A-Za-z]:[/\\]', value))
        )
