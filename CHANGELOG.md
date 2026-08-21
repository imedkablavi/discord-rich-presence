# Changelog

## Unreleased

### Runtime and detection

- Clear Discord Rich Presence when activity disappears, becomes blocked, the lock screen is detected, or the service exits normally.
- Compare complete sanitized payloads so button, URL, timestamp, and party changes are not missed.
- Add a final Discord RPC contract sanitizer for detector output and manual overrides.
- Align payload timestamps and clickable URLs with `pypresence 4.6.2`.
- Add Discord activity types for listening, watching, and playing.
- Add single-instance locking, runtime heartbeat/status, graceful stop requests, and SIGTERM handling.
- Stabilize media timelines so Discord renders live elapsed/remaining timers without RPC updates on every scan.
- Prefer `playerctl` for Linux MPRIS media detection, with pydbus/PyGObject retained as a fallback.
- Fix Windows Media Control event-loop lifecycle so exceptional scans cannot leave an event loop open/current.
- Add KDE Plasma Wayland foreground-window detection through `kdotool` and keep Sway support through `swaymsg`.
- Reduce the default activity detection interval from 5 seconds to 2 seconds while sending RPC updates only when the normalized payload changes.
- Normalize reverse-domain application IDs such as KDE app IDs into readable Rich Presence labels.
- Use application-specific Rich Presence artwork for known browsers, editors, terminals, media players, and desktop applications.
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
- Add configurable `smart`, `foreground_first`, `media_first`, and `custom` cross-application priority policies.
- Add declarative exact/`*.wildcard` mappings for self-hosted/custom browser services.

### Privacy and configuration

- Rebuild configuration from defaults on hot reload and validate critical settings before applying them.
- Make `off`, `balanced`, and `strict` privacy behavior consistent with the UI and documentation.
- Add `none`, `domain`, `path`, and redacted `full` Browser Companion URL policies; Balanced defaults to domain-only.
- Redact values following sensitive terminal flags such as token/password/authorization arguments in Balanced mode.
- Drop browser links when their source title required privacy redaction.
- Harden POSIX configuration/runtime/log/terminal-cache directories to `0700` and sensitive files to `0600` where possible.
- Stop persistent logs from recording complete Rich Presence payloads containing page titles, terminal commands, buttons, or URLs.
- Reduce the default terminal raw-command cache lifetime from six hours to 15 minutes and delete expired PID-scoped cache files.
- Bound config-file size, custom service mappings, privacy regex/list sizes, icon overrides, and other user-controlled collections.
- Validate privacy regexes, icon overrides, detector flags, button/override URLs, terminal cache TTL, priority configuration, Browser Companion settings, and party values.
- Add lock-screen suppression and a separate toggle for generic application activity.
- Make GUI settings changes transactional when validation fails.

### Windows and GUI

- Ship a built-in public Discord Application ID so normal users do not need to create a Developer Portal application or paste an ID.
- Keep an advanced `application_id_override` for users who intentionally maintain their own Discord application/assets.
- Add custom buttons, service controls, log access, and a real Discord RPC connection test.
- Show live service PID, heartbeat, RPC state, activity summary, and recent runtime errors in the control panel.
- Persist tray privacy changes and report the actual configured mode.
- Avoid reinstalling dependencies on every Windows launch and recreate outdated virtual environments when needed.
- Add a packaged application entry point that supports tray/service mode and `--gui`.
- Keep the control panel available from the tray in packaged builds.

### Release, security, and maintenance

- Set the supported Python baseline to 3.10+.
- Add pytest regression tests and GitHub Actions QA on Windows/Ubuntu with Python 3.10/3.12.
- Add `pip check`, `pip-audit`, and high-severity Bandit scanning to release QA.
- Upgrade Pillow to 12.3+ after the 11.x line was reported with multiple 2026 security advisories.
- Syntax-check Bash/Zsh/PowerShell hooks and assert private Bash/Zsh cache permissions in CI.
- Build and smoke-test a Windows EXE on pull requests.
- Build and smoke-test a Linux x86_64 executable on pull requests.
- Validate and package a clean Browser Companion ZIP in CI.
- Publish tagged Windows, Linux, and Browser Companion artifacts with SHA-256 checksums.
- Add optional Windows Authenticode signing in the release workflow when a real PFX certificate is configured through repository secrets.
- Add security, privacy, troubleshooting, and contribution documentation.
- Add Dependabot and structured bug/feature issue templates.

## 2.0.0 — Windows support

The repository added Windows foreground-window and media integrations, gaming detection, Git helpers, system-tray support, a modern GUI, and broader editor/language mappings.

Some documentation from the original 2.0.0 notes referenced installer/support files that are not present in the current repository snapshot; those claims have been removed here so the changelog only describes code that is currently available.

## 1.0.0 — Initial Linux implementation

Initial Linux/X11 activity detection, browser/media/coding/terminal detectors, Discord RPC publishing, and privacy configuration.

## Planned

- Fully code-signed Windows releases and installer packaging once a signing certificate is provisioned.
- Official browser-store publication/signing for the Browser Companion.
- Native macOS foreground-window support.
- Reliable integrations for additional Wayland compositors.
- Detector/plugin extension API.
