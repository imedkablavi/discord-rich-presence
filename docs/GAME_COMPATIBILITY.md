# Game Compatibility

CYBREX Presence has distinct levels of game support. Keeping them separate avoids misleading compatibility claims: detecting that a game is running is not the same as knowing its current map, server, mode or match state.

## Standard game support

The desktop app identifies installed/foreground games from local metadata where possible. Steam, Epic Games and Heroic are metadata-driven, so support is not limited to a hardcoded list: a game can work even when its title is not present in this repository's curated catalog.

For release QA and product documentation, CYBREX also ships a curated compatibility catalog containing **346 popular titles** across Steam-heavy, cross-launcher and current-2026 targets. The source of truth is:

- `game_packs/popular_catalog.json`
- `game_packs/popular_cross_launcher.json`
- `game_packs/popular_2026.json`

The catalog includes representative titles such as Counter-Strike 2, Dota 2, GTA V, ELDEN RING, Baldur's Gate 3, Fortnite, VALORANT, League of Legends, Minecraft, Roblox, World of Warcraft, Diablo IV, Rocket League, Genshin Impact, Squad, Deadlock, PEAK and EA SPORTS FC 26.

A title being in the curated catalog means it is an explicit compatibility/QA target. It does **not** mean every launcher, operating system, game version or storefront build has been manually tested on real hardware, and it does not imply deep match telemetry.

## Activity accuracy tiers

### Tier 1 — game identity

For ordinary launcher-resolved games CYBREX can publish the canonical game name, launcher/source, Steam artwork/store link when available, and elapsed activity time. This is the baseline for the broad catalog.

CYBREX must not invent map/server/mode values for Tier-1 titles.

### Tier 2 — local match metadata

A game may expose reliable, read-only local state without requiring account credentials or game-memory access. CYBREX can enrich those games only from verified local evidence and must fall back to Tier 1 when that evidence is unavailable.

**Squad** is handled in this tier. CYBREX recognizes Steam AppID `393380` and the exact `SquadGame` foreground process as a conservative fallback. While Squad is foreground, CYBREX can tail the local `SquadGame.log` with a bounded read and extract high-confidence current layer/map/mode. A server name or population is published only when the same recent log window also contains current join/loading evidence; unrelated server-browser search results are rejected. IP addresses, EOS IDs, Steam IDs, tokens and other account/network identifiers are never copied into Presence. In Strict privacy mode CYBREX keeps the generic `Game · Gaming` contract and does not read the Squad log at all.

This is intentionally read-only: no DLL/code injection, memory reading, packet capture, EOS credential emulation or RCON is used.

### Tier 3 — documented live integration

Current enhanced integrations are:

| Game / platform | Source | Live fields when available |
| --- | --- | --- |
| Counter-Strike 2 | Valve Game State Integration on authenticated loopback | map, mode, team/score context |
| League of Legends | Riot local Live Client API | supported live match context |
| FiveM | optional CYBREX loopback companion | server/session context supplied by the companion |
| Minecraft | optional CYBREX Fabric companion | dimension/server context supplied by the companion |
| Squad | bounded read-only local game log | layer, map, mode; current server/population only when session evidence is strong |

Enhanced support must not be inferred from membership in the 346-title catalog.

## Why Squad does not query the public server browser

Squad replaced its Steam backend calls with Epic Online Services. CYBREX does not reproduce the game's Steam-ticket/EOS authentication flow merely to obtain Presence metadata, and RCON requires server-admin credentials. For a normal player, local client evidence is a safer and more stable boundary. If Squad changes its log format, enrichment fails soft to ordinary `Squad · Steam` Presence instead of guessing.

## Detection order

1. Resolve Steam from local Steam manifests/library metadata.
2. Resolve Epic Games from local Epic manifest metadata.
3. Resolve Heroic/Legendary from local Heroic metadata.
4. Consult the validated Community Game Pack for conservative exact-process fallbacks.
5. Apply the small built-in verified process aliases for known games/launchers.
6. When the foreground process is a known launcher and local catalog resolution was unavailable, accept its window title only when it is a known alias or an **exact normalized match** to the curated 346-title catalog.
7. Apply a game-specific enrichment provider only after the game identity is resolved; enrichment failure must never turn a correctly detected game into a false negative.

Launcher metadata remains authoritative over all fallback aliases and title matching. Generic launcher pages such as Store, Library, News and arbitrary promotional window titles fail closed and are not reported as games.

## Safety boundary

CYBREX Presence does not need game-memory reading, DLL/code injection, anti-cheat bypasses, packet interception or input automation to provide standard or supported enhanced game Presence. Community Game Packs use exact normalized process names only; regex/wildcard process scanning and arbitrary command execution are not part of the pack format.

Game-specific integrations must meet all of these rules:

- prefer an official/documented local API when one exists;
- otherwise use bounded read-only local files only when the format has high-confidence markers;
- never require a user's account/session token just to make Presence richer;
- never publish IP addresses, account IDs, auth tokens or private server credentials;
- never guess a server/map from stale browser results;
- fail soft to Tier-1 game identity when richer data is unavailable.

## Why the catalog is separate from process matching

Hardcoding hundreds of guessed executable names would create false positives and would age badly as games update. The curated catalog therefore records supported product targets, while runtime detection uses authoritative local launcher metadata whenever available. Exact process aliases are added only when they are known and useful as a fallback. The launcher-title fallback also requires an exact curated title rather than substring matching.

## CI contract

`tests/test_popular_games.py` fails if the bundled curated catalog drops below 300 unique titles, if its schema/normalization rules regress, or if launcher-title fallback starts accepting arbitrary non-curated titles. Game-pack tests verify exact process matching. Squad telemetry has dedicated parser/privacy/staleness tests. Gamer Integrations CI also imports the catalog and runs the Game Library integration tests, while Installer QA is triggered by game activity/presence changes so Windows and Linux packaged builds are re-qualified.

## Reporting a missing or inaccurate game

For a missing game, report the game title, launcher, operating system and executable/process name if known. For inaccurate enhanced activity, include only the non-sensitive expected map/mode and whether CYBREX showed stale or missing data. Do not include account tokens, private server credentials, raw player identifiers or other secrets.
