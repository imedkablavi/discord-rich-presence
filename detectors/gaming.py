"""Conservative foreground-game detection with optional CS2 GSI enrichment."""

import logging
from typing import Optional, Dict, Any

from config import Config
from cs2_gsi import discover_cs2_cfg_dirs, get_cs2_gsi, install_gsi_config


class GamingDetector:
    """Detect known games and enrich Counter-Strike 2 through official GSI."""

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

    CS2_MODE_NAMES = {
        'competitive': 'Competitive',
        'casual': 'Casual',
        'deathmatch': 'Deathmatch',
        'scrimcomp2v2': 'Wingman',
        'scrimpcomp2v2': 'Wingman',
        'wingman': 'Wingman',
        'gungameprogressive': 'Arms Race',
        'gungametrbomb': 'Demolition',
        'demolition': 'Demolition',
        'survival': 'Danger Zone',
        'training': 'Training',
        'custom': 'Custom',
    }

    CS2_MAP_NAMES = {
        'de_mirage': 'Mirage',
        'de_dust2': 'Dust II',
        'de_inferno': 'Inferno',
        'de_nuke': 'Nuke',
        'de_ancient': 'Ancient',
        'de_anubis': 'Anubis',
        'de_overpass': 'Overpass',
        'de_train': 'Train',
        'de_vertigo': 'Vertigo',
        'cs_office': 'Office',
    }

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        gaming_enabled = bool(config.get('rules.enabled_detectors.gaming', True))
        # Do not bind a port or modify the game's cfg when the entire gaming
        # detector is disabled by the user.
        self.cs2_gsi = get_cs2_gsi(config, start=True) if gaming_enabled else None
        if self.cs2_gsi and bool(config.get('cs2_gsi.auto_install', True)):
            self._auto_configure_cs2_gsi()

    def _auto_configure_cs2_gsi(self) -> None:
        """Make packaged/source installs zero-setup when CS2 is discoverable."""
        try:
            locations = discover_cs2_cfg_dirs()
            if not locations:
                return
            install_gsi_config(self.config, locations[0])
            self.logger.info('Counter-Strike 2 GSI integration is configured')
        except (OSError, ValueError):
            # Never break generic game detection because the Steam install is
            # read-only or unusual. The standalone installer supports --cfg-dir.
            self.logger.warning(
                'Counter-Strike 2 GSI auto-setup could not write the game config; '
                'use scripts/install-cs2-gsi.py for manual setup'
            )

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not window_info or not self.config.get('rules.enabled_detectors.gaming', False):
            return None

        app_name = str(window_info.get('app_name', '')).lower().replace('.exe', '')
        title = str(window_info.get('title', '')).strip()

        game_name = self._match(app_name, self.KNOWN_GAMES)
        launcher_name = self._match(app_name, self.GAME_LAUNCHERS)
        if game_name:
            activity: Dict[str, Any] = {
                'type': 'gaming', 'game_name': game_name,
                'launcher': launcher_name, 'is_game': True
            }
            if game_name == 'Counter-Strike 2':
                self._enrich_cs2(activity)
            return activity

        # Some Linux compositors expose a slightly different CS2 app/class
        # string. A fresh authenticated GSI snapshot is enough to disambiguate
        # only when the foreground name still clearly contains Counter-Strike.
        if self.cs2_gsi and ('counter-strike' in app_name or 'counter strike' in app_name):
            activity = {
                'type': 'gaming', 'game_name': 'Counter-Strike 2',
                'launcher': launcher_name or 'Steam', 'is_game': True,
            }
            self._enrich_cs2(activity)
            return activity

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

    def _enrich_cs2(self, activity: Dict[str, Any]) -> None:
        if not self.cs2_gsi:
            return
        snapshot = self.cs2_gsi.latest()
        if not snapshot:
            return

        map_key = str(snapshot.get('map', '') or '').lower()
        mode_key = str(snapshot.get('mode', '') or '').lower()
        team = str(snapshot.get('team', '') or '').upper()
        map_name = self._friendly_map(map_key)
        mode_name = self.CS2_MODE_NAMES.get(mode_key, self._friendly_label(mode_key))
        team_name = 'Counter-Terrorists' if team == 'CT' else ('Terrorists' if team == 'T' else '')
        ct_score = int(snapshot.get('ct_score', 0) or 0)
        t_score = int(snapshot.get('t_score', 0) or 0)

        state_parts = [part for part in (mode_name, map_name, team_name) if part]
        if map_name:
            state_parts.append(f'CT {ct_score}–{t_score} T')

        activity.update({
            'gsi': True,
            # PresenceBuilder already uses launcher as the gaming state line.
            # For CS2 this becomes the live, user-facing match summary.
            'launcher': ' · '.join(state_parts) or activity.get('launcher') or 'Steam',
            'map': map_name,
            'map_key': map_key,
            'mode': mode_name,
            'mode_key': mode_key,
            'team': team,
            'team_name': team_name,
            'ct_score': ct_score,
            't_score': t_score,
            'round': int(snapshot.get('round', 0) or 0),
            'phase': str(
                snapshot.get('round_phase')
                or snapshot.get('countdown_phase')
                or snapshot.get('map_phase')
                or ''
            ),
            'player_activity': str(snapshot.get('player_activity', '') or ''),
        })

    @classmethod
    def _friendly_map(cls, map_key: str) -> str:
        if not map_key:
            return ''
        if map_key in cls.CS2_MAP_NAMES:
            return cls.CS2_MAP_NAMES[map_key]
        raw = map_key
        for prefix in ('de_', 'cs_', 'workshop_'):
            if raw.startswith(prefix):
                raw = raw[len(prefix):]
                break
        return cls._friendly_label(raw)

    @staticmethod
    def _friendly_label(value: str) -> str:
        text = str(value or '').replace('_', ' ').replace('-', ' ').strip()
        return text.title() if text else ''

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
