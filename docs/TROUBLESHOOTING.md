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

## The service is already running

Only one service instance is allowed per user. The GUI, tray, `run.bat`, and startup entry all share the same runtime lock.

If the Dashboard reports a live PID, stop the service from the control panel or tray. Stale lock files are automatically recovered when the recorded process no longer exists.

## A browser page is not detected

Browser detection uses the foreground window title. It does not have access to the exact tab URL. Private/incognito windows are intentionally reduced to generic activity.

For exact URL integration, a browser extension or native browser integration is required.

## Terminal commands do not appear

Terminal command tracking needs one of the supplied shell hooks.

- Bash: source `scripts/hooks/bash.sh`
- Zsh: source `scripts/hooks/zsh.zsh`
- PowerShell: dot-source `scripts/hooks/powershell.ps1`

Restart the shell after installing the hook. The service uses per-shell PID cache files and may intentionally show no command when it cannot safely match the focused terminal.

## Linux foreground detection

X11 requires `xprop`, commonly shipped by `x11-utils`.

Sway is supported through `swaymsg`. Other Wayland compositors may not expose a reliable foreground-window API; in that case the service returns no foreground activity instead of guessing from running processes.

## Media is not detected on Linux

Linux media detection uses MPRIS over the desktop D-Bus session. Confirm the player exposes an `org.mpris.MediaPlayer2.*` service and that the service is running in the same desktop session.

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
