from types import SimpleNamespace

from detectors.gaming import GamingDetector


class _Config:
    def __init__(self, privacy='balanced'):
        self.privacy = privacy

    def get(self, key, default=None):
        if key == 'rules.enabled_detectors.gaming':
            return True
        if key == 'privacy.mode':
            return self.privacy
        return default


class _NoCatalog:
    @staticmethod
    def resolve(_window_info):
        return None


class _NoPack:
    @staticmethod
    def activity(_process):
        return None


def _detector_without_services(*, privacy='balanced', warthunder_snapshot=None):
    detector = object.__new__(GamingDetector)
    detector.config = _Config(privacy)
    detector.cs2_gsi = None
    detector.steam_catalog = _NoCatalog()
    detector.epic_catalog = _NoCatalog()
    detector.heroic_catalog = _NoCatalog()
    detector.game_packs = _NoPack()
    detector.warthunder_telemetry = SimpleNamespace(
        snapshot=lambda: dict(warthunder_snapshot or {})
    )
    detector._sync_cs2_gsi = lambda: None
    detector._enrich_minecraft = lambda activity: None
    detector._enrich_fivem = lambda activity: None
    detector._enrich_league = lambda activity: None
    return detector


def test_minecraft_launcher_itself_is_not_reported_as_playing_minecraft():
    detector = _detector_without_services()
    activity = detector.detect({
        'app_name': 'MinecraftLauncher.exe',
        'title': 'Minecraft Launcher',
        'pid': None,
    })
    assert activity is not None
    assert activity['launcher'] == 'Minecraft Launcher'
    assert activity['game_name'] is None
    assert activity['is_game'] is False


def test_java_minecraft_window_is_reported_as_the_game():
    detector = _detector_without_services()
    activity = detector.detect({
        'app_name': 'javaw.exe',
        'title': 'Minecraft 1.21.5',
        'pid': 4242,
    })
    assert activity is not None
    assert activity['game_name'] == 'Minecraft'
    assert activity['is_game'] is True


def test_exact_launcher_process_does_not_hit_known_game_substring_aliases():
    detector = _detector_without_services()
    activity = detector.detect({
        'app_name': 'minecraftlauncher',
        'title': 'Store',
        'pid': None,
    })
    assert activity == {
        'type': 'gaming',
        'game_name': None,
        'launcher': 'Minecraft Launcher',
        'is_game': False,
    }


def test_generic_java_window_is_never_minecraft():
    assert not GamingDetector._is_minecraft_window('java', 'IntelliJ IDEA')
    assert GamingDetector._is_minecraft_window('java', 'Minecraft 1.21.5')
    assert not GamingDetector._is_minecraft_window('minecraftlauncher', 'Minecraft Launcher')


def test_exact_warthunder_client_process_gets_safe_local_enrichment():
    detector = _detector_without_services(warthunder_snapshot={
        'warthunder_telemetry': True,
        'branch': 'Ground',
        'vehicle': 'T 80bvm',
        'mission_status': 'running',
    })
    activity = detector.detect({
        'app_name': 'aces.exe',
        'title': 'War Thunder',
        'pid': None,
    })
    assert activity is not None
    assert activity['game_name'] == 'War Thunder'
    assert activity['warthunder_local'] is True
    assert activity['game_source'] == 'Ground · T 80bvm · In Battle'


def test_warthunder_strict_privacy_does_not_probe_telemetry():
    calls = {'count': 0}
    detector = _detector_without_services(privacy='strict')

    def snapshot():
        calls['count'] += 1
        return {'warthunder_telemetry': True, 'branch': 'Ground'}

    detector.warthunder_telemetry = SimpleNamespace(snapshot=snapshot)
    activity = detector.detect({'app_name': 'aces', 'title': 'War Thunder', 'pid': None})
    assert activity is not None
    assert activity['game_name'] == 'War Thunder'
    assert 'warthunder_local' not in activity
    assert calls['count'] == 0


def test_process_name_containing_aces_is_not_warthunder():
    detector = _detector_without_services()
    assert detector.detect({'app_name': 'traces-ui', 'title': '', 'pid': None}) is None
