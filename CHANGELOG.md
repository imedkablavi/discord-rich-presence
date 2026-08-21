# Changelog

## Unreleased

### Runtime and detection

- Clear Discord Rich Presence when activity disappears, becomes blocked, the lock screen is detected, or the service exits normally.
- Compare complete sanitized payloads so button, URL, timestamp, and party changes are not missed.
- Add a final Discord RPC contract sanitizer for detector output and manual overrides.
- Enforce Discord's 256-character activity URL limit before RPC updates so long browser URLs cannot trigger reconnect loops.
- Align payload timestamps and clickable URLs with `pypresence 4.6.2`.
- Add Discord activity types for listening, watching, and playing.
- Add single-instance locking, runtime heartbeat/status, graceful stop requests, and SIGTERM handling.
- Stabilize media timelines so Discord renders live elapsed/remaining timers without RPC updates on every scan.
- Prefer `playerctl` for Linux MPRIS media detection, with pydbus/PyGObject retained as a fallback.
- Fix Windows Media Control event-loop lifecycle so exceptional scans cannot leave an event loop open/current.
- Add KDE Plasma Wayland foreground-window detection through `kdotool` and keep Sway support through `swaymsg`.
- Reduce the default activity detection interval from 5 seconds to 2 seconds while sending RPC updates only when the normalized payload changes.
- Normalize reverse-domain application IDs such as KDE app IDs into readable Rich Presence labels.
- Use application-specific Rich Presence artwork for known browsers, editors, terminals, media players, games, launchers, and desktop applications.
- Allow application artwork to use external raster image URLs, with per-app overrides and a switch to use Developer Portal assets only.
- Isolate terminal command caches per shell PID and avoid cross-terminal command leakage.
- Improve editor-title parsing for hyphenated filenames and Windows paths.
- Reduce Git enrichment to two bounded subprocesses per lookup.
- Remove unreliable process-list guessing for generic Wayland sessions.
- Keep unsupported platforms from falling through to X11 detection.

### Browser Companion and activity priority

- Add an optional Manifest V3 Browser Companion for Chromium-family browsers and Firefox.
- Add a loopback-only desktop bridge on `127.0.0.1` for exact local tab URL/title/focus/visibility and HTML media metadata.
- Bound Companion request bodies, request duration, record TTL, server threads, and in-memory record count.
- Remove closed tabs immediately and clear Companion snapshots during service shutdown/reconfiguration.
- Avoid duplicating tab URLs into fallback record identifiers.
- Add exact browser-media attribution when Chromium MPRIS omits `xesam:url`.
- Prevent stale service labels and one-letter `X` heuristics from misclassifying unrelated Firefox/Chromium tabs.
- Add configurable `smart`, `foreground_first`, `media_first`, and `custom` cross-application priority policies.
- Add declarative exact/`*.wildcard` mappings for self-hosted/custom browser services.

### Games and Counter-Strike 2

- Resolve installed Steam games from local `appmanifest_*.acf` metadata, including additional Steam libraries, Linux/Flatpak Steam, Windows Registry installs, Steam AppID window classes, process ancestry, and install paths.
- Resolve native Epic Games Launcher installs on Windows from local `.item` manifests.
- Resolve Heroic/Legendary installs from local `installed.json` metadata, including Flatpak layouts.
- Filter Steam runtimes/tools, Epic tools, Heroic DLC entries, and ambiguous executable-name matches instead of publishing them as games.
- Normalize labels such as `csgo`, `steam_app_730`, and `CS GO Steam` to Counter-Strike 2.
- Add Steam game artwork, elapsed play-session time, Steam context, and a `View on Steam` button where applicable.
- Add authenticated, loopback-only Counter-Strike 2 Game State Integration for map, mode, team, and score.
- Keep CS2 GSI read-only and minimal: request only `provider`, `map`, and `player_id`; do not retain Steam IDs, player names, weapons, health, money, positions, or all-player data.
- Add automatic CS2 GSI configuration plus source and packaged repair commands.
- Hot-reload CS2 GSI enable/disable, port, TTL, and auto-install settings without restarting the desktop service; stale CYBREX game config is removed when the integration is disabled.
- Add anti-cheat boundary tests that reject common memory-reading, injection, input-automation, and unsafe launch-flag patterns.

### Windows control center

- Replace the old settings-only window with a release-facing control center organized into Overview, Integrations, Activity, Privacy, Settings, Diagnostics, and About pages.
- Show live service state, Discord RPC connection, current activity, heartbeat, last error, Browser Companion status, and CS2 GSI status.
- Add one-click Browser Companion checks, Discord RPC test, CS2 GSI install/repair, diagnostics, log access, and config access.
- Expose activity-priority, browser privacy, detector, artwork, startup, and integration settings without requiring YAML edits for normal use.
- Fix packaged Windows Start Service behavior so the one-file executable launches itself in tray/service mode instead of trying to execute a missing `main.py` file.
- Keep Windows startup registration compatible with packaged and source installs.

### Privacy and configuration

- Rebuild configuration from defaults on hot reload and validate critical settings before applying them.
- Add formal validated defaults for the CS2 GSI integration (`enabled`, `auto_install`, `port`, and `ttl_secs`).
- Validate Discord activity URLs at 256 characters and button URLs at their separate 512-character limit.
- Keep Browser Companion exact URLs in memory only and default Balanced publishing to domain/origin only.
- Make config, runtime, log, and terminal-cache files private on POSIX where possible.
- Reduce raw terminal-command cache retention to 15 minutes by default and remove expired entries.

### Security, QA, and packaging

- Upgrade Pillow to the patched 12.x line and gate runtime dependencies with `pip-audit` on Windows and Linux.
- Run Bandit high-severity Python scanning, `pip check`, shell syntax checks, PowerShell validation, Browser Companion permission/package checks, and regression tests in CI.
- Build and smoke-test both the Windows executable and Linux x86_64 packaged binary in pull-request QA.
- Disable UPX compression for release binaries to reduce unnecessary antivirus/SmartScreen false-positive risk.
- Gate tagged releases on a fresh security audit before packaging.
- Publish Windows, Linux, and Browser Companion artifacts with SHA-256 checksums and verify checksums before release publication.
- Keep GitHub Actions repository permissions read-only except the final publish job and scope optional Windows signing secrets only to signing steps.

### Known Discord transport limitation

- The built-in public CYBREX Discord Application ID removes per-user Developer Portal setup, but the current pypresence/legacy IPC transport can still display the registered application name `CybrexTech` at the top of activity cards.
- A truly dynamic top-level app/game name requires a future Discord Social SDK transport; the legacy `name=` override was removed after real-device testing showed it was not reliable.
