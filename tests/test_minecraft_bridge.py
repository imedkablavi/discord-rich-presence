import time
from pathlib import Path

from config import Config
from detectors.gaming import GamingDetector
from minecraft_bridge import MinecraftBridge


def _config(tmp_path: Path) -> Config:
    return Config(tmp_path / 'config.yaml')


def test_minecraft_payload_drops_sensitive_extra_fields():
    payload = MinecraftBridge.normalize_payload({
        'mode': 'multiplayer',
        'dimension': 'minecraft:overworld',
        'server_name': 'Example Server',
        'server_ip': '127.0.0.1:25565',
        'username': 'PrivatePlayer',
        'coordinates': [10, 64, -12],
        'world_seed': 123456,
        'chat': 'secret',
    })
    assert payload == {
        'mode': 'Multiplayer',
        'dimension': 'minecraft:overworld',
        'server_name': 'Example Server',
    }


def test_minecraft_bridge_requires_companion_header(tmp_path):
    bridge = MinecraftBridge(_config(tmp_path))
    assert not bridge.ingest(
        {'mode': 'Singleplayer', 'dimension': 'minecraft:overworld'},
        companion_header='something-else',
    )
    assert bridge.latest() is None


def test_minecraft_server_name_is_hidden_by_default(tmp_path):
    bridge = MinecraftBridge(_config(tmp_path))
    assert bridge.ingest(
        {
            'mode': 'Multiplayer',
            'dimension': 'minecraft:the_nether',
            'server_name': 'Private SMP',
        },
        companion_header='minecraft-fabric-1',
    )
    assert bridge.latest() == {
        'mode': 'Multiplayer',
        'dimension': 'minecraft:the_nether',
    }


def test_minecraft_server_name_requires_desktop_opt_in(tmp_path):
    config = _config(tmp_path)
    config.set('minecraft.show_server_name', True)
    bridge = MinecraftBridge(config)
    assert bridge.ingest(
        {
            'mode': 'Multiplayer',
            'dimension': 'minecraft:overworld',
            'server_name': 'Public SMP',
        },
        companion_header='minecraft-fabric-1',
    )
    assert bridge.latest()['server_name'] == 'Public SMP'


def test_minecraft_snapshot_expires(tmp_path, monkeypatch):
    bridge = MinecraftBridge(_config(tmp_path))
    now = [50.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    assert bridge.ingest(
        {'mode': 'Singleplayer', 'dimension': 'minecraft:overworld'},
        companion_header='minecraft-fabric-1',
    )
    assert bridge.latest() is not None
    now[0] += 16
    assert bridge.latest() is None


def test_minecraft_dimension_validation_rejects_urls_and_traversal():
    assert MinecraftBridge.normalize_payload({
        'mode': 'Singleplayer', 'dimension': 'https://example.com/private'
    })['dimension'] == ''
    assert MinecraftBridge.normalize_payload({
        'mode': 'Singleplayer', 'dimension': '../world/private'
    })['dimension'] == ''


def test_minecraft_window_requires_java_plus_explicit_title():
    assert GamingDetector._is_minecraft_window('javaw', 'Minecraft 26.2')
    assert GamingDetector._is_minecraft_window('java', 'Minecraft* 1.21.11')
    assert GamingDetector._is_minecraft_window('minecraftlauncher', 'Minecraft Launcher')
    assert not GamingDetector._is_minecraft_window('javaw', 'IntelliJ IDEA')
    assert not GamingDetector._is_minecraft_window('python', 'Minecraft tools')


def test_minecraft_friendly_dimensions():
    assert GamingDetector._friendly_minecraft_dimension('minecraft:overworld') == 'Overworld'
    assert GamingDetector._friendly_minecraft_dimension('minecraft:the_nether') == 'Nether'
    assert GamingDetector._friendly_minecraft_dimension('minecraft:the_end') == 'The End'
    assert GamingDetector._friendly_minecraft_dimension('mod:moon_base') == 'Moon Base'


def test_minecraft_enrichment_uses_filtered_snapshot(tmp_path):
    class FakeBridge:
        def __init__(self):
            self.config = None
            self.started = False

        def start(self):
            self.started = True
            return True

        def latest(self):
            return {
                'mode': 'Multiplayer',
                'dimension': 'minecraft:overworld',
                'server_name': 'Public SMP',
            }

    detector = object.__new__(GamingDetector)
    detector.config = _config(tmp_path)
    detector.minecraft_bridge = FakeBridge()
    activity = {'type': 'gaming', 'game_name': 'Minecraft', 'is_game': True}
    detector._enrich_minecraft(activity)
    assert detector.minecraft_bridge.started is True
    assert activity['minecraft_companion'] is True
    assert activity['game_source'] == 'Multiplayer · Overworld · Public SMP'
