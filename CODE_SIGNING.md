# Code signing policy

CYBREX Presence treats Windows code signing as a release-integrity control.

## Current policy

A Windows artifact is described as signed only when its Authenticode signature has been created and verified successfully during the release workflow.

The release pipeline supports Authenticode PFX signing for:

- `DiscordRichPresence.exe`
- `CYBREX-Presence-Setup.exe`

Stable Windows publication is blocked when the signing path is not configured and verified. An explicitly marked GitHub prerelease may be unsigned, in which case the release must remain clearly identified as a prerelease and Windows SmartScreen may warn users.

SHA-256 checksums and build provenance are published independently of Authenticode signing.

## Release requirements

A release build must:

1. originate from this public repository and an explicit version tag;
2. run the regression suite before packaging;
3. pass dependency and high-severity static security checks;
4. pass packaged Windows and Linux smoke tests;
5. pass installer install, launch and uninstall checks;
6. publish SHA-256 verification data and build provenance;
7. not claim a signing status that the workflow did not verify.

Prerelease tags contain a suffix such as `-rc6` and are published as GitHub prereleases.

## Credential handling

Signing certificates, private keys and certificate passwords must never be committed to the repository, included in release assets or pasted into issues, pull requests or public diagnostics.

Repository secrets used for signing must remain limited to the release signing steps.

## User verification

Windows users can inspect Authenticode status with PowerShell:

```powershell
Get-AuthenticodeSignature .\CYBREX-Presence-Setup.exe
```

Release pages also publish SHA-256 values so users can verify exact artifact bytes independently of publisher identity.

The release provenance file records the repository, tag, commit, workflow run and whether the Windows Authenticode path was enabled for that build.

See [Download and integrity verification](docs/DOWNLOAD.md) and [Security Policy](SECURITY.md).
