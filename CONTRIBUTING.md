# Contributing to CYBREX Presence

Contributions are welcome when they keep the project predictable, local-first, privacy-aware, and easy to maintain.

You do **not** need to understand the whole desktop application to contribute. The easiest first contribution is usually adding conservative standard support for a missing game through the Community Game Pack.

## Fastest first contribution: add a game without Python

Standard fallback definitions live in:

```text
game_packs/community.json
```

Read [`game_packs/README.md`](game_packs/README.md) first.

A good Community Game Pack entry uses an **exact executable/process basename** that you have verified from a real install or trustworthy upstream/community documentation. Do not submit full install paths, command lines, regexes, wildcards, DLL names, window-title guesses, or memory/module signatures.

Why this is deliberately strict:

- Steam, Epic Games and Heroic local manifests are authoritative when available;
- a fallback should never silently override a launcher-resolved title;
- exact executable matching reduces false positives;
- contributors can add useful coverage without introducing invasive detection techniques.

If you do not know the exact executable, open a **Game support request** instead of guessing.

## Standard vs enhanced game support

### Standard support

Standard support may include:

- game name;
- launcher/source;
- Steam AppID where applicable;
- artwork/store link;
- exact-process fallback.

This is usually suitable for Community Game Packs.

### Enhanced support

Enhanced support means live game-specific state such as map, game mode, role, party size, dimension or match timer.

Enhanced integrations require a documented/safe source such as:

- an official game-state integration;
- documented local API;
- supported mod/plugin API;
- server resource explicitly installed by a server owner;
- OS-provided session/media API;
- loopback-only companion that sends a minimal, documented payload.

The project does **not** accept game enrichment based on process-memory reading, DLL injection, input automation, packet manipulation, anti-cheat bypasses, credential/session scraping, or undocumented invasive hooks.

## Before opening a pull request

1. Create a branch from the current target branch for the work. For normal independent contributions, use `main`.
2. Keep unrelated changes in separate pull requests.
3. Add or update tests for behavior changes.
4. Explain what user problem the change solves.
5. For a new data source, document what is read, what is retained, what reaches Discord, and what is explicitly excluded.
6. Run the relevant local checks.

Core checks:

```bash
python -m compileall -q .
ruff check . --select E9,F63,F7,F82
pytest -q
```

Game/community changes should also keep the Gamer Integrations checks green.

For Windows packaging changes:

```powershell
pyinstaller --clean --noconfirm discord-rich-presence.spec
```

For Linux packaging changes, test without `sudo` when the package is intended to preserve user-owned self-update semantics.

## Detector changes

A detector should return `None` when it cannot determine activity reliably. Do not guess foreground activity from unrelated running processes.

New or modified detectors must:

- respect their config toggle;
- avoid publishing raw process/class strings as user-facing titles when a stable friendly name is available;
- fail closed when local metadata is malformed or ambiguous;
- avoid bypassing privacy/redaction layers;
- clean up listeners/threads when disabled or when the service exits;
- include tests for false positives and malformed data where practical.

## Privacy-sensitive changes

Do not log or publish secrets, full terminal history, account tokens, private file contents, exact private paths, unnecessary browser data, player identifiers, server IPs, chat, coordinates, credentials, session/auth tokens, or other fields unrelated to Presence.

When adding a new data source, document:

1. where the data comes from;
2. whether it is local or remote;
3. which fields CYBREX reads;
4. which fields are retained in memory;
5. which fields can reach Discord;
6. TTL/cleanup behavior;
7. privacy controls/defaults;
8. fields intentionally ignored.

Prefer minimal endpoints and minimal payloads over broad “all state” APIs.

## UI changes

For GUI changes:

- keep controls understandable without reading the README;
- prefer user terminology over internal detector/module names;
- include screenshots for meaningful visual changes;
- preserve Windows/Linux behavior unless the feature is explicitly platform-specific;
- avoid adding a setting unless the default cannot safely serve most users.

## Installer / release changes

The private Discord Social SDK toolchain is read during tagged builds with the
`SOCIAL_SDK_ASSET_TOKEN` Actions secret. It must be a fine-grained GitHub token
limited to this repository with **Contents: read** only. Do not grant workflow,
administration or write permissions, and never place the token in source,
release notes, artifacts or logs. Rotate it if access scope or ownership changes.

Installer changes should be treated as application code because they affect trust and update behavior.

Verify:

- install path and permissions;
- uninstall behavior;
- upgrade behavior;
- whether the installed executable remains compatible with verified self-update;
- release asset naming contracts expected by `updater.py`;
- checksums/signing flow;
- packaged smoke tests.

Do not move the Linux executable into a root-owned path and still claim in-app self-update works for a normal user unless the updater has been explicitly redesigned and tested for that packaging model.

## Pull requests

A useful pull request includes:

- the problem/use case;
- the behavior after the change;
- privacy/security impact;
- how it was tested;
- screenshots for GUI changes;
- real-device notes when CI cannot reproduce the environment.

Avoid committing:

- local config files;
- logs/runtime state;
- `.venv` or dependency caches;
- PyInstaller `build/` / `dist/` output;
- browser profiles;
- game logs containing personal data;
- generated files not required by the source tree.

## Good first issues

Good first issues should be small, independently testable, and not require access to private user data. Good candidates include:

- a verified Community Game Pack entry;
- documentation fixes;
- installer/documentation platform clarifications;
- tests for an already supported executable alias;
- artwork/store metadata fixes;
- non-invasive launcher manifest fixtures.

If an issue would require undocumented memory access, injection, anti-cheat bypasses, credential extraction, or broad packet inspection, it is not a suitable contribution for this project.
