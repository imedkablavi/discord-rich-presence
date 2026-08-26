# Download CYBREX Presence

Official desktop builds are distributed through this repository's [GitHub Releases](https://github.com/imedkablavi/discord-rich-presence/releases).

## Release channels

- **Stable:** normal-user channel after release qualification. Stable Windows publication requires verified Authenticode signing.
- **Preview:** release candidates used for qualification before stable promotion. A preview build may be unsigned and is labeled as a GitHub prerelease.

Always check the release label before installing.

## Windows

Published Windows assets include:

- `CYBREX-Presence-Setup.exe`: per-user installer
- `DiscordRichPresence.exe`: portable executable

For a signed build, verify the Authenticode signature before relying on publisher identity. An unsigned prerelease may trigger Windows SmartScreen.

## Linux x86_64

Published Linux assets include:

- `CYBREX-Presence-linux-x86_64.tar.gz`: user-level installation bundle
- `CYBREX-DiscordRichPresence-linux-x86_64`: portable executable

The user-level installer does not require `sudo`. It verifies the bundle checksum manifest when present and fails closed if verification cannot be completed successfully.

## Integrity verification

Release assets include SHA-256 sidecars. The release pipeline also publishes:

- `SHA256SUMS.txt`: combined release checksums
- `BUILD-PROVENANCE.txt`: repository, tag, commit, workflow run and Windows signing status

Linux example:

```bash
sha256sum -c CYBREX-DiscordRichPresence-linux-x86_64.sha256
```

Windows PowerShell example:

```powershell
Get-FileHash .\CYBREX-Presence-Setup.exe -Algorithm SHA256
Get-AuthenticodeSignature .\CYBREX-Presence-Setup.exe
```

Compare hashes only with values published on the same official GitHub Release.

## Official sources only

Do not rely on binaries re-uploaded to file-sharing sites or unofficial mirrors. The authoritative source code, releases, checksums and build provenance are published under this repository.

See [Code signing policy](../CODE_SIGNING.md), [Security Policy](../SECURITY.md) and [Privacy](PRIVACY.md).
