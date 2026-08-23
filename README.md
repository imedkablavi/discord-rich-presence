<div align="center">

# CYBREX Presence

**Automatic Discord Rich Presence for games, social web apps, browsers, coding, terminals and media — local-first, privacy-aware, and built for Windows + Linux.**

[![QA](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/qa.yml/badge.svg)](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/qa.yml)
[![Gamer Integrations](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/gamer-integrations.yml/badge.svg)](https://github.com/imedkablavi/discord-rich-presence/actions/workflows/gamer-integrations.yml)
[![Latest Release](https://img.shields.io/github/v/release/imedkablavi/discord-rich-presence?display_name=tag&sort=semver)](https://github.com/imedkablavi/discord-rich-presence/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Windows + Linux](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](#download)

[**Download latest release**](https://github.com/imedkablavi/discord-rich-presence/releases/latest) · [**Supported integrations**](#supported-integrations) · [**Privacy**](#privacy-by-default) · [**Report a bug**](https://github.com/imedkablavi/discord-rich-presence/issues/new/choose)

</div>

CYBREX Presence watches the activity you are actually using and updates Discord automatically. No Discord Developer Portal setup is required for normal users, and there is no CYBREX cloud backend collecting your activity.

<p align="center">
  <img src="docs/images/control-panel.png" alt="CYBREX Presence control panel" width="820">
</p>

<p align="center">
  <img src="docs/images/activity.png" alt="CYBREX Presence activity on Discord" width="520">
</p>

## Why use it?

- **One app for more than games.** Games, social web apps, browsers, editors, terminals, Spotify/media and normal desktop apps can all become Rich Presence.
- **Built for gamers.** Steam/Epic/Heroic discovery, Game Library, Gamer Mode, CS2 GSI, League live state, FiveM and Minecraft companions.
- **Privacy-safe social presence.** WhatsApp, Facebook, Messenger, Instagram, LinkedIn, Threads, TikTok, Telegram, Snapchat, Discord Web, Pinterest, Bluesky, X and Reddit are reduced to generic service state before Discord sees them.
- **Actually local-first.** Detection happens on your machine. Browser, game and companion bridges bind to loopback only.
- **Privacy controls are part of the product.** Balanced/Strict modes, URL reduction, secret/path redaction and conservative game detection.
- **Windows and Linux are first-class targets.** Windows desktop integration plus KDE Plasma Wayland, Sway and X11 support on Linux.
- **Updates do not require reinstalling.** Packaged builds can check and install verified GitHub Release updates with SHA-256 validation.
- **Designed to fail closed.** If CYBREX cannot identify an activity reliably, it avoids broad guesses rather than publishing the wrong thing.

## Download

### Windows — recommended installer

Download **`CYBREX-Presence-Setup.exe`** from the latest GitHub Release:

**[Download for Windows →](https://github.com/imedkablavi/discord-rich-presence/releases/latest)**

The installer is per-user, does not require administrator rights for its normal install path, creates a Start Menu entry, supports normal Windows uninstall, and keeps the application in a user-owned location so verified in-app self-updates can replace the executable later.

If you prefer a portable build, the same Release also contains `DiscordRichPresence.exe`.

Python and a source checkout are not required for either option.

### Linux x86_64 — recommended user installer

Download **`CYBREX-Presence-linux-x86_64.tar.gz`** from the latest GitHub Release, then:

```bash
tar -xzf CYBREX-Presence-linux-x86_64.tar.gz
cd CYBREX-Presence-linux-x86_64
./install-user.sh
```

The installer deliberately does **not** use `sudo`. It installs for the current user under `~/.local`, creates a `cybrex-presence` command and desktop entry, and keeps the executable user-owned so the verified self-updater continues to work.

To remove the installed application later while leaving your configuration/logs intact:

```bash
./install-user.sh --uninstall
```

If you prefer a portable build, the same Release also contains `CYBREX-DiscordRichPresence-linux-x86_64` plus its checksum.

Every desktop installer/portable asset has a matching `.sha256` file. Tagged releases run release security checks before publication, and the in-app updater verifies the expected release asset before replacement.

> If a stable Release has not been published for the branch you are testing, use the source instructions under [Development / source setup](#development--source-setup).

## What Discord can show

Examples depend on the active integration and your privacy settings:

```text
Counter-Strike 2 · Competitive
Mirage · Counter-Terrorists · 8–6
```

```text
League of Legends
Ahri · Mid · Summoner's Rift
```

```text
Minecraft
Multiplayer · Overworld
```

```text
Using Instagram
Instagram · Firefox
```

```text
Using WhatsApp
WhatsApp · Chrome
```

```text
Visual Studio Code
Working in Python · main.py
```

The project intentionally does not promise live details for a game unless there is a documented/safe source for them. Social/messaging integrations intentionally do the opposite of “rich private context”: they publish the service identity but discard conversation/profile/post details before Presence building.

## Supported integrations

| Integration | Detection | Enhanced state | Notes |
| --- | --- | --- | --- |
| Steam | Automatic local catalog | Per-game where supported | Resolves installed titles from Steam manifests |
| Epic Games | Automatic local catalog | Standard presence | Windows launcher manifests |
| Heroic / Legendary | Automatic local catalog | Standard presence | Native + Flatpak layouts |
| Counter-Strike 2 | Automatic + Steam | **Enhanced** | Valve GSI: map, mode, team, score |
| League of Legends | Automatic | **Enhanced** | Riot local Live Client Data API |
| FiveM | Automatic process detection | **Enhanced with companion** | Optional server resource + loopback bridge |
| Minecraft Java | Window detection | **Enhanced with Fabric companion** | Mode + dimension; server label opt-in |
| Social web apps | Browser Companion / title fallback | **Privacy-safe generic** | WhatsApp, Facebook, Messenger, Instagram, LinkedIn, Threads, TikTok, Telegram, Snapchat, Discord Web, Pinterest, Bluesky, X, Reddit |
| Browser Companion | Chrome-family + Firefox | **Enhanced** | Exact focused service/tab/media state locally |
| Spotify / media | Local media APIs | Enhanced | MPRIS / Windows Media Control where available |
| Coding / terminals | Foreground detection | Enhanced | IDE/editor/shell aware |
| Community game packs | Exact process fallback | Standard presence | Data-driven contributions without Python changes |

Steam, Epic and Heroic metadata remain authoritative before community fallback definitions. Community packs use exact executable names, not regex/wildcard process scraping.

## Gamer Mode + Game Library

Open **Game Library** from the tray or with:

```text
DiscordRichPresence.exe --game-library
```

The library discovers locally installed Steam, Epic and Heroic games, marks enhanced integrations, and lets you enable/disable Presence per game.

**Gamer Mode (games only)** temporarily disables browser/media/coding/terminal/application detectors so games always own the Presence. Turning it off restores your previous detector preferences instead of resetting them to defaults.

## Enhanced game integrations

### Counter-Strike 2

CYBREX uses Valve Game State Integration — not DLL injection, memory reading, input automation or packet manipulation. The listener binds to:

```text
127.0.0.1:32192
```

Only the minimal state needed for Presence is retained. See [Counter-Strike 2](docs/COUNTER_STRIKE_2.md) and [Anti-cheat boundaries](docs/ANTI_CHEAT.md).

### League of Legends

League enrichment uses Riot's local Live Client Data API while the game is foreground. CYBREX keeps only the local player's champion, role/position, game mode and game time for Presence. Riot IDs, names, KDA, items, runes, enemy data and other-player state are not retained or published.

See [League of Legends integration](docs/LEAGUE_OF_LEGENDS.md).

### FiveM

The optional `CYBREX-FiveM-Companion.zip` Release asset contains a small FiveM server resource. It can provide server display name, player count and an optional `cfx.re` Join URL to the desktop bridge:

```text
127.0.0.1:32193
```

Player names, identifiers/licenses, jobs, inventory, money, coordinates, chat and framework state are not collected. Server name and Join button are opt-in in the desktop configuration.

### Minecraft Java

The optional `CYBREX-Minecraft-Companion-26.2.jar` is a Fabric client companion for the supported Minecraft/Fabric target. It publishes a minimal local snapshot to:

```text
127.0.0.1:32194
```

It does not read/send username or UUID, server IP, chat, coordinates, world seed, inventory, health, entities or session/auth tokens. Server-name sharing is disabled by default in both the mod and desktop app.

## Browser Companion

The optional Browser Companion improves browser activity beyond window-title heuristics. It can identify the focused tab/service and HTML media state while keeping communication local:

```text
127.0.0.1:32191
```

Balanced privacy reduces ordinary browser URLs to the origin/domain by default. Records are memory-only and expire.

Social and messaging pages use a stricter contract: the exact tab URL is used only to identify the service, then the page title, deep path/query, conversation/profile/post identifiers and social-page media metadata are discarded. Discord receives only generic state such as `Using Instagram`, and any automatic Open button points to the service homepage rather than the current private page. This remains true even if ordinary browser URL mode is `path` or `full`.

To prepare a clean unpacked development build:

```bash
bash scripts/prepare-browser-companion.sh
```

Then load the generated `CYBREX-Browser-Companion` directory — **not the repository root** — in your browser's extension developer page.

See [Browser Companion](docs/BROWSER_COMPANION.md) and [Social web presence](docs/SOCIAL_PRESENCE.md).

## Privacy by default

CYBREX Presence is designed around local activity, so privacy failures would be especially damaging. The project therefore uses explicit boundaries rather than treating privacy as a README claim.

| Mode | Behavior |
| --- | --- |
| `off` | Minimal project-side redaction |
| `balanced` | Recommended; useful context with secret/path/URL reduction |
| `strict` | Generic activity; identifying browser URLs/buttons removed |

Additional safeguards include:

- loopback-only companion listeners;
- social/messaging title and deep-link suppression before Presence building;
- browser URL modes: `none`, `domain`, `path`, `full` for ordinary pages;
- configurable secret/path redaction;
- no full Rich Presence payloads in persistent logs;
- conservative foreground/game matching;
- anti-cheat regression tests around enhanced game integrations;
- short TTLs for companion state;
- no project-operated telemetry/activity backend.

See [Privacy](docs/PRIVACY.md), [Social web presence](docs/SOCIAL_PRESENCE.md), and [Security](SECURITY.md).

## Linux desktop support

| Environment | Foreground detection |
| --- | --- |
| KDE Plasma Wayland | `kdotool` |
| Sway | `swaymsg` |
| X11 desktops | `xprop` |

Linux media detection prefers MPRIS/playerctl where available. If the compositor does not expose a reliable foreground-window API, CYBREX avoids guessing from unrelated running processes.

## Self updates

Packaged Windows/Linux builds support:

```text
--check-update
--update
```

The system tray also exposes **Check for updates** and **Install latest update**.

Updates come only from published stable GitHub Releases, not arbitrary commits. The updater requires the expected platform asset plus its `.sha256` sidecar, validates allowed GitHub HTTPS hosts, applies size/time limits and refuses downgrades.

See [Updates and trust model](docs/UPDATES.md).

## Help grow game support

Game support does not have to wait for a Python release. Conservative process-only fallbacks live in the validated community game pack.

If your game is missing:

1. open a **Game support request** from the issue chooser;
2. include the game, launcher, OS and exact executable name if known;
3. or submit a PR adding a validated community-pack entry.

Enhanced integrations require a documented/safe local source. Memory injection, input automation and packet manipulation are intentionally out of scope.

## Community

- [Report a bug](https://github.com/imedkablavi/discord-rich-presence/issues/new/choose)
- [Request game support](https://github.com/imedkablavi/discord-rich-presence/issues/new/choose)
- [Request an integration](https://github.com/imedkablavi/discord-rich-presence/issues/new/choose)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

If CYBREX Presence is useful to you, starring the repository helps other Discord/Linux/gaming users discover it.

## QA / release engineering

Pull requests are checked with:

- Windows + Ubuntu, Python 3.10 and 3.12;
- Python compile + critical Ruff checks;
- dependency audits and Linux Bandit high-severity scanning;
- Windows EXE and Linux x86_64 PyInstaller builds + smoke tests;
- Windows installer compile + silent install + installed-app smoke test + uninstall;
- Linux user-level installer build + install + smoke test + uninstall;
- Browser Companion manifest/permission/JavaScript/package validation;
- social-site structural matching and privacy-regression tests;
- Gamer Integration regression, Lua/JS and privacy-boundary checks;
- Minecraft Java/Fabric compile/remap/JAR verification;
- shell-hook syntax and private-cache-permission checks.

No CI suite can replace real-device testing for Discord Desktop, GPU/game environments, launchers or desktop compositors. Release candidates remain subject to real-device validation.

## Development / source setup

Requirements:

- Python 3.10+
- Discord Desktop

### Windows

```powershell
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python launcher.py --gui
```

### Linux

```bash
git clone https://github.com/imedkablavi/discord-rich-presence.git
cd discord-rich-presence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python launcher.py --gui
```

Run one detection cycle without publishing to Discord:

```bash
python main.py --dry-run --once --verbose
```

Run the tests:

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q .
ruff check . --select E9,F63,F7,F82
pytest -q
```

## Configuration

Default locations:

```text
Windows: %APPDATA%\discord-rich-presence\config.yaml
Linux:   ~/.config/discord-rich-presence/config.yaml
```

Normal users do not need a Discord Client/Application ID. Advanced users who maintain their own Discord application can set `discord.application_id_override`.

See [config.example.yaml](config.example.yaml) for the full schema.

## Current platform limits

- macOS foreground-window support is not implemented.
- Wayland support depends on a compositor exposing a trustworthy foreground-window interface.
- Dynamic top-level Discord application names require the newer Discord Social SDK transport; legacy desktop RPC may still show the registered CYBREX application name at the top of the card.
- Windows Authenticode signing requires a real signing certificate to be configured in repository secrets.

## License

MIT. See [LICENSE](LICENSE).

<div align="center">

**Built by CYBREX@TECH** · https://imedkablavi.info

</div>
