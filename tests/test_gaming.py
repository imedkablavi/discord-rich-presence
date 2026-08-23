from pathlib import Path

from config import Config
from detectors.gaming import GamingDetector


def _detector(tmp_path: Path) -> GamingDetector:
    return GamingDetector(Config(tmp_path / 'config.yaml'))


def test_known_shipping_executable_is_detected_exactly(tmp_path: Path):
    result = _detector(tmp_path).detect({
        'app_name': r'C:\\Games\\Palworld-Win64-Shipping.exe',
        'title': 'Palworld',
    })
    assert result is not None
    assert result['is_game'] is True
    assert result['game_name'] == 'Palworld'


def test_similar_process_name_is_not_a_game(tmp_path: Path):
    result = _detector(tmp_path).detect({
        'app_name': 'my-apex-monitor.exe',
        'title': 'Apex statistics',
    })
    assert result is None


def test_launcher_without_verified_title_suffix_is_not_game(tmp_path: Path):
    result = _detector(tmp_path).detect({
        'app_name': 'steam.exe',
        'title': 'Steam Library',
    })
    assert result is not None
    assert result['is_game'] is False


def test_launcher_title_suffix_can_identify_foreground_game(tmp_path: Path):
    result = _detector(tmp_path).detect({
        'app_name': 'steam.exe',
        'title': 'Factorio - Steam',
    })
    assert result is not None
    assert result['is_game'] is True
    assert result['game_name'] == 'Factorio'
