# Discord Rich Presence Service

A modular, cross-platform background service that dynamically updates your Discord Rich Presence based on your active window, IDE, terminal, and browser activities. 

Unlike conventional presence tools that rely heavily on static window titles, this project uses active process memory indexing (CWD arrays, native `psutil`, `/proc` parsing) to pull accurate context from applications, while relying on explicit user-defined fallbacks and strong privacy filtering.

## 🛠 Features & Capabilities

- **State-Based Adaptive Polling**: Polls application activity continuously but updates Discord instantly only when an actual context shift happens, preventing API throttling.
- **Process Memory Git Hooking**: Accurately extracts `(branch)` datasets from environments by querying explicit working directories, not window titles.
- **Strict Privacy Isolation**: Toggleable filters (Off, Balanced, Strict) that scrub personal paths, passwords, private browsing modes, and explicit URLs from network payloads before they are serialized.
- **Native OS Wrappers**: Directly interfaces with Windows `win32gui`, Linux `xprop`, and D-Bus APIs (instead of wrapping raw bash commands) for deep process tracing.
- **No Remote Tracking**: All footprint hashing and regex detection runs entirely locally. Data is sent exclusively to your local Discord IPC socket.

## ⚠️ Important Limitations

This project attempts to provide wide coverage natively, but there are explicit platform and API barriers you should be aware of:

- **Discord Application Client ID Required**: There is no built-in or default application ID. You **must** create your own Application in the [Discord Developer Portal](https://discord.com/developers/applications) and configure your `client_id` inside `config.yaml`.
- **Icon Rendering Context**: To render application icons (VS Code, Python, YouTube), you must manually upload those images to your Discord Application's "Rich Presence Art Assets" tab and name them to match your configuration mapping. Discord does not magically fetch icons otherwise.
- **Wayland (Linux)**: Wayland aggressively isolates process access for security reasons. Window names and process IDs are heavily restricted compared to X11. This service falls back to generic fallback titles under Wayland sessions.
- **macOS**: Native GUI window tracking requires `AppKit` CoreGraphics implementations which are currently only partially implemented as stubs.
- **Button Interaction**: Discord's API strictly restricts interaction buttons to `http://` or `https://` URIs. Local file paths or application deep links (e.g. `vscode://`) are rejected physically by Discord's backend.

## 🗂 Architecture

The system runs a loosely coupled loop governed by a central state machine.

```ascii
+-----------------------+      +---------------------------+      +-----------------------+
| Window Reader Factory | ---> |      Detector Router      | ---> |     ActivityState     |
| (OS-Specific Queries) |      | (Sequential Feature Maps) |      |   (Normalized Model)  |
+-----------------------+      +---------------------------+      +-----------------------+
                                                                             |
                                                                             v
                               +---------------------------+      +-----------------------+
                               |   Async Presence Service  | <--- |   Privacy Redactor    |
                               |   (Adaptive Polling Loop) |      |   (Strict Scrubbing)  |
                               +---------------------------+      +-----------------------+
```

## 🚀 Setup & Installation

### Requirements
- Python 3.10+
- The active Discord Desktop Client (Running)

### 1. Configure Discord Application
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a "New Application" and copy its **Application ID**.
3. (Optional) Go to **Rich Presence -> Art Assets** and upload your desired icons (e.g. `vscode`, `youtube`, `terminal`).

### 2. Download and Run
```bash
# Clone the repository
git clone https://github.com/yourusername/discord-rich-presence.git
cd discord-rich-presence

# Install cross-platform dependencies
pip install -r requirements.txt

# Copy config template
cp config.example.yaml config.yaml

# INSERT YOUR CLIENT ID IN config.yaml
```

```bash
# Start background daemon
python main.py
```

### 3. Optional Graphical Manager
We include a `customtkinter` frontend panel to manipulate `config.yaml` values, privacy settings, and registry autostart on the fly:
```bash
python gui_modern.py
```

## 🔒 Privacy Configuration

You can force strict rules on the outbound Discord data to avoid exposing system metrics. Modify `privacy.mode` in `config.yaml`:

| Mode | Behavior |
| :--- | :--- |
| **Off** (Public) | Everything is transmitted directly without mutation. |
| **Balanced** (Default) | Redacts explicit authentication hashes and tokens natively (via regex configuration). Maps user-home structures strictly to `~/`. |
| **Strict** (Private) | Discards all active URIs and file paths. Discards buttons. Generalizes fields to "Writing Code", "Terminal Active", or "Consuming Media". |

## 📃 License

Distributed under the MIT License. See `LICENSE` for more information.
