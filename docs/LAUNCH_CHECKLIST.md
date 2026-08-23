# CYBREX Presence public launch checklist

This checklist separates repository settings that must be changed in GitHub's UI from code/release work that can be validated in CI.

## 1. Repository metadata

Use this repository description:

> Automatic, privacy-first Discord Rich Presence for Windows & Linux — games, social web apps, browsers, coding and media.

Recommended GitHub Topics (20 maximum):

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

Before launch:

- [ ] Replace the current long repository description with the concise description above.
- [ ] Replace/expand the current Topics with the list above.
- [ ] Add a project homepage only when there is a real CYBREX Presence landing page; do not point users to an unrelated homepage just to fill the field.
- [ ] Enable GitHub Discussions after the first stable release so support, game requests, showcases and ideas do not all become Issues.
- [ ] Enable `delete_branch_on_merge` after the stacked feature branches have been merged, to keep the public branch list clean.

The exact owner-only steps are also summarized in `docs/OWNER_ACTIONS.md`.

## 2. Social preview

Create a 1280×640 social preview with:

- CYBREX Presence name/logo;
- the phrase `Automatic Discord Rich Presence`;
- `Windows + Linux`;
- a compact set of categories such as `Gaming · Social · Browsers · Coding · Media`;
- a real Discord activity card / product screenshot, not fake benchmark numbers or star counts;
- no tiny feature list that becomes unreadable when embedded on Reddit/Discord/X/LinkedIn.

Before uploading it in **Settings → General → Social preview**, verify it still reads clearly at mobile-card size.

- [ ] Social preview created.
- [ ] Social preview uploaded in repository settings.
- [ ] Test the repository link in Discord and another Open Graph preview tool.

## 3. Public `main` must match the product

Do not promote the repository while the best features are hidden in draft PRs.

Merge order remains:

1. release-hardening stack (#17);
2. Browser Companion / priority engine stack (#18);
3. gamer integrations + verified self-updates (#22);
4. launch-readiness / installers (#23);
5. privacy-safe social web presence (#24).

The optional Discord Social SDK transport (#21) is not a blocker for the first stable release.

For every retarget/merge:

- [ ] complete required real-device tests;
- [ ] retarget the next stacked PR to `main`;
- [ ] rerun all required workflows;
- [ ] verify the README on `main`, not only on a feature branch;
- [ ] verify release links and screenshots render from the default branch.

## 4. First stable release

The first public release should be usable without a source checkout.

Required release assets:

- [ ] `CYBREX-Presence-Setup.exe` — recommended Windows entry point;
- [ ] `CYBREX-Presence-Setup.exe.sha256`;
- [ ] `DiscordRichPresence.exe` — portable Windows build;
- [ ] `DiscordRichPresence.exe.sha256`;
- [ ] `CYBREX-Presence-linux-x86_64.tar.gz` — user-level Linux installer bundle;
- [ ] `CYBREX-Presence-linux-x86_64.tar.gz.sha256`;
- [ ] `CYBREX-DiscordRichPresence-linux-x86_64` — portable Linux build;
- [ ] portable Linux `.sha256`;
- [ ] Browser Companion ZIP + `.sha256`;
- [ ] FiveM Companion ZIP + `.sha256`;
- [ ] Minecraft Companion JAR + `.sha256`.

Release notes should lead with user-visible changes and installation, not commit history.

Recommended release-note order:

1. What CYBREX Presence does.
2. Download table for Windows/Linux/companions.
3. What's new.
4. Privacy/security notes, including Social Presence behavior.
5. Known limitations.
6. Upgrade behavior.
7. Checksums/signing status.

## 5. Installation conversion

### Windows

- [x] Installer QA builds the Inno Setup installer.
- [x] Silent install succeeds on Windows runner.
- [x] Installed EXE passes one-cycle dry-run smoke test.
- [x] Uninstaller succeeds.
- [ ] Real Windows 10 test.
- [ ] Real Windows 11 test.
- [ ] If an Authenticode certificate is configured, sign both the inner EXE and final Setup EXE.
- [ ] Confirm self-update can replace the installed `%LOCALAPPDATA%` executable in a real release-to-release update.

### Linux

The installer intentionally stays user-level instead of placing the executable in root-owned `/usr/bin`, because a root-owned package would conflict with the existing in-app self-update model.

- [x] Bundle installs to `~/.local/lib/cybrex-presence` without sudo in Installer QA.
- [x] CLI symlink created under `~/.local/bin` in Installer QA.
- [x] desktop entry created under the user's XDG applications directory in Installer QA.
- [x] installed binary remains writable by the user for verified self-update in Installer QA.
- [x] uninstaller leaves configuration/logs intact in Installer QA.
- [ ] real KDE Plasma Wayland test.
- [ ] one full release-to-release update test.

## 6. README conversion check

A new visitor should understand these points without scrolling through implementation detail:

- [x] what the app does;
- [x] Windows/Linux support;
- [x] where to download it;
- [x] what Discord can display;
- [x] supported games/integrations;
- [x] supported social web apps and their generic privacy contract;
- [x] local-first/privacy model;
- [x] self-update support;
- [x] how to request another game;
- [x] how to report a bug;
- [ ] screenshots are refreshed from the final release candidate and remain legible.

Do not add badges that report vanity metrics with no user value. Build/release/license/platform badges are enough until there is meaningful download/community data.

## 7. Social Presence validation

Built-in services include WhatsApp Web, Facebook, Messenger, Instagram, LinkedIn, Threads, TikTok, Telegram Web, Snapchat Web, Discord Web, Pinterest, Bluesky, X and Reddit.

Automated regression coverage must keep these guarantees:

- [x] known services are matched by parsed hostname/path, not query-string substrings;
- [x] social tab/page titles are replaced with generic `Using <service>` state;
- [x] conversation/profile/post IDs and deep URLs are removed before Presence building;
- [x] social-page media metadata is discarded;
- [x] any automatic Open button points only to the public service homepage;
- [x] the social privacy contract stays conservative even when ordinary browser URL mode is `path` or `full`;
- [ ] live Browser Companion tab switching is tested against several real social services;
- [ ] private/incognito social browsing is validated on a real browser build;
- [ ] closing social tabs/browser verifies stale state expires immediately/within the documented TTL.

See `docs/SOCIAL_PRESENCE.md`.

## 8. Community funnel

- [x] Structured Bug Report issue form exists.
- [x] Structured Feature Request issue form exists.
- [x] Dedicated Game Support request form exists.
- [x] Dedicated Integration Request form exists.
- [ ] Add `good first issue` labels to simple Community Game Pack requests after the first requests arrive.
- [ ] Enable Discussions categories: `Announcements`, `Q&A`, `Show and tell`, `Ideas`.
- [ ] Pin one Discussion explaining how to add a Community Game Pack.
- [ ] Respond to first users quickly; unanswered install issues damage launch conversion more than a missing feature.

## 9. Browser distribution

After extension real-device testing:

- [ ] Chrome Web Store listing.
- [ ] Firefox Add-ons listing.
- [ ] Store screenshots use the same CYBREX Presence branding.
- [ ] README links to store installs first and manual unpacked installation second.
- [x] prepared permission/privacy/listing copy exists in `docs/BROWSER_STORE_LISTING.md`.
- [ ] compare the final store form against the checked-in manifest before submission.

The store listing must describe the existing minimal permission model accurately. Do not add `tabs`, `file://`, or unrelated host permissions only to simplify submission.

## 10. Launch content

Do not post the same generic advertisement everywhere. Each community should get a use-case-specific demo.

Prepare:

- [ ] 20–40 second demo GIF/video: app switch → Discord Presence switch;
- [ ] gaming clip: CS2/League/Minecraft/FiveM;
- [ ] social clip: switch WhatsApp/Instagram/LinkedIn tabs and demonstrate generic privacy-safe Presence;
- [ ] Linux/KDE clip;
- [ ] privacy/local-first explanation;
- [ ] one concise technical architecture diagram for developer communities.

Potential channels after the stable release is downloadable:

- relevant Discord customization communities;
- Linux/KDE communities for the Wayland angle;
- Minecraft/FiveM communities for their companion integrations;
- Reddit communities where self-promotion rules allow it;
- LinkedIn/X/GitHub profile;
- a short YouTube installation/demo video.

Every post should link to a working stable Release, not a draft branch.

## 11. Owner-only blockers

These cannot be completed safely by a contributor without the repository/store owner:

- [ ] GitHub repository description/topics/social preview/Discussions settings;
- [ ] Windows Authenticode certificate/secrets, if signing is desired;
- [ ] Chrome Web Store owner/developer account and submission;
- [ ] Firefox Add-ons owner/developer account and submission;
- [ ] Windows 10/11 real-device checks;
- [ ] Linux/KDE real-device checks;
- [ ] first public stable tag/release after the merge stack is complete.

Credentials, signing keys, store passwords and recovery codes must never be posted in chat/issues/PRs. Use account settings/secrets directly. See `docs/OWNER_ACTIONS.md`.

## 12. Metrics to watch

Stars are an outcome, not the only quality metric. For the first releases, track public GitHub metrics manually:

- release downloads by asset;
- stars/week;
- unique contributors;
- issue-to-resolution time;
- game/integration support requests;
- external referrers/traffic in GitHub Insights;
- ratio of repository visits to Release downloads.

Do not add telemetry to the desktop application just to measure launch conversion.
