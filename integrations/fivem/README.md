# FiveM Enhanced Presence

CYBREX can enrich a normal FiveM game card with a small amount of server context through the optional `cybrex_presence` resource in this directory.

## Privacy model

The resource intentionally sends only:

- server display name
- current player count
- configured maximum player count
- an optional `https://cfx.re/join/...` URL

It does **not** send player names, player identifiers, licenses, Steam IDs, jobs, inventory, money, position, vehicle, voice data, chat, framework state, or other server-specific gameplay data.

The desktop application binds the receiver to `127.0.0.1` only and accepts the NUI origin for this resource. Snapshots expire quickly. By default the desktop app hides the server name and does not publish a Join button.

## Server installation

Copy `cybrex_presence/` into the server's resources directory and add:

```cfg
ensure cybrex_presence
```

Optional server settings:

```cfg
# Optional public Cfx join URL. Leave empty to disable it.
set cybrex_join_url "https://cfx.re/join/yourcode"

# Only needed when the CYBREX desktop bridge uses a non-default port.
setr cybrex_presence_port 32193
```

The resource is optional for players. If CYBREX is not installed or is not running, the NUI bridge silently drops the local request and does not interfere with gameplay.

## Desktop privacy options

These settings are intentionally opt-in where they can reveal a specific community:

```yaml
fivem:
  port: 32193
  ttl_secs: 15
  show_server_name: false
  show_player_count: true
  allow_join_button: false
```

`show_server_name` and `allow_join_button` should be enabled by the player, not forced by a server.

## Presence examples

Default privacy:

```text
FiveM
42/128 players
```

With server-name sharing enabled:

```text
FiveM
Los Santos Roleplay · 42/128 players
```

When the player also enables the Join button and the server provides a valid `cfx.re` join URL, CYBREX can expose that URL as a Discord activity button.
