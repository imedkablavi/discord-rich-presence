# Application updates

Packaged CYBREX Presence builds can update in place on Windows and Linux. Users do not need to uninstall or reinstall the application for normal upgrades.

## Commands

```text
DiscordRichPresence --check-update
DiscordRichPresence --update
```

The system tray also exposes **Check for updates** and **Install latest update**.

## Trust model

Automatic updates use only the repository's **latest published stable GitHub Release**. Branch commits, pull-request artifacts, draft releases and prereleases are never selected by the stable updater.

For the current platform, the updater requires both the packaged application asset and its matching `.sha256` sidecar. It downloads only public HTTPS URLs hosted by GitHub/GitHub's content hosts, rejects URL credentials and non-standard ports, applies response and binary size limits, verifies the sidecar SHA-256, and also verifies GitHub's release-asset SHA-256 digest when GitHub provides one.

If any required asset, checksum, version tag or download invariant is invalid, the update fails closed and the current executable remains in place. A stable build ranks above a release candidate with the same core version, so `2.1.0-rc3` can correctly update to `2.1.0`.

## Windows

The verified replacement is staged next to the current executable. Because Windows does not reliably allow a running executable to replace itself, a small temporary PowerShell helper waits for the updater process to exit, swaps the executable and keeps a rollback copy during startup. If the replacement exits immediately during the startup check, the helper restores and relaunches the previous executable.

## Linux

The verified replacement is staged in the same directory as the current executable and installed with an atomic rename. For self-update, the previous executable is retained as a short-lived `.old` rollback copy until the relaunched build survives its startup check. If the replacement exits immediately, the previous executable is restored and relaunched.

The user-level release installer verifies the bundled `SHA256SUMS` when present and fails closed if verification cannot be performed or the digest does not match.

## Release channels

Version tags use SemVer-style names:

```text
vMAJOR.MINOR.PATCH
vMAJOR.MINOR.PATCH-PRERELEASE
```

Examples:

```text
v2.1.0
v2.1.0-rc4
```

Tags containing a prerelease suffix are published as GitHub prereleases. Stable Windows tags are blocked by the generic release workflow until Windows code signing is configured and verified.

The release workflow stamps the tag version into packaged builds, runs regression/security gates, verifies packaged installers, and publishes checksums plus build provenance.

## Update assets

The stable updater currently expects these platform assets and sidecars:

- `DiscordRichPresence.exe`
- `DiscordRichPresence.exe.sha256`
- `CYBREX-DiscordRichPresence-linux-x86_64`
- `CYBREX-DiscordRichPresence-linux-x86_64.sha256`

Changing these asset names requires a coordinated updater change.

## Code signing

Windows code signing and updater checksum verification solve different problems. A build must not be described as Authenticode-signed unless its Windows signature has been verified successfully. See [Code signing policy](../CODE_SIGNING.md) for the current signing status and SignPath Foundation plan.
