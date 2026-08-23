# Discord Rich Presence

[![QA](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/qa.yml/badge.svg)](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/qa.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Windows + Linux](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/imedkablavi/discord-rich-presence)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

A local desktop app that turns your current activity into Discord Rich Presence with explicit privacy controls.

It detects the foreground app, builds a Rich Presence payload, applies your privacy settings, and sends that payload through Discord Desktop RPC. There is no project-operated cloud service in the activity path.

## Screenshots

| Control panel | Discord activity |
| :---: | :---: |
| ![Control panel](docs/images/control-panel.png) | ![Discord activity](docs/images/activity.png) |
| Service, activity, privacy, and update controls | Example Rich Presence output |

## What it detects

| Category | Examples |
| --- | --- |
| Coding | VS Code, VSCodium, Trae, JetBrains IDEs, Vim/Neovim, Sublime Text, Notepad++ |
| Browsers | Chrome, Firefox, Edge, Brave, Chromium, Opera, Vivaldi, Floorp, LibreWolf, Zen |
| Media | Spotify, VLC, MPV, browser media sessions, Windows media sessions |
| Terminal | Bash, Zsh, PowerShell, Windows Terminal, CMD and other supported terminals |
| Gaming | Known game executables using conservative exact matching |
| Applications | Optional fallback for foreground apps that do not match a specialized detector |

Every detector switch in **Activity** controls the detector itself. If a category is disabled, that detector is not run.

## Install

Open the [Releases](https://github.com/imedkablavi/discord-rich-presence/releases) page and choose the package for your system.

### Windows

Release builds provide:

- a normal per-user installer
- a portable ZIP
- the standalone portable executable used by the signed updater

The installer does not require an administrator account and installs into the current user's application directory. This also allows verified in-app updates without asking the app to overwrite a protected system directory.

### Linux

Release builds provide:

- portable `tar.gz`
- Debian `.deb`
- RPM `.rpm`
- standalone portable binary

The portable build can update itself when signed updates are configured. DEB/RPM installs stay owned by the system package manager; the app does not silently overwrite `/usr/bin`.

### Run from source

Python 3.10 or newer and Discord Desktop are required.

Windows:

```bat
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
run.bat
```

Linux:

```bash
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Source checkouts never replace themselves through the updater.

## Desktop support

| Platform/session | Foreground app detection | Behavior |
| --- | --- | --- |
| Windows | Win32 | Supported |
| Linux X11 | `xprop` | Supported when `xprop` is installed |
| KDE Plasma Wayland | `kdotool` | Supported when `kdotool` is available |
| Sway | `swaymsg` | Supported in a real Sway session |
| GNOME Wayland | No stable global active-window API used | Detection stays off instead of guessing |
| Other Wayland compositors | Depends on a trusted compositor-specific source | Detection stays off when none is available |
| macOS | Not implemented | Foreground detection unavailable |

The service never treats an arbitrary background process as the active application just because the compositor does not expose a reliable foreground-window source.

## Privacy

Three privacy modes are available:

| Mode | Behavior |
| --- | --- |
| `off` | Uses detected details without project-side redaction |
| `balanced` | Hides configured secret patterns and reduces personal path exposure |
| `strict` | Shares general activity only and removes browser links/buttons |

`balanced` is the default.

Rich Presence is cleared when publishable activity disappears or becomes blocked. It can also be cleared when a known lock-screen window is detected.

See [docs/PRIVACY.md](docs/PRIVACY.md) for the exact local data paths and redaction behavior.

## Browser companion

The optional browser companion adds richer browser context without sending browser data to a separate project server.

By default it is disabled. When enabled, the local companion:

- binds to `127.0.0.1` only
- requires a per-user bearer token
- accepts supported browser-extension origins
- uses short-lived browser state
- always removes URL fragments
- always strips title/service/URL from private or incognito payloads
- shares origin-only URLs by default
- requires an explicit opt-in before sharing a full path/query

See [docs/BROWSER_COMPANION.md](docs/BROWSER_COMPANION.md) for the protocol and threat model.

## Updates

Packaged portable builds support signed in-app updates.

The update flow is:

1. fetch the release manifest over HTTPS
2. verify its Ed25519 signature
3. select the exact platform/architecture asset
4. download it to a staging location
5. enforce the signed file size
6. verify SHA-256
7. stop the background service before replacement when updating from the control panel
8. keep a rollback copy of the current executable
9. replace and restart the app
10. restore the previous executable if the new process exits immediately

The **Overview** page shows update status, download progress, **Update now**, and a link to release notes. Update failures leave the current executable in place.

Signed updates remain disabled until the release public key is configured. The matching private key belongs only in the GitHub Actions secret `UPDATE_SIGNING_PRIVATE_KEY_B64`.

See [docs/RELEASE.md](docs/RELEASE.md) for release-key bootstrap and publishing steps.

## Configuration

Configuration is stored at:

- Windows: `%APPDATA%\discord-rich-presence\config.yaml`
- Linux: `~/.config/discord-rich-presence/config.yaml`

The full example is in [config.example.yaml](config.example.yaml).

```yaml
discord:
  client_id: "1437867564762923028"
  buttons: []

privacy:
  mode: balanced
  hide_home_paths: true

rules:
  clear_on_lock_screen: true
  enabled_detectors:
    media: true
    terminal: true
    coding: true
    browser: true
    gaming: true
    application: true
```

Set `application: false` if you only want recognized activity categories and do not want generic foreground-window titles published.

The config loader validates Client IDs, button limits, URLs, privacy regexes, detector switches, update keys, party sizes, and related values before saving them.

## Control panel

The desktop control panel has five sections:

- **Overview** — real service/RPC/activity state, foreground capability, logs, updates
- **Activity** — detector switches that directly control the running detection pipeline
- **Privacy** — redaction level, lock-screen clearing, browser detail permissions
- **Preferences** — Discord ID, profile buttons, startup, signed update source
- **About** — version, project links, platform detection capability

The status view does not claim that something is being shown on Discord when RPC is disconnected. A per-user runtime lock prevents multiple service instances from competing for the same RPC session.

Settings are validated before they are saved. The service watches the config file and reloads accepted changes without requiring a reinstall.

## Terminal command tracking

Terminal command tracking is optional. Install only the hook for shells where you want command activity published.

Bash (`~/.bashrc`):

```bash
source /path/to/discord-rich-presence/scripts/hooks/bash.sh
```

Zsh (`~/.zshrc`):

```zsh
source /path/to/discord-rich-presence/scripts/hooks/zsh.zsh
```

PowerShell (`$PROFILE`):

```powershell
. "C:\path\to\discord-rich-presence\scripts\hooks\powershell.ps1"
```

The supplied hooks write local PID-scoped cache files. The PowerShell hook preserves an existing PSReadLine history handler instead of replacing it.

## Command line

```text
python main.py [--config PATH] [--privacy off|balanced|strict]
               [--dry-run] [--once] [--verbose] [--tray] [--check-update]
```

For a local detection diagnostic that does not publish to Discord:

```bash
python main.py --dry-run --once --verbose
```

## Logs and runtime state

Logs:

- Windows: `%LOCALAPPDATA%\discord-rich-presence\logs\app.log`
- Linux: `~/.local/state/discord-rich-presence/app.log`

Runtime state:

- Windows: `%LOCALAPPDATA%\discord-rich-presence\runtime\`
- Linux: `~/.local/state/discord-rich-presence/runtime/`

Logs rotate automatically. See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detector, Discord, and desktop-session diagnostics.

## Build and QA

Development checks:

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q .
ruff check . --select E9,F63,F7,F82
pytest -q
```

Pull-request QA runs on Windows and Ubuntu with Python 3.10 and 3.12. It also smoke-tests the packaged executables, builds the Windows installer, builds/inspects DEB and RPM packages, and runs short resource-leak soaks on both operating systems.

A separate scheduled/manual workflow provides longer resource soak coverage.

## Release artifacts

Tags matching `v*` build Windows and Linux release artifacts, generate SHA-256 checksums, create an Ed25519-signed update manifest, and publish a GitHub Release. A tagged release fails instead of publishing an unsigned updater manifest when the private signing secret is missing.

See [CHANGELOG.md](CHANGELOG.md) and [docs/RELEASE.md](docs/RELEASE.md).

## Known limitations

- A browser extension package is not bundled yet; the local browser companion protocol/server is implemented and documented.
- DEB/RPM self-replacement is intentionally disabled because those files are owned by the system package manager.
- GNOME Wayland foreground detection stays disabled rather than using an unreliable process-list guess.
- Game detection is intentionally conservative, so unknown games may fall back to generic app activity when that detector is enabled.
- Lock-screen recognition uses known lock applications/window markers and may need additions for new desktop environments.
- macOS foreground-window detection is not implemented.
- Windows Authenticode signing is not configured yet. Release manifests and update payloads use Ed25519/SHA-256 verification, but Windows may still show reputation warnings for unsigned binaries.
- The rollback health check catches an immediate restart failure; a longer multi-minute post-update health handshake is not implemented yet.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Security reports should follow [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
