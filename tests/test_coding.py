from config import Config
from detectors.coding import CodingDetector


def _detector(tmp_path):
    return CodingDetector(Config(tmp_path / 'config.yaml'))


def test_vscode_preserves_hyphenated_filename_and_workspace(tmp_path):
    detector = _detector(tmp_path)
    activity = detector.detect({
        'app_name': 'Code',
        'title': 'my-component.tsx - project-name - Visual Studio Code',
    })

    assert activity is not None
    assert activity['filename'] == 'my-component.tsx'
    assert activity['project'] == 'project-name'
    assert activity['language'] == 'typescript'


def test_vscode_unsaved_indicator_is_removed(tmp_path):
    detector = _detector(tmp_path)
    activity = detector.detect({
        'app_name': 'Code',
        'title': '● api-client.py - backend-service - Visual Studio Code',
    })

    assert activity is not None
    assert activity['filename'] == 'api-client.py'
    assert activity['project'] == 'backend-service'
    assert activity['language'] == 'python'


def test_vim_windows_path_returns_basename(tmp_path):
    detector = _detector(tmp_path)
    activity = detector.detect({
        'app_name': 'nvim',
        'title': r'C:\Users\alice\repo\src\main.rs',
    })

    assert activity is not None
    assert activity['filename'] == 'main.rs'
    assert activity['language'] == 'rust'


def test_generic_editor_does_not_split_hyphenated_filename(tmp_path):
    detector = _detector(tmp_path)
    activity = detector.detect({
        'app_name': 'notepad++',
        'title': 'release-notes.md - Notepad++',
    })

    assert activity is not None
    assert activity['filename'] == 'release-notes.md'
    assert activity['language'] == 'markdown'
