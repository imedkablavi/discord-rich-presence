"""
Gaming activity detection for popular game launchers
"""

import logging
from typing import Optional, Dict, Any
from config import Config


class GamingDetector:
    """Detects gaming activity from various launchers"""
    
    GAME_LAUNCHERS = {
        # Steam
        'steam': 'Steam',
        'steamwebhelper': 'Steam',
        
        # Epic Games
        'epicgameslauncher': 'Epic Games',
        'eossdk-win64-shipping': 'Epic Games',
        
        # EA
        'origin': 'Origin',
        'eadesktop': 'EA Desktop',
        
        # Ubisoft
        'uplay': 'Ubisoft Connect',
        'ubisoftconnect': 'Ubisoft Connect',
        
        # GOG
        'gog': 'GOG Galaxy',
        'galaxyclient': 'GOG Galaxy',
        
        # Battle.net
        'battle.net': 'Battle.net',
        'battlenet': 'Battle.net',
        
        # Riot
        'riotclientservices': 'Riot Client',
        'leagueclient': 'League of Legends',
        'valorant': 'VALORANT',
        
        # Xbox
        'gamebar': 'Xbox Game Bar',
        'xboxapp': 'Xbox',
        
        # Minecraft
        'minecraft': 'Minecraft',
        'javaw': 'Minecraft',  # May be Minecraft
    }
    
    KNOWN_GAMES = {
        # Popular games (process name -> game name)
        'leagueoflegends': 'League of Legends',
        'valorant': 'VALORANT',
        'csgo': 'Counter-Strike: Global Offensive',
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
        """Detect if window is a game or game launcher"""
        if not window_info:
            return None
        
        if not self.config.get('rules.enabled_detectors.gaming', False):
            return None
        
        app_name = window_info.get('app_name', '').lower()
        title = window_info.get('title', '')
        
        # Check if it's a known game launcher
        launcher_name = None
        for key, name in self.GAME_LAUNCHERS.items():
            if key in app_name:
                launcher_name = name
                break
        
        # Check if it's a known game
        game_name = None
        for key, name in self.KNOWN_GAMES.items():
            if key in app_name:
                game_name = name
                break
        
        # If we found a game, prioritize it
        if game_name:
            return {
                'type': 'gaming',
                'game_name': game_name,
                'launcher': launcher_name,
                'is_game': True
            }
        
        # If we found a launcher, return it
        if launcher_name:
            # Try to extract game from title
            if title and title != launcher_name:
                game_name = self._extract_game_from_title(title)
                if game_name:
                    return {
                        'type': 'gaming',
                        'game_name': game_name,
                        'launcher': launcher_name,
                        'is_game': True
                    }
            
            return {
                'type': 'gaming',
                'game_name': None,
                'launcher': launcher_name,
                'is_game': False
            }
        
        return None
    
    def _extract_game_from_title(self, title: str) -> Optional[str]:
        """Try to extract game name from window title"""
        # Remove common launcher suffixes
        for suffix in [' - Steam', ' - Epic Games', ' - Origin', ' - Battle.net']:
            if suffix in title:
                return title.replace(suffix, '').strip()
        
        return None
