# Minecraft Enhanced Presence

CYBREX includes an optional Fabric client companion for Minecraft Java Edition. The current source target is **Minecraft 26.2**, Fabric Loader **0.19.3**, Fabric API **0.156.0+26.2**, and Java **25**.

The companion exists because process/window detection can identify Minecraft, but it cannot safely know the current dimension or multiplayer/singleplayer context without game cooperation.

## Privacy model

The Fabric companion sends a small JSON snapshot to `127.0.0.1` only:

- `Singleplayer` or `Multiplayer`
- dimension resource identifier, for example `minecraft:overworld`
- optional server display name

It does **not** read or send:

- Minecraft username or UUID
- server IP/address
- chat or command history
- coordinates
- world seed
- inventory/items
- health, hunger, XP, entities or nearby players
- authentication/session tokens
- screenshots

Server-name sharing has two gates and is disabled at both layers by default:

1. Fabric companion: `send_server_name=false`
2. Desktop app: `minecraft.show_server_name=false`

So a server label is not transmitted out of the game at all unless the Fabric setting is explicitly enabled, and the desktop still refuses to publish it unless its own setting is enabled.

## Build

The repository builds the companion in GitHub Actions. To build it locally, install JDK 25 and Gradle 9.5.1, then run:

```bash
cd integrations/minecraft/fabric-26.2
gradle --no-daemon build
```

The main remapped JAR is created under `build/libs/`.

## Install

Install Fabric Loader and Fabric API for Minecraft 26.2, then place the built `CYBREX-Minecraft-Companion-26.2-*.jar` in the normal Minecraft `mods/` folder.

The mod creates:

```text
config/cybrex-presence.properties
```

with privacy-safe defaults:

```properties
port=32194
send_server_name=false
```

The port must match the desktop bridge when a custom port is used.

## Desktop settings

The desktop defaults are equivalent to:

```yaml
minecraft:
  port: 32194
  ttl_secs: 15
  show_server_name: false
```

No companion is required for basic Minecraft detection. Without the Fabric JAR, CYBREX still shows Minecraft when the foreground Java window is explicitly a Minecraft window, but the card remains generic.

## Presence examples

Default multiplayer presence:

```text
Minecraft
Multiplayer · Overworld
```

Singleplayer in the Nether:

```text
Minecraft
Singleplayer · Nether
```

With server-name sharing enabled at both layers:

```text
Minecraft
Multiplayer · Overworld · Example SMP
```
