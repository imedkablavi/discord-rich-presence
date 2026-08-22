# Discord Social SDK bridge

This optional native helper exists for one reason: Discord's Social SDK can set
`activity.name`, which allows the top line of a Rich Presence card to reflect
the current game/application instead of always showing the registered CYBREX
application name.

The existing pypresence/legacy RPC transport remains the fallback. Do not vendor
or commit Discord's proprietary SDK archive or runtime binaries to this
repository.

## Security model

The helper:

- uses Discord's documented direct Rich Presence flow (`SetApplicationId` +
  `UpdateRichPresence`) and does not call OAuth `Connect()`;
- receives already-sanitized presence fields over private stdin/stdout pipes;
- opens no TCP/UDP/listening socket;
- accepts a small allowlisted command protocol with a 16 KiB line limit;
- receives no Discord user token, password, OAuth token, Steam credential or
  browser history database;
- clears presence on an explicit `CLEAR`/`QUIT` command.

## Obtain the official SDK

1. Open the CYBREX Discord Application in the Discord Developer Portal.
2. Enable **Discord Social SDK** for that application if it is not enabled yet.
3. Open its **Downloads** page and download the latest **C++** SDK directly from
   Discord.
4. Extract it somewhere outside this repository, for example:

   - Linux: `$HOME/Downloads/discord_social_sdk`
   - Windows: `C:\Users\you\Downloads\discord_social_sdk`

The extracted directory must contain at least:

```text
include/discordpp.h
lib/release/...
bin/release/...        # Windows runtime
```

Discord documents the required runtime as `discord_partner_sdk.dll` on Windows
and `libdiscord_partner_sdk.so` on Linux.

## Build

Linux:

```bash
cmake -S native/discord_social_sdk_bridge \
  -B native/discord_social_sdk_bridge/build \
  -DDISCORD_SOCIAL_SDK_ROOT="$HOME/Downloads/discord_social_sdk" \
  -DCMAKE_BUILD_TYPE=Release
cmake --build native/discord_social_sdk_bridge/build --config Release -j
```

Windows PowerShell with Visual Studio Build Tools/CMake:

```powershell
cmake -S native/discord_social_sdk_bridge `
  -B native/discord_social_sdk_bridge/build `
  -DDISCORD_SOCIAL_SDK_ROOT="$env:USERPROFILE\Downloads\discord_social_sdk"
cmake --build native/discord_social_sdk_bridge/build --config Release
```

The CMake target copies the platform Social SDK runtime next to the helper after
a successful build.

## Manual protocol smoke test

The helper is intentionally not a general command shell. It accepts one
percent-encoded, tab-separated command per line:

```text
PING
SET_APP application_id=<public Discord application id>
UPDATE name=Firefox details=Browsing ...
CLEAR
QUIT
```

The Python service generates these commands through `social_sdk_protocol.py`;
normal users should not need to type them manually.

## Distribution note

Before packaging this helper into public releases, confirm Discord's current
Social SDK distribution/license requirements and test the exact official SDK
version on Windows and Linux. Linux support is currently marked experimental by
Discord, so legacy RPC remains an important fallback there.
