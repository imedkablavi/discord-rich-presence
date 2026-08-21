from pathlib import Path

from activity_priority import ActivityPriorityEngine
from config import Config


def _candidates():
    return {
        'media': {
            'type': 'media',
            'player': 'Spotify',
            'title': 'Artist - Song',
            'is_playing': True,
        },
        'coding': {
            'type': 'coding',
            'editor': 'VS Code',
            'filename': 'main.py',
        },
        'application': {
            'type': 'application',
            'app_name': 'code',
            'window_title': 'main.py — VS Code',
        },
    }


def test_smart_policy_prefers_foreground_coding_over_background_media(tmp_path: Path):
    engine = ActivityPriorityEngine(Config(tmp_path / 'config.yaml'))
    selected = engine.choose({'app_name': 'code'}, _candidates())
    assert selected is not None
    assert selected['type'] == 'coding'


def test_smart_policy_prefers_media_when_player_is_foreground(tmp_path: Path):
    engine = ActivityPriorityEngine(Config(tmp_path / 'config.yaml'))
    candidates = _candidates()
    selected = engine.choose({'app_name': 'spotify'}, candidates)
    assert selected is candidates['media']


def test_smart_policy_recognizes_browser_backed_foreground_media(tmp_path: Path):
    engine = ActivityPriorityEngine(Config(tmp_path / 'config.yaml'))
    candidates = {
        'media': {'type': 'media', 'player': 'Brave', 'is_playing': True},
        'browser': {'type': 'browser', 'browser_name': 'Brave', 'page_title': 'YouTube'},
    }
    selected = engine.choose({'app_name': 'com.brave.Browser'}, candidates)
    assert selected is candidates['media']


def test_media_first_policy_can_restore_old_behavior(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('rules.activity_priority.policy', 'media_first')
    engine = ActivityPriorityEngine(cfg)
    candidates = _candidates()
    selected = engine.choose({'app_name': 'code'}, candidates)
    assert selected is candidates['media']


def test_custom_policy_respects_user_order(tmp_path: Path):
    cfg = Config(tmp_path / 'config.yaml')
    cfg.set('rules.activity_priority.policy', 'custom')
    cfg.set('rules.activity_priority.custom_order', ['browser', 'coding', 'media'])
    engine = ActivityPriorityEngine(cfg)
    candidates = _candidates()
    candidates['browser'] = {'type': 'browser', 'browser_name': 'Firefox'}
    selected = engine.choose({'app_name': 'code'}, candidates)
    assert selected is candidates['browser']


def test_gaming_wins_in_smart_policy(tmp_path: Path):
    engine = ActivityPriorityEngine(Config(tmp_path / 'config.yaml'))
    candidates = _candidates()
    candidates['gaming'] = {'type': 'gaming', 'game_name': 'Game', 'is_game': True}
    selected = engine.choose({'app_name': 'game'}, candidates)
    assert selected is candidates['gaming']
