#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/browser_extension"

if command -v xdg-user-dir >/dev/null 2>&1; then
    DOWNLOAD_DIR="$(xdg-user-dir DOWNLOAD 2>/dev/null || true)"
else
    DOWNLOAD_DIR=""
fi
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$HOME/Downloads}"
DEST_DIR="${1:-$DOWNLOAD_DIR/CYBREX-Browser-Companion}"

required_files=(manifest.json background.js content.js README.md)
for file in "${required_files[@]}"; do
    if [[ ! -f "$SOURCE_DIR/$file" ]]; then
        printf 'Missing Browser Companion file: %s\n' "$SOURCE_DIR/$file" >&2
        exit 1
    fi
done

rm -rf -- "$DEST_DIR"
mkdir -p -- "$DEST_DIR"
for file in "${required_files[@]}"; do
    cp -- "$SOURCE_DIR/$file" "$DEST_DIR/$file"
done

printf '\nBrowser Companion prepared successfully.\n'
printf 'In Brave, open brave://extensions, enable Developer mode, choose Load unpacked, and select:\n\n%s\n\n' "$DEST_DIR"
printf 'Do not select the discord-rich-presence repository root.\n'
