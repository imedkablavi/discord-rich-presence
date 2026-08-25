# Code signing policy

CYBREX Presence treats Windows code signing as a release-integrity control, not a marketing badge.

## Current status

The project is applying to the SignPath Foundation open-source program. The intended provider statement is:

> Free code signing provided by SignPath.io, certificate by SignPath Foundation.

Until SignPath approval and CI integration are complete, a Windows artifact must be described as **unsigned** unless its Authenticode signature has been verified successfully. Existing unsigned release candidates are not retroactively described as signed.

The generic release workflow intentionally blocks a stable tag when no Windows signing integration is configured. Unsigned builds may be produced only for CI validation or an explicitly marked GitHub prerelease.

## Signing scope

When signing is active, the Windows release scope is:

- `DiscordRichPresence.exe`;
- `CYBREX-Presence-Setup.exe`.

Browser Companion archives, Linux archives, checksum files and provenance files are verified through the release pipeline but are not Authenticode artifacts.

## Build and approval policy

A signable release must:

1. originate from this public GitHub repository;
2. be built by the repository's GitHub Actions release workflow;
3. pass the regression suite, dependency audit and high-severity static security checks;
4. pass packaged Windows/Linux smoke tests and installer install/launch/uninstall checks;
5. publish SHA-256 checksums and build provenance;
6. be associated with an explicit version tag;
7. receive explicit maintainer approval before a stable release is published.

Release candidates use tags containing a prerelease suffix such as `-rc4` and must be published as GitHub prereleases. Stable tags must not bypass the signing gate.

## Maintainer and signing roles

Primary maintainer / committer / release approver: **Imed Kablavi** (`imedkablavi` on GitHub).

The maintainer is responsible for reviewing release inputs, approving signing requests, protecting signing credentials, and revoking or stopping a release if provenance cannot be established.

Repository and SignPath accounts participating in signing should use multi-factor authentication. Signing private keys or certificate secrets must never be committed to the repository, placed in release artifacts, or pasted into issues or chat transcripts.

## Verification

Windows users should verify a signed artifact through Windows file properties or PowerShell `Get-AuthenticodeSignature`. SHA-256 values are published separately so users can also verify exact artifact bytes.

The release provenance file records the repository, tag, commit, workflow run, and whether the Windows Authenticode path was enabled for that build.

## Privacy and security

Code signing does not change the application's data-handling rules. See [Privacy](docs/PRIVACY.md) and [Security Policy](SECURITY.md).
