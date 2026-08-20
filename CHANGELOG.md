# Changelog

## Unreleased — QA hardening

- Clear Discord Rich Presence when activity disappears, becomes blocked, or the service exits normally.
- Compare complete normalized payloads so button, URL, timestamp, and party changes are not missed.
- Align payload timestamps and clickable URLs with `pypresence 4.6.2`.
- Add Discord activity types for listening, watching, and playing.
- Rebuild configuration from defaults on hot reload and validate critical settings.
- Make `off`, `balanced`, and `strict` privacy behavior consistent with the UI/documentation.
- Fix browser service detection and inferred URL generation.
- Reduce gaming false positives and stop presenting launchers as games.
- Add local Bash, Zsh, and PowerShell terminal hooks with cache expiration.
- Remove unreliable process-list guessing for generic Wayland sessions.
- Explicitly disable foreground publishing on unsupported platforms instead of attempting X11 commands.
- Add rotating local logs and a real Discord RPC connection test in the GUI.
- Add editable Client ID, two custom buttons, service controls, and log access in the GUI.
- Persist tray privacy changes and report the actual configured tray privacy mode.
- Avoid reinstalling dependencies on every Windows launch.
- Set the supported Python baseline to 3.10+.
- Add pytest regression tests and GitHub Actions QA on Windows/Ubuntu with Python 3.10/3.12.

## 2.0.0 — Windows support

The repository added Windows foreground-window and media integrations, gaming detection, Git helpers, system-tray support, a modern GUI, and broader editor/language mappings.

Some documentation from the original 2.0.0 notes referenced installer/support files that are not present in the current repository snapshot; those claims have been removed here so the changelog only describes code that is currently available.

## 1.0.0 — Initial Linux implementation

Initial Linux/X11 activity detection, browser/media/coding/terminal detectors, Discord RPC publishing, and privacy configuration.

## Planned

- Native macOS foreground-window support.
- Reliable integrations for additional Wayland compositors.
- Exact browser URL integration through an extension or native browser API.
- Detector/plugin extension API.
- Packaged release/update workflow.
