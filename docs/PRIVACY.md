# Privacy

Discord Rich Presence reads local activity so it can build a status for Discord. There is no project-operated telemetry or analytics service.

## What the service can read

Depending on the enabled detectors and operating system, the service may read:

- the foreground application name and window title;
- editor filenames and workspace names;
- media player metadata and playback position;
- browser window titles and recognized service names;
- game process names;
- optional terminal commands written by the supplied shell hooks.

The browser detector does not read the exact browser tab URL. Links shown in Rich Presence are inferred search or service links from visible window-title information.

## What reaches Discord

Only the Rich Presence payload produced after detector rules and privacy filtering is sent through Discord Desktop RPC. That payload can contain activity text, image keys or external image URLs, timestamps, buttons, and configured URLs.

By default, known applications can use external artwork URLs from the Simple Icons CDN so the Rich Presence image follows the application actually in use. The service itself does not download those images; the URL is included in the Discord activity payload. Set `images.use_external_app_icons: false` to use only Discord Developer Portal asset keys, or use `images.icon_overrides` to select your own asset key or image URL for a specific application.

If you do not want a category published, disable its detector. `rules.enabled_detectors.application` controls the generic fallback for applications that do not match a specialized detector.

## Privacy modes

### `off`

Keeps detected activity details with no project-side redaction. Use this only if you are comfortable publishing the detected text.

### `balanced`

Keeps useful context while applying configured redaction patterns and reducing path exposure. This is the default mode.

For terminal commands, values following common sensitive flags such as token, password, authorization, API-key, access-key, and private-key arguments are redacted in addition to the configured regex rules. For browsers, an inferred link is removed if its source window title had to be redacted; this prevents the original value from surviving only in percent-encoded URL form.

### `strict`

Uses generic descriptions and removes identifying browser URLs and buttons.

The service can also clear Rich Presence when a known lock-screen window is detected.

## Local files

### Windows

- Configuration: `%APPDATA%\discord-rich-presence\config.yaml`
- Logs: `%LOCALAPPDATA%\discord-rich-presence\logs\app.log`
- Runtime state: `%LOCALAPPDATA%\discord-rich-presence\runtime\`
- Terminal hook cache: `%LOCALAPPDATA%\discord-rich-presence\cache\`

### Linux

- Configuration: `~/.config/discord-rich-presence/config.yaml`
- Logs: `~/.local/state/discord-rich-presence/app.log`
- Runtime state: `~/.local/state/discord-rich-presence/runtime/`
- Terminal hook cache: `~/.cache/discord-rich-presence/`

Logs rotate locally. Runtime state is used by the control panel and single-instance guard. Terminal command cache entries expire according to `rules.terminal_command_ttl_secs`.

## Terminal hooks

Terminal command tracking is optional. Bash, Zsh, and PowerShell hooks write commands to local per-shell cache files. The detector attempts to match the foreground terminal process tree before using a command entry. If a PID-scoped hook cache exists but does not match the focused terminal, the detector does not fall back to another terminal's command.

Do not enable terminal tracking on a machine where displaying command text in Discord is unacceptable, even with redaction enabled.
