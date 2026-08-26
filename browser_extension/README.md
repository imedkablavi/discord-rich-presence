# CYBREX Browser Companion

The Browser Companion is optional. It gives the desktop service focused browser-tab, service and media context that foreground-window titles or media APIs cannot always provide reliably.

It does not connect to Discord itself. It sends short-lived snapshots only to the local CYBREX desktop bridge on `127.0.0.1`. The default port is `32191`.

## What it adds

- focused tab URL and title for local classification
- exact service/domain identification
- browser audio/video playing state, position and duration
- improved YouTube/media attribution
- tab-aware activity priority when media is playing in another tab

## Permissions

The extension runs content scripts on normal `http://` and `https://` pages. It does not request `file://` access.

The ordinary extension permission is:

- `storage`: stores the local bridge port selected in Options

The extension does not request the broad `tabs` permission.

Its explicit loopback host permission is:

```text
http://127.0.0.1/*
```

Requests time out quickly when the local service is unavailable.

## Privacy

Bridge records are bounded and memory-only. Closed tabs are removed when reported by the browser, old records expire and Companion state is cleared when the bridge stops.

Balanced privacy publishes only the permitted browser URL scope. Recognized social and messaging pages use a stricter contract: page titles, contact or conversation names, profile/post identifiers, deep social links and social-page media metadata are removed before Discord Presence is built.

Private or incognito browsing is handled conservatively by the desktop application.

See [Privacy](../docs/PRIVACY.md) and [Social Web Presence](../docs/SOCIAL_PRESENCE.md).

## Prepare a clean unpacked extension

From the repository root:

```bash
bash scripts/prepare-browser-companion.sh
```

Select the generated `CYBREX-Browser-Companion` directory in your browser's extension developer page. Do not select the repository root.

## Chromium-family browsers

For Brave, Chrome or Edge:

1. Open the browser extension management page.
2. Enable Developer mode.
3. Choose Load unpacked.
4. Select the generated Companion directory or the `browser_extension` directory.
5. Start CYBREX Presence and verify the Companion status.

The toolbar badge reports whether the local bridge accepted the latest snapshot.

## Firefox temporary installation

1. Open `about:debugging`.
2. Choose **This Firefox**.
3. Choose **Load Temporary Add-on**.
4. Select `manifest.json` from this directory.

The manifest includes the background configuration needed by the supported Chromium and Firefox development paths.

## Change the bridge port

The desktop and extension must use the same port.

Desktop configuration example:

```yaml
browser_companion:
  enabled: true
  port: 32191
```

Set the same port in the extension Options page and use its connection test.

The extension stores only this port preference. It does not persist the URLs or titles it sends to the local desktop bridge.

## Distribution status

GitHub Release ZIPs are suitable for local unpacked installation. Do not describe them as Chrome Web Store or Firefox AMO signed packages unless an official store publication has actually completed.
