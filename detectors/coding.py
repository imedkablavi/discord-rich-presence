"""
Coding activity detection for various editors
"""

import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from config import Config
from .git_helper import GitHelper


class CodingDetector:
    """Detects code editor activity"""
    
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
        'emacs': 'Emacs',
        'sublime': 'Sublime Text',
        'sublime_text': 'Sublime Text',
        'subl': 'Sublime Text',
        'atom': 'Atom',
        'notepad++': 'Notepad++',
        'notepadplusplus': 'Notepad++',
        'devenv': 'Visual Studio',
        'msbuild': 'Visual Studio',
        'gedit': 'gedit',
        'kate': 'Kate',
        'nano': 'Nano',
        'eclipse': 'Eclipse',
        'netbeans': 'NetBeans',
        'androidstudio': 'Android Studio',
        'studio': 'Android Studio',
        'xcode': 'Xcode',
        'qtcreator': 'Qt Creator',
        'rstudio': 'RStudio',
        'spyder': 'Spyder',
        'jupyter': 'Jupyter',
        'matlab': 'MATLAB',
        'octave': 'Octave',
        'trae': 'Trae',
        'trae-ide': 'Trae',
    }
    
    LANGUAGE_EXTENSIONS = {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'jsx': 'javascript',
        'tsx': 'typescript',
        'java': 'java',
        'cpp': 'cpp',
        'cc': 'cpp',
        'cxx': 'cpp',
        'c': 'c',
        'h': 'c',
        'hpp': 'cpp',
        'cs': 'csharp',
        'go': 'go',
        'rs': 'rust',
        'php': 'php',
        'rb': 'ruby',
        'swift': 'swift',
        'kt': 'kotlin',
        'dart': 'dart',
        'html': 'html',
        'css': 'css',
        'scss': 'css',
        'sass': 'css',
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml',
        'md': 'markdown',
        'sql': 'sql',
        'sh': 'shell',
        'bash': 'shell',
        'zsh': 'shell',
        'r': 'r',
        'lua': 'lua',
        'pl': 'perl',
        'pm': 'perl',
        'vim': 'vim',
        'asm': 'assembly',
        's': 'assembly',
        'f90': 'fortran',
        'f95': 'fortran',
        'ml': 'ocaml',
        'hs': 'haskell',
        'scala': 'scala',
        'clj': 'clojure',
        'ex': 'elixir',
        'exs': 'elixir',
        'erl': 'erlang',
        'nim': 'nim',
        'zig': 'zig',
        'v': 'vlang',
        'jl': 'julia',
        'cr': 'crystal',
        'vue': 'vue',
        'svelte': 'svelte',
        'xml': 'xml',
        'svg': 'svg',
        'toml': 'toml',
        'ini': 'ini',
        'conf': 'config',
        'env': 'env',
        'ps1': 'powershell',
        'bat': 'batch',
        'cmd': 'batch',
        'rst': 'restructuredtext',
        'tex': 'latex',
        'adoc': 'asciidoc',
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.git_helper = GitHelper()
    
    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect if window is a code editor and extract activity"""
        if not window_info:
            return None
        
        if not self.config.get('rules.enabled_detectors.coding', True):
            return None
        
        app_name = window_info.get('app_name', '').lower()
        title = window_info.get('title', '')
        
        # Check if it's a code editor
        editor_name = None
        editor_key = None
        for key, name in self.EDITORS.items():
            if key in app_name:
                editor_name = name
                editor_key = key
                break
        
        if not editor_name:
            return None
        
        # Parse title based on editor type
        if editor_key in ['code', 'code-oss', 'codium']:
            return self._parse_vscode_title(title, editor_name)
        elif editor_key in ['pycharm', 'idea', 'webstorm', 'phpstorm', 'goland', 'rider', 'clion', 'rubymine']:
            return self._parse_jetbrains_title(title, editor_name)
        elif editor_key in ['nvim', 'vim']:
            return self._parse_vim_title(title, editor_name, window_info)
        else:
            return self._parse_generic_editor(title, editor_name)
    
    def _parse_vscode_title(self, title: str, editor_name: str) -> Dict[str, Any]:
        """
        Parse VS Code window title
        Format: "filename - workspace - Visual Studio Code"
        or: "● filename - workspace - Visual Studio Code" (unsaved)
        """
        filename = ''
        project = ''
        language = ''
        
        # Remove unsaved indicator
        title = title.replace('●', '').strip()
        
        # Split by separator
        parts = re.split(r'\s*[-—–]\s*', title)
        
        if len(parts) >= 3:
            # Format: filename - workspace - editor
            filename = parts[0].strip()
            project = parts[1].strip()
        elif len(parts) == 2:
            # Format: filename - editor
            filename = parts[0].strip()
        elif len(parts) == 1:
            filename = parts[0].strip()
        
        # Extract language from filename extension
        if filename:
            language = self._get_language_from_filename(filename)
        
        # Try to get Git project name and branch
        if project:
            git_info = self._get_git_info_from_project(project)
            if git_info:
                project = git_info
        
        return {
            'type': 'coding',
            'editor': editor_name,
            'filename': filename,
            'language': language,
            'project': project
        }
    
    def _parse_jetbrains_title(self, title: str, editor_name: str) -> Dict[str, Any]:
        """
        Parse JetBrains IDE window title
        Format: "filename - [project] - EditorName"
        """
        filename = ''
        project = ''
        language = ''
        
        # Split by separator
        parts = re.split(r'\s*[-—–]\s*', title)
        
        if len(parts) >= 2:
            filename = parts[0].strip()
            
            # Project name is often in brackets
            if len(parts) > 1:
                project_part = parts[1].strip()
                # Remove brackets if present
                project = re.sub(r'[\[\]]', '', project_part)
        
        # Extract language from filename
        if filename:
            language = self._get_language_from_filename(filename)
        
        return {
            'type': 'coding',
            'editor': editor_name,
            'filename': filename,
            'language': language,
            'project': project
        }
    
    def _parse_vim_title(self, title: str, editor_name: str, window_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Vim/Neovim title
        Often just shows filename or path
        """
        filename = title.strip()
        language = ''
        project = ''
        
        # Extract just the filename if it's a path
        if '/' in filename:
            filename = Path(filename).name
        
        # Extract language
        if filename:
            language = self._get_language_from_filename(filename)
        
        return {
            'type': 'coding',
            'editor': editor_name,
            'filename': filename,
            'language': language,
            'project': project
        }
    
    def _parse_generic_editor(self, title: str, editor_name: str) -> Dict[str, Any]:
        """Parse generic editor title"""
        filename = title.strip()
        language = ''
        
        # Try to extract filename
        parts = re.split(r'\s*[-—–]\s*', title)
        if parts:
            filename = parts[0].strip()
        
        if filename:
            language = self._get_language_from_filename(filename)
        
        return {
            'type': 'coding',
            'editor': editor_name,
            'filename': filename,
            'language': language,
            'project': ''
        }
    
    def _get_language_from_filename(self, filename: str) -> str:
        """Extract programming language from filename extension"""
        if not filename or '.' not in filename:
            return ''
        
        ext = filename.rsplit('.', 1)[-1].lower()
        return self.LANGUAGE_EXTENSIONS.get(ext, '')
    
    def _get_git_info_from_project(self, project_path: str) -> Optional[str]:
        """
        Try to get Git repository name and branch with status
        Returns formatted string like "repo-name (branch) [↑2 *3]"
        """
        git_info = self.git_helper.get_repo_info(project_path)
        if git_info:
            return self.git_helper.format_git_status(git_info)
        return None
