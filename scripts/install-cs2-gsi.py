#!/usr/bin/env python3
"""Install the CYBREX Counter-Strike 2 GSI configuration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from cs2_gsi import discover_cs2_cfg_dirs, install_gsi_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Install the local Counter-Strike 2 GSI integration for CYBREX Rich Presence.'
    )
    parser.add_argument(
        '--cfg-dir',
        type=Path,
        help='Optional explicit Counter-Strike 2 game/csgo/cfg directory.',
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List detected Counter-Strike 2 cfg directories and exit.',
    )
    args = parser.parse_args()

    if args.list:
        locations = discover_cs2_cfg_dirs()
        if not locations:
            print('No Counter-Strike 2 cfg directory detected.')
            return 1
        for location in locations:
            print(location)
        return 0

    try:
        config = Config()
        target = install_gsi_config(config, args.cfg_dir)
    except Exception as exc:
        print(f'CS2 GSI installation failed: {exc}', file=sys.stderr)
        return 1

    print('Counter-Strike 2 GSI installed successfully.')
    print(f'Configuration: {target}')
    print('Restart Counter-Strike 2 if it is already running.')
    print('Then start Discord Rich Presence and join a match.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
