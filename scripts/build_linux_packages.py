#!/usr/bin/env python3
"""Build portable tar.gz, Debian, and RPM packages from a PyInstaller binary."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


def safe_version(value: str) -> str:
    return value.strip().lstrip("v").replace("-", "~")


def build_portable(binary: Path, output: Path, version: str, root: Path) -> None:
    portable_name = f"DiscordRichPresence-{version}-linux-x86_64"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        portable = temp / portable_name
        portable.mkdir()
        app = portable / "DiscordRichPresence"
        shutil.copy2(binary, app)
        app.chmod(0o755)
        for name in ("README.md", "config.example.yaml", "LICENSE"):
            shutil.copy2(root / name, portable / name)
        with tarfile.open(output / f"{portable_name}.tar.gz", "w:gz") as archive:
            archive.add(portable, arcname=portable.name)


def build_deb(binary: Path, output: Path, version: str, root: Path) -> None:
    if shutil.which("dpkg-deb") is None:
        raise SystemExit("dpkg-deb is required to create the Debian package")
    with tempfile.TemporaryDirectory() as temp_dir:
        package_root = Path(temp_dir) / "pkg"
        debian = package_root / "DEBIAN"
        bin_dir = package_root / "usr" / "bin"
        app_dir = package_root / "usr" / "share" / "applications"
        doc_dir = package_root / "usr" / "share" / "doc" / "discord-rich-presence"
        for directory in (debian, bin_dir, app_dir, doc_dir):
            directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, bin_dir / "discord-rich-presence")
        (bin_dir / "discord-rich-presence").chmod(0o755)
        shutil.copy2(root / "packaging" / "linux" / "discord-rich-presence.desktop", app_dir)
        shutil.copy2(root / "README.md", doc_dir / "README.md")
        shutil.copy2(root / "LICENSE", doc_dir / "LICENSE")
        (debian / "control").write_text(
            "Package: discord-rich-presence\n"
            f"Version: {version}\n"
            "Section: utils\n"
            "Priority: optional\n"
            "Architecture: amd64\n"
            "Maintainer: imedkablavi\n"
            "Suggests: x11-utils, kdotool\n"
            "Description: Privacy-aware Discord Rich Presence manager\n"
            " Detects foreground activity locally and publishes configurable Discord Rich Presence.\n",
            encoding="utf-8",
        )
        deb_path = output / f"discord-rich-presence_{version}_amd64.deb"
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(package_root), str(deb_path)],
            check=True,
        )


def build_rpm(binary: Path, output: Path, version: str, root: Path) -> None:
    if shutil.which("rpmbuild") is None:
        raise SystemExit("rpmbuild is required to create the RPM package")
    with tempfile.TemporaryDirectory() as temp_dir:
        topdir = Path(temp_dir) / "rpmbuild"
        for name in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
            (topdir / name).mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, topdir / "SOURCES" / "DiscordRichPresence")
        shutil.copy2(
            root / "packaging" / "linux" / "discord-rich-presence.desktop",
            topdir / "SOURCES" / "discord-rich-presence.desktop",
        )
        spec = topdir / "SPECS" / "discord-rich-presence.spec"
        spec.write_text(
            "Name: discord-rich-presence\n"
            f"Version: {version}\n"
            "Release: 1%{?dist}\n"
            "Summary: Privacy-aware Discord Rich Presence manager\n"
            "License: MIT\n"
            "BuildArch: x86_64\n"
            "Source0: DiscordRichPresence\n"
            "Source1: discord-rich-presence.desktop\n"
            "\n"
            "%description\n"
            "Detect foreground activity locally and publish configurable Discord Rich Presence.\n"
            "\n"
            "%prep\n"
            "\n"
            "%build\n"
            "\n"
            "%install\n"
            "mkdir -p %{buildroot}/usr/bin %{buildroot}/usr/share/applications\n"
            "install -m 0755 %{SOURCE0} %{buildroot}/usr/bin/discord-rich-presence\n"
            "install -m 0644 %{SOURCE1} %{buildroot}/usr/share/applications/discord-rich-presence.desktop\n"
            "\n"
            "%files\n"
            "/usr/bin/discord-rich-presence\n"
            "/usr/share/applications/discord-rich-presence.desktop\n"
            "\n"
            "%changelog\n"
            "* Sun Aug 23 2026 imedkablavi - release package\n"
            "- Automated release build\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["rpmbuild", "-bb", "--define", f"_topdir {topdir}", str(spec)],
            check=True,
        )
        rpm_candidates = list((topdir / "RPMS" / "x86_64").glob("*.rpm"))
        if len(rpm_candidates) != 1:
            raise SystemExit(f"Expected one RPM artifact, found {len(rpm_candidates)}")
        shutil.copy2(rpm_candidates[0], output / rpm_candidates[0].name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path("release-dist"))
    args = parser.parse_args()

    binary = args.binary.resolve()
    if not binary.is_file():
        raise SystemExit(f"Missing binary: {binary}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    version = safe_version(args.version)
    root = Path(__file__).resolve().parents[1]

    build_portable(binary, output, version, root)
    build_deb(binary, output, version, root)
    build_rpm(binary, output, version, root)


if __name__ == "__main__":
    main()
