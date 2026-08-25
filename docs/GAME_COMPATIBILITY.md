# Game Compatibility

CYBREX Presence has two distinct levels of game support. Keeping them separate avoids misleading compatibility claims.

## Standard game support

The desktop app identifies installed/foreground games from local metadata where possible. Steam, Epic Games and Heroic are metadata-driven, so support is not limited to a hardcoded list: a game can work even when its title is not present in this repository's curated catalog.

For release QA and product documentation, CYBREX also ships a curated compatibility catalog containing **346 popular titles** across Steam-heavy, cross-launcher and current-2026 targets. The source of truth is:

- `game_packs/popular_catalog.json`
- `game_packs/popular_cross_launcher.json`
- `game_packs/popular_2026.json`

The catalog includes representative titles such as Counter-Strike 2, Dota 2, GTA V, ELDEN RING, Baldur's Gate 3, Fortnite, VALORANT, League of Legends, Minecraft, Roblox, World of Warcraft, Diablo IV, Rocket League, Genshin Impact, Deadlock, PEAK and EA SPORTS FC 26.

A title being in the curated catalog means it is an explicit compatibility/QA target. It does **not** mean every launcher, operating system, game version or storefront build has been manually tested on real hardware.

## Enhanced support

Enhanced support is narrower and may add safe live context through a documented local interface or companion. Current examples include Counter-Strike 2 GSI, League of Legends Live Client data, FiveM's optional loopback companion and Minecraft's optional Fabric companion.

Enhanced support must not be inferred from membership in the 346-title catalog.

## Detection order

1. Resolve Steam from local Steam manifests/library metadata.
2. Resolve Epic Games from local Epic manifest metadata.
3. Resolve Heroic/Legendary from local Heroic metadata.
4. Consult the validated Community Game Pack for conservative exact-process fallbacks.
5. Apply the small built-in verified process aliases for known games/launchers.
6. When the foreground process is a known launcher and local catalog resolution was unavailable, accept its window title only when it is a known alias or an **exact normalized match** to the curated 346-title catalog.

Launcher metadata remains authoritative over all fallback aliases and title matching. Generic launcher pages such as Store, Library, News and arbitrary promotional window titles fail closed and are not reported as games.

## Safety boundary

CYBREX Presence does not need game-memory reading, DLL/code injection, anti-cheat bypasses, packet interception or input automation to provide standard game Presence. Community Game Packs use exact normalized process names only; regex/wildcard process scanning and arbitrary command execution are not part of the pack format.

## Why the catalog is separate from process matching

Hardcoding hundreds of guessed executable names would create false positives and would age badly as games update. The curated catalog therefore records supported product targets, while runtime detection uses authoritative local launcher metadata whenever available. Exact process aliases are added only when they are known and useful as a fallback. The launcher-title fallback also requires an exact curated title rather than substring matching.

## CI contract

`tests/test_popular_games.py` fails if the bundled curated catalog drops below 300 unique titles, if its schema/normalization rules regress, or if launcher-title fallback starts accepting arbitrary non-curated titles. Gamer Integrations CI also imports the catalog and runs the Game Library integration tests.

## Reporting a missing game

If a game is not detected, report the game title, launcher, operating system and executable/process name if known. Do not include account tokens, private server credentials or other secrets. A process fallback should only be added after the executable identity is verified and shown not to collide with a launcher/helper/anti-cheat process.
