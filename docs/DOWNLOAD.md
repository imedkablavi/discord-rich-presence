# Download CYBREX Presence

Official CYBREX Presence desktop builds are distributed through this repository's [GitHub Releases](https://github.com/imedkablavi/discord-rich-presence/releases).

## Release channels

- **Stable:** intended for normal users after release qualification. Stable Windows publication is blocked until the configured code-signing path succeeds.
- **Prerelease / release candidate:** intended for validation before stable promotion. A prerelease may be unsigned and must not be represented as a signed stable build.

The latest currently published release candidate is available from the repository's Releases page. Check the release label before installing it.

## Windows

The normal Windows distribution is:

- `CYBREX-Presence-Setup.exe` — per-user installer;
- `DiscordRichPresence.exe` — portable executable.

For a signed build, verify its Authenticode signature in Windows before relying on publisher identity. An unsigned artifact may trigger Windows SmartScreen.

## Linux x86_64

The normal Linux distributions are:

- `CYBREX-Presence-linux-x86_64.tar.gz` — user-level installation bundle;
- `CYBREX-DiscordRichPresence-linux-x86_64` — portable executable.

The user-level installer does not require `sudo` and verifies the bundle SHA-256 manifest before installation when the manifest is present.

## Integrity verification

Release assets include SHA-256 sidecars and the generic release pipeline publishes:

- `SHA256SUMS.txt` — combined release checksums;
- `BUILD-PROVENANCE.txt` — repository, tag, commit, workflow run and Windows signing-path status.

Example verification on Linux:

```bash
sha256sum -c CYBREX-DiscordRichPresence-linux-x86_64.sha256
```

Example verification on Windows PowerShell:

```powershell
Get-FileHash .\CYBREX-Presence-Setup.exe -Algorithm SHA256
Get-AuthenticodeSignature .\CYBREX-Presence-Setup.exe
```

Compare hashes only with values published on the same official GitHub Release.

## Code signing policy

The project is applying to the SignPath Foundation open-source code-signing program.

> Free code signing provided by SignPath.io, certificate by SignPath Foundation.

This statement describes the intended SignPath provider relationship and does **not** claim that an existing artifact is signed before SignPath approval and CI integration are complete. The release workflow is designed to fail closed for stable Windows publication when signing is unavailable.

See the full [Code signing policy](../CODE_SIGNING.md), [Security Policy](../SECURITY.md), and [Privacy Policy](PRIVACY.md).

## Official sources only

Do not rely on binaries re-uploaded to file-sharing sites or unofficial mirrors. The authoritative source code, releases, checksums and build provenance are under:

`https://github.com/imedkablavi/discord-rich-presence`
