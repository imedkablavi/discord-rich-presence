<div align="center">

# CYBREX Presence

**Automatic Discord Rich Presence for games, browsers, social web apps, coding, terminals, media and desktop applications on Windows and Linux.**

[![QA](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/qa.yml/badge.svg)](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/qa.yml)
[![Gamer Integrations](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/gamer-integrations.yml/badge.svg)](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/gamer-integrations.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Windows + Linux](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](#download)

[**Downloads**](https://github.com/imedkablavi/discord-rich-presence/releases) · [**Game compatibility**](docs/GAME_COMPATIBILITY.md) · [**Privacy**](docs/PRIVACY.md) · [**Report a bug**](https://github.com/imedkablavi/discord-rich-presence/issues/new/choose)

</div>

CYBREX Presence detects the activity you are actually using and updates Discord automatically. Normal users do not need to create a Discord application or paste account credentials. Detection runs locally and the project does not operate an activity telemetry backend.

<p align="center">
  <img src="docs/images/control-panel.png" alt="CYBREX Presence control panel" width="820">
</p>

<p align="center">
  <img src="docs/images/activity.png" alt="CYBREX Presence activity on Discord" width="520">
</p>

## Download

Official builds are published only through [GitHub Releases](https://github.com/imedkablavi/discord-rich-presence/releases).

### Windows

Recommended asset:

```text
CYBREX-Presence-Setup.exe
```

A portable `DiscordRichPresence.exe` is also published. The normal installer is per-user and does not require administrator rights for its standard install path.

Stable Windows releases are blocked by release policy unless Authenticode signing is configured and verified. A clearly marked prerelease may be unsigned and can trigger Windows SmartScreen. Every published desktop asset includes SHA-256 verification data.

### Linux x86_64

Recommended asset:

```text
CYBREX-Presence-linux-x86_64.tar.gz
```

Install for the current user:

```bash
tar -xzf CYBREX-Presence-linux-x86_64.tar.gz
cd CYBREX-Presence-linux-x86_64
./install-user.sh
```

No `sudo` is required. The installer places the application under `~/.local`, creates a `cybrex-presence` command and desktop entry, and keeps the executable user-owned so verified in-app updates can replace it.

Uninstall while keeping configuration and logs:

```bash
./install-user.sh --uninstall
```

A portable `CYBREX-DiscordRichPresence-linux-x86_64` binary is also published.

See [Download and integrity verification](docs/DOWNLOAD.md).

## What it can show

Examples depend on the active integration and privacy mode.

```text
Counter-Strike 2
Competitive · Mirage · Counter-Terrorists · CT 8–6 T
```

```text
War Thunder
Ground · T 80bvm · In Battle
```

```text
League of Legends
Ahri · Mid · Summoner's Rift
```

```text
Minecraft
Multiplayer · Overworld
```

```text
Using Instagram
Instagram · Firefox
```

```text
Visual Studio Code
Working in Python · main.py
```

CYBREX does not invent live game fields when a trustworthy source is unavailable. Standard game detection and enhanced live telemetry are documented separately.

## Supported integrations

| Integration | Detection | Enhanced state |
| --- | --- | --- |
| Steam | Local manifests and library metadata | Per-game metadata where available |
| Epic Games | Local launcher metadata | Standard game presence |
| Heroic / Legendary | Local launcher metadata | Standard game presence |
| Counter-Strike 2 | Steam / exact game identity | Valve GSI map, mode, team and score context |
| League of Legends | Game identity | Riot local Live Client data |
| War Thunder | Steam AppID or exact client process | Bounded local `127.0.0.1:8111` telemetry for branch, vehicle label and battle state |
| Squad | Steam AppID or exact game process | Bounded read-only local log enrichment when evidence is current |
| FiveM | Game identity | Optional loopback companion for minimal server/session context |
| Minecraft Java | Game identity | Optional Fabric companion for mode and dimension |
| Browser Companion | Chromium-family browsers and Firefox | Focused service/tab/media context locally |
| Social web apps | Browser Companion or conservative title fallback | Generic privacy-safe service presence |
| Spotify / media | Local media APIs | Playback metadata where available |
| Coding / terminals | Foreground detection | Editor, workspace, language and shell context |
| Community Game Packs | Exact process fallback | Standard game presence |

The curated game catalog contains more than 300 compatibility targets, but catalog membership is not a claim that every title has deep telemetry or every hardware/storefront combination has been manually tested. See [Game Compatibility](docs/GAME_COMPATIBILITY.md).

## Game integration boundary

Enhanced game support remains read-only and outside the game process. CYBREX does not use DLL injection, process-memory reading, input automation, packet interception, anti-cheat bypasses or credential emulation to enrich Presence.

War Thunder enrichment reads only fixed local HTTP telemetry with bounded response size, short timeouts and a short cache. Tactical map objects, chat and HUD/damage streams are not used. If local telemetry is unavailable or invalid, Presence falls back to normal War Thunder game identity.

Counter-Strike 2 uses Valve GSI. League uses Riot's local Live Client Data API. FiveM and Minecraft use optional local companions. Squad uses bounded, high-confidence local log evidence. Details and limits are in [Game Compatibility](docs/GAME_COMPATIBILITY.md) and [Anti-Cheat Boundary](docs/ANTI_CHEAT.md).

## Browser Companion

The optional Browser Companion improves focused-tab and browser-media accuracy. It communicates only with the local desktop bridge on `127.0.0.1:32191` by default.

Social and messaging services use a stricter contract than ordinary web pages. CYBREX reduces recognized services such as WhatsApp, Instagram, Facebook, Messenger, LinkedIn, Threads, TikTok, Telegram, Snapchat, Discord Web, Pinterest, Bluesky, X and Reddit to generic service state before the Discord payload is built.

Conversation names, contact names, profile/post identifiers, deep social URLs and social-page media metadata are not published to Discord.

See [Browser Companion](browser_extension/README.md) and [Social Web Presence](docs/SOCIAL_PRESENCE.md).

## Privacy

Privacy modes:

| Mode | Behavior |
| --- | --- |
| `off` | Minimal project-side redaction |
| `balanced` | Default. Keeps useful context with secret, path and URL reduction |
| `strict` | Generic activity. Identifying browser links/buttons are removed and deep game telemetry collection is suppressed |

Additional controls include loopback-only companion listeners, bounded in-memory records, secret/path redaction, conservative foreground matching, short state TTLs and logs that avoid complete Rich Presence payloads.

See [Privacy](docs/PRIVACY.md) and [Security](SECURITY.md).

## Discord transport and dynamic app names

CYBREX supports two desktop transport paths:

- **Discord Social SDK helper**, when an official SDK-built helper is included in the package. This path can set the top-level activity name to the real program or game.
- **Legacy Discord RPC fallback**, which keeps Presence working when the helper is unavailable but may show the registered CYBREX Discord application name at the top of the card.

The Social SDK helper does not use Discord user OAuth tokens, bot tokens, access tokens or a network listener. It communicates with the Python application over private stdin/stdout pipes and falls back to legacy RPC on failure.

See [Social SDK helper](native/discord_social_sdk_bridge/README.md).

## Linux desktop support

| Environment | Foreground detection |
| --- | --- |
| KDE Plasma Wayland | `kdotool` |
| Sway | `swaymsg` |
| X11 desktops | `xprop` |

Linux media detection uses `playerctl` when available. If a compositor does not expose a trustworthy foreground-window API, CYBREX returns no foreground activity instead of guessing from unrelated running processes.

## Updates

Packaged builds support Stable and Preview update channels. Update checks use published GitHub Release metadata. Installation requires the expected platform asset and checksum, applies download bounds and refuses invalid or unsafe release data.

The application never installs an update silently. Users can check or install from **About > Updates**, the tray menu or the command line:

```text
--check-update
--update
```

See [Application Updates](docs/UPDATES.md).

## Configuration

Default configuration paths:

```text
Windows: %APPDATA%\discord-rich-presence\config.yaml
Linux:   ~/.config/discord-rich-presence/config.yaml
```

Normal users should leave `discord.application_id_override` empty. Advanced users maintaining their own Discord application can configure an override deliberately.

See [config.example.yaml](config.example.yaml) for the full schema.

## Development

Requirements:

- Python 3.10+
- Discord Desktop for live Rich Presence testing

Windows:

```powershell
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python launcher.py --gui
```

Linux:

```bash
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python launcher.py --gui
```

Run one local cycle without publishing to Discord:

```bash
python main.py --dry-run --once --verbose
```

Run the test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q .
ruff check . --select E9,F63,F7,F82
pytest -q
```

## Contributing

Use the structured issue forms for bugs, missing games and integration requests. Conservative game fallbacks can be added through Community Game Packs without changing Python detector code.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Current limits

- macOS foreground-window support is not implemented.
- Wayland support depends on compositor APIs that can identify the real foreground application.
- Legacy Discord RPC cannot guarantee a dynamic top-level activity name.
- Some integrations depend on optional local tools, companions or game-provided APIs.
- Automated CI cannot prove every real Discord Desktop, game, launcher, compositor or hardware combination.

## License

MIT. See [LICENSE](LICENSE).

<div align="center">

Built by CYBREX@TECH · https://imedkablavi.info

</div>
