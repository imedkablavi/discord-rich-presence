# Discord Rich Presence

A local-first Discord Rich Presence service for Windows and Linux. It detects the activity you are actually using — browsers, editors, terminals, media players, desktop applications, and games — and publishes a privacy-aware Rich Presence to the Discord Desktop client.

No Discord Developer Portal setup is required for normal use. The project ships with the public CYBREX Discord Application ID and connects to the Discord Desktop account already running on the computer.

<p align="center">
  <img src="docs/images/control-panel.png" alt="Discord Rich Presence control panel" width="820">
</p>

<p align="center">
  <img src="docs/images/activity.png" alt="Discord Rich Presence activity" width="520">
</p>

## Highlights

- Windows and Linux support.
- KDE Plasma Wayland foreground detection through `kdotool`, plus Sway and X11 support.
- Windows foreground-window and Windows Media Control integration.
- Optional local Browser Companion for Chromium-family browsers and Firefox.
- Exact local browser tab/service/media attribution when the companion is installed.
- Smart activity priority so a background YouTube tab does not hide active coding, terminal, browser, or game activity.
- Local Steam, Epic Games, and Heroic/Legendary game detection from installed-library metadata.
- Counter-Strike 2 Game State Integration for map, mode, team, and score.
- Application/game/service-aware artwork with local overrides.
- Balanced and Strict privacy modes with secret/path/URL redaction.
- Windows tray support, autostart, diagnostics, and a full desktop control center.
- Packaged Windows and Linux builds are smoke-tested in CI.

## Windows control center

The desktop UI is organized into:

- **Overview** — service state, Discord RPC, current activity, heartbeat, last error, Browser Companion, and CS2 GSI status.
- **Integrations** — Browser Companion, game detection, and CS2 GSI setup/repair.
- **Activity** — detector switches and Smart/Foreground/Media/Custom priority modes.
- **Privacy** — privacy mode, browser URL policy, path hiding, and lock-screen clearing.
- **Settings** — update interval, artwork, custom buttons, and Windows startup.
- **Diagnostics** — config validation, Discord connection, local bridge status, detected game catalogs, logs, and config access.

The packaged executable starts the service/tray directly; it does not require Python or a source checkout.

## Browser Companion

The optional Browser Companion improves browser detection beyond window-title heuristics. It can provide the exact local tab URL/title, service, focus/visibility, and HTML media state to the desktop service.

The bridge listens only on loopback:

```text
127.0.0.1:32191
```

No CYBREX browser-history backend is used. Exact tab URLs/titles are kept in memory and expire. Balanced privacy publishes only the browser origin/domain by default.

The extension intentionally has a small permission surface: no `tabs` permission, no `file://` access, HTTP/HTTPS content scripts, and loopback access for the local bridge.

To prepare a clean unpacked extension directory:

```bash
bash scripts/prepare-browser-companion.sh
```

Then use **Load unpacked** in the browser and select the generated `CYBREX-Browser-Companion` directory rather than the repository root.

See `docs/BROWSER_COMPANION.md` for details.

## Smart activity priority

Available policies:

```yaml
rules:
  activity_priority:
    policy: smart
```

- `smart` — recommended. Games stay strongest; foreground work beats unrelated background media; foreground media wins when you are actually using it.
- `foreground_first` — strongly prefers foreground terminal/code/browser activity.
- `media_first` — keeps the older background-media-first behavior.
- `custom` — uses `custom_order` from the config.

## Game detection

### Steam

Installed Steam games are resolved from local `appmanifest_*.acf` metadata instead of relying only on executable/window names. The detector supports native Linux Steam, Flatpak Steam, Windows Steam Registry/Program Files installs, additional libraries from `libraryfolders.vdf`, `steam_app_<appid>` window classes, Steam process ancestry, and executable paths inside game install directories.

This means an installed Steam game can show its real Steam title even if it has never been hardcoded in this project. Steam runtimes/tools such as Proton and Steamworks Common Redistributables are filtered.

Where available, Steam activities use the app's Steam artwork and include a **View on Steam** button.

### Epic Games

On Windows, installed Epic games are resolved from local Epic Games Launcher `.item` manifests under ProgramData. Unreal Engine/launcher/tool manifests are filtered.

### Heroic / Legendary

Heroic/Legendary installs are resolved from local `installed.json` metadata. Native and Flatpak Heroic layouts are supported. DLC entries and ambiguous executable-name matches are ignored rather than guessed.

Other launcher/game executable aliases remain conservative fallbacks when a stable local catalog is not available.

## Counter-Strike 2

CS2 uses Valve Game State Integration (GSI), not game-memory reading or injection. A typical Rich Presence can show:

```text
Counter-Strike 2 · Competitive
Mirage · Counter-Terrorists · 8–6
```

The listener is local and authenticated:

```text
127.0.0.1:32192
```

The generated GSI configuration requests only:

```text
provider
map
player_id
```

The service does not retain Steam IDs, player names, health, money, weapons, positions, or all-player state. It does not use DLL injection, memory APIs, input automation, packet manipulation, `-insecure`, or `-allow_third_party_software`.

Auto-setup is enabled by default when CS2 is found in a Steam library. Manual source repair:

```bash
python scripts/install-cs2-gsi.py
```

Packaged Windows repair:

```text
DiscordRichPresence.exe --install-cs2-gsi
```

The packaged Linux binary accepts the same `--install-cs2-gsi` argument.

Restart CS2 after creating or changing its GSI configuration. See `docs/COUNTER_STRIKE_2.md` and `docs/ANTI_CHEAT.md`.

## Discord application-name limitation

The current transport uses `pypresence` and Discord's legacy desktop RPC IPC path. Discord may therefore display the registered application name **CybrexTech** at the top of the activity card even though the dynamic details, state, artwork, game, browser service, map, and other fields are correct.

Real-device testing confirmed that sending a legacy `name` field does not reliably replace that registered application name, so the project does not pretend otherwise. A truly dynamic top-level app/game name requires a future Discord Social SDK transport.

## Installation from source

### Windows

```powershell
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python launcher.py --gui
```

### Linux

```bash
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python launcher.py --gui
```

For the background service directly:

```bash
python main.py --verbose
```

For an interactive detection test that does not publish to Discord:

```bash
python main.py --dry-run --once --verbose
```

## KDE Plasma Wayland

Foreground-window detection on KDE Plasma Wayland uses `kdotool` when available. Linux media detection prefers `playerctl`/MPRIS.

Typical checks:

```bash
kdotool getactivewindow getwindowclassname getwindowname getwindowpid
playerctl -l
```

If `kdotool` is unavailable on KDE Wayland, the service does not guess foreground applications from a process list.

## Configuration

Default locations:

```text
Windows: %APPDATA%\discord-rich-presence\config.yaml
Linux:   ~/.config/discord-rich-presence/config.yaml
```

Normal users do not enter a Discord Client ID. Advanced users who intentionally maintain their own Discord application can use:

```yaml
discord:
  application_id_override: ""
```

Useful defaults:

```yaml
update_interval_secs: 2

privacy:
  mode: balanced
  browser_url_mode: domain

browser_companion:
  enabled: true
  port: 32191
  ttl_secs: 15

cs2_gsi:
  enabled: true
  auto_install: true
  port: 32192
  ttl_secs: 30

rules:
  activity_priority:
    policy: smart
```

See `config.example.yaml` for the complete configuration.

## Privacy

Privacy modes:

- `off` — minimal redaction.
- `balanced` — recommended; redacts sensitive values and limits browser URL exposure.
- `strict` — generic activity only; browser URLs and buttons are not published.

Browser URL modes:

- `none`
- `domain` — default; for example `https://www.youtube.com`
- `path`
- `full` — query values are still passed through privacy redaction.

Persistent logs do not store full Rich Presence payloads containing page titles, terminal commands, browser URLs, or buttons. Explicit `--dry-run` output is intended for interactive local troubleshooting.

See `docs/PRIVACY.md` and `SECURITY.md`.

## QA and release hardening

Pull-request QA currently includes:

- Ubuntu and Windows tests on Python 3.10 and 3.12.
- Python compilation and critical Ruff checks.
- `pip check` and dependency vulnerability audits.
- Bandit high-severity scanning on Linux.
- Bash/Zsh syntax and private cache-permission checks.
- PowerShell syntax validation.
- Browser Companion manifest, permission, JavaScript, helper, and package validation.
- Windows packaged EXE build + smoke test.
- Linux x86_64 packaged binary build + smoke test.

Tagged releases run a fresh security audit before packaging and include SHA-256 checksum files. Windows Authenticode signing is supported when a real signing certificate is configured in repository secrets.

No automated test suite can prove that a desktop application has zero bugs. Real-device validation is still required for current Discord Desktop behavior, KDE Wayland, browser extensions, Windows Media Control, game launchers, and packaged Windows UX.

## Troubleshooting

See:

- `docs/TROUBLESHOOTING.md`
- `docs/BROWSER_COMPANION.md`
- `docs/COUNTER_STRIKE_2.md`
- `docs/ANTI_CHEAT.md`
- `docs/PRIVACY.md`

## Contributing

Contributions are welcome. Keep detectors conservative: if foreground state or a game/service identity cannot be determined reliably, do not guess. Privacy/security regressions and features that require game-memory access, injection, or input automation are not accepted.

## License

See `LICENSE`.

Built with ❤️ by CYBREX@TECH  
https://imedkablavi.info
