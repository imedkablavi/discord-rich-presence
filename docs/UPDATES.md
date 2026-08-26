# Application updates

Packaged CYBREX Presence builds can update in place on Windows and Linux. Normal upgrades do not require uninstalling and reinstalling the application.

## User flow

Open **About > Updates** in the control panel.

- **Check for updates:** checks release metadata only.
- **Download & install:** downloads the expected platform asset after explicit user action, verifies it, replaces the packaged executable and relaunches CYBREX.
- **Check at startup:** performs a metadata-only update check. It never installs silently.

The tray menu also exposes update actions.

Command-line equivalents:

```text
--check-update
--update
```

## Update channels

CYBREX has two channels:

- **Stable:** published non-prerelease GitHub Releases only.
- **Preview:** published release candidates plus stable releases.

Stable never installs a preview release. Preview can move to a newer release candidate or a newer stable release. Draft releases, branch commits and pull-request artifacts are never selected.

Release tags use SemVer-style names:

```text
vMAJOR.MINOR.PATCH
vMAJOR.MINOR.PATCH-PRERELEASE
```

Examples:

```text
v2.1.0
v2.1.0-rc6
```

## Verification model

The updater requires the expected packaged application asset and matching `.sha256` sidecar. It downloads only allowed public GitHub HTTPS locations, rejects URL credentials and non-standard ports, applies response and binary size limits, verifies SHA-256 and refuses malformed, unsafe or downgrade release data.

If a required asset, checksum, version tag or download invariant is invalid, the update fails closed and the current executable remains in place.

A stable version outranks a release candidate with the same core version. Preview comparison distinguishes candidate numbers correctly:

```text
2.1.0-rc3 < 2.1.0-rc6 < 2.1.0-rc10 < 2.1.0
```

## Windows rollback

The verified replacement is staged next to the current executable. A temporary PowerShell helper waits for the running process to exit, swaps the executable and retains a rollback copy through the startup check. If the replacement exits immediately, the helper restores and relaunches the previous executable.

Stable Windows publication is blocked until Authenticode signing is configured and verified. A Preview release may be unsigned and must remain clearly labeled as a prerelease.

## Linux rollback

The verified replacement is staged in the same directory and installed with an atomic rename. The previous executable is retained as a short-lived `.old` rollback copy through the startup check. If the replacement exits immediately, the previous executable is restored and relaunched.

The supported Linux installer keeps the executable user-owned, so self-update does not require `sudo`.

## Expected desktop assets

The updater expects:

```text
DiscordRichPresence.exe
DiscordRichPresence.exe.sha256
CYBREX-DiscordRichPresence-linux-x86_64
CYBREX-DiscordRichPresence-linux-x86_64.sha256
```

Changing these names requires a coordinated updater change.

## Browser Companion

The desktop updater updates the CYBREX desktop executable. Browser Companion is a separate browser extension package. Unpacked installations must update the extension package separately. A future store-published extension can use the browser store's normal update mechanism after that distribution channel exists.

## Release integrity

Tagged release builds run regression and security gates before packaging. The publish job verifies platform checksums and publishes combined `SHA256SUMS.txt` plus `BUILD-PROVENANCE.txt`.

Windows code signing and updater checksum verification solve different integrity problems. A build is described as Authenticode-signed only when its signature was verified successfully.

See [Code signing policy](../CODE_SIGNING.md) and [Download and integrity verification](DOWNLOAD.md).
