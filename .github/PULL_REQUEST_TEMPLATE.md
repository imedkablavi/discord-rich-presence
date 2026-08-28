## Summary

Describe the user-visible problem and the change that fixes it.

## Safety and privacy

- Data sources or permissions changed:
- Sensitive fields explicitly excluded:
- Cleanup, timeout, and fallback behavior:

## Validation

- [ ] `python -m compileall -q .`
- [ ] `ruff check . --select E9,F63,F7,F82`
- [ ] `pytest -q`
- [ ] Relevant Windows/Linux packaging or real-device checks documented

## Release impact

- [ ] No release behavior changed
- [ ] Prerelease-only impact
- [ ] Stable gate/signing impact is documented
