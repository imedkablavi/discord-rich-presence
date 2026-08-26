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
- Report the active foreground-detection capability/backend to the control panel.
- Require an actual Sway session before using `swaymsg`; merely having the command installed is not sufficient.
- Keep GNOME Wayland fail-safe when no stable trusted global active-window API is available.
- Expand known-game executable mappings while replacing broad substring matching with normalized exact executable-stem matching.
- Close unhealthy Discord RPC transports after update/clear failures before reconnecting.
- Make every Activity detector switch authoritative: disabled game/media/terminal/coding/browser/application detectors are no longer executed.
- Stop the control panel from claiming an activity is being shown when Discord RPC is disconnected.

### Privacy and configuration

- Rebuild configuration from defaults on hot reload and validate critical settings.
- Make `off`, `balanced`, and `strict` privacy behavior consistent with the UI and documentation.
- Validate privacy regexes, detector flags, button/override URLs, terminal cache TTL, and party values.
- Add lock-screen suppression and a separate toggle for generic application activity.
- Make GUI settings changes transactional when validation fails.
- Add an optional authenticated browser companion bound to loopback only.
- Make exact browser URL access an explicit opt-in; origin-only is the default companion URL policy.
- Strip title, service, and URL from private/incognito companion payloads regardless of extension input.
- Add privacy regression tests for companion authentication, URL minimization, and private browsing.

### Desktop, startup, and GUI

- Add editable Client ID, two custom buttons, service controls, log access, and a real Discord RPC connection test.
- Show live service PID, heartbeat, RPC state, activity summary, recent runtime errors, and foreground backend in the control panel.
- Persist tray privacy changes and report the actual configured mode.
- Avoid reinstalling dependencies on every Windows launch and recreate outdated virtual environments when needed.
- Add a packaged application entry point that supports tray/service mode and `--gui`.
- Keep the control panel available from the tray in packaged builds.
- Add per-user startup registration for Windows and Linux desktop sessions.
- Add control-panel settings for browser companion privacy and signed updates.
- Show application version and signed-update status in the control panel.
- Add graceful packaged-service shutdown for the Windows uninstaller and unconditional autostart registry cleanup.
- Rework the control panel into Overview, Activity, Privacy, Preferences, and About sections with shorter user-facing copy and clearer grouping.
- Add a complete update card with check, release notes, download/verification progress, `Update now`, restart, and error recovery states.
- Install the Windows build per-user so normal signed self-updates do not require administrator access.

### Release, updater, and QA

- Set the supported Python baseline to 3.10+.
- Add pytest regression tests and GitHub Actions QA on Windows/Ubuntu with Python 3.10/3.12.
- Build and smoke-test Windows and Linux PyInstaller executables in CI.
- Add Windows Inno Setup installer packaging in addition to the portable executable.
- Add Linux portable `tar.gz`, Debian `.deb`, and Fedora/Bazzite-compatible RPM packages.
- Add tagged GitHub Releases with SHA-256 checksums.
- Add Ed25519-signed update manifests with HTTPS, signed-size, and SHA-256 verification.
- Reject HTTPS-to-HTTP redirect downgrade for manifests and update assets.
- Add staged portable self-update with rollback backup, immediate restart-health rollback, and fail-closed behavior.
- Add user-approved manual update staging independently of the optional startup auto-update setting.
- Report real byte progress while a verified update asset is downloaded.
- Never self-replace source checkouts or unwritable/package-managed installs.
- Require the update signing private key secret before a tagged release can publish.
- Add regression tests proving disabled Activity detectors are not called and manual update staging reports real state.
- Add short cross-platform resource-leak soak tests to PR QA and a scheduled/manual long soak workflow.
- Track RSS, thread count, and file-descriptor/handle growth during soak runs.
- Add security, privacy, troubleshooting, browser companion, release, and contribution documentation.
- Add Dependabot and structured bug/feature issue templates.

## 2.0.0 - Windows support

The repository added Windows foreground-window and media integrations, gaming detection, Git helpers, system-tray support, a modern GUI, and broader editor/language mappings.

Some documentation from the original 2.0.0 notes referenced installer/support files that are not present in the current repository snapshot; those claims have been removed here so the changelog only describes code that is currently available.

## 1.0.0 - Initial Linux implementation

Initial Linux/X11 activity detection, browser/media/coding/terminal detectors, Discord RPC publishing, and privacy configuration.

## Planned

- Authenticode/code-signed Windows binaries and installer once signing credentials are available.
- Native macOS foreground-window support.
- Reliable trusted integrations for additional Wayland compositors when stable APIs exist.
- Browser extension packages that implement the documented local companion protocol.
- AppImage packaging after distribution-specific validation.
- Detector/plugin extension API.
