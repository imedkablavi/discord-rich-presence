# Discord Social SDK dynamic activity-name helper

CYBREX's normal fallback transport uses Discord's legacy desktop RPC. That path can publish details, state, artwork, buttons and timestamps, but Discord may still display the registered Discord application name at the top of the card.

The optional helper in this directory uses Discord Social SDK `Activity::SetName` so the top-level activity name can follow the real current program or game, for example `Brave`, `Visual Studio Code`, or `Counter-Strike 2`.

## Trust boundary

- The official Discord Social SDK is **not vendored** in this repository.
- The helper communicates with the Python process only over its private stdin/stdout pipes.
- It does not open a localhost/network listener.
- It does not implement Discord user OAuth, access-token, refresh-token, or account-login flows.
- The helper receives only the already-sanitized Rich Presence fields used by CYBREX.
- If the helper is missing or fails, CYBREX automatically falls back to legacy RPC rather than stopping Presence.

## Maintainer build

Download the current official C++ Social SDK for the CYBREX Discord application from Discord's Developer Portal and extract it locally. Do not commit the SDK archive, libraries, credentials, or account material to this repository.

Configure and build the helper with CMake:

```bash
cmake -S native/discord_social_sdk_bridge \
  -B native/discord_social_sdk_bridge/build \
  -DDISCORD_SOCIAL_SDK_ROOT=/absolute/path/to/extracted/discord-social-sdk

cmake --build native/discord_social_sdk_bridge/build --config Release
```

The current CMake configuration expects the official SDK archive to expose `include/discordpp.h` plus the release library/runtime directories used by the Discord C++ SDK. If Discord changes its archive layout, update the CMake paths after checking the current official documentation rather than guessing or downloading third-party copies.

## Local discovery

CYBREX searches for the helper next to the packaged application, in the local source/build directories, and on `PATH`. A developer can explicitly point to a locally built helper with:

```bash
export CYBREX_DISCORD_SOCIAL_SDK_HELPER=/absolute/path/to/cybrex-discord-social-sdk
```

On Linux, keep the official Discord Social SDK runtime library next to the helper as produced by the CMake post-build step. On Windows, keep the corresponding SDK DLL next to the helper executable.

## Release requirement

Do not claim dynamic top-level activity names in a public release until the helper is built from the official SDK and validated on current Discord Desktop on both intended operating systems. Legacy RPC remains the safe fallback.
