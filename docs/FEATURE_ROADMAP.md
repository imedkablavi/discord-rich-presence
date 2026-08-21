# Product feature roadmap

This roadmap keeps the project focused on automatic, local, privacy-first presence instead of becoming another manual Rich Presence editor.

## In development

### Browser Companion

A small browser extension provides exact local tab/service/media context to the desktop service. The desktop app remains the only component that talks to Discord.

The first version targets Chromium-family browsers and Firefox and is designed to degrade safely when the extension is not installed.

### Smart Activity Priority

One priority engine chooses between games, foreground coding/terminal/browser activity, background media, and generic applications.

The default `smart` policy keeps games strongest, shows media when the media tab/player is actually foreground, and prevents background playback from masking active work.

### Declarative self-hosted domains

Custom/self-hosted domains should be configurable as data, not executable browser scripts. This keeps the extension smaller and reduces the security risk of community-contributed service definitions.

## High-value next features

### Smart privacy / streamer profile

Automatically move to a safer display policy while streaming, presenting, screen sharing, or using configured sensitive applications. Keep this local and opt-in.

### Local profiles and rules

Profiles such as Default, Work, Gaming, Streamer, and Privacy should be able to change detector priority, redaction, buttons, and application/site rules. Automatic profile activation should be rule based and remain local.

### Presence preview

Show the exact Rich Presence payload and rendered intent before publishing it. Make it easy to understand which detector won and why.

### Diagnostics center

Report Discord RPC, foreground-window backend, media backend, Browser Companion health, image assets, startup configuration, and common packaging/runtime problems in one place.

### Declarative community service recipes

Allow community-defined service metadata using a constrained JSON/YAML format: domains, labels, icons, page-title rules, privacy defaults, and optional safe selectors. Avoid arbitrary remote JavaScript in the desktop service.

### Local activity insights

Optional local-only activity history with automatic expiry. No project-operated analytics backend is required.

### Broader Discord client compatibility

Diagnose and support official Discord Desktop first, then compatible clients/IPC bridges where practical, including Flatpak and Vesktop-style setups.

## Release engineering

Before broad binary distribution: code signing, installer/uninstaller, updater strategy, version resources, extension store packaging/signing, and first-run diagnostics.
