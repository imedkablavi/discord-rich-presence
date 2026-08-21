# Security Policy

## Supported versions

Security fixes are applied to the current release line and the `main` branch. Older builds should be upgraded before reporting a problem that may already be fixed.

## Reporting a vulnerability

Do not publish sensitive security reports, tokens, private paths, browser URLs, terminal history, or unredacted diagnostic output in a public issue.

Use GitHub's private vulnerability reporting for this repository when available. Include:

- the affected version or commit;
- operating system and Python version;
- a short reproduction case;
- what data or behavior is exposed;
- any logs needed to reproduce the issue, with personal data removed.

For ordinary bugs that do not expose private data or create a security-boundary issue, use a normal GitHub issue.

## Security model

The service is a local desktop application. It reads local activity selected by enabled detectors and sends only the final Rich Presence payload to Discord Desktop RPC. The project does not operate its own telemetry, analytics, browser-history, or command-history backend.

The optional Browser Companion listens only on loopback (`127.0.0.1`) and applies origin checks, a marker header, request-size limits, short record TTLs, bounded in-memory storage, socket/request timeouts, and clean shutdown. Loopback is **not** a security boundary against another malicious process already running as the same OS user.

On POSIX systems, configuration/runtime/log/cache directories and sensitive files are hardened to user-only permissions where possible. Persistent logs intentionally do not record complete activity payloads.

See [docs/PRIVACY.md](docs/PRIVACY.md) for detailed data paths and privacy behavior.

## Dependency and code checks

Pull-request QA includes:

- Python tests on supported Windows and Linux/Python combinations;
- `pip check` dependency consistency checks;
- `pip-audit` against runtime requirements for known published vulnerabilities;
- Bandit high-severity Python security scanning;
- JavaScript/Manifest V3 validation for the Browser Companion;
- shell-hook syntax and POSIX cache-permission checks;
- Windows and Linux packaged-binary smoke tests.

A dependency advisory that affects the resolved runtime requirements is treated as a release blocker until it is upgraded, removed, or explicitly investigated.

## Release integrity

Tagged releases publish SHA-256 checksum files for the Windows executable, Linux executable, and Browser Companion archive. Verify the checksum before running an artifact when integrity matters.

The release workflow supports Windows Authenticode signing when a real code-signing PFX certificate is configured through repository secrets. Development or releases produced without those secrets remain unsigned and can trigger Windows SmartScreen.

Browser-store signing/publication is separate from the unpacked Browser Companion archive in this repository; official Chrome Web Store or Firefox AMO publication requires the corresponding store account and review/signing process.
