"""Conservative foreground-game detection."""

import logging
from typing import Optional, Dict, Any

from config import Config


class GamingDetector:
    """Detect known games and launchers without treating launchers as games."""

    GAME_LAUNCHERS = {
        'steam': 'Steam', 'steamwebhelper': 'Steam',
        'epicgameslauncher': 'Epic Games', 'eossdk-win64-shipping': 'Epic Games',
        'origin': 'Origin', 'eadesktop': 'EA Desktop',
        'uplay': 'Ubisoft Connect', 'ubisoftconnect': 'Ubisoft Connect',
        'gog': 'GOG Galaxy', 'galaxyclient': 'GOG Galaxy',
        'battle.net': 'Battle.net', 'battlenet': 'Battle.net',
        'riotclientservices': 'Riot Client', 'leagueclient': 'League of Legends',
        'xboxapp': 'Xbox',
    }

    KNOWN_GAMES = {
        'leagueoflegends': 'League of Legends',
        'valorant': 'VALORANT',
        'csgo': 'Counter-Strike: Global Offensive',
        'cs2': 'Counter-Strike 2',
        'dota2': 'Dota 2',
        'overwatch': 'Overwatch',
        'minecraft': 'Minecraft',
        'terraria': 'Terraria',
        'rocketleague': 'Rocket League',
        'fortnite': 'Fortnite',
        'apex': 'Apex Legends',
        'gta5': 'Grand Theft Auto V',
        'gtav': 'Grand Theft Auto V',
        'witcher3': 'The Witcher 3',
        'skyrim': 'Skyrim',
        'fallout4': 'Fallout 4',
        'cyberpunk2077': 'Cyberpunk 2077',
        'eldenring': 'Elden Ring',
        'darksouls': 'Dark Souls',
        'sekiro': 'Sekiro',
        'amongus': 'Among Us',
        'stardewvalley': 'Stardew Valley',
        'hollowknight': 'Hollow Knight',
        'celeste': 'Celeste',
        'hades': 'Hades',
        'deadcells': 'Dead Cells',
    }

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not window_info or not self.config.get('rules.enabled_detectors.gaming', False):
            return None

        app_name = str(window_info.get('app_name', '')).lower().replace('.exe', '')
        title = str(window_info.get('title', '')).strip()

        game_name = self._match(app_name, self.KNOWN_GAMES)
        launcher_name = self._match(app_name, self.GAME_LAUNCHERS)
        if game_name:
            return {
                'type': 'gaming', 'game_name': game_name,
                'launcher': launcher_name, 'is_game': True
            }

        # A launcher is useful context, but it is not itself a game. The service
        # deliberately ignores is_game=False for Rich Presence.
        if launcher_name:
            title_game = self._extract_game_from_title(title)
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
    def _match(process_name: str, mapping: Dict[str, str]) -> Optional[str]:
        # Prefer exact matches; then allow known executable stems as substrings.
        if process_name in mapping:
            return mapping[process_name]
        for key in sorted(mapping, key=len, reverse=True):
            if len(key) >= 5 and key in process_name:
                return mapping[key]
        return None

    @staticmethod
    def _extract_game_from_title(title: str) -> Optional[str]:
        if not title:
            return None
        for suffix in (' - Steam', ' - Epic Games', ' - Origin', ' - Battle.net'):
            if title.endswith(suffix):
                candidate = title[:-len(suffix)].strip()
                return candidate or None
        return None
