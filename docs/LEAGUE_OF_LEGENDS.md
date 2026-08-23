# League of Legends integration

CYBREX Rich Presence can enrich a detected League of Legends match with display-safe local context such as the champion, role/position and game mode.

## Data source

The integration uses Riot's documented **Live Client Data API** exposed by the running League game client on `https://127.0.0.1:2999`. It does not require a Riot API key, Riot Sign On, account password, process-memory access, DLL injection, input automation, packet interception or an overlay hook.

To minimize collection, CYBREX requests only:

- `/liveclientdata/gamestats`
- `/liveclientdata/activeplayername`
- `/liveclientdata/playerlist`

`activeplayername` is used only in memory to identify which entry in `playerlist` belongs to the local player. The retained snapshot contains only:

- champion name
- role/position
- game mode
- current match time

CYBREX does **not** retain or publish Riot ID, Summoner Name, KDA, items, runes, enemy information, other-player state, hidden information or information intended to create a competitive advantage.

## Fail-closed behavior

If the local API is unavailable, returns malformed/oversized data, or the local player cannot be identified confidently, the enhanced fields are omitted and CYBREX falls back to the normal `League of Legends · Riot Client` presence.

## Riot notice

CYBREX Rich Presence is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.

Before distributing the League integration as a player-facing production product, the project owner should review Riot's current Developer API Policy and product-registration requirements and register/update the product in the Riot Developer Portal as required.
