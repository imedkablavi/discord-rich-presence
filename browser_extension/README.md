# CYBREX Browser Companion

The Browser Companion is optional. It gives the desktop service exact browser-tab and media context that foreground-window titles and MPRIS often cannot provide reliably.

It does not connect to Discord itself. It sends short-lived activity snapshots only to the local desktop service over `127.0.0.1`. The default bridge port is `32191`.

## What it adds

- exact current web-tab URL and page title
- exact service/domain identification
- browser video/audio playing state, position, and duration
- YouTube title/channel enrichment
- reliable background browser-media attribution
- correct tab-aware activity priority when media is playing in another tab
- declarative self-hosted/custom-domain support on the desktop side

## Permissions

The extension runs its content script only on normal `http://` and `https://` pages. It does not request access to `file://` pages.

It requests:

- `tabs` so the background component can follow active-tab/window changes and request fresh snapshots;
- `storage` to save only the local bridge port selected in the Options page.

Its only explicit network host permission is:

```text
http://127.0.0.1/*
```

That permission is limited to the IPv4 loopback host. It is intentionally written without an explicit port so the same manifest works in Chromium-family browsers and Firefox, and so a user can move the local bridge when the default port is occupied.

The background component is not granted arbitrary cross-origin network access. Extension requests are aborted after a short timeout if the local service is unavailable.

## Privacy model

The bridge keeps a bounded set of recent snapshots in memory. Closed tabs are removed immediately when the browser reports their closure, old snapshots expire automatically, and the service clears Companion state when the bridge stops.

The desktop service does not upload browser history or Companion data to a CYBREX server.

Balanced privacy mode publishes only the URL origin by default (for example `https://www.youtube.com`), even though the extension can see the exact tab URL locally. This can be changed with `privacy.browser_url_mode`.

Private/incognito metadata is treated conservatively by the desktop service. Browsers normally keep extensions disabled in private windows unless the user explicitly grants private-window access.

## Prepare a clean unpacked extension directory

For the simplest setup, especially when Brave/Chrome is installed as a Flatpak, run from the repository root:

```bash
bash scripts/prepare-browser-companion.sh
```

The helper copies only the required extension files to a clean `CYBREX-Browser-Companion` directory in the user's Downloads folder and prints the exact directory to select.

Do **not** choose the `discord-rich-presence` repository root in **Load unpacked**. The repository contains Python directories such as `__pycache__`; Chromium-family browsers reject reserved extension filenames beginning with `_` when they are inside the selected extension directory.

## Load unpacked in Brave / Chrome / Edge

1. Open the browser extension management page.
2. Enable **Developer mode**.
3. Choose **Load unpacked**.
4. Select either the clean directory printed by `scripts/prepare-browser-companion.sh` or this repository's `browser_extension` directory specifically.
5. Start the desktop service and look for:

```text
Browser companion listening on http://127.0.0.1:32191
```

The toolbar badge shows `ON` when the local bridge accepts a snapshot and `OFF` when it is unavailable.

After the extension is loaded, reload it from the browser's extension page whenever development files under `browser_extension/` change.

## Temporary install in Firefox

1. Open `about:debugging`.
2. Choose **This Firefox**.
3. Choose **Load Temporary Add-on**.
4. Select `manifest.json` from this directory.

The manifest intentionally includes both the Manifest V3 service-worker background entry used by Chromium-family browsers and the background-script fallback used by Firefox.

## Change the bridge port

The desktop configuration and extension must use the same port.

Desktop config:

```yaml
browser_companion:
  enabled: true
  port: 32191
```

If you change that value, open the extension's **Options** page and enter the same port. Use **Test connection** there to verify that the desktop bridge is reachable.

The extension stores only this port number in `storage.local`; it does not persist the URLs/titles it sends to the desktop service.

## Public store release

The repository/release ZIP is suitable for unpacked local installation. Official Chrome Web Store or Firefox AMO publication requires the corresponding developer account, store metadata/privacy disclosures, and the store review/signing process. Do not describe the unpacked ZIP as store-signed until that process has actually been completed.
