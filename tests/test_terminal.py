import os
import time
from pathlib import Path

from config import Config
from detectors.terminal import TerminalDetector


def _detector(tmp_path: Path) -> TerminalDetector:
    detector = TerminalDetector(Config(tmp_path / 'config.yaml'))
    detector.cache_dir = tmp_path / 'cache'
    detector.cmd_file = detector.cache_dir / 'rp_last_cmd'
    detector.command_dir = detector.cache_dir / 'commands'
    detector.command_dir.mkdir(parents=True, exist_ok=True)
    return detector


def test_pid_specific_command_is_preferred_over_global_cache(tmp_path):
    detector = _detector(tmp_path)
    detector.cmd_file.write_text('global-command\n', encoding='utf-8')
    pid_file = detector.command_dir / f'{os.getpid()}.txt'
    pid_file.write_text('focused-command\n', encoding='utf-8')

    assert detector._get_last_command(os.getpid()) == 'focused-command'


def test_falls_back_to_legacy_global_cache_when_no_pid_match(tmp_path):
    detector = _detector(tmp_path)
    detector.cmd_file.write_text('legacy-command\n', encoding='utf-8')

    assert detector._get_last_command(99999999) == 'legacy-command'


def test_stale_command_cache_is_not_published(tmp_path):
    detector = _detector(tmp_path)
    detector.config.set('rules.terminal_command_ttl_secs', 2)
    pid_file = detector.command_dir / f'{os.getpid()}.txt'
    pid_file.write_text('old-command\n', encoding='utf-8')
    old = time.time() - 10
    os.utime(pid_file, (old, old))

    assert detector._get_last_command(os.getpid()) == ''


def test_hook_internal_commands_are_filtered(tmp_path):
    detector = _detector(tmp_path)
    pid_file = detector.command_dir / f'{os.getpid()}.txt'
    pid_file.write_text('Write-DrpCommandCache secret\n', encoding='utf-8')

    assert detector._get_last_command(os.getpid()) == ''
