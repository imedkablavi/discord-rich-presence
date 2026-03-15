import os
import re
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from config import Config
from core.activity_model import ActivityState
from .git_helper import GitHelper

class CodingDetector:
    EDITORS = {
        'code': 'VS Code',
        'code-oss': 'VS Code OSS',
        'codium': 'VSCodium',
        'pycharm': 'PyCharm',
        'idea': 'IntelliJ IDEA',
        'webstorm': 'WebStorm',
        'phpstorm': 'PhpStorm',
        'goland': 'GoLand',
        'rider': 'Rider',
        'clion': 'CLion',
        'rubymine': 'RubyMine',
        'nvim': 'Neovim',
        'vim': 'Vim',
        'sublime': 'Sublime Text',
        'sublime_text': 'Sublime Text',
        'notepad++': 'Notepad++',
        'nano': 'Nano',
        'trae': 'Trae',
    }

    LANGUAGE_EXTENSIONS = {
        'py': ('python', 'Python'),
        'js': ('javascript', 'JavaScript'),
        'ts': ('typescript', 'TypeScript'),
        'java': ('java', 'Java'),
        'cpp': ('cpp', 'C++'),
        'c': ('c', 'C'),
        'cs': ('csharp', 'C#'),
        'go': ('go', 'Go'),
        'rs': ('rust', 'Rust'),
        'php': ('php', 'PHP'),
        'rb': ('ruby', 'Ruby'),
        'html': ('html', 'HTML'),
        'css': ('css', 'CSS'),
        'json': ('json', 'JSON'),
        'yaml': ('yaml', 'YAML'),
        'yml': ('yaml', 'YAML'),
        'md': ('markdown', 'Markdown'),
        'sh': ('shell', 'Shell'),
        'bash': ('shell', 'Bash'),
    }

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.git_helper = GitHelper()
        self._start_times = {}

    def get_start_time(self, project: str) -> int:
        now = int(time.time())
        if project not in self._start_times:
            self._start_times[project] = now
            if len(self._start_times) > 10:
                oldest = min(self._start_times, key=self._start_times.get)
                del self._start_times[oldest]
        return self._start_times[project]

    def detect(self, window_info: Dict[str, Any]) -> Optional[ActivityState]:
        if not self.config.get('rules.enabled_detectors.coding', True):
            return None
            
        app_name = window_info.get('app_name', '').lower()
        title = window_info.get('title', '')
        cwd = window_info.get('cwd')
        
        editor_name = None
        for key, name in self.EDITORS.items():
            if key in app_name:
                editor_name = name
                break
                
        if not editor_name:
            if 'nvim' in title.lower() or 'vim' in title.lower():
                editor_name = 'Neovim' if 'nvim' in title.lower() else 'Vim'
            else:
                return None

        # Determine filename and project
        filename = ""
        project = ""
        
        # Safe multi-editor parsing block
        title = title.replace('●', '').strip()
        parts = re.split(r'\s*[-—–]\s*', title)
        
        if len(parts) >= 2:
            filename = parts[0].strip()
            # Jetbrains style `filename - [project] - IDE`
            if '[' in parts[1] and ']' in parts[1]:
                project = re.sub(r'[\[\]]', '', parts[1]).strip()
            else:
                project = parts[1].strip()
        elif len(parts) == 1:
            filename = parts[0].strip()
            
        # Handle full paths
        if '/' in filename or '\\' in filename:
            filename = Path(filename).name

        lang_key, lang_name = "", ""
        if '.' in filename:
            ext = filename.rsplit('.', 1)[-1].lower()
            if ext in self.LANGUAGE_EXTENSIONS:
                lang_key, lang_name = self.LANGUAGE_EXTENSIONS[ext]

        # Git Status leveraging CWD
        if cwd and Path(cwd).exists():
            git_info = self.git_helper.get_repo_info(cwd)
            if git_info:
                project = f"{git_info['repo_name']} ({git_info['branch']})"
                if git_info['is_dirty']:
                    project += " *"
        
        start_time = self.get_start_time(project if project else filename)

        large_image = self.config.get(f"images.apps.{app_name}", 'code')
        if editor_name == "VS Code":
            large_image = "vscode"
        small_image = self.config.get(f"images.langs.{lang_key}") if lang_key else None

        details = f"Editing {filename}" if filename else "Coding"
        state = f"{editor_name} · {project}" if project else editor_name
        
        return ActivityState(
            type="coding",
            details=details,
            state=state,
            large_image=large_image,
            large_text=editor_name,
            small_image=small_image,
            small_text=lang_name,
            start_time=start_time
        )
