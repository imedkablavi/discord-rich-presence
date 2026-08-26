# League of Legends integration

CYBREX Presence can enrich a detected League of Legends match with display-safe local context such as champion, role or position, game mode and match time.

## Data source

The integration uses Riot's local Live Client Data API exposed by the running League game client on `https://127.0.0.1:2999`. It does not require a Riot API key, account password, process-memory access, DLL injection, input automation, packet interception or overlay hooks.

To minimize collection, CYBREX requests only:

- `/liveclientdata/gamestats`
- `/liveclientdata/activeplayername`
- `/liveclientdata/playerlist`

`activeplayername` is used only in memory to identify the local player's entry in `playerlist`. The retained snapshot contains only:

- champion name
- role or position
- game mode
- current match time

CYBREX does not retain or publish Riot ID, Summoner Name, KDA, items, runes, enemy information, other-player state, hidden information or information intended to create a competitive advantage.

In Strict privacy mode the deep League telemetry path is not queried.

## Fail-closed behavior

If the local API is unavailable, returns malformed or oversized data, or the local player cannot be identified confidently, enhanced fields are omitted and CYBREX falls back to normal League of Legends game identity Presence.

## Riot notice

CYBREX Presence is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.

Distribution and use of this integration must continue to comply with Riot's current developer and product policies.
