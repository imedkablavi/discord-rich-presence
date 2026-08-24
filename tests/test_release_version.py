from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "write-version.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("write_version", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_version_accepts_stable_and_rc_semver():
    module = _load_module()
    for value in ("v2.1.0", "2.1.0", "v2.1.0-rc3", "2.1.0-beta.2"):
        match = module._SEMVER_RE.fullmatch(value)
        assert match is not None
        assert match.group("version") == value.lstrip("v")


def test_release_version_rejects_invalid_or_unsafe_values():
    module = _load_module()
    for value in (
        "v2.1",
        "v02.1.0",
        "2.1.0-01",
        "2.1.0/rc3",
        "2.1.0 rc3",
        "latest",
    ):
        assert module._SEMVER_RE.fullmatch(value) is None
