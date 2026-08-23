#!/usr/bin/env python3
"""Stamp app_version.py from a validated release tag before packaging."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: write-version.py vMAJOR.MINOR.PATCH", file=sys.stderr)
        return 2
    raw = sys.argv[1].strip()
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", raw)
    if not match:
        print(f"invalid release version: {raw}", file=sys.stderr)
        return 2
    version = ".".join(match.groups())
    target = Path(__file__).resolve().parent.parent / "app_version.py"
    target.write_text(
        '"""Build-time application version metadata."""\n\n'
        f'APP_VERSION = "{version}"\n',
        encoding="utf-8",
    )
    print(f"Stamped CYBREX version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
