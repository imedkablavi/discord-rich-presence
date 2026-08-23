#!/usr/bin/env bash
set -euo pipefail

APP_NAME="CYBREX Presence"
BINARY_NAME="CYBREX-DiscordRichPresence-linux-x86_64"
INSTALL_ROOT="${CYBREX_INSTALL_ROOT:-${HOME}/.local/lib/cybrex-presence}"
BIN_DIR="${CYBREX_BIN_DIR:-${HOME}/.local/bin}"
DESKTOP_DIR="${CYBREX_DESKTOP_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/applications}"
INSTALL_TARGET="${INSTALL_ROOT}/DiscordRichPresence"
CLI_LINK="${BIN_DIR}/cybrex-presence"
DESKTOP_FILE="${DESKTOP_DIR}/cybrex-presence.desktop"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

fail() {
  printf 'CYBREX Presence installer: %s\n' "$*" >&2
  exit 1
}

uninstall_user() {
  rm -f -- "$CLI_LINK" "$DESKTOP_FILE"
  rm -f -- "$INSTALL_TARGET" "${INSTALL_TARGET}.old"
  rmdir -- "$INSTALL_ROOT" 2>/dev/null || true
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
  fi
  printf '%s removed. User configuration and logs were left in place.\n' "$APP_NAME"
}

if [[ "${1:-}" == "--uninstall" ]]; then
  uninstall_user
  exit 0
fi

SOURCE_BINARY="${1:-${SCRIPT_DIR}/${BINARY_NAME}}"
[[ -f "$SOURCE_BINARY" ]] || fail "binary not found: $SOURCE_BINARY"
[[ ! -L "$SOURCE_BINARY" ]] || fail "refusing a symlink as the installer source"

if [[ -f "${SCRIPT_DIR}/SHA256SUMS" ]] && command -v sha256sum >/dev/null 2>&1; then
  expected="$(awk -v name="$BINARY_NAME" '$2 == name || $2 == "*" name {print $1; exit}' "${SCRIPT_DIR}/SHA256SUMS")"
  if [[ -n "$expected" ]]; then
    actual="$(sha256sum "$SOURCE_BINARY" | awk '{print $1}')"
    [[ "$actual" == "$expected" ]] || fail "binary SHA-256 does not match the bundle manifest"
  fi
fi

mkdir -p -- "$INSTALL_ROOT" "$BIN_DIR" "$DESKTOP_DIR"
chmod 700 "$INSTALL_ROOT"

staged="${INSTALL_TARGET}.new.$$"
trap 'rm -f -- "$staged"' EXIT
cp -- "$SOURCE_BINARY" "$staged"
chmod 755 "$staged"
mv -f -- "$staged" "$INSTALL_TARGET"
trap - EXIT

ln -sfn -- "$INSTALL_TARGET" "$CLI_LINK"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=CYBREX Presence
Comment=Automatic privacy-aware Discord Rich Presence
Exec=${INSTALL_TARGET} --gui
TryExec=${INSTALL_TARGET}
Terminal=false
Categories=Utility;Game;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

printf '%s installed for the current user.\n' "$APP_NAME"
printf 'Application: %s\n' "$INSTALL_TARGET"
printf 'Command:     %s\n' "$CLI_LINK"
printf 'Desktop:     %s\n' "$DESKTOP_FILE"
printf 'No sudo/root access was used. The installed executable remains user-owned so in-app self-update can replace it.\n'
