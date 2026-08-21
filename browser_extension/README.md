# CYBREX Browser Companion

The Browser Companion is optional. It gives the desktop service exact browser tab and media context that foreground-window titles and MPRIS often cannot provide reliably.

It does not connect to Discord itself. It only sends recent activity snapshots to the desktop service over `127.0.0.1:32191`.

## What it adds

- exact current tab URL and page title
- exact service/domain identification
- browser video/audio playing state, position, and duration
- YouTube title/channel enrichment
- reliable background browser-media attribution
- correct tab-aware activity priority when media is playing in another tab
- declarative self-hosted/custom-domain support on the desktop side

## Privacy model

The bridge binds to loopback only and keeps snapshots in memory. The desktop service does not upload browser history or Companion data to a CYBREX server.

Balanced privacy mode publishes only the URL origin by default (for example `https://www.youtube.com`), even though the extension can see the exact tab URL locally. This can be changed with `privacy.browser_url_mode`.

Private/incognito metadata is suppressed by the desktop service. Browsers normally keep extensions disabled in private windows unless the user explicitly grants private-window access.

## Load unpacked in Brave / Chrome / Edge

1. Open the browser extension management page.
2. Enable **Developer mode**.
3. Choose **Load unpacked**.
4. Select this `browser_extension` directory.
5. Start the desktop service and look for:

```text
Browser companion listening on http://127.0.0.1:32191
```

## Temporary install in Firefox

1. Open `about:debugging`.
2. Choose **This Firefox**.
3. Choose **Load Temporary Add-on**.
4. Select `manifest.json` from this directory.

The current files are for development/testing. Store packaging and signed extension releases should be handled separately before a public release.
