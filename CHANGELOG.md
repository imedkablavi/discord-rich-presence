# Changelog

## Unreleased

### Runtime and detection

- Clear Discord Rich Presence when activity disappears, becomes blocked, the lock screen is detected, or the service exits normally.
- Compare complete normalized payloads so button, URL, timestamp, and party changes are not missed.
- Align payload timestamps and clickable URLs with `pypresence 4.6.2`.
- Add Discord activity types for listening, watching, and playing.
- Add single-instance locking, runtime heartbeat/status, and graceful stop requests.
- Stabilize media timelines to avoid unnecessary RPC updates during normal playback.
- Isolate terminal command caches per shell PID and avoid cross-terminal command leakage.
- Improve editor-title parsing for hyphenated filenames and Windows paths.
- Remove unreliable process-list guessing for generic Wayland sessions.
- Keep unsupported platforms from falling through to X11 detection.

### Privacy and configuration

- Rebuild configuration from defaults on hot reload and validate critical settings.
- Make `off`, `balanced`, and `strict` privacy behavior consistent with the UI and documentation.
- Validate privacy regexes, detector flags, button/override URLs, terminal cache TTL, and party values.
- Add lock-screen suppression and a separate toggle for generic application activity.
- Make GUI settings changes transactional when validation fails.

### Windows and GUI

- Add editable Client ID, two custom buttons, service controls, log access, and a real Discord RPC connection test.
- Show live service PID, heartbeat, RPC state, activity summary, and recent runtime errors in the control panel.
- Persist tray privacy changes and report the actual configured mode.
- Avoid reinstalling dependencies on every Windows launch and recreate outdated virtual environments when needed.
- Add a packaged application entry point that supports tray/service mode and `--gui`.
- Keep the control panel available from the tray in packaged builds.

### Release and maintenance

- Set the supported Python baseline to 3.10+.
- Add pytest regression tests and GitHub Actions QA on Windows/Ubuntu with Python 3.10/3.12.
- Add a PyInstaller build check for the Windows executable.
- Add tagged GitHub Releases with SHA-256 checksums.
- Add security, privacy, troubleshooting, and contribution documentation.
- Add Dependabot and structured bug/feature issue templates.

## 2.0.0 — Windows support

The repository added Windows foreground-window and media integrations, gaming detection, Git helpers, system-tray support, a modern GUI, and broader editor/language mappings.

Some documentation from the original 2.0.0 notes referenced installer/support files that are not present in the current repository snapshot; those claims have been removed here so the changelog only describes code that is currently available.

## 1.0.0 — Initial Linux implementation

Initial Linux/X11 activity detection, browser/media/coding/terminal detectors, Discord RPC publishing, and privacy configuration.

## Planned

- Code-signed Windows releases and installer packaging.
- Native macOS foreground-window support.
- Reliable integrations for additional Wayland compositors.
- Exact browser URL integration through an extension or native browser API.
- Detector/plugin extension API.
