"""Coding activity detection for common editors and IDEs."""

import re
import logging
from typing import Optional, Dict, Any

from config import Config
from .git_helper import GitHelper


class CodingDetector:
    """Detect code-editor activity from foreground-window metadata."""

    EDITORS = {
        'code-oss': 'VS Code OSS',
        'codium': 'VSCodium',
        'code': 'VS Code',
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
        'sublime_text': 'Sublime Text',
        'sublime': 'Sublime Text',
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
        'trae-ide': 'Trae',
        'trae': 'Trae',
    }

    LANGUAGE_EXTENSIONS = {
        'py': 'python', 'js': 'javascript', 'ts': 'typescript',
        'jsx': 'javascript', 'tsx': 'typescript', 'java': 'java',
        'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp', 'c': 'c', 'h': 'c',
        'hpp': 'cpp', 'cs': 'csharp', 'go': 'go', 'rs': 'rust',
        'php': 'php', 'rb': 'ruby', 'swift': 'swift', 'kt': 'kotlin',
        'dart': 'dart', 'html': 'html', 'css': 'css', 'scss': 'css',
        'sass': 'css', 'json': 'json', 'yaml': 'yaml', 'yml': 'yaml',
        'md': 'markdown', 'sql': 'sql', 'sh': 'shell', 'bash': 'shell',
        'zsh': 'shell', 'r': 'r', 'lua': 'lua', 'pl': 'perl', 'pm': 'perl',
        'vim': 'vim', 'asm': 'assembly', 's': 'assembly', 'f90': 'fortran',
        'f95': 'fortran', 'ml': 'ocaml', 'hs': 'haskell', 'scala': 'scala',
        'clj': 'clojure', 'ex': 'elixir', 'exs': 'elixir', 'erl': 'erlang',
        'nim': 'nim', 'zig': 'zig', 'v': 'vlang', 'jl': 'julia',
        'cr': 'crystal', 'vue': 'vue', 'svelte': 'svelte', 'xml': 'xml',
        'svg': 'svg', 'toml': 'toml', 'ini': 'ini', 'conf': 'config',
        'env': 'env', 'ps1': 'powershell', 'bat': 'batch', 'cmd': 'batch',
        'rst': 'restructuredtext', 'tex': 'latex', 'adoc': 'asciidoc',
    }

    # Window-title separators are normally surrounded by whitespace. Requiring
    # whitespace prevents names such as "my-component.tsx" from being split.
    TITLE_SEPARATOR = re.compile(r'\s+[-—–]\s+')

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.git_helper = GitHelper()

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not window_info or not self.config.get('rules.enabled_detectors.coding', True):
            return None

        app_name = str(window_info.get('app_name', '')).lower()
        title = str(window_info.get('title', ''))
        editor_name = None
        editor_key = None
        for key, name in self.EDITORS.items():
            if key in app_name:
                editor_name = name
                editor_key = key
                break
        if not editor_name:
            return None

        if editor_key in {'code', 'code-oss', 'codium'}:
            return self._parse_vscode_title(title, editor_name)
        if editor_key in {'pycharm', 'idea', 'webstorm', 'phpstorm', 'goland', 'rider', 'clion', 'rubymine'}:
            return self._parse_jetbrains_title(title, editor_name)
        if editor_key in {'nvim', 'vim'}:
            return self._parse_vim_title(title, editor_name)
        return self._parse_generic_editor(title, editor_name)

    @classmethod
    def _split_title(cls, title: str) -> list[str]:
        return [part.strip() for part in cls.TITLE_SEPARATOR.split(title.strip()) if part.strip()]

    def _parse_vscode_title(self, title: str, editor_name: str) -> Dict[str, Any]:
        title = title.replace('●', '', 1).strip()
        parts = self._split_title(title)

        # VS Code generally ends with an editor suffix. Remove known suffixes so
        # the remaining components represent filename + workspace.
        if parts and (
            parts[-1].lower().startswith('visual studio code')
            or parts[-1].lower() in {'code', 'vscodium', 'code - oss'}
        ):
            parts.pop()

        filename = parts[0] if parts else ''
        project = ' - '.join(parts[1:]) if len(parts) > 1 else ''
        language = self._get_language_from_filename(filename)

        if project:
            git_info = self._get_git_info_from_project(project)
            if git_info:
                project = git_info

        return {
            'type': 'coding', 'editor': editor_name, 'filename': filename,
            'language': language, 'project': project
        }

    def _parse_jetbrains_title(self, title: str, editor_name: str) -> Dict[str, Any]:
        parts = self._split_title(title)
        if parts and editor_name.lower() in parts[-1].lower():
            parts.pop()

        filename = parts[0] if parts else ''
        project = re.sub(r'^\[|\]$', '', ' - '.join(parts[1:])).strip() if len(parts) > 1 else ''
        return {
            'type': 'coding', 'editor': editor_name, 'filename': filename,
            'language': self._get_language_from_filename(filename), 'project': project
        }

    def _parse_vim_title(self, title: str, editor_name: str) -> Dict[str, Any]:
        filename = self._basename(title.strip())
        return {
            'type': 'coding', 'editor': editor_name, 'filename': filename,
            'language': self._get_language_from_filename(filename), 'project': ''
        }

    def _parse_generic_editor(self, title: str, editor_name: str) -> Dict[str, Any]:
        parts = self._split_title(title)
        filename = parts[0] if parts else title.strip()
        return {
            'type': 'coding', 'editor': editor_name, 'filename': filename,
            'language': self._get_language_from_filename(filename), 'project': ''
        }

    @staticmethod
    def _basename(value: str) -> str:
        normalized = value.rstrip('/\\')
        return re.split(r'[/\\]', normalized)[-1] if normalized else ''

    def _get_language_from_filename(self, filename: str) -> str:
        if not filename or '.' not in filename:
            return ''
        ext = filename.rsplit('.', 1)[-1].lower()
        return self.LANGUAGE_EXTENSIONS.get(ext, '')

    def _get_git_info_from_project(self, project_path: str) -> Optional[str]:
        # Git enrichment only applies when the editor title exposes an actual
        # filesystem path. Workspace display names are intentionally left alone.
        git_info = self.git_helper.get_repo_info(project_path)
        if git_info:
            return self.git_helper.format_git_status(git_info)
        return None
