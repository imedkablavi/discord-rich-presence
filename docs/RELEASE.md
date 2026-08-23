# Release Engineering

## Versioning

The project uses semantic versions. Development builds keep `version.py` on a `-dev` version. The release workflow stamps the executable with the tag version before packaging.

Recommended progression:

1. Create a release candidate such as `v2.1.0-rc1`.
2. Validate packaged artifacts on real Windows and Linux desktops.
3. Complete the manual matrix below.
4. Tag `v2.1.0` only after the tested release candidate is acceptable.

## Update signing bootstrap

Generate a dedicated Ed25519 keypair once:

```bash
python scripts/generate_update_key.py
```

Store `UPDATE_SIGNING_PRIVATE_KEY_B64` only as a GitHub Actions repository secret with that exact name. Never commit the private key, put it in application configuration, or ship it inside an executable.

Copy only `UPDATE_SIGNING_PUBLIC_KEY_B64` into the shipped/default configuration as `updates.public_key`. A tagged release intentionally fails before publishing if the private signing secret is missing.

Key rotation is a release/security event. When possible, ship the new public key through a version signed by the old key before retiring the old private key.

## Release artifacts

Windows:

- `DiscordRichPresence-windows-x86_64.exe` — raw executable consumed by the signed updater.
- `DiscordRichPresence-<version>-windows-x86_64-portable.zip` — portable bundle.
- `DiscordRichPresence-Setup-<version>-windows-x86_64.exe` — per-user Inno Setup installer with uninstall support.

The Windows installer uses the current user's application directory rather than a protected system directory. This keeps normal updates non-privileged while preserving shortcuts, startup registration, and uninstall support.

Linux:

- `DiscordRichPresence-linux-x86_64` — raw portable executable used by the signed updater when its install directory is user-writable.
- `DiscordRichPresence-<version>-linux-x86_64.tar.gz` — distribution-neutral portable bundle.
- `discord-rich-presence_<version>_amd64.deb` — Debian/Ubuntu package.
- `discord-rich-presence-<version>-*.x86_64.rpm` — Fedora/Bazzite/RPM-family package.

Native DEB/RPM files stay owned by the package manager. The application must not silently overwrite those package-managed files.

Release metadata:

- `update-manifest.json` — Ed25519-signed metadata containing HTTPS URL, signed size, SHA-256, platform, architecture, and asset kind.
- `SHA256SUMS.txt` — checksums for all uploaded release assets.

## Updater behavior

Both startup auto-update and the user-approved **Update now** path use the same verification pipeline:

1. Fetch the manifest over HTTPS and reject an HTTPS-to-HTTP redirect downgrade.
2. Verify its Ed25519 signature using the configured public key.
3. Select the exact platform/architecture asset.
4. Download into a staging location.
5. Report byte progress to the control panel for a manual update.
6. Enforce the signed byte size.
7. Verify SHA-256.
8. Refuse source checkouts and unwritable/package-managed locations.
9. For a control-panel update, stop the background service before replacement.
10. Wait for the remaining app process to exit.
11. Rename the previous executable to a `.rollback` backup.
12. Replace it with the staged executable and restart.
13. Observe a short restart-health window. If the new process exits immediately, restore and restart the rollback executable.

The `.rollback` backup is retained after a successful replacement. Update failures before scheduling leave the current executable untouched. If the control panel stopped a running service and preparation then fails, it starts the service again.

A longer multi-minute application health handshake is not implemented yet; the current rollback covers replacement failure and immediate startup failure.

## Control-panel update states

The **Overview** update card exposes real updater state rather than a decorative button:

- current version / updater configuration state
- check in progress
- update available with signed asset size
- `Update now`
- real download percentage
- verification/preparation errors
- ready/restarting state
- link to GitHub release notes

The UI only exits for restart after the updater reports `staged=True`.

## CI gates

Every pull request runs:

- Ubuntu and Windows Python 3.10/3.12 tests.
- compile checks and critical Ruff checks.
- short RSS/thread/FD-or-handle leak soak tests on Ubuntu and Windows.
- Windows PyInstaller portable smoke test.
- Windows Inno Setup installer build.
- Linux PyInstaller portable smoke test.
- Linux `tar.gz`, Debian, and RPM package creation/inspection.
- updater, rollback, privacy, Wayland fail-safe, RPC recovery, gaming false-positive, startup, and detector-switch regressions.

A separate `Soak` workflow supports a longer manual duration and runs on a weekly schedule on both operating systems.

## Manual release matrix

Hosted CI cannot prove desktop/compositor/Discord behavior. Check these on real systems before a stable tag.

### Windows 10/11

- Install with Inno Setup and confirm the app lands in the per-user application directory.
- Launch the control panel from Start Menu and optional desktop shortcut.
- Start/stop/restart the service repeatedly.
- Sign out/in with startup enabled and disabled.
- Confirm uninstall requests a graceful service stop and removes startup registration.
- Start Discord before and after the service; verify reconnect without restarting the app.
- Kill Discord while Presence is active; restart Discord and verify recovery.
- Publish a signed test release and verify **Check for updates → Update now → progress → restart**.
- Confirm settings survive the update.
- Confirm the previous executable is preserved as `.rollback`.
- Force an immediately crashing test update in an isolated RC environment and verify automatic rollback.
- Verify Windows Defender/SmartScreen behavior. Authenticode signing is recommended before broad distribution.

### Fedora/Bazzite and Debian-family Linux

- Install/remove the native package and confirm the desktop entry resolves the packaged executable.
- Confirm package removal leaves user configuration intact by design.
- Enable and disable per-user desktop-session autostart before package removal.
- Validate the distribution-neutral portable bundle separately from the native package.
- Run the signed updater from a user-writable portable install.
- Confirm a native package install refuses direct self-replacement and tells the user to use the package manager.

### KDE Plasma Wayland

- Confirm the UI reports the `kdotool` backend when installed.
- Focus several apps and verify exact foreground changes.
- Disable `kdotool`; verify the UI reports unavailable and publishes no guessed foreground app.
- Lock the session and verify Presence clears.

### GNOME Wayland

- Verify the UI explicitly reports foreground detection unavailable.
- Install `swaymsg` if desired and confirm GNOME still does not use it or guess an app.
- Verify independent media integrations do not cause the app to claim an unsupported foreground window.

### Sway

- Verify an active Sway session plus `swaymsg` reports the Sway backend.
- Focus tiled and floating windows and verify the focused node is used.
- Start outside Sway with `swaymsg` installed; verify the backend remains unavailable.

### Browser companion

- Use a development extension following `docs/BROWSER_COMPANION.md`.
- Confirm bad/missing bearer tokens return HTTP 401.
- Confirm private/incognito tabs publish no title/service/URL.
- Confirm default URL policy keeps only the origin.
- Enable exact URL explicitly and confirm fragments are still removed.
- Switch to strict privacy and confirm the final Discord payload contains no browser URL/button.

### Activity switches

- Disable each Activity category one at a time and verify its detector stops producing Presence.
- Disable all categories and verify no generic or specialized activity is published.
- Re-enable one category and verify only matching foreground activity is considered.

## Stable release checklist

- CI green on the final release PR head.
- Long soak completed at the desired duration on Windows and Linux.
- Manual desktop matrix completed for every environment claimed as supported.
- Current UI screenshots captured from the release candidate and reviewed.
- `CHANGELOG.md` reviewed.
- Update public key configured in the shipped/default configuration before enabling update checks by default.
- Matching private update key present only in GitHub Actions secrets.
- Browser extension packaging either completed or clearly documented as not bundled.
- Consider Authenticode signing for the Windows installer/executable.
- Create and test a release candidate before the stable tag.
