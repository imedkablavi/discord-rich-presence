# Application updates

Packaged CYBREX Presence builds can update in place on Windows and Linux. Users do not need to uninstall or reinstall the desktop application for normal upgrades.

## Normal user flow

Open **About → Updates** in the CYBREX control panel. The page shows the installed version and update channel and provides:

- **Check for updates** — checks release metadata only; it does not download or install anything.
- **Download & install** — downloads the platform binary only after the user explicitly chooses to install, verifies it, replaces the packaged executable, and relaunches CYBREX.
- **Check for updates when CYBREX starts** — metadata-only background check. It never silently installs a release.

The system tray also exposes **Check for updates** and **Install latest update**.

Command-line equivalents remain available:

```text
DiscordRichPresence --check-update
DiscordRichPresence --update
```

## Update channels

CYBREX exposes two channels:

- **Stable** — only published non-prerelease GitHub Releases. Stable builds default to this channel.
- **Preview** — published release candidates plus stable releases. Release-candidate builds default to this channel so a user on `2.1.0-rc4` can receive `2.1.0-rc5` and later `2.1.0` without reinstalling.

The selected channel is stored locally in the CYBREX configuration. Changing channels does not bypass package verification.

Stable never installs a preview release. Preview may upgrade to a newer release candidate or to a newer stable release. Draft releases, branch commits and pull-request artifacts are never selected.

Version tags use SemVer-style names:

```text
vMAJOR.MINOR.PATCH
vMAJOR.MINOR.PATCH-PRERELEASE
```

Examples:

```text
v2.1.0
v2.1.0-rc4
v2.1.0-rc5
```

## Trust model

For the current platform, the updater requires both the packaged application asset and its matching `.sha256` sidecar. It downloads only public HTTPS URLs hosted by GitHub/GitHub's content hosts, rejects URL credentials and non-standard ports, applies response and binary size limits, verifies the sidecar SHA-256, and also verifies GitHub's release-asset SHA-256 digest when GitHub provides one.

If any required asset, checksum, version tag or download invariant is invalid, the update fails closed and the current executable remains in place.

A stable build outranks a release candidate with the same core version. Preview version comparison also distinguishes candidate numbers correctly, for example:

```text
2.1.0-rc3 < 2.1.0-rc4 < 2.1.0-rc10 < 2.1.0
```

## Windows

The verified replacement is staged next to the current executable. Because Windows does not reliably allow a running executable to replace itself, a small temporary PowerShell helper waits for the updater process to exit, swaps the executable and keeps a rollback copy during startup. If the replacement exits immediately during the startup check, the helper restores and relaunches the previous executable.

Stable Windows releases remain blocked by release policy until Windows code signing is configured and verified. Preview releases may be unsigned and should be labeled accordingly.

## Linux

The verified replacement is staged in the same directory as the current executable and installed with an atomic rename. For self-update, the previous executable is retained as a short-lived `.old` rollback copy until the relaunched build survives its startup check. If the replacement exits immediately, the previous executable is restored and relaunched.

The supported user-level installer keeps the executable user-owned, so future self-updates do not require `sudo`. The release installer verifies its bundled `SHA256SUMS` when present and fails closed if verification cannot be performed or the digest does not match.

## Update assets

The desktop updater expects these platform assets and sidecars:

- `DiscordRichPresence.exe`
- `DiscordRichPresence.exe.sha256`
- `CYBREX-DiscordRichPresence-linux-x86_64`
- `CYBREX-DiscordRichPresence-linux-x86_64.sha256`

Changing these asset names requires a coordinated updater change.

## Browser Companion

The desktop self-updater updates the CYBREX desktop executable. The Browser Companion is a separate browser extension package, so unpacked/developer installations still need the extension package updated separately. A future browser-store distribution can use the browser's normal extension update mechanism.

## Release engineering

Tags containing a prerelease suffix are published as GitHub prereleases. The generic release workflow stamps the tag version into packaged builds, runs regression/security gates, verifies packaged installers, and publishes checksums plus build provenance.

One-shot release-candidate workflows used during development are not part of the permanent release path and should be removed after the corresponding candidate is published.

## Code signing

Windows code signing and updater checksum verification solve different problems. A build must not be described as Authenticode-signed unless its Windows signature has been verified successfully. See [Code signing policy](../CODE_SIGNING.md) for the current signing status and SignPath Foundation plan.
