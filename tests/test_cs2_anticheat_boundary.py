"""Regression tests that keep the CS2 integration on Valve's read-only GSI path.

These checks are intentionally conservative. Rich Presence should never need to
read/write game memory, inject code, automate input, or weaken CS2/VAC launch
settings. If a future feature genuinely needs one of these techniques it must be
designed and reviewed separately instead of silently expanding the GSI surface.
"""

from pathlib import Path

from config import Config
from cs2_gsi import CS2GSIBridge, render_gsi_config


ROOT = Path(__file__).resolve().parents[1]
CS2_RUNTIME_FILES = (
    ROOT / 'cs2_gsi.py',
    ROOT / 'detectors' / 'gaming.py',
    ROOT / 'main.py',
    ROOT / 'launcher.py',
)

# Techniques that are unnecessary for official Game State Integration and would
# materially change the anti-cheat risk profile of this feature.
FORBIDDEN_RUNTIME_MARKERS = (
    'ReadProcessMemory',
    'WriteProcessMemory',
    'NtReadVirtualMemory',
    'NtWriteVirtualMemory',
    'process_vm_readv',
    'process_vm_writev',
    'VirtualAllocEx',
    'CreateRemoteThread',
    'SetWindowsHookEx',
    'ptrace(',
    'LD_PRELOAD',
    'SendInput',
    'keybd_event',
    'mouse_event',
    '-insecure',
    '-allow_third_party_software',
)

FORBIDDEN_RUNTIME_PACKAGES = {
    'pymem',
    'frida',
    'frida-tools',
    'pyautogui',
    'pynput',
    'keyboard',
    'mouse',
}


def test_cs2_runtime_does_not_cross_process_or_anti_cheat_boundary():
    combined = '\n'.join(path.read_text(encoding='utf-8') for path in CS2_RUNTIME_FILES)
    lowered = combined.lower()
    for marker in FORBIDDEN_RUNTIME_MARKERS:
        assert marker.lower() not in lowered, (
            f'CS2 Rich Presence must stay on Valve GSI; forbidden runtime marker found: {marker}'
        )


def test_runtime_dependencies_do_not_add_memory_or_input_automation_tooling():
    requirements = ROOT / 'requirements.txt'
    packages = set()
    for raw_line in requirements.read_text(encoding='utf-8').splitlines():
        line = raw_line.split('#', 1)[0].strip()
        if not line:
            continue
        name = line
        for separator in ('==', '>=', '<=', '~=', '!=', '>', '<', '['):
            name = name.split(separator, 1)[0]
        packages.add(name.strip().lower().replace('_', '-'))

    assert not (packages & FORBIDDEN_RUNTIME_PACKAGES), (
        'CS2 Rich Presence does not require game-memory or input-automation dependencies'
    )


def test_generated_gsi_stays_loopback_and_minimum_data_only():
    rendered = render_gsi_config(32192, 'A' * 43)
    assert '"uri" "http://127.0.0.1:32192/v1/cs2"' in rendered
    for required in ('provider', 'map', 'round', 'player_id', 'phase_countdowns'):
        assert f'"{required}" "1"' in rendered

    for forbidden in (
        'allplayers',
        'allgrenades',
        'player_state',
        'player_weapons',
        'player_position',
        'player_match_stats',
        'bomb',
    ):
        assert forbidden not in rendered


def test_gsi_listener_is_ipv4_loopback_and_status_never_contains_auth(tmp_path):
    config = Config(tmp_path / 'config.yaml')
    bridge = CS2GSIBridge(config)
    assert bridge.host == '127.0.0.1'
    status_text = repr(bridge.status()).lower()
    assert bridge.token not in status_text
    assert 'token' not in status_text
    assert 'steamid' not in status_text
    assert 'player_name' not in status_text
