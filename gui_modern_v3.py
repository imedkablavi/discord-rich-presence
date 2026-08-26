"""Resource-aware CYBREX control panel.

Builds on the polished Arabic-safe UI while keeping periodic probes and update
checks on bounded workers instead of creating unbounded background threads.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys

import customtkinter as ctk

from app_version import APP_VERSION
from config import Config
from gui_modern_v2 import ModernControlPanel as PolishedControlPanel
from update_manager import check_for_update, configured_update_channel, normalize_channel
from updater import UpdateError


class ModernControlPanel(PolishedControlPanel):
    """Polished UI with bounded long-running probe and update resources."""

    INTEGRATION_POLL_MS = 10_000

    def __init__(self, config: Config):
        self._probe_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="cybrex-gui-probe",
        )
        self._probe_future = None
        self._update_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="cybrex-update-check",
        )
        self._update_future = None
        self._available_update = None
        self._closing = False
        super().__init__(config)
        self._build_update_controls()
        if bool(self.config.get("updates.check_on_startup", True)):
            self.after(1_500, self.check_updates_background)

    # -------------------------------------------------------------- integrations
    def _poll_integrations(self):
        if self._closing:
            return

        future = self._probe_future
        if future is not None and future.done():
            self._probe_future = None
            try:
                browser_ok, cs2_ok, cs2_data = future.result()
            except Exception:
                browser_ok, cs2_ok, cs2_data = False, False, None

            self.browser_value.configure(
                text="Connected" if browser_ok else "Not connected",
                text_color=self.SUCCESS if browser_ok else self.MUTED,
            )
            self.browser_status_label.configure(
                text="Status: connected" if browser_ok else "Status: not connected",
                text_color=self.SUCCESS if browser_ok else self.MUTED,
            )
            if cs2_ok:
                connected = bool((cs2_data or {}).get("connected", False))
                label = "Match data active" if connected else "Listener ready"
                color = self.SUCCESS if connected else self.PRIMARY
            else:
                label = "Not connected"
                color = self.MUTED
            self.cs2_value.configure(text=label, text_color=color)
            self.cs2_status_label.configure(text=f"Status: {label.lower()}", text_color=color)

        if self._probe_future is None:
            browser_port = self._safe_port(
                self.config.get("browser_companion.port", 32191), 32191
            )
            cs2_port = self._safe_port(self.config.get("cs2_gsi.port", 32192), 32192)

            def collect():
                browser_ok, _, _ = self._probe_json(
                    f"http://127.0.0.1:{browser_port}/v1/health", 0.6
                )
                cs2_ok, cs2_data, _ = self._probe_json(
                    f"http://127.0.0.1:{cs2_port}/v1/status", 0.6
                )
                return browser_ok, cs2_ok, cs2_data

            self._probe_future = self._probe_executor.submit(collect)

        self.after(self.INTEGRATION_POLL_MS, self._poll_integrations)

    # ------------------------------------------------------------------- updates
    def _build_update_controls(self):
        about = self.pages.get("about")
        if about is None:
            return

        box = self._section(
            about,
            "Updates",
            "Check GitHub Releases, verify SHA-256, then replace the packaged app safely. "
            "Stable never installs preview builds; Preview can receive release candidates and stable releases.",
        )

        channel_row = ctk.CTkFrame(box, fg_color="transparent")
        channel_row.pack(fill="x", padx=16, pady=(7, 4))
        ctk.CTkLabel(
            channel_row,
            text="Update channel",
            text_color=self.TEXT,
            font=self._font(13, "bold"),
        ).pack(side="left", padx=5)
        self.update_channel = ctk.StringVar(
            value=configured_update_channel(self.config).title()
        )
        self.update_channel_menu = ctk.CTkOptionMenu(
            channel_row,
            variable=self.update_channel,
            values=["Stable", "Preview"],
            width=145,
            command=self._on_update_channel_changed,
        )
        self.update_channel_menu.pack(side="left", padx=12)

        self.update_startup = ctk.BooleanVar(
            value=bool(self.config.get("updates.check_on_startup", True))
        )
        ctk.CTkSwitch(
            box,
            text="Check for updates when CYBREX starts",
            variable=self.update_startup,
            command=self._save_update_preferences,
        ).pack(anchor="w", padx=21, pady=(8, 8))

        self.update_status = ctk.CTkLabel(
            box,
            text=f"Current version: {APP_VERSION}",
            text_color=self.MUTED,
            font=self._font(13),
            justify="left",
            anchor="w",
            wraplength=820,
        )
        self.update_status.pack(fill="x", padx=21, pady=(3, 10))

        actions = ctk.CTkFrame(box, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 17))
        self.update_check_button = ctk.CTkButton(
            actions,
            text="Check for updates",
            width=155,
            command=self.check_updates_background,
        )
        self.update_check_button.pack(side="left", padx=5)
        self.update_install_button = ctk.CTkButton(
            actions,
            text="Download & install",
            width=165,
            state="disabled",
            command=self.install_available_update,
        )
        self.update_install_button.pack(side="left", padx=5)

        ctk.CTkLabel(
            box,
            text=(
                "Updates are downloaded only after you choose Install. The current desktop binary is kept "
                "until verification succeeds, and failed startup triggers rollback."
            ),
            text_color=self.MUTED,
            font=self._font(12),
            justify="left",
            wraplength=820,
        ).pack(anchor="w", padx=21, pady=(0, 17))

    def _save_update_preferences(self):
        try:
            channel = normalize_channel(self.update_channel.get())
            self.config.set("updates.channel", channel)
            self.config.set("updates.check_on_startup", bool(self.update_startup.get()))
            self.config.save()
        except Exception as exc:
            self.update_status.configure(
                text=f"Could not save update settings: {exc}",
                text_color=self.DANGER,
            )

    def _on_update_channel_changed(self, _value=None):
        self._available_update = None
        self.update_install_button.configure(state="disabled")
        self._save_update_preferences()
        self.check_updates_background()

    def check_updates_background(self):
        if self._closing or self._update_future is not None:
            return

        try:
            channel = normalize_channel(self.update_channel.get())
        except Exception:
            channel = configured_update_channel(self.config)

        self._save_update_preferences()
        self.update_check_button.configure(state="disabled")
        self.update_install_button.configure(state="disabled")
        self.update_status.configure(
            text=f"Checking {channel.title()} releases…",
            text_color=self.MUTED,
        )
        self._update_future = self._update_executor.submit(
            check_for_update,
            APP_VERSION,
            channel=channel,
        )
        self.after(120, self._poll_update_result)

    def _poll_update_result(self):
        if self._closing:
            return
        future = self._update_future
        if future is None:
            return
        if not future.done():
            self.after(120, self._poll_update_result)
            return

        self._update_future = None
        self.update_check_button.configure(state="normal")
        try:
            info = future.result()
        except UpdateError as exc:
            self._available_update = None
            self.update_install_button.configure(state="disabled")
            self.update_status.configure(
                text=f"Update check failed: {exc}",
                text_color=self.DANGER,
            )
            return
        except Exception as exc:
            self._available_update = None
            self.update_install_button.configure(state="disabled")
            self.update_status.configure(
                text=f"Update check failed: {exc}",
                text_color=self.DANGER,
            )
            return

        if info is None:
            self._available_update = None
            self.update_install_button.configure(state="disabled")
            self.update_status.configure(
                text=f"CYBREX {APP_VERSION} is up to date on the {self.update_channel.get()} channel.",
                text_color=self.SUCCESS,
            )
            return

        self._available_update = info
        self.update_install_button.configure(state="normal")
        self.update_status.configure(
            text=f"CYBREX {info.latest_version} is available. Ready to download and verify.",
            text_color=self.PRIMARY,
        )

    def install_available_update(self):
        if self._closing or self._available_update is None:
            return
        if not getattr(sys, "frozen", False):
            self.update_status.configure(
                text="Self-update is available in packaged builds only.",
                text_color=self.WARNING,
            )
            return

        self._save_update_preferences()
        self.update_check_button.configure(state="disabled")
        self.update_install_button.configure(state="disabled")
        self.update_status.configure(
            text=f"Starting verified update to {self._available_update.latest_version}…",
            text_color=self.PRIMARY,
        )
        try:
            subprocess.Popen([sys.executable, "--update"], close_fds=True)
        except Exception as exc:
            self.update_check_button.configure(state="normal")
            self.update_install_button.configure(state="normal")
            self.update_status.configure(
                text=f"Could not start updater: {exc}",
                text_color=self.DANGER,
            )
            return

        # The updater process owns verification/replacement. Exit this GUI so
        # Windows can release the executable and Linux can relaunch cleanly.
        self.after(150, self.destroy)

    def destroy(self):
        if self._closing:
            return
        self._closing = True
        try:
            self._probe_executor.shutdown(wait=False, cancel_futures=True)
            self._update_executor.shutdown(wait=False, cancel_futures=True)
        finally:
            super().destroy()


if __name__ == "__main__":
    app = ModernControlPanel(Config())
    app.mainloop()
