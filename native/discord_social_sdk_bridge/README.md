# Discord Social SDK dynamic activity-name helper

CYBREX's normal fallback transport uses Discord's legacy desktop RPC. That path can publish details, state, artwork, buttons and timestamps, but Discord may still display the registered Discord application name at the top of the card.

The optional helper in this directory uses Discord Social SDK `Activity::SetName` so the top-level activity name can follow the real current program or game, for example `Brave`, `Visual Studio Code`, or `Counter-Strike 2`.

## Trust boundary

- The raw official Discord Social SDK archive is **not vendored** in this repository.
- The helper communicates with the Python process only over private stdin/stdout pipes.
- It does not open a localhost/network listener.
- It does not implement Discord user OAuth, access-token, refresh-token, or account-login flows. Direct desktop Rich Presence does not require those flows.
- The helper receives only the already-sanitized Rich Presence fields used by CYBREX.
- Unknown protocol fields are rejected.
- If an asynchronous Rich Presence update times out, the helper recreates its SDK client before accepting another update so pending native callback state cannot grow without bound.
- If the helper is missing or fails, CYBREX automatically falls back to legacy RPC rather than stopping Presence.

## Maintainer build

Download the current official standalone C++ Social SDK for the CYBREX Discord application from Discord's Developer Portal and extract it locally. Do not commit the SDK archive, SDK libraries, credentials, or account material to this repository.

The preferred build/staging command is:

```bash
python scripts/build_social_sdk_bridge.py \
  --sdk-root /absolute/path/to/discord_social_sdk \
  --sdk-version 1.10.18687 \
  --output-dir build/social-sdk-bundle
```

The script validates `discordpp.h`, `cdiscord.h`, the platform runtime, linker input and `License-Notices.txt`, builds the helper with CMake, then stages only:

- `cybrex-discord-social-sdk` / `cybrex-discord-social-sdk.exe`
- `libdiscord_partner_sdk.so` / `discord_partner_sdk.dll`
- `Discord-Social-SDK-Notices.txt`
- `SOCIAL_SDK_MANIFEST.json` with SHA-256 and size metadata

The current bridge API was compile-validated against Discord Social SDK **1.10.18687**. This is a build compatibility statement, not a claim that every Discord Desktop/environment combination has been manually qualified.

## One-file packaging

Official CYBREX builds can set:

```bash
export CYBREX_SOCIAL_SDK_BUNDLE_DIR="$PWD/build/social-sdk-bundle"
pyinstaller --clean --noconfirm discord-rich-presence.spec
```

The PyInstaller spec embeds the verified helper and Discord runtime inside the normal single CYBREX executable. At runtime PyInstaller extracts them together under its private runtime directory, and `social_sdk_transport.py` discovers the helper there first. This preserves the existing single-file installer and updater model; users do not need to manage a separate SDK installation.

A build without `CYBREX_SOCIAL_SDK_BUNDLE_DIR` remains valid and falls back to legacy RPC. A build that sets the variable but provides an incomplete bundle fails closed during packaging.

## Local development discovery

A developer can also explicitly point CYBREX to a locally built helper with:

```bash
export CYBREX_DISCORD_SOCIAL_SDK_HELPER=/absolute/path/to/cybrex-discord-social-sdk
```

On Linux, keep `libdiscord_partner_sdk.so` next to the helper. On Windows, keep `discord_partner_sdk.dll` next to the helper executable.

## Release requirement

Do not promote a Stable release as supporting dynamic top-level activity names until the helper is built from the official SDK and manually validated with current Discord Desktop on both intended operating systems. Legacy RPC remains the safe fallback.
