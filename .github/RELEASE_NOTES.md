## Release candidate

This prerelease is intended for real-device qualification before the v2.1.0 stable release. It includes Windows and Linux desktop packages plus the Browser Companion.

### Highlights

- Dynamic Discord activity identity when the packaged Discord Social SDK helper is available, with bounded Legacy RPC fallback when it is unavailable or fails.
- Conservative game detection and privacy controls, including current-session Squad enrichment and bounded local War Thunder telemetry.
- Resource lifecycle hardening for reconnects, background workers, GUI and tray shutdown, helper processes, local HTTP integrations and repeated activity switching.
- Windows portable executable and installer, Linux portable executable and user-level installer bundle, SHA-256 files and build provenance.

### Known limitations

- Real Discord Social SDK behavior, KDE/Wayland, real Squad matches, real War Thunder battles and multi-hour desktop memory behavior still require physical-device validation.
- Windows prerelease artifacts may be unsigned and can trigger Microsoft Defender SmartScreen. Stable Windows publication remains blocked until Authenticode signing is configured and verified.
- Game map, server and player details are shown only when a current trusted local source supports them; otherwise Presence falls back to the game name.

Please report release-candidate problems through GitHub Issues without attaching account identifiers, tokens, private server addresses or sensitive logs.
