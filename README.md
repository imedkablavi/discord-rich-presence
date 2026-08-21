# Discord Rich Presence Service

[![QA](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/qa.yml/badge.svg)](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/qa.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Windows + Linux](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/imedkablavi/discord-rich-presence)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

A local Discord Rich Presence service for coding, browsers, media, terminals, games, and normal desktop applications.

It watches local activity, applies privacy rules, chooses the most relevant activity, and publishes the result through Discord Desktop RPC. There is no CYBREX telemetry or activity-history backend.

## Screenshots

| Control Panel | Discord Activity |
| :---: | :---: |
| ![Control Panel](docs/images/control-panel.png) | ![Activity Detection](docs/images/activity.png) |
| Control panel and service status | Rich Presence in Discord |

## Highlights

- No Discord Developer Portal setup is required for normal users.
- Windows and Linux support with packaged release artifacts.
- KDE Plasma Wayland support through `kdotool`, plus X11 and Sway support.
- Windows Media Control and Linux MPRIS/playerctl integration.
- Smart activity priority so background media does not unnecessarily hide foreground coding or terminal work.
- Optional Browser Companion for exact tab/service/media context.
- Balanced, strict, and unfiltered privacy modes.
- Application-aware artwork with configurable Discord asset-key fallbacks.
- Local terminal command hooks with secret redaction and short-lived private cache files.
- Single-instance runtime guard, graceful shutdown, hot configuration reload, and bounded caches.

## What it detects

| Category | Examples |
| --- | --- |
| Coding | VS Code, VSCodium, Trae, JetBrains IDEs, Vim/Neovim, Sublime Text, Notepad++ |
| Browsers | Chrome, Firefox, Edge, Brave, Chromium, Opera, Vivaldi |
| Media | Spotify, VLC, MPV, browser media, Windows media sessions, Linux MPRIS |
| Terminal | Bash, Zsh, PowerShell, Windows Terminal, CMD and supported terminal emulators |
| Gaming | Known game processes with conservative matching |
| Applications | Optional foreground-app fallback |

Playing media uses Discord timestamps so elapsed/remaining time advances without rewriting the RPC payload every second.

## Browser Companion

The optional Browser Companion improves browser accuracy by sending the active tab title, URL, focus/visibility state, recognized service, and HTML media metadata to a loopback-only bridge on `127.0.0.1`.

It is useful when Chromium MPRIS does not expose enough information to distinguish a background YouTube tab from the foreground browser tab.

The desktop service keeps only a small, short-lived in-memory snapshot set. Normal web-page origins are rejected by the bridge, requests require the Companion marker header, request/body sizes are bounded, and the project does not upload browser history to a CYBREX server.

To prepare a clean unpacked extension directory on Linux:

```bash
bash scripts/prepare-browser-companion.sh
```

Then load the generated directory through the browser's extension page. See [browser_extension/README.md](browser_extension/README.md) for Chromium/Brave/Edge and Firefox instructions.

### Browser URL privacy

Balanced mode defaults to sharing only the URL origin, for example `https://www.youtube.com`.

```yaml
privacy:
  browser_url_mode: domain
```

Supported values are `none`, `domain`, `path`, and `full`. Query values that look like credentials/tokens are redacted, fragments are removed, and strict mode removes identifying browser URLs.

## Privacy

| Mode | Behavior |
| --- | --- |
| `off` | Keeps detected activity without project-side redaction. |
| `balanced` | Redacts sensitive patterns and reduces browser/path exposure. Default. |
| `strict` | Uses generic descriptions and removes identifying URLs/buttons. |

Rich Presence is cleared when activity disappears, becomes blocked, or a supported lock-screen window is detected.

Terminal commands are optional. PID-scoped cache files are matched to the focused terminal where possible, sensitive command flags are redacted, and the default raw command cache lifetime is only 15 minutes.

On POSIX systems, configuration/runtime/log/cache directories and sensitive files are hardened to user-only permissions. Persistent logs intentionally avoid writing full Rich Presence payloads containing page titles, commands, buttons, or URLs.

See [docs/PRIVACY.md](docs/PRIVACY.md) for the detailed data-flow and file locations.

## Windows

### Packaged release

Tagged releases publish:

```text
DiscordRichPresence.exe
DiscordRichPresence.exe.sha256
CYBREX-Browser-Companion.zip
CYBREX-Browser-Companion.zip.sha256
```

The EXE contains the service, tray controls, and control panel. A SHA-256 checksum is included for integrity verification.

[Open Releases](https://github.com/imedkablavi/discord-rich-presence/releases)

Windows Authenticode signing is supported by the release workflow when the repository has a valid code-signing certificate configured. Unsigned development builds may still trigger Windows SmartScreen.

### Run from source

Requirements:

- Python 3.10+
- Discord Desktop

```bat
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
run.bat
```

`run.bat` creates/repairs the virtual environment, verifies runtime packages, and starts the service.

## Linux

Tagged releases also publish:

```text
CYBREX-DiscordRichPresence-linux-x86_64
CYBREX-DiscordRichPresence-linux-x86_64.sha256
```

For source installations, requirements are:

- Python 3.10+
- Discord Desktop
- X11: `xprop`
- KDE Plasma Wayland: `kdotool`
- Sway: `swaymsg`
- Media: `playerctl` recommended

```bash
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

KDE Plasma Wayland uses `kdotool`; Sway uses `swaymsg`. Unsupported Wayland compositors return no foreground activity rather than guessing from unrelated processes.

## Configuration

Configuration paths:

- Windows: `%APPDATA%\discord-rich-presence\config.yaml`
- Linux: `~/.config/discord-rich-presence/config.yaml`

Normal users do **not** need to create a Discord application or copy a Developer ID. The project includes its public Discord Application ID. A custom application ID is an advanced override only.

```yaml
discord:
  application_id_override: ""
  buttons: []

privacy:
  mode: balanced
  browser_url_mode: domain
  hide_home_paths: true

update_interval_secs: 2

browser_companion:
  enabled: true
  port: 32191
  ttl_secs: 15
  domain_services: {}

images:
  use_external_app_icons: true
  icon_overrides: {}

rules:
  clear_on_lock_screen: true
  terminal_command_ttl_secs: 900
  activity_priority:
    policy: smart
    custom_order:
      - gaming
      - terminal
      - coding
      - browser
      - media
      - application
```

The full example is in [config.example.yaml](config.example.yaml).

### Activity priority

`rules.activity_priority.policy` supports:

- `smart` — foreground work beats background media; foreground media still wins.
- `foreground_first` — terminal/coding/browser is preferred to background media.
- `media_first` — media receives the old high priority.
- `custom` — use `custom_order`.

### Custom/self-hosted services

The Companion can map private or self-hosted domains without custom JavaScript:

```yaml
browser_companion:
  domain_services:
    media.home.example: "Jellyfin"
    "*.corp.example": "Company Portal"
```

### Artwork

Known apps can use external raster artwork URLs where supported by the Discord client. If external images are unreliable in your client, disable them and use Discord Developer Portal asset keys instead:

```yaml
images:
  use_external_app_icons: false
```

Specific apps can be overridden with either an asset key or direct image URL:

```yaml
images:
  icon_overrides:
    trae: "my-trae-asset"
    konsole: "https://example.com/konsole.png"
```

## Control panel

The control panel can start/stop the service, change privacy settings, edit common configuration, inspect current runtime status, test Discord RPC, and open local logs.

A per-user runtime lock prevents multiple service processes from fighting over Discord RPC. GUI/tray shutdown requests are graceful so the activity, RPC connection, Browser Companion server, and local runtime state can close cleanly.

## Terminal command tracking

Terminal command tracking is optional.

### Bash

```bash
source /path/to/discord-rich-presence/scripts/hooks/bash.sh
```

### Zsh

```zsh
source /path/to/discord-rich-presence/scripts/hooks/zsh.zsh
```

### PowerShell

```powershell
. "C:\path\to\discord-rich-presence\scripts\hooks\powershell.ps1"
```

The supplied hooks preserve existing prompt/history integrations instead of replacing them.

## Command line

```text
python main.py [--config PATH] [--privacy off|balanced|strict]
               [--dry-run] [--once] [--verbose] [--tray]
```

Useful local diagnostic:

```bash
python main.py --dry-run --once --verbose
```

The full payload is printed to the interactive terminal for explicit dry-run debugging, while persistent rotating logs keep only non-sensitive protocol metadata.

## Local files

### Windows

- Config: `%APPDATA%\discord-rich-presence\config.yaml`
- Logs: `%LOCALAPPDATA%\discord-rich-presence\logs\app.log`
- Runtime: `%LOCALAPPDATA%\discord-rich-presence\runtime\`
- Terminal cache: `%LOCALAPPDATA%\discord-rich-presence\cache\`

### Linux

- Config: `~/.config/discord-rich-presence/config.yaml`
- Logs: `~/.local/state/discord-rich-presence/app.log`
- Runtime: `~/.local/state/discord-rich-presence/runtime/`
- Terminal cache: `~/.cache/discord-rich-presence/`

## Development and release checks

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
python -m compileall -q .
ruff check . --select E9,F63,F7,F82
pytest -q
pip-audit -r requirements.txt
bandit -q -r . -x ./tests,./build,./dist -lll
```

CI covers Python 3.10/3.12 on Windows and Ubuntu, Browser Companion syntax/package validation, Bash/Zsh permissions, PowerShell syntax, known-vulnerability auditing, Windows EXE packaging, and Linux x86_64 packaging/smoke tests.

## Current limitations

- Wayland foreground-window support currently targets KDE Plasma (`kdotool`) and Sway (`swaymsg`).
- Browser Companion store publication/signing is separate from the unpacked extension included in this repository.
- External Rich Presence image URLs depend on the Discord client; Developer Portal asset keys remain the deterministic fallback.
- Unknown games/apps may fall back to generic application activity.
- Lock-screen heuristics may need updates for new desktop environments.
- macOS foreground-window detection is not implemented.
- Windows SmartScreen reputation/code signing requires a real third-party signing certificate; the workflow can use one when configured.

## Security

Do not publish tokens, private paths, sensitive screenshots, or raw terminal history in public issues. Follow [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

Released under the MIT License. See [LICENSE](LICENSE).

---

<div align="center">
  <strong>Built with ❤️ by CYBREX@TECH</strong><br>
  Check out my other projects at <a href="https://imedkablavi.info">imedkablavi.info</a>
</div>
