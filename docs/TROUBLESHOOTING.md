# Troubleshooting

## Discord shows no Rich Presence

1. Confirm the Discord desktop client is running.
2. Open the control panel and check the Discord connection status.
3. Normal users should leave `discord.application_id_override` empty.
4. Check the local log for Discord connection or detector errors.
5. Run one diagnostic cycle without publishing:

```bash
python main.py --dry-run --once --verbose
```

The sanitized dry-run payload is printed to the terminal. Review it before sharing because it can contain activity text relevant to the test.

## Discord still shows the CYBREX application name

Dynamic top-level activity names require a package that includes the optional Discord Social SDK helper. When that helper is missing or fails, CYBREX falls back to legacy Discord RPC so Presence continues working. Legacy RPC may display the registered CYBREX Discord application name at the top of the card.

The control panel reports the active Discord transport. If it reports legacy RPC, this behavior is expected.

## The service is already running

Only one service instance is allowed per user. The GUI, tray, packaged binary and startup entry share the same runtime lock.

If the control panel reports a live PID, stop or restart the service from the control panel or tray. Stale locks are recovered when the recorded process no longer exists or the PID has been reused by another process.

## Browser Companion is not connecting

The optional Browser Companion sends snapshots only to `http://127.0.0.1:32191` by default.

Check that the service is running and look for:

```text
Browser companion listening on http://127.0.0.1:32191
```

From a source checkout, prepare a clean unpacked extension directory with:

```bash
bash scripts/prepare-browser-companion.sh
```

Select the generated `CYBREX-Browser-Companion` directory, not the repository root, in the browser's extension developer page.

If the extension reports the bridge as unavailable, check whether another local process owns port `32191`, Browser Companion is disabled or endpoint security is blocking loopback extension requests.

## A browser page is inaccurate

Without Browser Companion, detection relies on visible foreground-window information and conservative service markers.

With Browser Companion enabled, CYBREX can receive exact local tab URL/title/focus/media metadata. Balanced privacy still publishes only the permitted URL scope. Private or incognito foreground windows do not reuse normal-tab metadata.

## Rich Presence shows a generic image

Run a local dry-run and inspect `large_image`:

```bash
python main.py --dry-run --once --verbose
```

If the payload contains a public image URL but Discord does not render it, use configured Discord asset keys for deterministic artwork. To disable external app artwork:

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

Unknown applications intentionally fall back to configured category assets.

## Terminal commands do not appear

Terminal tracking needs one of the optional shell hooks:

- Bash: source `scripts/hooks/bash.sh`
- Zsh: source `scripts/hooks/zsh.zsh`
- PowerShell: dot-source `scripts/hooks/powershell.ps1`

Restart the shell after installing a hook. CYBREX uses per-shell PID cache files and may intentionally show no command when it cannot safely associate a command with the focused terminal.

The default command-cache lifetime is 15 minutes.

## Linux foreground detection

X11 uses `xprop`.

KDE Plasma Wayland uses `kdotool`:

```bash
kdotool getactivewindow getwindowclassname getwindowname getwindowpid
```

Sway uses `swaymsg`. Other Wayland compositors may not expose a reliable foreground-window API. CYBREX returns no foreground activity instead of guessing from unrelated running processes.

## Media is not detected on Linux

Linux media detection uses stateless `playerctl` probing when available. Confirm that `playerctl` can see an MPRIS player:

```bash
playerctl --all-players status
playerctl --all-players metadata --format '{{playerName}} | {{artist}} | {{title}} | {{position}} | {{mpris:length}}'
```

The former persistent pydbus/GLib polling fallback is not used in the current runtime.

## War Thunder activity is generic

CYBREX can enrich War Thunder only while the game is identified confidently, Strict privacy is not active and the game's local `127.0.0.1:8111` telemetry is available and valid.

If port `8111` is unavailable or returns invalid data, CYBREX intentionally falls back to normal War Thunder game identity instead of guessing map, server or vehicle context.

## Background media hides coding or terminal activity

The default `smart` priority policy lets foreground coding, terminal and browser activity beat unrelated background media while still allowing foreground media to win.

```yaml
rules:
  activity_priority:
    policy: smart
```

Other supported policies are `foreground_first`, `media_first` and `custom`.

## Activity changes feel delayed

`update_interval_secs` controls local polling. The default is 2 seconds and the supported range is 1 to 3600 seconds. Existing configuration files keep their saved value.

Linux example:

```bash
grep -n 'update_interval_secs' ~/.config/discord-rich-presence/config.yaml
```

Discord updates are sent only when the normalized payload changes.

## Windows packaged build does not start

Check:

- Discord Desktop is running
- only one CYBREX service instance is active
- `%LOCALAPPDATA%\discord-rich-presence\logs\app.log` for startup errors
- Windows Security or antivirus did not quarantine the executable

Every tagged release includes checksum verification data. An unsigned prerelease can still trigger Windows SmartScreen.

## Linux packaged build does not start

If the executable bit was removed during download:

```bash
chmod +x CYBREX-DiscordRichPresence-linux-x86_64
./CYBREX-DiscordRichPresence-linux-x86_64 --dry-run --once
```

Optional Linux detectors depend on the relevant system integration tool such as `kdotool`, `xprop`, `swaymsg` or `playerctl`.

## Where are the logs?

```text
Windows: %LOCALAPPDATA%\discord-rich-presence\logs\app.log
Linux:   ~/.local/state/discord-rich-presence/app.log
```

Logs rotate automatically and avoid complete Rich Presence payloads. Use an explicit dry-run when you need to inspect the actual sanitized payload locally.
