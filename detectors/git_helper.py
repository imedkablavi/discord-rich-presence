"""Lightweight Git repository enrichment for coding activity."""

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any


class GitHelper:
    """Read repository status with a small, bounded number of Git subprocesses."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _run(self, path: Path, *args: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ['git', *args],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as e:
            self.logger.debug('Git command failed: %s', e)
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def get_repo_info(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            path_obj = Path(path).expanduser()
            if not path_obj.exists():
                return None

            root_text = self._run(path_obj, 'rev-parse', '--show-toplevel')
            if not root_text:
                return None
            repo_root = Path(root_text)

            status = self._run(repo_root, 'status', '--porcelain=v1', '--branch')
            if status is None:
                return None
            lines = status.splitlines()
            header = lines[0] if lines and lines[0].startswith('## ') else ''
            changes = lines[1:] if header else lines

            branch = 'unknown'
            ahead = 0
            behind = 0
            if header:
                branch_part = header[3:].split('...', 1)[0].strip()
                if branch_part and not branch_part.startswith('HEAD '):
                    branch = branch_part
                ahead_match = re.search(r'\bahead (\d+)\b', header)
                behind_match = re.search(r'\bbehind (\d+)\b', header)
                if ahead_match:
                    ahead = int(ahead_match.group(1))
                if behind_match:
                    behind = int(behind_match.group(1))

            uncommitted = sum(1 for line in changes if line.strip())
            return {
                'repo_name': repo_root.name,
                'repo_path': str(repo_root),
                'branch': branch,
                'ahead': ahead,
                'behind': behind,
                'uncommitted': uncommitted,
                'is_dirty': uncommitted > 0,
            }
        except (OSError, ValueError) as e:
            self.logger.debug('Failed to get Git info: %s', e)
            return None

    def format_git_status(self, info: Dict[str, Any]) -> str:
        parts = [str(info.get('repo_name', 'repository'))]
        branch = str(info.get('branch', '') or '')
        if branch and branch != 'unknown':
            parts.append(f'({branch})')

        status_parts = []
        if int(info.get('ahead', 0) or 0) > 0:
            status_parts.append(f"↑{info['ahead']}")
        if int(info.get('behind', 0) or 0) > 0:
            status_parts.append(f"↓{info['behind']}")
        if int(info.get('uncommitted', 0) or 0) > 0:
            status_parts.append(f"*{info['uncommitted']}")
        if status_parts:
            parts.append('[' + ' '.join(status_parts) + ']')
        return ' '.join(parts)
