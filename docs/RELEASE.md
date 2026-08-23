# Release Engineering

## Versioning

The project uses semantic versions. Development builds keep `version.py` on a `-dev` version. The release workflow stamps the executable with the tag version before packaging.

Recommended progression:

1. `v2.1.0-rc1` for a release candidate.
2. Validate packaged artifacts on real Windows and Linux desktops.
3. Tag `v2.1.0` only after the manual matrix below passes.

## Update signing bootstrap

Generate a dedicated Ed25519 keypair once:

```bash
python scripts/generate_update_key.py
```

Store `UPDATE_SIGNING_PRIVATE_KEY_B64` only as the GitHub Actions repository secret with the same name. Never commit it, place it in application configuration, or ship it inside an executable.

Copy only `UPDATE_SIGNING_PUBLIC_KEY_B64` into the default/user configuration as `updates.public_key`. A tagged release intentionally fails before publishing when the private signing secret is missing.

Rotating the update key is a release/security event. Ship the new public key through a version signed by the old key before retiring the old private key whenever possible.

## Release artifacts

Windows:

- `DiscordRichPresence-windows-x86_64.exe` — raw portable executable used by the signed auto-updater.
- `DiscordRichPresence-<version>-windows-x86_64-portable.zip` — portable bundle.
- `DiscordRichPresence-Setup-<version>-windows-x86_64.exe` — Inno Setup installer with uninstall support.

Linux:

- `DiscordRichPresence-linux-x86_64` — raw portable executable used by the signed auto-updater when the install directory is user-writable.
- `DiscordRichPresence-<version>-linux-x86_64.tar.gz` — distribution-neutral portable bundle.
- `discord-rich-presence_<version>_amd64.deb` — Debian/Ubuntu package.
- `discord-rich-presence-<version>-*.x86_64.rpm` — Fedora/Bazzite/RPM-family package.

Release metadata:

- `update-manifest.json` — Ed25519-signed asset metadata containing HTTPS URL, size, SHA-256, platform, and architecture.
- `SHA256SUMS.txt` — release checksums for all uploaded assets.

## Automatic updater behavior

The self-updater is fail-closed:

1. Fetch manifest over HTTPS and reject HTTPS-to-HTTP redirect downgrade.
2. Verify Ed25519 signature using the configured public key.
3. Choose an exact platform/architecture asset.
4. Download to a staged file over HTTPS.
5. Enforce the signed byte size.
6. Verify SHA-256.
7. Refuse source checkouts and unwritable/package-managed locations.
8. Wait for the running process to exit.
9. Rename the previous executable to a `.rollback` backup.
10. Replace with the staged binary and restart.
11. Observe a short restart-health window; if the new process exits immediately, restore and restart the rollback executable.

The `.rollback` backup is intentionally retained after a successful replacement. A longer application-level health handshake across multiple minutes is not yet implemented; the current automatic rollback protects replacement failures and immediate startup crashes.

## CI gates

Every pull request runs:

- Ubuntu and Windows Python 3.10/3.12 tests.
- compile checks and critical Ruff checks.
- short RSS/thread/FD-or-handle leak soak tests on Ubuntu and Windows.
- Windows PyInstaller portable smoke test.
- Windows Inno Setup installer build.
- Linux PyInstaller portable smoke test.
- Linux `tar.gz`, Debian, and RPM package creation/inspection.

A separate `Soak` workflow supports a longer manual duration and runs on a weekly schedule on both operating systems.

## Manual release matrix

The following cannot be proven reliably by hosted CI and must be checked on real desktops before a stable tag:

### Windows 10/11

- Install with Inno Setup and launch the control panel.
- Start/stop/restart the service repeatedly.
- Sign out/in with startup enabled and disabled.
- Confirm uninstall requests a graceful service stop and removes installed files plus startup registration.
- Start Discord before and after the service; verify reconnect without restarting the app.
- Kill Discord while Presence is active; restart Discord and verify recovery.
- Run a signed update from a user-writable portable install and verify `.rollback` preservation.
- Force an immediately crashing test build in an isolated release-candidate environment and verify automatic rollback.
- Verify Windows Defender/SmartScreen behavior. Authenticode signing is recommended before broad distribution.

### Fedora/Bazzite and Debian-family Linux

- Install/remove the native package and confirm the desktop entry resolves the packaged executable.
- Confirm package removal leaves user configuration intact by design.
- Enable and disable per-user desktop-session autostart before package removal.
- Validate the distribution-neutral portable bundle separately from the native package.

### KDE Plasma Wayland

- Confirm the UI reports the `kdotool` backend when installed.
- Focus several apps and verify exact foreground changes.
- Remove/disable `kdotool`; verify the UI reports unavailable and publishes no guessed foreground app.
- Lock the session and verify Presence clears.

### GNOME Wayland

- Verify the UI explicitly reports foreground detection unavailable.
- Install `swaymsg` if desired and confirm GNOME still does not use it or guess an app.
- Verify MPRIS/media detection can continue independently where applicable without claiming a foreground window.

### Sway

- Verify an active Sway session plus `swaymsg` reports the Sway backend.
- Focus tiled and floating windows and verify the focused node is used.
- Start outside Sway with `swaymsg` installed; verify the backend remains unavailable rather than querying another compositor.

### Browser companion

- Use a development extension following `docs/BROWSER_COMPANION.md`.
- Confirm bad/missing bearer tokens return HTTP 401.
- Confirm private/incognito tabs publish no title/service/URL.
- Confirm default URL policy keeps only the origin.
- Enable exact URL explicitly and confirm fragments are still removed.
- Switch to strict privacy and confirm final Discord payload contains no browser URL/button.

## Stable release checklist

- CI green on the release PR/head.
- Long soak completed at the desired duration on Windows and Linux.
- Manual desktop matrix completed for the environments claimed as supported.
- `CHANGELOG.md` reviewed.
- Update public key configured in the build/default configuration before enabling updates by default.
- Private update key present only in GitHub Actions secrets.
- Consider Authenticode signing for Windows installer/executable.
- Create and test a release candidate before the stable tag.
