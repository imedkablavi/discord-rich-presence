# Security Policy

## Supported versions

Security fixes are applied to the current release line and `main`. Older builds should be upgraded before reporting a problem that may already be fixed.

## Reporting a vulnerability

Do not publish sensitive security reports, tokens, private paths, browser URLs, terminal history or unredacted diagnostic output in a public issue.

Use GitHub private vulnerability reporting for this repository when available. Include the affected version or commit, operating system, a minimal reproduction, the security impact and only the redacted logs needed to investigate it.

Ordinary bugs that do not cross a security or privacy boundary can use the normal issue tracker.

## Security model

CYBREX Presence is a local desktop application. Enabled detectors read local activity and the final sanitized Rich Presence payload is sent to the local Discord client. The project does not operate an activity, browser-history or command-history telemetry backend.

Optional browser and game companion listeners bind to IPv4 loopback. They use bounded requests, short timeouts, bounded worker counts or fixed local endpoints, short state TTLs and explicit parsing rules. Loopback is not a security boundary against another malicious process already running as the same operating-system user.

Links that can leave the application through Discord Presence are filtered at the final publication boundary. Public links and external artwork use HTTPS. URL credentials, control characters, localhost names, private/link-local IP literals and common local DNS suffixes are rejected.

On POSIX systems, configuration, runtime, log and cache paths are hardened to user-only permissions where practical. Persistent logs intentionally avoid complete Rich Presence payloads.

See [Privacy](docs/PRIVACY.md) for the detailed data paths.

## Game integration boundary

Enhanced game integrations remain read-only and outside the game process. CYBREX does not use process-memory reading, DLL/code injection, input automation, packet interception, credential emulation or anti-cheat bypasses to enrich Presence.

Strict privacy suppresses deep game telemetry collection rather than collecting rich state and hiding it only at publication time.

See [Anti-Cheat and Game Integration Boundary](docs/ANTI_CHEAT.md) and [Game Compatibility](docs/GAME_COMPATIBILITY.md).

## Discord Social SDK boundary

The optional Discord Social SDK helper communicates with the Python application over private stdin/stdout pipes. It does not open a network listener and does not implement Discord user OAuth, bot-token, access-token or refresh-token flows.

If the helper is unavailable or fails, CYBREX falls back to legacy Discord RPC. Helper protocol input is bounded and allowlisted, and helper failure paths are covered by resource-cleanup tests.

## Dependency and code checks

Release validation includes:

- Python regression tests and critical Ruff checks;
- `pip check` dependency consistency checks;
- `pip-audit` for known published dependency vulnerabilities;
- Bandit high-severity Python scanning;
- Browser Companion manifest and JavaScript validation;
- shell-hook syntax and local-cache permission checks;
- gamer integration privacy and anti-cheat boundary tests;
- Windows and Linux packaged-binary smoke tests;
- Windows installer install, launch and uninstall checks;
- Linux user-level installer install, launch and uninstall checks;
- packaged process-tree memory/resource soaks on Linux.

A dependency advisory affecting resolved runtime requirements is treated as a release blocker until upgraded, removed or investigated and explicitly justified.

## Release integrity

Tagged releases publish SHA-256 verification files and build provenance. The release workflow verifies checksums before publication.

Prerelease tags are published as GitHub prereleases. Stable Windows publication is blocked when Authenticode signing is not configured and verified. An unsigned Windows build may be used for CI or an explicitly marked prerelease, but it must not be represented as a signed stable release.

See [Code signing policy](CODE_SIGNING.md) and [Download and integrity verification](docs/DOWNLOAD.md).
