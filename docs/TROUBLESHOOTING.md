# Troubleshooting

## Discord shows no Rich Presence

1. Confirm the Discord **desktop** client is running.
2. Open the control panel and check **Discord RPC** on the Dashboard.
3. Normal users should leave `discord.application_id_override` empty. A custom numeric application ID is only for users who intentionally maintain their own Discord application/assets.
4. Check the local log for `Discord RPC unavailable`, `Invalid ID`, or detector errors.
5. Run one local diagnostic cycle without publishing anything:

```bash
python main.py --dry-run --once --verbose
```

The full sanitized dry-run payload is printed to the terminal. Review it before sharing it publicly because it can still contain activity text relevant to the test.

If the service can connect to Discord but no payload is produced, the next step is detector/platform troubleshooting rather than Discord authentication.

## The service is already running

Only one service instance is allowed per user. The GUI, tray, `run.bat`, packaged binary, and startup entry share the same runtime lock.

If the Dashboard reports a live PID, stop the service from the control panel or tray. Stale lock files are recovered automatically when the recorded process no longer exists or the PID has been reused by another process.

## Browser Companion is not connecting

The optional Companion sends browser snapshots only to `http://127.0.0.1:32191` by default.

Check that the service is running and look for:

```text
Browser companion listening on http://127.0.0.1:32191
```

For Brave/Chrome/Edge, do not choose the repository root in **Load unpacked**. Prepare a clean extension directory instead:

```bash
bash scripts/prepare-browser-companion.sh
```

Then select the generated `CYBREX-Browser-Companion` directory and reload the extension after development updates.

If the extension badge shows `OFF`, check whether another local program is already using port `32191`, whether the desktop service has Browser Companion disabled, or whether a browser/endpoint security product is blocking loopback extension requests.

The extension aborts a local bridge request after a short timeout rather than leaving a request hanging indefinitely.

## A browser page is inaccurate

Without Browser Companion, browser detection relies on the visible foreground window title and recognized service markers.

With Browser Companion enabled, the service can receive exact local tab URL/title/focus/media metadata. Balanced privacy still publishes only the URL origin by default; exact URLs do not automatically become public Discord links.

Private/incognito foreground windows intentionally do not reuse normal-tab Companion metadata.

## Rich Presence keeps showing a generic image

Known applications can use app-specific external raster artwork by default. Run:

```bash
python main.py --dry-run --once --verbose
```

Inspect `large_image`. If the payload contains a direct raster image URL but Discord still shows no image, the current Discord client/RPC path is likely not rendering that external asset. Do not keep changing random CDNs; use Discord Developer Portal asset keys for deterministic release artwork.

To force Portal assets only:

```yaml
images:
  use_external_app_icons: false
```

To override one application:

```yaml
images:
  icon_overrides:
    brave: "my-brave-asset"
    trae: "https://example.com/trae.png"
```

PNG, JPEG, or WebP is recommended for direct image URLs. Unknown applications intentionally fall back to configured category/Portal assets.

## Terminal commands do not appear

Terminal command tracking needs one of the supplied optional shell hooks:

- Bash: source `scripts/hooks/bash.sh`
- Zsh: source `scripts/hooks/zsh.zsh`
- PowerShell: dot-source `scripts/hooks/powershell.ps1`

Restart the shell after installing the hook. The service uses per-shell PID cache files and may intentionally show no command when it cannot safely associate a command with the focused terminal.

The hardened default command-cache lifetime is 15 minutes. Old commands can therefore disappear even when the terminal remains open; this is intentional privacy behavior.

## Linux foreground detection

X11 requires `xprop`, commonly shipped by `x11-utils` or the equivalent package for your distribution.

KDE Plasma Wayland uses `kdotool`. Verify it directly:

```bash
kdotool getactivewindow getwindowclassname getwindowname getwindowpid
```

Sway uses `swaymsg`. Other Wayland compositors may not expose a reliable foreground-window API; the service returns no foreground activity instead of guessing from unrelated running processes.

## Media is not detected on Linux

Linux media detection prefers `playerctl` and falls back to pydbus/PyGObject when available. Confirm `playerctl` can see a playing MPRIS session:

```bash
playerctl --all-players status
playerctl --all-players metadata --format '{{playerName}} | {{artist}} | {{title}} | {{position}} | {{mpris:length}}'
```

If `playerctl` is unavailable, the pydbus fallback also needs PyGObject (`gi`) to be importable by the same Python environment. Installing the `pydbus` wheel alone does not guarantee that `gi` exists inside a virtual environment.

## Background media hides coding/terminal activity

The default `smart` priority policy lets foreground coding/terminal/browser activity beat unrelated background media while still allowing foreground media to win.

Check:

```yaml
rules:
  activity_priority:
    policy: smart
```

Other options are `foreground_first`, `media_first`, and `custom`.

## Activity changes feel delayed

`update_interval_secs` controls local polling. The default is 2 seconds and the supported range is 1-3600 seconds. Existing configuration files keep their saved value, so an older config may still contain `5`.

Linux:

```bash
grep -n 'update_interval_secs' ~/.config/discord-rich-presence/config.yaml
```

Setting it to `1` gives the fastest supported polling. Discord RPC updates are still sent only when the resulting normalized payload changes.

## Windows packaged build does not start

Check:

- Discord Desktop is installed and running;
- only one `DiscordRichPresence.exe` service instance is active;
- `%LOCALAPPDATA%\discord-rich-presence\logs\app.log` for startup errors;
- Windows Security/antivirus has not quarantined the executable.

Tagged releases include a `.sha256` checksum. If the release is unsigned, Windows SmartScreen may still warn even when the checksum is correct. Authenticode signing requires a real signing certificate configured by the project owner.

## Linux packaged build does not start

Make the downloaded release artifact executable if your browser removed its executable bit:

```bash
chmod +x CYBREX-DiscordRichPresence-linux-x86_64
./CYBREX-DiscordRichPresence-linux-x86_64 --dry-run --once
```

The Linux release binary still depends on system-level desktop integrations such as `kdotool`, `xprop`, `swaymsg`, or `playerctl` for the corresponding optional detectors.

## Dependency/security audit fails

Release QA runs `pip-audit` against runtime dependencies and treats known advisories as blockers. Do not suppress a new advisory just to make CI green. Upgrade/remove the affected dependency or document a narrowly justified exception only after investigating whether the advisory applies.

For local verification:

```bash
python -m pip install -r requirements-dev.txt
pip-audit -r requirements.txt
bandit -q -r . -x ./tests,./build,./dist -lll
```

## Where are the logs?

- Windows: `%LOCALAPPDATA%\discord-rich-presence\logs\app.log`
- Linux: `~/.local/state/discord-rich-presence/app.log`

Logs rotate automatically. Persistent logs intentionally avoid complete Rich Presence payloads; use an explicit dry run when you need to inspect the actual payload locally.
