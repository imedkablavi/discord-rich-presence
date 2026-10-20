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


def test_falls_back_to_legacy_global_cache_when_no_pid_scoped_hooks_exist(tmp_path):
    detector = _detector(tmp_path)
    detector.cmd_file.write_text('legacy-command\n', encoding='utf-8')

    assert detector._get_last_command(99999999) == 'legacy-command'


def test_does_not_leak_global_command_when_other_pid_hook_is_active(tmp_path):
    detector = _detector(tmp_path)
    detector.cmd_file.write_text('terminal-a-secret\n', encoding='utf-8')
    (detector.command_dir / '424242.txt').write_text('terminal-a-secret\n', encoding='utf-8')

    assert detector._get_last_command(99999999) == ''


def test_stale_command_cache_is_not_published_and_is_deleted(tmp_path):
    detector = _detector(tmp_path)
    detector.config.set('rules.terminal_command_ttl_secs', 2)
    pid_file = detector.command_dir / f'{os.getpid()}.txt'
    pid_file.write_text('old-command\n', encoding='utf-8')
    detector.cmd_file.parent.mkdir(parents=True, exist_ok=True)
    detector.cmd_file.write_text('old-global-command\n', encoding='utf-8')
    old = time.time() - 10
    os.utime(pid_file, (old, old))
    os.utime(detector.cmd_file, (old, old))

    assert detector._get_last_command(os.getpid()) == ''
    assert not pid_file.exists()
    assert not detector.cmd_file.exists()


def test_hook_internal_commands_are_filtered(tmp_path):
    detector = _detector(tmp_path)
    pid_file = detector.command_dir / f'{os.getpid()}.txt'
    pid_file.write_text('Write-DrpCommandCache secret\n', encoding='utf-8')

    assert detector._get_last_command(os.getpid()) == ''


def test_default_terminal_command_ttl_is_short_lived(tmp_path):
    detector = _detector(tmp_path)
    assert detector._ttl() == 900



def test_command_cache_read_is_bounded_for_oversized_files(tmp_path):
    detector = _detector(tmp_path)
    oversized = tmp_path / 'oversized-command.txt'
    oversized.write_text('x' * (2 * 1024 * 1024), encoding='utf-8')

    command = detector._read_command(oversized)

    assert command == 'x' * detector._MAX_COMMAND_CHARS
    assert len(command) <= detector._MAX_COMMAND_CHARS



def test_zero_ttl_disables_command_publication_and_deletes_cache(tmp_path):
    detector = _detector(tmp_path)
    detector.config.set('rules.terminal_command_ttl_secs', 0)
    command_file = detector.command_dir / f'{os.getpid()}.txt'
    command_file.write_text('deploy --token secret-value\n', encoding='utf-8')
    detector.cmd_file.write_text('legacy-secret-value\n', encoding='utf-8')

    assert detector._ttl() == 0
    assert detector._get_last_command(os.getpid()) == ''
    assert not command_file.exists()
    assert not detector.cmd_file.exists()


def test_disabled_terminal_detector_clears_fresh_command_cache(tmp_path):
    detector = _detector(tmp_path)
    detector.config.set('rules.enabled_detectors.terminal', False)
    command_file = detector.command_dir / '424242.txt'
    command_file.write_text('example-command\n', encoding='utf-8')
    detector.cmd_file.write_text('legacy-command\n', encoding='utf-8')

    assert detector.detect({'app_name': 'Firefox', 'title': 'news'}) is None
    assert not command_file.exists()
    assert not detector.cmd_file.exists()

def test_stale_command_cache_is_cleaned_when_no_foreground_window_exists(tmp_path):
    detector = _detector(tmp_path)
    detector.config.set('rules.terminal_command_ttl_secs', 2)
    command_file = detector.command_dir / '424242.txt'
    command_file.write_text('private-command\n', encoding='utf-8')
    old = time.time() - 10
    os.utime(command_file, (old, old))

    assert detector.detect({}) is None
    assert not command_file.exists()



def test_clear_command_cache_removes_pid_scoped_and_legacy_files(tmp_path):
    detector = _detector(tmp_path)
    pid_file = detector.command_dir / f'{os.getpid()}.txt'
    pid_file.write_text('private-command\n', encoding='utf-8')
    detector.cmd_file.write_text('legacy-private-command\n', encoding='utf-8')

    detector.clear_command_cache()

    assert not pid_file.exists()
    assert not detector.cmd_file.exists()



def test_terminal_cache_tolerates_small_future_timestamp_skew(tmp_path):
    detector = _detector(tmp_path)
    command_file = detector.command_dir / '424242.txt'
    command_file.write_text('recent-command\n', encoding='utf-8')
    future = time.time() + 2
    os.utime(command_file, (future, future))

    assert detector._is_fresh(command_file) is True
    assert detector._read_command(command_file) == 'recent-command'


def test_terminal_cache_rejects_materially_future_timestamp(tmp_path):
    detector = _detector(tmp_path)
    command_file = detector.command_dir / '424242.txt'
    command_file.write_text('future-command\n', encoding='utf-8')
    future = time.time() + detector._MAX_CACHE_FUTURE_SKEW_SECS + 30
    os.utime(command_file, (future, future))

    assert detector._is_fresh(command_file) is False
