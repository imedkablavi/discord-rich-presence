# Anti-Cheat and Game Integration Boundary

CYBREX Discord Rich Presence is a presence/telemetry client, not a game automation or modification tool.

## Counter-Strike 2

Counter-Strike 2 support uses Valve Game State Integration (GSI). CS2 writes explicitly requested game-state fields to a local HTTP endpoint configured by a `gamestate_integration_*.cfg` file. The desktop service reads that feed and turns a small subset into Discord Rich Presence.

The CS2 integration does **not**:

- inject DLLs or code into Counter-Strike 2;
- open the CS2 process to read or write memory;
- use `ReadProcessMemory`, `WriteProcessMemory`, `ptrace`, remote threads, hooks, or `LD_PRELOAD`;
- automate keyboard/mouse input;
- auto-accept matches, auto-buy, aim, recoil, movement, or other gameplay actions;
- launch CS2 with `-insecure` or weaken anti-cheat/trusted-mode settings;
- use packet interception, Game Coordinator manipulation, or undocumented lobby scraping;
- request GSI `allplayers`, positions, weapons, health, money, or grenade state for Rich Presence.

The generated GSI configuration requests only the minimum match context currently required for the feature: `provider`, `map`, `round`, `player_id`, and `phase_countdowns`. `player_id` is needed to determine the current local/observed CT/T side; identifiers received as part of that GSI component are discarded immediately and are not retained or sent to Discord.

## VAC statement

Game State Integration is a Valve-provided interface intended for external applications to consume game state. The project deliberately stays on that documented, out-of-process path.

No third-party project can promise that an account can *never* receive an anti-cheat or platform enforcement action. Valve controls VAC and can change its policies or detection systems. The relevant safety property of this project is therefore technical and auditable: the CS2 feature does not use cheat-style process access, injection, input automation, or anti-cheat bypass techniques.

A VAC ban caused by unrelated software, modified game binaries, injected overlays, cheats, automation tools, or future Valve policy changes is outside the control of this project.

## Discord

The application sends Rich Presence through the local Discord client. It does not use a user token, automate a Discord account, self-bot, scrape DMs, or impersonate Discord authentication. Rich Presence text is public to the same extent as the user's normal Discord activity sharing settings.

## Security controls

The CS2 GSI bridge:

- binds only to IPv4 loopback (`127.0.0.1`);
- uses a random per-user authentication token for GSI POSTs;
- validates Counter-Strike App ID `730`;
- limits request size and request time;
- bounds the listener queue and expires stale state;
- discards raw GSI payloads after parsing;
- does not persist Steam IDs, player names, health, money, weapons, positions, or all-player state;
- keeps token-bearing files private on POSIX where supported.

The automated QA suite also contains an anti-cheat boundary regression test. CI fails if the CS2 runtime starts using known process-memory/injection/input-automation primitives or adds common memory/automation packages.

## Contribution rule

Any future game integration that would require process-memory access, code injection, input automation, anti-cheat bypasses, packet manipulation, or undocumented private game APIs must be treated as a separate project/design decision. It must not be added silently to the Rich Presence detector path.
