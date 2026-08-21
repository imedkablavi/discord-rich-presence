# Counter-Strike 2 Rich Presence

Counter-Strike 2 can provide live match context through Valve Game State Integration (GSI). CYBREX Discord Rich Presence uses that official, read-only feed instead of reading game memory or injecting code into the game.

## What Discord can show

When CS2 is the detected game and a fresh GSI snapshot is available, Rich Presence can show:

- Counter-Strike 2 as the game;
- the current game mode, such as Competitive, Casual, Deathmatch, or Wingman;
- the current map, such as Mirage, Dust II, Inferno, Nuke, Ancient, or Anubis;
- the local side: Counter-Terrorists or Terrorists;
- the current CT/T round score.

Example:

```text
Playing · Counter-Strike 2
Competitive · Mirage · Counter-Terrorists · CT 8–6 T
```

If GSI is not configured or the latest snapshot has expired, ordinary foreground-game detection still reports Counter-Strike 2 without the live match fields.

## Zero-setup path

When the desktop service starts, it checks common Steam library locations. If it finds Counter-Strike 2 and the game configuration directory is writable, it prepares:

```text
game/csgo/cfg/gamestate_integration_cybrex.cfg
```

The generated integration points only to the local IPv4 loopback listener:

```text
http://127.0.0.1:32192/v1/cs2
```

The integration uses a random per-user authentication token. If the GSI file is created while CS2 is already running, restart CS2 once so the game loads the new integration configuration.

## Manual setup fallback

From a source checkout:

```bash
python scripts/install-cs2-gsi.py
```

To see detected installations first:

```bash
python scripts/install-cs2-gsi.py --list
```

For a non-standard installation, pass the exact `game/csgo/cfg` directory:

```bash
python scripts/install-cs2-gsi.py --cfg-dir "/path/to/Counter-Strike Global Offensive/game/csgo/cfg"
```

The discovery code supports common Windows Steam locations, native Linux Steam locations, additional Steam libraries listed in `libraryfolders.vdf`, and the common Flatpak Steam path.

## Diagnostics

Start the service and look for:

```text
CS2 GSI listening on http://127.0.0.1:32192/v1/cs2
```

The listener has privacy-safe local diagnostics:

```bash
curl -s http://127.0.0.1:32192/v1/health
curl -s http://127.0.0.1:32192/v1/status
```

`/v1/status` reports only connection age plus map/mode/local side. It does not expose the authentication token, Steam ID, player name, weapons, money, health, positions, or other players.

## Data minimization

The generated GSI configuration requests only:

- `provider`;
- `map`;
- `round`;
- `player_id`;
- `phase_countdowns`.

It intentionally does **not** request `allplayers`, player weapons, or player state. The desktop bridge additionally discards fields it does not need after parsing. In particular it does not retain player names, Steam IDs, health, money, weapons, positions, all-player state, or team names.

The listener binds to `127.0.0.1`, uses a random local authentication token, limits request sizes, applies socket timeouts, and expires stale game state automatically.

## Supported mode labels

Known internal mode names are normalized for Discord, including Competitive, Casual, Deathmatch, Wingman, Arms Race, Demolition, Danger Zone, Training, and Custom. Unknown modes are converted to a readable title instead of being discarded.

Known map identifiers receive friendly names. Unknown or workshop map identifiers are normalized automatically so custom maps can still appear without a project update.
