# Contributing

Contributions are welcome when they keep the project predictable, local-first, and easy to maintain.

## Before opening a pull request

1. Create a branch from `main`.
2. Keep unrelated changes in separate pull requests.
3. Add or update tests for behavior changes.
4. Run the same checks used by CI:

```bash
python -m compileall -q .
ruff check . --select E9,F63,F7,F82
pytest -q
```

For Windows packaging changes, also build the executable:

```powershell
pyinstaller --clean --noconfirm discord-rich-presence.spec
```

## Detector changes

A detector should return `None` when it cannot determine activity reliably. Do not guess foreground activity from unrelated running processes. New detectors should respect the corresponding config toggle and should not bypass the privacy layer.

## Privacy-sensitive changes

Do not log secrets, full terminal history, exact browser data, or private file contents. When adding a new data source, document what is collected, where it is stored, and what reaches Discord.

## Pull requests

A useful pull request explains the problem, the behavior after the change, and how it was tested. Screenshots are useful for GUI changes. Avoid generated lock files, local config files, logs, runtime state, and build output.
