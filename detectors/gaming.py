import logging
from typing import Optional, Dict, Any
from config import Config
from core.activity_model import ActivityState
import time

class GamingDetector:
    GAME_LAUNCHERS = {
        'steam': 'Steam',
        'epicgameslauncher': 'Epic Games',
        'origin': 'Origin',
        'eadesktop': 'EA Desktop',
        'uplay': 'Ubisoft Connect',
        'battle.net': 'Battle.net',
        'leagueclient': 'League of Legends',
        'valorant': 'VALORANT',
        'gamebar': 'Xbox Game Bar',
        'minecraft': 'Minecraft',
    }
    
    KNOWN_GAMES = {
        'leagueoflegends': 'League of Legends',
        'valorant': 'VALORANT',
        'csgo': 'CS:GO',
        'dota2': 'Dota 2',
        'minecraft': 'Minecraft',
        'roblox': 'Roblox',
        'rocketleague': 'Rocket League',
    }

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._start_time = int(time.time())

    def detect(self, window_info: Dict[str, Any]) -> Optional[ActivityState]:
        if not self.config.get('rules.enabled_detectors.gaming', False):
            return None
            
        app_name = window_info.get('app_name', '').lower()
        title = window_info.get('title', '')
        
        launcher_name = None
        for key, name in self.GAME_LAUNCHERS.items():
            if key in app_name:
                launcher_name = name
                break
                
        game_name = None
        for key, name in self.KNOWN_GAMES.items():
            if key in app_name:
                game_name = name
                break
                
        if game_name or launcher_name:
            final_name = game_name if game_name else launcher_name
            return ActivityState(
                type="gaming",
                details=f"Playing {final_name}",
                state="Gaming" if not launcher_name else launcher_name,
                large_image=self.config.get(f"images.games.{final_name.lower().replace(' ', '')}", 'app'),
                large_text=final_name,
                start_time=self._start_time
            )
        return None
