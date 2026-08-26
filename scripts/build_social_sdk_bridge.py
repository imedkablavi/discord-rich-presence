#!/usr/bin/env python3
"""Build and stage the optional Discord Social SDK Rich Presence helper.

The Discord SDK archive itself is intentionally not vendored in this repository.
Point this script at an SDK extracted from Discord's Developer Portal. The staged
output contains only the CYBREX helper, the platform runtime library and the SDK
open-source notices needed by the packaged application.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SOURCE = ROOT / "native" / "discord_social_sdk_bridge"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def platform_layout(platform_name: str) -> tuple[str, Path]:
    if platform_name == "windows":
        return "cybrex-discord-social-sdk.exe", Path("bin/release/discord_partner_sdk.dll")
    if platform_name == "linux":
        return "cybrex-discord-social-sdk", Path("lib/release/libdiscord_partner_sdk.so")
    if platform_name == "darwin":
        return "cybrex-discord-social-sdk", Path("lib/release/libdiscord_partner_sdk.dylib")
    raise ValueError(f"unsupported Social SDK build platform: {platform_name}")


def normalized_platform(value: str | None = None) -> str:
    raw = (value or sys.platform).lower()
    if raw.startswith("win"):
        return "windows"
    if raw.startswith("linux"):
        return "linux"
    if raw.startswith("darwin") or raw.startswith("mac"):
        return "darwin"
    raise ValueError(f"unsupported Social SDK build platform: {raw}")


def validate_sdk_root(sdk_root: Path, platform_name: str) -> dict[str, Path]:
    sdk_root = sdk_root.expanduser().resolve()
    include = sdk_root / "include" / "discordpp.h"
    c_header = sdk_root / "include" / "cdiscord.h"
    notice = sdk_root / "License-Notices.txt"
    helper_name, runtime_relative = platform_layout(platform_name)
    runtime = sdk_root / runtime_relative

    missing = [path for path in (include, c_header, runtime, notice) if not path.is_file()]
    if missing:
        joined = "\n  - ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Discord Social SDK is incomplete; missing:\n  - {joined}")

    if platform_name == "windows":
        link_library = sdk_root / "lib" / "release" / "discord_partner_sdk.lib"
    elif platform_name == "linux":
        link_library = sdk_root / "lib" / "release" / "libdiscord_partner_sdk.so"
    else:
        link_library = sdk_root / "lib" / "release" / "libdiscord_partner_sdk.dylib"
    if not link_library.is_file():
        raise FileNotFoundError(f"Discord Social SDK link library is missing: {link_library}")

    return {
        "sdk_root": sdk_root,
        "header": include,
        "c_header": c_header,
        "runtime": runtime,
        "link_library": link_library,
        "notice": notice,
        "helper_name": Path(helper_name),
    }


def find_built_helper(build_dir: Path, helper_name: str) -> Path:
    candidates = [
        build_dir / helper_name,
        build_dir / "Release" / helper_name,
        build_dir / "RelWithDebInfo" / helper_name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    matches = [path for path in build_dir.rglob(helper_name) if path.is_file()]
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"built Social SDK helper was not found under {build_dir}")


def run_build(
    sdk_root: Path,
    output_dir: Path,
    *,
    sdk_version: str,
    platform_name: str,
    build_dir: Path,
) -> dict[str, object]:
    layout = validate_sdk_root(sdk_root, platform_name)
    if not BRIDGE_SOURCE.is_dir():
        raise FileNotFoundError(f"bridge source directory is missing: {BRIDGE_SOURCE}")

    build_dir = build_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    configure = [
        "cmake",
        "-S",
        str(BRIDGE_SOURCE),
        "-B",
        str(build_dir),
        f"-DDISCORD_SOCIAL_SDK_ROOT={layout['sdk_root']}",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    subprocess.run(configure, cwd=ROOT, check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--config", "Release", "--parallel", "2"],
        cwd=ROOT,
        check=True,
    )

    helper_name = str(layout["helper_name"])
    helper = find_built_helper(build_dir, helper_name)
    runtime = Path(layout["runtime"])
    notice = Path(layout["notice"])

    staged_helper = output_dir / helper_name
    staged_runtime = output_dir / runtime.name
    staged_notice = output_dir / "Discord-Social-SDK-Notices.txt"
    shutil.copy2(helper, staged_helper)
    shutil.copy2(runtime, staged_runtime)
    shutil.copy2(notice, staged_notice)
    if platform_name != "windows":
        staged_helper.chmod(0o755)

    files = [staged_helper, staged_runtime, staged_notice]
    manifest: dict[str, object] = {
        "schema": 1,
        "sdk_version": sdk_version.strip() or "unknown",
        "platform": platform_name,
        "architecture": platform.machine() or "unknown",
        "source": "Discord Developer Portal Social SDK download",
        "files": {
            path.name: {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
            for path in files
        },
    }
    manifest_path = output_dir / "SOCIAL_SDK_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sdk-root",
        default=os.environ.get("DISCORD_SOCIAL_SDK_ROOT", ""),
        help="Extracted discord_social_sdk directory from the Developer Portal archive",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "build" / "social-sdk-bundle"),
        help="Directory that receives the helper/runtime bundle",
    )
    parser.add_argument(
        "--build-dir",
        default=str(ROOT / "build" / "discord-social-sdk-bridge"),
    )
    parser.add_argument("--sdk-version", default=os.environ.get("DISCORD_SOCIAL_SDK_VERSION", "unknown"))
    parser.add_argument("--platform", dest="platform_name", default=None)
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.sdk_root:
        raise SystemExit("--sdk-root or DISCORD_SOCIAL_SDK_ROOT is required")
    platform_name = normalized_platform(args.platform_name)
    sdk_root = Path(args.sdk_root)
    layout = validate_sdk_root(sdk_root, platform_name)
    if args.check_only:
        print(f"Discord Social SDK input OK: {layout['sdk_root']}")
        print(f"Platform: {platform_name}")
        print(f"Runtime: {layout['runtime']}")
        return 0

    manifest = run_build(
        sdk_root,
        Path(args.output_dir),
        sdk_version=args.sdk_version,
        platform_name=platform_name,
        build_dir=Path(args.build_dir),
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
