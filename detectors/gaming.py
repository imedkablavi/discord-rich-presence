"""Conservative foreground-game detection."""

import logging
import re
from typing import Optional, Dict, Any

from config import Config


class GamingDetector:
    """Detect known games and launchers without treating launchers as games."""

    GAME_LAUNCHERS = {
        'steam': 'Steam', 'steamwebhelper': 'Steam',
        'epicgameslauncher': 'Epic Games', 'eossdkwin64shipping': 'Epic Games',
        'origin': 'Origin', 'eadesktop': 'EA Desktop',
        'uplay': 'Ubisoft Connect', 'ubisoftconnect': 'Ubisoft Connect',
        'gog': 'GOG Galaxy', 'galaxyclient': 'GOG Galaxy',
        'battlenet': 'Battle.net',
        'riotclientservices': 'Riot Client', 'leagueclient': 'League of Legends',
        'xboxapp': 'Xbox',
    }

    # Exact normalized executable stems only. False positives are worse than
    # missing an unknown game, so arbitrary process-name substrings are avoided.
    KNOWN_GAMES = {
        'leagueoflegends': 'League of Legends',
        'valorantwin64shipping': 'VALORANT',
        'valorant': 'VALORANT',
        'csgo': 'Counter-Strike: Global Offensive',
        'cs2': 'Counter-Strike 2',
        'dota2': 'Dota 2',
        'overwatch': 'Overwatch',
        'minecraft': 'Minecraft',
        'terraria': 'Terraria',
        'rocketleague': 'Rocket League',
        'fortniteclientwin64shipping': 'Fortnite',
        'fortnite': 'Fortnite',
        'r5apex': 'Apex Legends',
        'apex': 'Apex Legends',
        'gta5': 'Grand Theft Auto V',
        'gtav': 'Grand Theft Auto V',
        'rdr2': 'Red Dead Redemption 2',
        'witcher3': 'The Witcher 3',
        'skyrimse': 'Skyrim Special Edition',
        'skyrim': 'Skyrim',
        'fallout4': 'Fallout 4',
        'cyberpunk2077': 'Cyberpunk 2077',
        'eldenring': 'Elden Ring',
        'darksoulsiii': 'Dark Souls III',
        'darksouls': 'Dark Souls',
        'sekiro': 'Sekiro',
        'amongus': 'Among Us',
        'stardewvalley': 'Stardew Valley',
        'hollowknight': 'Hollow Knight',
        'celeste': 'Celeste',
        'hades': 'Hades',
        'hades2': 'Hades II',
        'deadcells': 'Dead Cells',
        'bg3': "Baldur's Gate 3",
        'baldursgate3': "Baldur's Gate 3",
        'helldivers2': 'HELLDIVERS 2',
        'destiny2': 'Destiny 2',
        'warframex64': 'Warframe',
        'warframe': 'Warframe',
        'ffxivdx11': 'FINAL FANTASY XIV',
        'ffxiv': 'FINAL FANTASY XIV',
        'pathofexile': 'Path of Exile',
        'pathofexilesteam': 'Path of Exile',
        'palworldwin64shipping': 'Palworld',
        'genshinimpact': 'Genshin Impact',
        'zenlesszonezero': 'Zenless Zone Zero',
        'starrail': 'Honkai: Star Rail',
        'forzahorizon5': 'Forza Horizon 5',
        'haloinfinite': 'Halo Infinite',
        'seaofthieves': 'Sea of Thieves',
        'rainbowsix': 'Rainbow Six Siege',
        'deadbydaylightwin64shipping': 'Dead by Daylight',
        'hogwartslegacy': 'Hogwarts Legacy',
        'monsterhunterwilds': 'Monster Hunter Wilds',
        'monsterhunterrise': 'Monster Hunter Rise',
    }

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not window_info or not self.config.get('rules.enabled_detectors.gaming', False):
            return None

        app_name = self._normalize_process_name(str(window_info.get('app_name', '')))
        title = str(window_info.get('title', '')).strip()

        game_name = self.KNOWN_GAMES.get(app_name)
        launcher_name = self.GAME_LAUNCHERS.get(app_name)
        if game_name:
            return {
                'type': 'gaming', 'game_name': game_name,
                'launcher': launcher_name, 'is_game': True
            }

        if launcher_name:
            title_game = self._extract_game_from_title(title, launcher_name)
            if title_game:
                return {
                    'type': 'gaming', 'game_name': title_game,
                    'launcher': launcher_name, 'is_game': True
                }
            return {
                'type': 'gaming', 'game_name': None,
                'launcher': launcher_name, 'is_game': False
            }
        return None

    @staticmethod
    def _normalize_process_name(process_name: str) -> str:
        raw = process_name.replace('\\', '/').rsplit('/', 1)[-1].strip().lower()
        if raw.endswith('.exe'):
            raw = raw[:-4]
        return re.sub(r'[^a-z0-9]+', '', raw)

    @staticmethod
    def _extract_game_from_title(title: str, launcher_name: str) -> Optional[str]:
        if not title:
            return None
        suffixes = {
            'Steam': (' - Steam',),
            'Epic Games': (' - Epic Games', ' - Epic Games Launcher'),
            'Origin': (' - Origin',),
            'EA Desktop': (' - EA app', ' - EA Desktop'),
            'Battle.net': (' - Battle.net',),
            'GOG Galaxy': (' - GOG GALAXY', ' - GOG Galaxy'),
            'Ubisoft Connect': (' - Ubisoft Connect',),
        }.get(launcher_name, ())
        for suffix in suffixes:
            if title.endswith(suffix):
                candidate = title[:-len(suffix)].strip()
                if 1 <= len(candidate) <= 120:
                    return candidate
        return None
