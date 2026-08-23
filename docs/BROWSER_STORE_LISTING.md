# Browser Companion store listing draft

Use this as the source of truth when submitting the CYBREX Presence Browser Companion to browser extension stores. Re-check each store's current form fields and policy wording at submission time.

## Product name

**CYBREX Presence Browser Companion**

## Short description

Connects the active browser tab to the local CYBREX Presence desktop app for accurate, privacy-aware Discord Rich Presence.

## Long description

CYBREX Presence Browser Companion improves browser activity detection for the CYBREX Presence Windows/Linux desktop application.

It helps the desktop app identify the browser service you are actively using and distinguish the focused tab from unrelated background media. Communication stays on the local computer through the CYBREX loopback bridge.

Supported experiences include browser/media services and privacy-safe social web presence for services such as WhatsApp Web, Facebook, Messenger, Instagram, LinkedIn, Threads, TikTok, Telegram Web, Snapchat Web, Discord Web, Pinterest, Bluesky, X and Reddit.

Social and messaging pages use a stricter privacy contract: CYBREX reduces them to generic service state before building Discord Presence. Contact names, conversation/group names, profile/post identifiers and deep social URLs are not forwarded to Discord.

The companion is optional. CYBREX Presence continues to provide conservative browser/window detection without it, but exact focused-tab attribution is less reliable.

## Permission explanation

### Website access

The extension uses content scripts on normal HTTP/HTTPS pages so it can identify the currently focused web page and basic HTML media state for the local desktop app.

It does not request `file://` access.

### Storage

Extension storage is used for local companion preferences/state required by the extension UI.

### Loopback host access

The extension communicates with the desktop bridge at:

```text
http://127.0.0.1:32191
```

The bridge is local to the user's machine. The extension is not designed to upload browsing history to a CYBREX cloud backend.

### Deliberately not requested

The current manifest does not request the browser `tabs` permission.

Do not broaden permissions during store submission merely to make review/setup easier. Any future permission addition must be justified in code review and privacy documentation first.

## Data handling / privacy copy

The Browser Companion sends active-page metadata only to the local CYBREX Presence desktop bridge on the user's computer. Browser Companion records are memory-bounded and expire.

The desktop application applies privacy rules before publishing activity to Discord. Balanced mode limits ordinary exact browser URLs by policy; Strict mode removes identifying browser URLs/buttons.

For recognized social/messaging services, the desktop detector discards page titles, deep links, conversation/profile/post identifiers and social-page media metadata before Presence building, even when ordinary browser URL policy is configured more broadly.

The project does not operate a CYBREX browsing-history or activity telemetry backend.

See the repository documentation:

- `docs/BROWSER_COMPANION.md`
- `docs/SOCIAL_PRESENCE.md`
- `docs/PRIVACY.md`
- `SECURITY.md`

## Suggested screenshots

Use current screenshots captured from a release candidate, not mockups that imply unsupported behavior.

1. Browser Companion enabled/healthy in the CYBREX control panel.
2. YouTube/Spotify or another normal web service correctly reflected in Discord.
3. Instagram/WhatsApp/LinkedIn generic social Presence demonstrating that private titles are hidden.
4. Browser extension options/status page showing loopback-only connection.
5. Privacy settings showing Balanced/Strict modes.

Redact personal tabs, account names, browser profile names, Discord account identity, server names and local paths before uploading screenshots.

## Store-review verification before submission

- build the clean extension package through the repository helper/release workflow;
- verify manifest JSON and JavaScript syntax;
- verify no repository `__pycache__`, source-only files or secrets are included;
- verify loopback connection with the release-candidate desktop build;
- verify private/incognito behavior;
- verify social-title/deep-link suppression;
- compare requested permissions against the checked-in manifest;
- use the same version number/store metadata intended for the public release.
