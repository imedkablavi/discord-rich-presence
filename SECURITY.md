# Security Policy

## Supported versions

Security fixes are applied to the current release line and the `main` branch. Older builds should be upgraded before reporting a problem that may already be fixed.

## Reporting a vulnerability

Please do not publish sensitive security reports, tokens, private paths, or terminal output in a public issue.

Use GitHub's private vulnerability reporting for this repository when available. Include:

- the affected version or commit;
- operating system and Python version;
- a short reproduction case;
- what data or behavior is exposed;
- any logs needed to reproduce the issue, with personal data removed.

For ordinary bugs that do not expose private data or create a security boundary issue, use a normal GitHub issue.

## Local data

The service keeps configuration, logs, runtime state, and optional terminal-hook cache files on the local machine. Selected activity data is sent to Discord through Discord Desktop RPC when Rich Presence is enabled. The project does not operate its own telemetry or analytics backend.

See [docs/PRIVACY.md](docs/PRIVACY.md) for the data paths and privacy modes.
