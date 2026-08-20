# Discord Rich Presence Service

A local Discord Rich Presence service that derives activity from the foreground application, applies configurable privacy rules, and publishes a Rich Presence payload through Discord Desktop RPC.

## Status

This project currently targets **Windows and Linux**. macOS is not advertised as supported until a native foreground-window implementation is added.

**Requirements:** Python 3.10+ and Discord Desktop.

## Features

- Foreground application detection on Windows and Linux/X11.
- Limited Wayland support (best on Sway; other compositors may not expose reliable focus information).
- Browser, coding, media, terminal, and conservative gaming detectors.
- Discord activity types for listening/watching/playing.
- Clickable Rich Presence URLs with `pypresence 4.6.2`.
- Privacy modes: `off`, `balanced`, and `strict`.
- Whitelist/blacklist rules.
- Config hot reload with validation.
- System tray controls.
- Rotating local logs.
- Automated regression tests on Windows and Linux.

## Privacy modes

| Mode | Behavior |
| --- | --- |
| `off` | Sends detected activity without privacy redaction. Use only if you accept the exposure risk. |
| `balanced` | Redacts configured secret patterns and reduces path exposure while preserving useful context. |
| `strict` | Sends generic activity descriptions and removes browser URLs/buttons and identifying details. |

If an activity becomes blocked, disappears, or the service shuts down normally, the service clears the previous Rich Presence instead of intentionally leaving stale activity visible.

## Installation

### Windows

```bat
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
run.bat
```

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

See `config.example.yaml` for the available options.

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
  enabled_detectors:
    media: true
    terminal: true
    coding: true
    browser: true
    gaming: true
  whitelist:
    apps: []
    sites: []
    games: []
  blacklist:
    apps: []
    sites: []
    games: []
```

## Terminal command tracking

The service does not inspect shell command lines remotely. Optional local shell hooks write the current/recent command to a local cache file that the terminal detector reads.

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

Restart the shell after installing a hook. Balanced and strict privacy rules are still applied before terminal information is sent to Discord.

## CLI

```text
python main.py [--config PATH] [--privacy off|balanced|strict]
               [--dry-run] [--once] [--verbose] [--tray]
```

`--dry-run` is useful when validating detectors and privacy output without publishing it to Discord.

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
- macOS support is not implemented yet.

## License

MIT. See `LICENSE`.
