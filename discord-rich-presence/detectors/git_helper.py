"""
Git integration helper for better repository information
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any


class GitHelper:
    """Helper class for Git repository information"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_repo_info(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive Git repository information
        Returns: {
            'repo_name': str,
            'branch': str,
            'ahead': int,
            'behind': int,
            'uncommitted': int,
            'is_dirty': bool
        }
        """
        try:
            path_obj = Path(path).expanduser()
            if not path_obj.exists():
                return None
            
            # Check if it's a Git repository
            if not self._is_git_repo(path_obj):
                return None
            
            info = {}
            
            # Get repository root and name
            repo_root = self._get_repo_root(path_obj)
            if repo_root:
                info['repo_name'] = repo_root.name
                info['repo_path'] = str(repo_root)
            else:
                return None
            
            # Get current branch
            branch = self._get_current_branch(path_obj)
            info['branch'] = branch or 'unknown'
            
            # Get ahead/behind commits
            ahead, behind = self._get_ahead_behind(path_obj)
            info['ahead'] = ahead
            info['behind'] = behind
            
            # Get uncommitted changes
            uncommitted = self._get_uncommitted_count(path_obj)
            info['uncommitted'] = uncommitted
            info['is_dirty'] = uncommitted > 0
            
            return info
            
        except Exception as e:
            self.logger.debug(f"Failed to get Git info: {e}")
            return None
    
    def _is_git_repo(self, path: Path) -> bool:
        """Check if path is inside a Git repository"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=path,
                capture_output=True,
                timeout=1
            )
            return result.returncode == 0
        except:
            return False
    
    def _get_repo_root(self, path: Path) -> Optional[Path]:
        """Get Git repository root directory"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except:
            pass
        
        return None
    
    def _get_current_branch(self, path: Path) -> Optional[str]:
        """Get current Git branch name"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    def _get_ahead_behind(self, path: Path) -> tuple[int, int]:
        """Get number of commits ahead/behind remote"""
        try:
            # Get upstream branch
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', '@{upstream}'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode != 0:
                return 0, 0
            
            upstream = result.stdout.strip()
            
            # Get ahead/behind counts
            result = subprocess.run(
                ['git', 'rev-list', '--left-right', '--count', f'HEAD...{upstream}'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) == 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
                    return ahead, behind
        except:
            pass
        
        return 0, 0
    
    def _get_uncommitted_count(self, path: Path) -> int:
        """Get number of uncommitted changes"""
        try:
            # Get status in short format
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Filter out empty lines
                return len([line for line in lines if line.strip()])
        except:
            pass
        
        return 0
    
    def format_git_status(self, info: Dict[str, Any]) -> str:
        """Format Git status for display"""
        parts = [info['repo_name']]
        
        # Add branch
        branch = info.get('branch', '')
        if branch and branch != 'unknown':
            parts.append(f"({branch})")
        
        # Add status indicators
        status_parts = []
        
        if info.get('ahead', 0) > 0:
            status_parts.append(f"↑{info['ahead']}")
        
        if info.get('behind', 0) > 0:
            status_parts.append(f"↓{info['behind']}")
        
        if info.get('uncommitted', 0) > 0:
            status_parts.append(f"*{info['uncommitted']}")
        
        if status_parts:
            parts.append('[' + ' '.join(status_parts) + ']')
        
        return ' '.join(parts)
