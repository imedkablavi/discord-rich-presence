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
- launch CS2 with `-insecure` or `-allow_third_party_software`, or weaken anti-cheat/trusted-mode settings;
- use packet interception, Game Coordinator manipulation, or undocumented lobby scraping;
- request GSI `allplayers`, positions, weapons, health, money, grenade state, player state, round events, or phase countdowns for Rich Presence.

The generated GSI configuration requests only three game-state components: `provider`, `map`, and `player_id`. `map` already supplies the map/mode/round-score context required for Rich Presence. `player_id` is needed to determine the current local/observed CT/T side; identity fields received as part of that GSI component are not retained or sent to Discord.

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
- limits request body size and request time;
- caps concurrent request workers and bounds the listener queue;
- expires and removes stale match state;
- refuses automatic CS2 configuration until its own listener has successfully bound the configured port;
- removes an auto-managed stale GSI cfg where possible if that port cannot be owned;
- discards raw GSI payloads after parsing;
- does not persist Steam IDs, player names, health, money, weapons, positions, or all-player state;
- exposes only metadata-level connection diagnostics on the unauthenticated `/v1/status` endpoint, not map/mode/team/player details;
- keeps token-bearing files private on POSIX where supported.

The automated QA suite also contains an anti-cheat boundary regression test. CI fails if the CS2 runtime starts using known process-memory/injection/input-automation primitives or adds common memory/automation packages.

## Contribution rule

Any future game integration that would require process-memory access, code injection, input automation, anti-cheat bypasses, packet manipulation, or undocumented private game APIs must be treated as a separate project/design decision. It must not be added silently to the Rich Presence detector path.
