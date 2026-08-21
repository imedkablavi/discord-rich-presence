# Privacy

Discord Rich Presence reads local activity so it can build a status for Discord. There is no project-operated telemetry, analytics, or browser-history service.

## What the service can read

Depending on the enabled detectors and operating system, the service may read:

- the foreground application name and window title;
- editor filenames and workspace names;
- media player metadata and playback position;
- browser window titles and recognized service names;
- game process names;
- optional terminal commands written by the supplied shell hooks.

When the optional Browser Companion extension is installed, the desktop service can also receive the current tab URL/title, recognized service/domain, tab focus/visibility state, and HTML audio/video playback metadata. This lets the service distinguish, for example, a background YouTube tab from another foreground tab when Chromium MPRIS does not expose the real media URL.

The Companion sends snapshots only to the loopback bridge on `127.0.0.1`. The bridge bounds request bodies, keeps at most 100 short-lived records, removes closed tabs, and clears its in-memory records when it stops. The browser-side request is also aborted after a short timeout so a half-open local bridge does not leave extension requests hanging.

## Browser URL privacy

Without the Browser Companion, browser links are inferred only from visible window-title information.

With the Companion, the exact URL is available locally so detection can be accurate. Balanced mode does **not** publish the exact URL by default. `privacy.browser_url_mode` controls what can survive privacy filtering:

- `none` — publish no browser URL;
- `domain` — publish only the origin, for example `https://www.youtube.com` (default);
- `path` — include the path but remove query parameters and fragments;
- `full` — keep ordinary query parameters, redact values of sensitive token/auth/key parameters, and always remove the URL fragment.

If a page title itself requires redaction, the associated URL is removed instead of trying to preserve a derived link.

Private/incognito foreground windows are treated conservatively and do not reuse a normal-tab Companion snapshot. Browsers normally keep extensions disabled in private windows unless the user explicitly grants private-window access.

## What reaches Discord

Only the Rich Presence payload produced after detector rules and privacy filtering is sent through Discord Desktop RPC. A final protocol sanitizer validates the payload before it reaches `pypresence`, including optional text fields, URLs, buttons, image values, timestamps, and party fields.

The resulting payload can contain activity text, image keys or external image URLs, timestamps, buttons, and configured URLs.

Known applications can attempt to use external raster artwork URLs. External artwork rendering depends on the Discord client; Developer Portal asset keys remain the more deterministic option for release-critical icons. Set `images.use_external_app_icons: false` to use configured Discord asset keys only, or use `images.icon_overrides` for a specific application.

If you do not want a category published, disable its detector. `rules.enabled_detectors.application` controls the generic fallback for applications that do not match a specialized detector.

## Privacy modes

### `off`

Keeps detected activity details with no project-side redaction. Use this only if you are comfortable publishing the detected text. With Browser Companion enabled, exact local browser URLs may reach the Rich Presence builder.

### `balanced`

Keeps useful context while applying configured redaction patterns and reducing path and browser-URL exposure. This is the default mode.

For terminal commands, values following common sensitive flags such as token, password, authorization, API-key, access-key, and private-key arguments are redacted in addition to configured regex rules. Exact Companion URLs use the `browser_url_mode` policy above.

### `strict`

Uses generic descriptions and removes identifying browser URLs and buttons.

The service can also clear Rich Presence when a known lock-screen window is detected.

## Local files and local network state

### Windows

- Configuration: `%APPDATA%\discord-rich-presence\config.yaml`
- Logs: `%LOCALAPPDATA%\discord-rich-presence\logs\app.log`
- Runtime state: `%LOCALAPPDATA%\discord-rich-presence\runtime\`
- Terminal hook cache: `%LOCALAPPDATA%\discord-rich-presence\cache\`

These paths rely on the per-user Windows profile/ACL model.

### Linux / POSIX

- Configuration: `~/.config/discord-rich-presence/config.yaml`
- Logs: `~/.local/state/discord-rich-presence/app.log`
- Runtime state: `~/.local/state/discord-rich-presence/runtime/`
- Terminal hook cache: `~/.cache/discord-rich-presence/`

The service hardens its sensitive POSIX directories to user-only access (`0700`) and sensitive files to `0600`, including older files it encounters where possible.

The optional Browser Companion bridge listens only on `127.0.0.1` (default port `32191`). POST requests require the Companion marker header and browser-origin CORS checks reject normal web-page origins. This is not intended as a security boundary against a malicious process already running as the same local user.

## Logs

Logs rotate locally and are bounded. Persistent logs intentionally avoid recording complete Rich Presence payloads, so normal debug logging does not persist full page titles, commands, buttons, or activity URLs.

An explicit interactive `--dry-run` prints the full sanitized payload to the terminal because that mode is intended for local diagnosis. Users should therefore avoid posting raw dry-run output publicly without reviewing it first.

Runtime state is used by the control panel and single-instance guard. It may include a short activity summary while the service is running and is removed on clean shutdown.

## Terminal hooks

Terminal command tracking is optional. Bash, Zsh, and PowerShell hooks write commands to local per-shell cache files. The detector attempts to match the foreground terminal process tree before using a command entry. If a PID-scoped hook cache exists but does not match the focused terminal, the detector does not fall back to another terminal's command.

Raw command cache entries expire according to `rules.terminal_command_ttl_secs`; the hardened default is 900 seconds (15 minutes). Expired PID-scoped entries are deleted, and the cache is bounded even when many shells are created.

Do not enable terminal tracking on a machine where displaying command text in Discord is unacceptable, even with redaction enabled.
