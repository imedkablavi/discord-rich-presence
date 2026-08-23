"""Foreground-game detection from local launcher catalogs with safe game enrichment."""

import logging
import re
from typing import Optional, Dict, Any

from config import Config
from cs2_gsi import (
    discover_cs2_cfg_dirs,
    get_cs2_gsi,
    install_gsi_config,
    stop_cs2_gsi,
)
from epic_catalog import EpicGame, EpicGameCatalog
from fivem_bridge import get_fivem_bridge
from heroic_catalog import HeroicGame, HeroicGameCatalog
from league_client import LeagueLiveClient
from minecraft_bridge import get_minecraft_bridge
from steam_catalog import SteamGame, SteamGameCatalog


class GamingDetector:
    """Detect foreground games and enrich supported games through safe local APIs."""

    GAME_LAUNCHERS = {
        'steam': 'Steam', 'steamwebhelper': 'Steam',
        'epicgameslauncher': 'Epic Games', 'eossdk-win64-shipping': 'Epic Games',
        'heroic': 'Heroic',
        'origin': 'Origin', 'eadesktop': 'EA Desktop',
        'uplay': 'Ubisoft Connect', 'ubisoftconnect': 'Ubisoft Connect',
        'gog': 'GOG Galaxy', 'galaxyclient': 'GOG Galaxy',
        'battle.net': 'Battle.net', 'battlenet': 'Battle.net',
        'riotclientservices': 'Riot Client', 'leagueclient': 'League of Legends',
        'minecraftlauncher': 'Minecraft Launcher',
        'xboxapp': 'Xbox',
    }

    # Fallback aliases for launchers/platforms that do not expose a local game
    # catalog we can resolve safely. Steam/Epic/Heroic are resolved locally first.
    KNOWN_GAMES = {
        'leagueoflegends': 'League of Legends',
        'league of legends': 'League of Legends',
        'valorant': 'VALORANT',
        'fivem': 'FiveM',
        'citizenfx': 'FiveM',
        'csgo': 'Counter-Strike 2',
        'cs2': 'Counter-Strike 2',
        'steam_app_730': 'Counter-Strike 2',
        'dota2': 'Dota 2',
        'overwatch': 'Overwatch 2',
        'minecraft': 'Minecraft',
        'terraria': 'Terraria',
        'rocketleague': 'Rocket League',
        'fortnite': 'Fortnite',
        'apex': 'Apex Legends',
        'r5apex': 'Apex Legends',
        'gta5': 'Grand Theft Auto V',
        'gta5_enhanced': 'Grand Theft Auto V Enhanced',
        'gtav': 'Grand Theft Auto V',
        'witcher3': 'The Witcher 3: Wild Hunt',
        'skyrim': 'The Elder Scrolls V: Skyrim',
        'fallout4': 'Fallout 4',
        'cyberpunk2077': 'Cyberpunk 2077',
        'eldenring': 'Elden Ring',
        'darksouls': 'Dark Souls',
        'sekiro': 'Sekiro: Shadows Die Twice',
        'amongus': 'Among Us',
        'stardewvalley': 'Stardew Valley',
        'hollowknight': 'Hollow Knight',
        'celeste': 'Celeste',
        'hades': 'Hades',
        'deadcells': 'Dead Cells',
        'helldivers2': 'HELLDIVERS 2',
        'marvelrivals': 'Marvel Rivals',
        'rainbowsix': 'Tom Clancy’s Rainbow Six Siege',
        'rainbow six': 'Tom Clancy’s Rainbow Six Siege',
        'destiny2': 'Destiny 2',
        'warframe': 'Warframe',
        'war thunder': 'War Thunder',
        'pathofexile': 'Path of Exile',
        'poe2': 'Path of Exile 2',
        'ffxiv': 'FINAL FANTASY XIV Online',
        'ffxiv_dx11': 'FINAL FANTASY XIV Online',
        'wow': 'World of Warcraft',
        'diablo iv': 'Diablo IV',
        'diablo4': 'Diablo IV',
    }

    TITLE_GAME_ALIASES = {
        'cs go': 'Counter-Strike 2',
        'cs:go': 'Counter-Strike 2',
        'counter strike 2': 'Counter-Strike 2',
        'counter-strike 2': 'Counter-Strike 2',
        'counter-strike: global offensive': 'Counter-Strike 2',
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

    CS2_ROUND_SCORE_MODES = {
        'competitive', 'casual', 'scrimcomp2v2', 'scrimpcomp2v2', 'wingman',
        'gungametrbomb', 'demolition',
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

    MINECRAFT_DIMENSIONS = {
        'minecraft:overworld': 'Overworld',
        'minecraft:the_nether': 'Nether',
        'minecraft:the_end': 'The End',
    }

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.steam_catalog = SteamGameCatalog()
        self.epic_catalog = EpicGameCatalog()
        self.heroic_catalog = HeroicGameCatalog()
        self.league_client = LeagueLiveClient()
        self.fivem_bridge = get_fivem_bridge(config, start=False)
        self.minecraft_bridge = get_minecraft_bridge(config, start=False)
        self.cs2_gsi = None
        self._last_gsi_signature: Optional[tuple[bool, bool, bool, int, float]] = None
        self._sync_cs2_gsi(force=True)

    @staticmethod
    def _strict_bool_setting(config: Config, key: str, default: bool) -> bool:
        value = config.get(key, default)
        return value if isinstance(value, bool) else False

    def _gsi_signature(self) -> tuple[bool, bool, bool, int, float]:
        gaming_enabled = bool(self.config.get('rules.enabled_detectors.gaming', True))
        gsi_enabled = self._strict_bool_setting(self.config, 'cs2_gsi.enabled', True)
        auto_install = self._strict_bool_setting(self.config, 'cs2_gsi.auto_install', True)
        try:
            port = int(self.config.get('cs2_gsi.port', 32192) or 32192)
        except (TypeError, ValueError):
            port = 32192
        try:
            ttl = float(self.config.get('cs2_gsi.ttl_secs', 30) or 30)
        except (TypeError, ValueError):
            ttl = 30.0
        return gaming_enabled, gsi_enabled, auto_install, port, ttl

    def _sync_cs2_gsi(self, *, force: bool = False) -> None:
        """Apply hot-reloaded GSI settings without leaving stale listeners behind."""
        signature = self._gsi_signature()
        if not force and signature == self._last_gsi_signature:
            return

        previous = self._last_gsi_signature
        self._last_gsi_signature = signature
        if previous is not None:
            stop_cs2_gsi()
            self.cs2_gsi = None

        gaming_enabled, gsi_enabled, auto_install, _port, _ttl = signature
        if not gaming_enabled or not gsi_enabled:
            # Disabling the integration should also prevent future CS2 launches
            # from continuing to POST to the CYBREX endpoint. A currently running
            # game may retain its already-loaded cfg until it restarts.
            self._remove_cybrex_gsi_config()
            return

        # Fail closed: never point CS2 at a port unless our own loopback listener
        # successfully owns that port first. Otherwise an unrelated local process
        # could receive GSI metadata if it happened to bind the configured port.
        candidate = get_cs2_gsi(self.config, start=False)
        if candidate is not None and candidate.start():
            self.cs2_gsi = candidate
            if auto_install:
                self._auto_configure_cs2_gsi()
            if previous is not None:
                self.logger.info('Counter-Strike 2 GSI configuration reloaded')
            return

        self.cs2_gsi = None
        if candidate is not None and auto_install:
            self._remove_cybrex_gsi_config()
        self.logger.warning(
            'CS2 GSI listener is unavailable; automatic game configuration '
            'was disabled to avoid sending game state to an unverified local port. '
            'Restart CS2 if it was already running.'
        )

    def _remove_cybrex_gsi_config(self) -> None:
        try:
            locations = discover_cs2_cfg_dirs()
        except OSError:
            return
        for cfg_dir in locations:
            target = cfg_dir / 'gamestate_integration_cybrex.cfg'
            try:
                target.unlink(missing_ok=True)
            except OSError as exc:
                self.logger.warning(
                    'Could not remove CYBREX CS2 GSI configuration %s: %s',
                    target,
                    exc,
                )

    def _auto_configure_cs2_gsi(self) -> None:
        try:
            locations = discover_cs2_cfg_dirs()
            if not locations:
                return
            install_gsi_config(self.config, locations[0])
            self.logger.info('Counter-Strike 2 GSI integration is configured')
        except (OSError, ValueError):
            self.logger.warning(
                'Counter-Strike 2 GSI auto-setup could not write the game config; '
                'use scripts/install-cs2-gsi.py for manual setup'
            )

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._sync_cs2_gsi()
        if not window_info or not self.config.get('rules.enabled_detectors.gaming', False):
            return None

        app_name = str(window_info.get('app_name', '')).lower().replace('.exe', '')
        title = str(window_info.get('title', '')).strip()

        # FiveM runs GTA inside a CitizenFX/FiveM process tree. Detect that
        # identity before Steam path matching so it cannot be mislabeled as GTA V.
        if self._is_fivem_process(app_name):
            activity: Dict[str, Any] = {
                'type': 'gaming',
                'game_name': 'FiveM',
                'launcher': 'FiveM',
                'game_source': 'FiveM',
                'is_game': True,
            }
            self._enrich_fivem(activity)
            return activity

        # Minecraft Java often exposes only java/javaw as the process name. Pair
        # that generic process identity with an explicit Minecraft window title;
        # never classify arbitrary Java applications as games.
        if self._is_minecraft_window(app_name, title):
            activity = {
                'type': 'gaming',
                'game_name': 'Minecraft',
                'launcher': 'Minecraft Launcher',
                'game_source': 'Minecraft',
                'is_game': True,
            }
            self._enrich_minecraft(activity)
            return activity

        # Local launcher catalogs are authoritative when available. They provide
        # the real installed title instead of leaking process/class strings into
        # Discord, and they work for games never hardcoded in this project.
        steam_game = self.steam_catalog.resolve(window_info)
        if steam_game:
            activity = self._steam_activity(steam_game)
            if steam_game.appid == 730 or self._is_cs2_name(steam_game.name):
                activity['game_name'] = 'Counter-Strike 2'
                self._enrich_cs2(activity)
            return activity

        epic_game = self.epic_catalog.resolve(window_info)
        if epic_game:
            return self._epic_activity(epic_game)

        heroic_game = self.heroic_catalog.resolve(window_info)
        if heroic_game:
            return self._heroic_activity(heroic_game)

        game_name = self._match(app_name, self.KNOWN_GAMES)
        launcher_name = self._match(app_name, self.GAME_LAUNCHERS)
        if game_name:
            activity = {
                'type': 'gaming',
                'game_name': game_name,
                'launcher': launcher_name or ('Steam' if game_name == 'Counter-Strike 2' else 'Gaming'),
                'is_game': True,
            }
            if game_name == 'Counter-Strike 2':
                activity.update({
                    'steam_appid': 730,
                    'game_source': 'Steam',
                    'artwork_url': self._steam_artwork_url(730),
                    'store_url': 'https://store.steampowered.com/app/730/',
                })
                self._enrich_cs2(activity)
            elif game_name == 'League of Legends':
                self._enrich_league(activity)
            elif game_name == 'FiveM':
                self._enrich_fivem(activity)
            elif game_name == 'Minecraft':
                self._enrich_minecraft(activity)
            return activity

        if self.cs2_gsi and ('counter-strike' in app_name or 'counter strike' in app_name):
            activity = {
                'type': 'gaming', 'game_name': 'Counter-Strike 2',
                'launcher': launcher_name or 'Steam', 'is_game': True,
                'steam_appid': 730, 'game_source': 'Steam',
                'artwork_url': self._steam_artwork_url(730),
                'store_url': 'https://store.steampowered.com/app/730/',
            }
            self._enrich_cs2(activity)
            return activity

        # A launcher is useful context, but it is not itself a game. Only use a
        # title fallback when it contains a plausible game title, never generic
        # launcher/store/library text.
        if launcher_name:
            title_game = self._extract_game_from_title(title)
            if title_game:
                return {
                    'type': 'gaming', 'game_name': title_game,
                    'launcher': launcher_name, 'game_source': launcher_name,
                    'is_game': True,
                }
            return {
                'type': 'gaming', 'game_name': None,
                'launcher': launcher_name, 'is_game': False,
            }
        return None

    @classmethod
    def _steam_activity(cls, game: SteamGame) -> Dict[str, Any]:
        return {
            'type': 'gaming',
            'game_name': game.name,
            'launcher': 'Steam',
            'is_game': True,
            'steam_appid': game.appid,
            'game_source': 'Steam',
            'artwork_url': game.artwork_url,
            'store_url': f'https://store.steampowered.com/app/{game.appid}/',
        }

    @staticmethod
    def _epic_activity(game: EpicGame) -> Dict[str, Any]:
        return {
            'type': 'gaming',
            'game_name': game.name,
            'launcher': 'Epic Games',
            'game_source': 'Epic Games',
            'epic_app_name': game.app_name,
            'is_game': True,
        }

    @staticmethod
    def _heroic_activity(game: HeroicGame) -> Dict[str, Any]:
        return {
            'type': 'gaming',
            'game_name': game.name,
            'launcher': 'Heroic',
            'game_source': 'Heroic',
            'heroic_app_name': game.app_name,
            'is_game': True,
        }

    @staticmethod
    def _steam_artwork_url(appid: int) -> str:
        return (
            'https://shared.cloudflare.steamstatic.com/store_item_assets/'
            f'steam/apps/{int(appid)}/header.jpg'
        )

    @staticmethod
    def _is_cs2_name(name: str) -> bool:
        normalized = re.sub(r'[^a-z0-9]+', '', str(name or '').lower())
        return normalized in {'counterstrike2', 'counterstrikeglobaloffensive'}

    @staticmethod
    def _is_fivem_process(app_name: str) -> bool:
        lowered = str(app_name or '').lower()
        return 'fivem' in lowered or 'citizenfx' in lowered

    @staticmethod
    def _is_minecraft_window(app_name: str, title: str) -> bool:
        app = str(app_name or '').lower().replace('.exe', '').strip()
        window = str(title or '').strip().lower()
        if app in {'minecraft', 'minecraftlauncher'}:
            return True
        if app not in {'java', 'javaw'}:
            return False
        return bool(re.match(r'^minecraft(?:\s|$|\*)', window))

    def _enrich_league(self, activity: Dict[str, Any]) -> None:
        snapshot = self.league_client.snapshot()
        if not snapshot:
            activity['launcher'] = 'Riot Client'
            activity['game_source'] = 'Riot Client'
            return
        champion = str(snapshot.get('champion', '') or '').strip()
        position = str(snapshot.get('position', '') or '').strip()
        mode = str(snapshot.get('mode', '') or '').strip()
        state_parts = [part for part in (champion, position, mode) if part]
        activity.update({
            'launcher': 'Riot Client',
            'game_source': ' · '.join(state_parts) or 'Riot Client',
            'league_live': True,
            'league_game_time': int(snapshot.get('game_time', 0) or 0),
        })

    def _enrich_fivem(self, activity: Dict[str, Any]) -> None:
        self.fivem_bridge.config = self.config
        self.fivem_bridge.start()
        snapshot = self.fivem_bridge.latest()
        activity['launcher'] = 'FiveM'
        if not snapshot:
            activity['game_source'] = 'FiveM'
            return

        state_parts: list[str] = []
        server_name = str(snapshot.get('server_name', '') or '').strip()
        if server_name:
            state_parts.append(server_name)
        player_count = int(snapshot.get('player_count', 0) or 0)
        max_players = int(snapshot.get('max_players', 0) or 0)
        if max_players > 0:
            state_parts.append(f'{player_count}/{max_players} players')
        elif player_count > 0:
            state_parts.append(f'{player_count} players')

        activity.update({
            'fivem_companion': True,
            'game_source': ' · '.join(state_parts) or 'FiveM',
        })
        join_url = str(snapshot.get('join_url', '') or '').strip()
        if join_url:
            activity['store_url'] = join_url

    def _enrich_minecraft(self, activity: Dict[str, Any]) -> None:
        self.minecraft_bridge.config = self.config
        self.minecraft_bridge.start()
        snapshot = self.minecraft_bridge.latest()
        activity['launcher'] = 'Minecraft Launcher'
        if not snapshot:
            activity['game_source'] = 'Minecraft'
            return

        mode = str(snapshot.get('mode', '') or '').strip()
        dimension_key = str(snapshot.get('dimension', '') or '').strip().lower()
        dimension = self._friendly_minecraft_dimension(dimension_key)
        server_name = str(snapshot.get('server_name', '') or '').strip()
        state_parts = [part for part in (mode, dimension, server_name) if part]
        activity.update({
            'minecraft_companion': True,
            'minecraft_mode': mode,
            'minecraft_dimension': dimension,
            'game_source': ' · '.join(state_parts) or 'Minecraft',
        })

    @classmethod
    def _friendly_minecraft_dimension(cls, value: str) -> str:
        key = str(value or '').strip().lower()
        if not key:
            return ''
        if key in cls.MINECRAFT_DIMENSIONS:
            return cls.MINECRAFT_DIMENSIONS[key]
        raw = key.split(':', 1)[-1].replace('_', ' ').replace('-', ' ').strip()
        return raw.title()[:80] if raw else ''

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
        score_is_meaningful = mode_key in self.CS2_ROUND_SCORE_MODES or ct_score > 0 or t_score > 0
        if map_name and score_is_meaningful:
            state_parts.append(f'CT {ct_score}–{t_score} T')

        activity.update({
            'gsi': True,
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
        if process_name in mapping:
            return mapping[process_name]
        for key in sorted(mapping, key=len, reverse=True):
            if len(key) >= 5 and key in process_name:
                return mapping[key]
        return None

    @classmethod
    def _extract_game_from_title(cls, title: str) -> Optional[str]:
        if not title:
            return None
        candidate = title.strip()
        for suffix in (
            ' - Steam', ' — Steam', ' – Steam', ' | Steam',
            ' - Epic Games', ' — Epic Games', ' - Origin', ' - Battle.net',
            ' - Heroic', ' — Heroic',
        ):
            if candidate.lower().endswith(suffix.lower()):
                candidate = candidate[:-len(suffix)].strip()
                break
        else:
            if candidate.lower().endswith(' steam'):
                candidate = candidate[:-6].strip()

        lowered = candidate.lower().strip(' -—–|')
        if not lowered or lowered in {
            'steam', 'store', 'library', 'community', 'friends', 'downloads',
            'epic games', 'heroic', 'origin', 'battle.net',
        }:
            return None
        if lowered in cls.TITLE_GAME_ALIASES:
            return cls.TITLE_GAME_ALIASES[lowered]
        return candidate[:160] or None
