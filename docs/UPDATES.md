# Application updates

Packaged CYBREX Rich Presence builds can update in place on Windows and Linux. Users do not need to uninstall or reinstall the application for normal upgrades.

## Commands

```text
DiscordRichPresence --check-update
DiscordRichPresence --update
```

The system tray also exposes **Check for updates** and **Install latest update**.

## Trust model

Automatic updates use only the repository's **latest published stable GitHub Release**. Branch commits, pull-request artifacts, draft releases and prereleases are never selected by the stable updater.

For the current platform, the updater requires both the packaged application asset and its matching `.sha256` sidecar. It downloads only HTTPS URLs hosted by GitHub/GitHub's content hosts, applies response and binary size limits, verifies the sidecar SHA-256, and also verifies GitHub's release-asset SHA-256 digest when GitHub provides one.

If any required asset, checksum, version tag or download invariant is invalid, the update fails closed and the current executable remains in place.

## Windows

The verified replacement is staged next to the current executable. Because Windows does not reliably allow a running executable to replace itself, a small temporary PowerShell helper waits for the updater process to exit, swaps the executable with rollback protection, and can relaunch the control panel.

## Linux

The verified replacement is staged in the same directory as the current executable and installed with an atomic rename. A short-lived `.old` rollback copy is removed after a successful swap.

## Release requirements

Release tags must use `vMAJOR.MINOR.PATCH`. The release workflow stamps that version into the packaged build and publishes these assets:

- `DiscordRichPresence.exe`
- `DiscordRichPresence.exe.sha256`
- `CYBREX-DiscordRichPresence-linux-x86_64`
- `CYBREX-DiscordRichPresence-linux-x86_64.sha256`

Changing those asset names requires a coordinated updater change.
