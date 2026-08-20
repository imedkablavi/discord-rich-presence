# Troubleshooting

## Discord shows no Rich Presence

1. Confirm the Discord desktop client is running.
2. Open the control panel and check **Discord RPC** on the Dashboard.
3. Verify the configured Discord Client ID is numeric and belongs to an application with the expected Rich Presence assets.
4. Check the local log file for `Discord RPC unavailable`, `Invalid ID`, or detector errors.
5. Run one local diagnostic cycle without publishing anything:

```bash
python main.py --dry-run --once --verbose
```

If the log says `Connected to Discord RPC` but no update payload is produced, the RPC connection is working and the next step is detector/platform troubleshooting rather than Discord authentication.

## The service is already running

Only one service instance is allowed per user. The GUI, tray, `run.bat`, and startup entry all share the same runtime lock.

If the Dashboard reports a live PID, stop the service from the control panel or tray. Stale lock files are automatically recovered when the recorded process no longer exists.

## A browser page is not detected

Browser detection uses the foreground window title. It does not have access to the exact tab URL. Private/incognito windows are intentionally reduced to generic activity.

For exact URL integration, a browser extension or native browser integration is required.

## Rich Presence keeps showing a generic image

Known applications use application-specific external artwork by default. Run a dry-run and inspect `large_image`:

```bash
python main.py --dry-run --once --verbose
```

For a known app such as Brave, the payload should contain an application-specific image URL rather than only `app`, `browser`, or `video`. If you prefer assets uploaded in the Discord Developer Portal, set:

```yaml
images:
  use_external_app_icons: false
```

To force one application's artwork, use an asset key or direct image URL:

```yaml
images:
  icon_overrides:
    brave: "my-brave-asset"
    trae: "https://example.com/trae.png"
```

Unknown applications intentionally fall back to the configured category/Developer Portal image. External artwork also depends on the Discord client being able to fetch the referenced URL.

## Terminal commands do not appear

Terminal command tracking needs one of the supplied shell hooks.

- Bash: source `scripts/hooks/bash.sh`
- Zsh: source `scripts/hooks/zsh.zsh`
- PowerShell: dot-source `scripts/hooks/powershell.ps1`

Restart the shell after installing the hook. The service uses per-shell PID cache files and may intentionally show no command when it cannot safely match the focused terminal.

## Linux foreground detection

X11 requires `xprop`, commonly shipped by `x11-utils` or the equivalent package for your distribution.

KDE Plasma Wayland uses `kdotool`. Verify it can read the focused window directly:

```bash
kdotool getactivewindow getwindowclassname getwindowname getwindowpid
```

Sway uses `swaymsg`. Other Wayland compositors may not expose a reliable foreground-window API; in that case the service returns no foreground activity instead of guessing from running processes.

## Media is not detected on Linux

Linux media detection prefers `playerctl` and falls back to pydbus/PyGObject when available. Confirm `playerctl` can see a playing MPRIS session:

```bash
playerctl --all-players status
playerctl --all-players metadata --format '{{playerName}} | {{artist}} | {{title}} | {{position}} | {{mpris:length}}'
```

If `playerctl` is unavailable, the pydbus fallback also needs PyGObject (`gi`) to be importable by the same Python environment that runs the service. Installing the `pydbus` wheel alone does not guarantee that `gi` is available inside a virtual environment.

## Activity changes feel delayed

`update_interval_secs` controls local polling. The default is 2 seconds and the supported range is 1-3600 seconds. Existing configuration files keep their saved value, so an older config may still contain `5`.

Check Linux configuration with:

```bash
grep -n 'update_interval_secs' ~/.config/discord-rich-presence/config.yaml
```

Setting it to `1` gives the fastest supported polling. Discord RPC updates are still sent only when the resulting payload changes.

## Windows packaged build does not start

Check:

- Discord Desktop is installed and running;
- only one `DiscordRichPresence.exe` service instance is active;
- `%LOCALAPPDATA%\discord-rich-presence\logs\app.log` for startup errors;
- Windows security software has not quarantined the unsigned executable.

Release builds include a `.sha256` file. Compare it with the downloaded executable before running it if you need integrity verification.

## Where are the logs?

- Windows: `%LOCALAPPDATA%\discord-rich-presence\logs\app.log`
- Linux: `~/.local/state/discord-rich-presence/app.log`

The application keeps rotating log files rather than one unbounded log.
