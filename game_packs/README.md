# Community Game Packs

Game packs let contributors add conservative process fallbacks without editing Python detector code.

They are intentionally a **fallback**. Steam, Epic and Heroic local manifests are checked first and remain authoritative when they can identify the installed game.

## Schema

```json
{
  "schema": 1,
  "games": [
    {
      "name": "Example Game",
      "launcher": "Steam",
      "steam_appid": 123456,
      "processes": ["examplegame"]
    }
  ]
}
```

`steam_appid` is optional. When present it gives the fallback card trusted Steam artwork and a Steam store button.

## Matching rules

Processes are matched **exactly** after case-folding and removal of a trailing `.exe`.

Good:

```json
"processes": ["rustclient", "palworld-win64-shipping"]
```

Not supported:

- regular expressions
- wildcards
- command-line matching
- window-title scraping
- process-memory inspection
- DLL/module scanning
- network packet inspection

Exact aliases reduce false positives and keep community contributions auditable.

## Validation limits

The loader rejects or bounds:

- packs larger than 256 KiB
- unsupported schemas
- more than 512 games
- more than 24 executable aliases per game
- malformed process names
- invalid Steam AppIDs
- duplicate process aliases that would override an earlier definition

The first valid definition wins a process-name collision; later entries cannot silently replace it.

## Adding a game

Before opening a PR:

1. Verify the actual foreground executable name from a trustworthy source or real local test.
2. Prefer the game's official launcher manifest support when possible; do not add a pack entry just to duplicate reliable Steam detection.
3. Add only the executable(s) that represent the actual game, not launchers, crash reporters, anti-cheat helpers, updaters or telemetry processes.
4. If the game is on Steam, verify the AppID against the official Steam store page.
5. Add/extend regression tests when the executable could be confused with another application.

The initial pack includes conservative fallbacks for PUBG: BATTLEGROUNDS, Palworld, Rust, HELLDIVERS 2, Dead by Daylight and Delta Force.
