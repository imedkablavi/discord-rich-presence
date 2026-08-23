# Owner-only launch actions

Most CYBREX Presence release work is automated in CI. The items below require the repository/store/account owner and should not be handled by sharing credentials in issues, pull requests, or chat.

## GitHub repository settings

In **Repository → Settings → General**:

1. Set the description to:

   > Automatic, privacy-first Discord Rich Presence for Windows & Linux — games, social web apps, browsers, coding and media.

2. Configure up to 20 discovery topics. Recommended launch set:

   ```text
   discord
   discord-rpc
   discord-rich-presence
   rich-presence
   discord-presence
   windows
   linux
   wayland
   gaming
   steam
   minecraft
   fivem
   league-of-legends
   browser-extension
   social-media
   privacy
   desktop-app
   system-tray
   kde-plasma
   open-source
   ```

3. Upload the approved 1280×640 Social Preview image.
4. Enable **Discussions** after the first stable Release.
5. After the stacked feature branches are merged, enable automatic branch deletion after merge if desired.

Do not set an unrelated homepage just to fill the homepage field.

## Windows code signing

The Release workflow already supports Authenticode signing. A real code-signing certificate is still an owner responsibility.

Add these only through **Repository → Settings → Secrets and variables → Actions**:

- `WINDOWS_SIGNING_PFX_BASE64`
- `WINDOWS_SIGNING_PFX_PASSWORD`

Do **not** paste the certificate, password, private key, or Base64 PFX into an issue, pull request, Discussion, README, or chat.

When the secrets exist, the workflow signs and verifies both the packaged application EXE and final Windows Setup EXE.

Code signing is strongly recommended before a large Windows public launch, but the project can still publish checksum-verified unsigned builds while the certificate is being arranged.

## Browser extension stores

Publishing requires store-owner accounts and acceptance of each store's current terms.

After live Browser Companion QA:

- Chrome Web Store: create/verify the developer account and upload the release ZIP.
- Firefox Add-ons (AMO): create/verify the developer account and submit the Firefox-compatible ZIP/source as required by AMO review.

Use `docs/BROWSER_STORE_LISTING.md` for prepared listing/privacy copy.

Never give store-account passwords or recovery codes to contributors or automation.

## Real-device release checks

CI cannot replace these owner/tester checks:

### Windows

- Windows 10 installer UI, Start Menu shortcut and uninstall.
- Windows 11 installer UI, Start Menu shortcut and uninstall.
- Discord Desktop reconnect/start-stop behavior.
- one real stable-release → newer-stable-release in-app update.

### Linux

- KDE Plasma Wayland install through the user-level tar bundle.
- desktop entry and tray behavior.
- compositor foreground detection.
- one real stable-release → newer-stable-release in-app update.

### Browser/social

With the packaged Browser Companion, switch among several normal and social tabs and confirm:

- WhatsApp/Instagram/Facebook/LinkedIn/etc. identify the correct service;
- Discord never shows contact names, chat/group names, profile handles, post IDs, or deep social URLs;
- private/incognito windows remain generic;
- closing a tab or browser clears/expires stale state.

### Gamer integrations

Before advertising an integration as live-validated, test its actual supported environment:

- CS2 GSI;
- League in-match state;
- FiveM resource → NUI → desktop loopback bridge;
- Minecraft Fabric companion.

## Discord Social SDK

PR #21 is optional and is **not** required for the first stable release. It exists to solve the legacy RPC top-level application-name limitation.

Only pursue it when the owner can:

1. enable/download the official Social SDK from the Discord Developer Portal;
2. review current redistribution terms;
3. build the native helper against the official SDK;
4. live-test Windows and Linux fallback behavior.

Do not vendor an unofficial SDK archive.

## Stable Release

Do not create the first stable tag until the stacked PR order and real-device release gates are complete.

After the final merge to `main`:

1. verify README/screenshots on `main`;
2. choose the stable semantic version;
3. create/push the release tag;
4. verify every published asset and checksum;
5. install from the public Release page, not from Actions artifacts;
6. only then start public promotion.
