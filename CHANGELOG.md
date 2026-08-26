# Changelog

## Unreleased

### Desktop experience

- Added the modern control panel with clearer Overview, Integrations, Activity, Privacy, Settings, Diagnostics and About pages.
- Added application and navigation artwork without requiring remote icon-font dependencies.
- Improved Arabic text rendering with deterministic shaping, BiDi handling and broader font fallbacks.
- Added single-instance control for the GUI and service lifecycle.
- Added Stable and Preview update-channel controls to the application UI.

### Discord transport

- Added an optional Discord Social SDK helper transport that can set the top-level activity name to the actual current app or game.
- Kept legacy Discord RPC as an automatic fallback when the helper is unavailable or fails.
- Added bounded helper protocol parsing, strict field allowlisting, timeout recovery and deterministic process/thread cleanup.
- Added a retry cooldown so repeated Social SDK failures do not create helper spawn/kill churn.
- Hardened legacy pypresence cleanup after connection, update and clear failures.

### Games

- Added a curated catalog containing more than 300 popular compatibility targets while keeping launcher metadata authoritative.
- Added conservative exact-process fallbacks and exact curated launcher-title matching instead of broad substring process guessing.
- Added War Thunder identity support through Steam AppID `236390` and exact client process names.
- Added bounded, read-only War Thunder enrichment from fixed local `127.0.0.1:8111` telemetry. Presence may include branch, a conservative vehicle label and mission/battle state. Tactical map objects, chat and HUD/damage streams are not used.
- Added bounded Squad local-log enrichment with strict evidence and staleness rules.
- Kept enhanced integrations for Counter-Strike 2 GSI, League local Live Client data, FiveM companion state and Minecraft Fabric companion state.
- Fixed `MinecraftLauncher` so the launcher is not mistaken for the running Minecraft game.
- Added application-specific artwork aliases for common games, launchers, browsers, editors, terminals and media applications.

### Browser and social presence

- Added the optional Manifest V3 Browser Companion for Chromium-family browsers and Firefox.
- Added a loopback-only desktop bridge with bounded records, request size, workers, socket timeouts and record TTLs.
- Added focused service/tab/media attribution while keeping Browser Companion records local and short-lived.
- Added privacy-safe generic Presence for major social and messaging web applications.
- Social titles, contact/conversation names, profile/post identifiers, deep social URLs and social-page media metadata are discarded before Presence building.
- Throttled background/hidden Browser Companion activity to reduce unnecessary wakeups and allocations.

### Privacy and security

- Strict privacy now suppresses collection of deep game telemetry instead of collecting rich state and hiding it later.
- Added final public-HTTPS URL validation for Rich Presence links and external artwork.
- Unsafe optional URLs fail soft without preventing the service from starting.
- Persistent logs avoid complete Rich Presence payloads and sensitive fields.
- Added dependency auditing, high-severity Bandit checks and privacy/security regression tests to CI.

### Reliability and memory

- Replaced thread-per-request loopback listeners with bounded fixed-worker servers where applicable.
- Reused a bounded GUI integration-probe worker instead of creating unbounded background work.
- Linux media detection now uses stateless `playerctl` probing and no longer keeps the former pydbus/GLib polling path.
- Added a process memory guard that records RSS, thread and file-descriptor pressure and can request allocator page return on Linux under pressure.
- Added packaged GUI and tray process-tree memory soaks.
- Added War Thunder telemetry to the core memory soak.
- Current automated Linux core stress covers 5,000 Browser Companion requests, 30,000 Presence builds and 20,000 War Thunder telemetry snapshots while checking RSS, thread and file-descriptor growth.

### Packaging and updates

- Added Windows installer and portable builds plus Linux x86_64 user-level installer and portable builds.
- Added checksum verification, combined release checksums and build provenance.
- Added verified self-update with rollback behavior on Windows and Linux.
- Added Windows Authenticode integration support. Stable Windows publication is blocked when signing is not configured and verified; explicitly marked prereleases may be unsigned.
- Added CI installation, launch and uninstall qualification for Windows and Linux packages.
- Reviewed public documentation and removed obsolete internal release-planning material from the release tree.

### Known limitations

- Automated tests do not replace real-device qualification for Discord Desktop, games, launchers, desktop compositors or hardware combinations.
- The optional Discord Social SDK transport must be included in a packaged build for dynamic top-level activity names. Legacy RPC may still display the registered CYBREX application name.
- macOS foreground-window support is not implemented.
- Wayland foreground detection depends on compositor-specific trustworthy APIs.
