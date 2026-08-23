# CYBREX Presence public launch checklist

This checklist separates repository settings that must be changed in GitHub's UI from code/release work that can be validated in CI.

## 1. Repository metadata

Use this repository description:

> Automatic, privacy-first Discord Rich Presence for Windows & Linux — games, Steam/Epic/Heroic, CS2, League, FiveM, Minecraft, browsers, coding, terminals and media.

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
python
desktop-app
privacy
system-tray
kde-plasma
open-source
```

Before launch:

- [ ] Replace the current long repository description with the concise description above.
- [ ] Replace/expand the current three Topics with the list above.
- [ ] Add a project homepage only when there is a real CYBREX Presence landing page; do not point users to an unrelated homepage just to fill the field.
- [ ] Enable GitHub Discussions after the first stable release so support, game requests, showcases and ideas do not all become Issues.
- [ ] Enable `delete_branch_on_merge` after the stacked feature branches have been merged, to keep the public branch list clean.

## 2. Social preview

Create a 1280×640 social preview with:

- CYBREX Presence name/logo;
- the phrase `Automatic Discord Rich Presence`;
- `Windows + Linux`;
- a compact set of categories: `Gaming · Browsers · Coding · Media`;
- a real Discord activity card / product screenshot, not fake benchmark numbers or star counts;
- no tiny feature list that becomes unreadable when embedded on Reddit/Discord/X/LinkedIn.

Before uploading it in **Settings → General → Social preview**, verify it still reads clearly at mobile-card size.

- [ ] Social preview created.
- [ ] Social preview uploaded in repository settings.
- [ ] Test the repository link in Discord and another Open Graph preview tool.

## 3. Public `main` must match the product

Do not promote the repository while the best features are hidden in draft PRs.

Merge order remains:

1. release-hardening stack;
2. Browser Companion / priority engine stack;
3. gamer integrations + verified self-updates;
4. launch-readiness / installers.

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
4. Privacy/security notes.
5. Known limitations.
6. Upgrade behavior.
7. Checksums/signing status.

## 5. Installation conversion

### Windows

- [ ] Installer QA builds the Inno Setup installer.
- [ ] Silent install succeeds on Windows runner.
- [ ] Installed EXE passes one-cycle dry-run smoke test.
- [ ] Uninstaller succeeds.
- [ ] Real Windows 10 test.
- [ ] Real Windows 11 test.
- [ ] If an Authenticode certificate is configured, sign both the inner EXE and final Setup EXE.
- [ ] Confirm self-update can replace the installed `%LOCALAPPDATA%` executable.

### Linux

The installer intentionally stays user-level instead of placing the executable in root-owned `/usr/bin`, because a root-owned package would conflict with the existing in-app self-update model.

- [ ] Bundle installs to `~/.local/lib/cybrex-presence` without sudo.
- [ ] CLI symlink created under `~/.local/bin`.
- [ ] desktop entry created under the user's XDG applications directory.
- [ ] installed binary remains writable by the user for verified self-update.
- [ ] uninstaller leaves configuration/logs intact.
- [ ] real KDE Plasma Wayland test.
- [ ] one full release-to-release update test.

## 6. README conversion check

A new visitor should understand these points without scrolling through implementation detail:

- [ ] what the app does;
- [ ] Windows/Linux support;
- [ ] where to download it;
- [ ] what Discord can display;
- [ ] supported games/integrations;
- [ ] local-first/privacy model;
- [ ] self-update support;
- [ ] how to request another game;
- [ ] how to report a bug;
- [ ] screenshots are current and legible.

Do not add badges that report vanity metrics with no user value. Build/release/license/platform badges are enough until there is meaningful download/community data.

## 7. Community funnel

- [x] Structured Bug Report issue form exists.
- [x] Structured Feature Request issue form exists.
- [x] Dedicated Game Support request form exists.
- [x] Dedicated Integration Request form exists.
- [ ] Add `good first issue` labels to simple Community Game Pack requests after the first requests arrive.
- [ ] Enable Discussions categories: `Announcements`, `Q&A`, `Show and tell`, `Ideas`.
- [ ] Pin one Discussion explaining how to add a Community Game Pack.
- [ ] Respond to first users quickly; unanswered install issues damage launch conversion more than a missing feature.

## 8. Browser distribution

After extension real-device testing:

- [ ] Chrome Web Store listing.
- [ ] Firefox Add-ons listing.
- [ ] Store screenshots use the same CYBREX Presence branding.
- [ ] README links to store installs first and manual unpacked installation second.
- [ ] document exact permissions and loopback-only behavior in store privacy text.

## 9. Launch content

Do not post the same generic advertisement everywhere. Each community should get a use-case-specific demo.

Prepare:

- [ ] 20–40 second demo GIF/video: app switch → Discord Presence switch;
- [ ] gaming clip: CS2/League/Minecraft/FiveM;
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

## 10. Metrics to watch

Stars are an outcome, not the only quality metric. For the first releases, track public GitHub metrics manually:

- release downloads by asset;
- stars/week;
- unique contributors;
- issue-to-resolution time;
- game support requests;
- external referrers/traffic in GitHub Insights;
- ratio of repository visits to Release downloads.

Do not add telemetry to the desktop application just to measure launch conversion.
