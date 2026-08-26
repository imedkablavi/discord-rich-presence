# Game Compatibility

CYBREX Presence separates standard game identity from enhanced game telemetry. Detecting that a game is running is not the same as knowing its current map, server, mode or match state.

## Standard support

Steam, Epic Games and Heroic are resolved from local launcher metadata where possible. Support is therefore not limited to a hardcoded executable list.

The bundled curated catalog contains more than 300 popular compatibility targets. Catalog membership means the title is an explicit detection and QA target. It does not mean every launcher, storefront, operating-system build or hardware combination has been manually tested, and it does not imply live match telemetry.

Launcher metadata remains authoritative. Community Game Packs use exact normalized process names as a conservative fallback. Generic launcher pages, store pages, news and unrelated window titles fail closed.

## Accuracy tiers

### Tier 1: game identity

Standard Presence can include canonical game name, launcher/source, Steam artwork or store link when available and elapsed activity time.

CYBREX does not invent map, server or mode values for Tier 1 games.

### Tier 2: bounded local metadata

A game may expose reliable local state without requiring account credentials or game-memory access.

**Squad** can use a bounded read of recent local `SquadGame.log` data while the game is foreground. Map/layer/mode are published only from high-confidence current evidence. Server name or population is used only when current session evidence exists in the same recent window. IP addresses, account identifiers and tokens are excluded.

**War Thunder** is recognized through Steam AppID `236390` or conservative exact client process names. While War Thunder is foreground and Strict privacy is not active, CYBREX reads only fixed local `127.0.0.1:8111` endpoints used by the integration. Requests have sub-second timeouts, a 64 KiB response cap, connection-close semantics and a short cache. Presence may include Ground/Air/Naval/Helicopter branch, a conservative vehicle label and mission running/loading state.

War Thunder tactical map objects, chat and HUD/damage streams are not used. CYBREX does not invent map or server identity from local data that cannot support that claim. Invalid or unavailable telemetry falls back to Tier 1 game identity.

### Tier 3: documented live integration

| Game / platform | Source | Live fields when available |
| --- | --- | --- |
| Counter-Strike 2 | Valve Game State Integration on authenticated loopback | map, mode, team and score context |
| League of Legends | Riot local Live Client Data API | local-player match context |
| FiveM | optional CYBREX loopback companion | minimal server/session context |
| Minecraft Java | optional CYBREX Fabric companion | mode and dimension; server label only when explicitly enabled |
| Squad | bounded read-only local game log | map/layer/mode and current server context when evidence is strong |
| War Thunder | bounded read-only local HTTP telemetry | branch, conservative vehicle label and mission state |

Enhanced support is narrower than the broad compatibility catalog.

## Detection order

1. Resolve Steam from local manifests and library metadata.
2. Resolve Epic Games from local launcher metadata.
3. Resolve Heroic/Legendary from local metadata.
4. Keep launcher boundaries explicit so a launcher such as `MinecraftLauncher` is not mistaken for the game.
5. Consult validated Community Game Packs for exact-process fallbacks.
6. Apply a small set of built-in verified process aliases.
7. For a known launcher with unavailable local catalog resolution, accept a window title only when it exactly matches a known curated title or alias.
8. Apply game-specific enrichment only after game identity is established.

Enrichment failure never turns a correctly detected game into a false negative.

## Safety boundary

CYBREX game Presence does not require process-memory reading, DLL/code injection, anti-cheat bypasses, packet interception or input automation.

Game-specific integrations follow these rules:

- prefer official or documented local APIs
- otherwise use bounded read-only local files only with high-confidence markers
- do not require account/session tokens solely for richer Presence
- do not publish IP addresses, account IDs, auth tokens or private server credentials
- do not guess map/server state from stale or ambiguous evidence
- fail soft to game identity when richer data is unavailable
- Strict privacy suppresses deep telemetry collection at the source

See [Anti-Cheat and Game Integration Boundary](ANTI_CHEAT.md).

## Curated catalog

The source data is stored in:

```text
game_packs/popular_catalog.json
game_packs/popular_cross_launcher.json
game_packs/popular_2026.json
```

Representative targets include Counter-Strike 2, Dota 2, GTA V, ELDEN RING, Baldur's Gate 3, Fortnite, VALORANT, League of Legends, Minecraft, Roblox, World of Warcraft, Diablo IV, Rocket League, Genshin Impact, Squad, War Thunder, Deadlock, PEAK and EA SPORTS FC 26.

## Reporting an inaccurate game

For a missing game, report the game title, launcher, operating system and executable/process name if known. For enhanced activity issues, include only the non-sensitive expected context and what CYBREX displayed. Do not include account tokens, private server credentials or raw player identifiers.
