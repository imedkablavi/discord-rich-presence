# Discord Rich Presence Service

A local Discord Rich Presence service that derives activity from the foreground application, applies configurable privacy rules, and publishes a Rich Presence payload through Discord Desktop RPC.

## Status

This project currently targets **Windows and Linux**. macOS is not advertised as supported until a native foreground-window implementation is added.

**Requirements:** Python 3.10+ and Discord Desktop.

## Features

- Foreground application detection on Windows and Linux/X11.
- Limited Wayland support: Sway has a reliable focus path; unknown compositors do not use process-list guessing.
- Browser, coding, media, terminal, conservative gaming, and optional generic-application activity.
- Discord activity types for listening/watching/playing.
- Clickable Rich Presence URLs with `pypresence 4.6.2`.
- Privacy modes: `off`, `balanced`, and `strict`.
- Whitelist/blacklist rules and lock-screen suppression.
- Config hot reload with schema-style validation.
- Single-instance protection so startup/GUI/tray cannot compete for Discord RPC.
- Local runtime heartbeat/status consumed by the control panel.
- Graceful GUI stop requests that clear Rich Presence before forced termination fallback.
- Stable media timelines that avoid unnecessary RPC updates during normal playback.
- Per-shell terminal command caches to avoid leaking commands between terminal windows.
- System tray controls and rotating local logs.
- Automated regression tests on Windows and Linux.

## Privacy modes

| Mode | Behavior |
| --- | --- |
| `off` | Sends detected activity without privacy redaction. Use only if you accept the exposure risk. |
| `balanced` | Redacts configured secret patterns and reduces path exposure while preserving useful context. |
| `strict` | Sends generic activity descriptions and removes browser URLs/buttons and identifying details. |

If an activity becomes blocked, disappears, the lock screen is detected, or the service shuts down normally, the service clears the previous Rich Presence instead of intentionally leaving stale activity visible.

## Installation

### Windows

```bat
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
run.bat
```

`run.bat` creates/repairs `.venv`, recreates an outdated pre-3.10 virtual environment, verifies the required `pypresence` API version, and only installs dependencies when repair is required.

### Linux

```bash
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

X11 foreground-window detection uses `xprop` (usually provided by `x11-utils`). Linux media detection uses MPRIS/D-Bus.

## Configuration

The default config lives at:

- Windows: `%APPDATA%\discord-rich-presence\config.yaml`
- Linux: `~/.config/discord-rich-presence/config.yaml`

See `config.example.yaml` for the available options. Invalid button URLs, privacy regexes, detector flags, party sizes, and unsafe override URLs are rejected before they reach Discord RPC.

Example:

```yaml
discord:
  client_id: "1437867564762923028"
  buttons: []

privacy:
  mode: balanced
  hide_home_paths: true

update_interval_secs: 5

rules:
  clear_on_lock_screen: true
  terminal_command_ttl_secs: 21600
  enabled_detectors:
    media: true
    terminal: true
    coding: true
    browser: true
    gaming: true
    application: true
  whitelist:
    apps: []
    sites: []
    games: []
  blacklist:
    apps: []
    sites: []
    games: []
```

Set `rules.enabled_detectors.application: false` if you only want recognized categories and do not want generic window titles published.

## Control panel and runtime state

The control panel reads the service's local runtime heartbeat. It can therefore display a service that was started by `run.bat`, the tray, or Windows autostart—not only a process started by the panel itself.

The dashboard shows:

- service PID and heartbeat freshness;
- Discord RPC connected/disconnected status;
- whether a Presence is currently published;
- a short current activity summary;
- the most recent runtime/RPC error.

Only one service instance can hold the per-user runtime lock. The GUI requests a graceful stop first; the service clears Discord and closes RPC before a terminate/kill fallback is used.

## Terminal command tracking

The service does not inspect shell command lines remotely. Optional local shell hooks write commands to local cache files before/when commands are accepted by the shell.

New hooks write a **per-shell PID cache**. The foreground terminal process tree is matched against those PID files, which avoids displaying a command from another open terminal window. A legacy global cache is read only when no fresh PID-scoped hook files exist.

### Bash

Add to `~/.bashrc`:

```bash
source /path/to/discord-rich-presence/scripts/hooks/bash.sh
```

### Zsh

Add to `~/.zshrc`:

```zsh
source /path/to/discord-rich-presence/scripts/hooks/zsh.zsh
```

### PowerShell

Add to `$PROFILE`:

```powershell
. "C:\path\to\discord-rich-presence\scripts\hooks\powershell.ps1"
```

The PowerShell hook preserves an existing PSReadLine `AddToHistoryHandler` instead of overwriting the user's history policy. Restart the shell after installing a hook. Balanced and strict privacy rules are still applied before terminal information is sent to Discord.

## CLI

```text
python main.py [--config PATH] [--privacy off|balanced|strict]
               [--dry-run] [--once] [--verbose] [--tray]
```

`--dry-run` is useful when validating detectors and privacy output without publishing it to Discord.

## Local runtime files

Runtime state contains PID/heartbeat/status only and stays local:

- Windows: `%LOCALAPPDATA%\discord-rich-presence\runtime\`
- Linux: `~/.local/state/discord-rich-presence/runtime/`

Terminal command caches are also local and are subject to `rules.terminal_command_ttl_secs`.

## Logs

Logs rotate automatically:

- Windows: `%LOCALAPPDATA%\discord-rich-presence\logs\app.log`
- Linux: `~/.local/state/discord-rich-presence/app.log`

## Development / QA

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check . --select E9,F63,F7,F82
```

GitHub Actions runs the regression suite on Windows and Ubuntu with Python 3.10 and 3.12.

## Known limitations

- Generic Wayland compositors may not expose a trustworthy foreground window; Sway has a dedicated path.
- Browser URLs are inferred search/home links from window-title metadata, not exact tab URLs. An extension/native browser integration is required for exact URLs.
- Game detection intentionally favors fewer false positives over claiming support for arbitrary games.
- Lock-screen detection is based on known foreground lock applications/window markers; operating systems/compositors can add new variants.
- macOS support is not implemented yet.

## License

MIT. See `LICENSE`.
