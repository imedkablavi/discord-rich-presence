# Privacy

CYBREX Presence reads local activity so it can build a Discord status. The project does not operate an activity telemetry, analytics, browser-history or command-history backend.

## What the application can read

Depending on enabled detectors and operating system, CYBREX may read:

- foreground application name and window title
- editor filenames and workspace names
- media metadata and playback position
- browser window titles and recognized service names
- game identity and supported local game-state sources
- optional terminal commands written by the supplied shell hooks

The optional Browser Companion can provide the current tab URL/title, recognized service/domain, tab focus/visibility and HTML audio/video metadata to the local desktop bridge. Records are bounded, short-lived and memory-only.

Optional enhanced game integrations use only their documented local sources. Strict privacy suppresses deep game telemetry collection, including supported CS2, League, FiveM, Minecraft, Squad and War Thunder enrichment paths, instead of collecting rich state and hiding it only after collection.

## Browser URL privacy

Without Browser Companion, browser links are inferred only from visible foreground-window information.

With Browser Companion, the exact URL is available locally for accurate detection. `privacy.browser_url_mode` controls what can survive privacy filtering on ordinary pages:

- `none`: publish no browser URL
- `domain`: publish only the origin, for example `https://www.youtube.com` (default)
- `path`: include the path but remove query parameters and fragments
- `full`: keep ordinary query parameters, redact sensitive token/auth/key values and remove the fragment

If a page title itself requires redaction, the associated URL is removed.

Recognized social and messaging services use a stricter contract regardless of ordinary browser URL mode. Conversation names, contact names, profile/post identifiers, deep social links and social-page media metadata are removed before Presence building.

Private or incognito foreground windows are handled conservatively and do not reuse a normal-tab Companion snapshot.

## What reaches Discord

Only the Rich Presence payload produced after detector rules and privacy filtering is sent to Discord. A final protocol sanitizer validates optional text, URLs, buttons, image values, timestamps and party fields before transport.

The final payload may contain activity text, image keys or safe public image URLs, timestamps, buttons and configured public URLs.

Known applications can use public HTTPS raster artwork URLs. Developer Portal asset keys remain the deterministic fallback when direct images are unsupported by the active Discord transport/client.

If you do not want a category published, disable its detector. `rules.enabled_detectors.application` controls the generic fallback for applications that do not match a specialized detector.

## Privacy modes

### `off`

Minimal project-side redaction. Use this only if you are comfortable publishing detected activity text and configured browser context.

### `balanced`

Default mode. Keeps useful context while applying secret/path redaction and reducing browser URL exposure.

For terminal commands, values following common sensitive flags such as token, password, authorization, API-key, access-key and private-key arguments are redacted in addition to configured rules.

### `strict`

Uses generic activity descriptions, removes identifying browser URLs/buttons and suppresses deep game telemetry collection.

The service also clears Rich Presence when a supported lock-screen state is detected.

## Local files

### Windows

- Configuration: `%APPDATA%\discord-rich-presence\config.yaml`
- Logs: `%LOCALAPPDATA%\discord-rich-presence\logs\app.log`
- Runtime state: `%LOCALAPPDATA%\discord-rich-presence\runtime\`
- Terminal hook cache: `%LOCALAPPDATA%\discord-rich-presence\cache\`

These paths use the per-user Windows profile and ACL model.

### Linux / POSIX

- Configuration: `~/.config/discord-rich-presence/config.yaml`
- Logs: `~/.local/state/discord-rich-presence/app.log`
- Runtime state: `~/.local/state/discord-rich-presence/runtime/`
- Terminal hook cache: `~/.cache/discord-rich-presence/`

CYBREX hardens sensitive POSIX directories to user-only access (`0700`) and sensitive files to `0600` where supported.

## Loopback services

Browser, game and companion bridges bind to IPv4 loopback only. They use bounded request sizes, short timeouts, fixed or bounded worker counts, short TTLs and explicit parsing rules.

Loopback is not a security boundary against another malicious process already running as the same operating-system user.

War Thunder enrichment reads only fixed `127.0.0.1:8111` telemetry endpoints used by the integration and applies response-size, timeout and cache bounds. Tactical map objects, chat and HUD/damage feeds are outside the Presence data path.

## Logs

Logs rotate locally and are bounded. Persistent logs intentionally avoid complete Rich Presence payloads, so normal logging does not persist full page titles, commands, buttons or activity URLs.

An explicit `--dry-run` prints the full sanitized payload to the local terminal for diagnosis. Review that output before sharing it publicly.

Runtime state is used by the control panel and instance guard. It may include a short activity summary while the service runs and is removed on clean shutdown.

## Terminal hooks

Terminal command tracking is optional. Bash, Zsh and PowerShell hooks write commands to local per-shell cache files. The detector attempts to match the focused terminal process tree before using a command entry.

Raw command cache entries expire according to `rules.terminal_command_ttl_secs`; the hardened default is 900 seconds. Expired PID-scoped entries are deleted and the cache remains bounded.

Do not enable terminal tracking on a machine where publishing command text to Discord is unacceptable, even with redaction enabled.
