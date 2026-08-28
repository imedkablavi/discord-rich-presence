"""Polished CYBREX control panel with Arabic-safe text rendering.

This layer intentionally subclasses the release control panel so all existing
settings/integration behavior remains unchanged while the presentation can be
improved independently.
"""

from __future__ import annotations

import re
import time
import tkinter.font as tkfont

import customtkinter as ctk

from config import Config
from gui_modern import ModernControlPanel as LegacyControlPanel

try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    _ARABIC_BIDI_AVAILABLE = True
except ImportError:  # pragma: no cover - graceful fallback for source checkouts
    arabic_reshaper = None
    get_display = None
    _ARABIC_BIDI_AVAILABLE = False


_ARABIC_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
_MOJIBAKE_HINTS = ("Ø", "Ù", "Ã", "Â", "â€", "ï¿½")


def repair_utf8_mojibake(value: object) -> str:
    """Repair common UTF-8 text that was accidentally decoded as Latin-1/CP1252.

    We only accept a candidate when it increases the amount of actual Arabic
    text or removes obvious mojibake markers. This keeps normal Western text
    unchanged and avoids destructive guesswork.
    """

    text = str(value or "")
    if not text or not any(marker in text for marker in _MOJIBAKE_HINTS):
        return text

    original_arabic = len(_ARABIC_RE.findall(text))
    original_noise = sum(text.count(marker) for marker in _MOJIBAKE_HINTS)

    for source_encoding in ("cp1252", "latin1"):
        try:
            candidate = text.encode(source_encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

        candidate_arabic = len(_ARABIC_RE.findall(candidate))
        candidate_noise = sum(candidate.count(marker) for marker in _MOJIBAKE_HINTS)
        if candidate_arabic > original_arabic or candidate_noise < original_noise:
            return candidate

    return text


def display_text(value: object, *, base_dir: str = "L") -> str:
    """Return UI-safe text with mojibake repair and Arabic shaping/BiDi.

    Tk on several Linux desktop stacks does not consistently perform Arabic
    shaping and bidirectional ordering. python-bidi + arabic-reshaper make the
    visual string deterministic while preserving the surrounding Latin text.
    """

    text = repair_utf8_mojibake(value)
    if not _ARABIC_RE.search(text) or not _ARABIC_BIDI_AVAILABLE:
        return text

    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped, base_dir=base_dir)
    except Exception:
        # Text rendering must never take down the service control panel.
        return text


class ModernControlPanel(LegacyControlPanel):
    """Release control panel with improved hierarchy, contrast and RTL safety."""

    BG = ("#F4F7FB", "#0B1220")
    SIDEBAR = ("#EDF2F8", "#101827")
    SURFACE = ("#FFFFFF", "#151F2E")
    SURFACE_ALT = ("#F8FAFC", "#192536")
    BORDER = ("#D9E2EC", "#2B3A4F")
    TEXT = ("#172033", "#F1F5F9")
    MUTED = ("#5F6B7A", "#A8B3C2")
    PRIMARY = ("#2563EB", "#3B82F6")
    PRIMARY_HOVER = ("#1D4ED8", "#2563EB")
    SUCCESS = ("#15803D", "#22C55E")
    WARNING = ("#B45309", "#F59E0B")
    DANGER = ("#DC2626", "#EF4444")
    DISABLED = ("#B7C1CF", "#475569")

    def __init__(self, config: Config):
        self.ui_font_family = ""
        super().__init__(config)
        self.configure(fg_color=self.BG)
        self.geometry("1260x800")
        self.minsize(1040, 700)

    def _pick_font_family(self) -> str:
        if self.ui_font_family:
            return self.ui_font_family
        try:
            families = {name.casefold(): name for name in tkfont.families(self)}
        except Exception:
            families = {}
        for candidate in (
            "Noto Sans Arabic",
            "Noto Sans",
            "Segoe UI",
            "DejaVu Sans",
            "Arial",
        ):
            match = families.get(candidate.casefold())
            if match:
                self.ui_font_family = match
                return match
        self.ui_font_family = "TkDefaultFont"
        return self.ui_font_family

    def _font(self, size: int = 14, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(family=self._pick_font_family(), size=size, weight=weight)

    # ---------------------------------------------------------------- layout
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self,
            width=238,
            corner_radius=0,
            fg_color=self.SIDEBAR,
            border_width=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(9, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=22, pady=(30, 24))
        ctk.CTkLabel(
            brand,
            text="CYBREX",
            text_color=self.TEXT,
            font=self._font(25, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand,
            text="Rich Presence",
            text_color=self.MUTED,
            font=self._font(13),
        ).pack(anchor="w", pady=(2, 0))

        self.nav = {}
        pages = (
            ("dashboard", "Overview"),
            ("integrations", "Integrations"),
            ("activity", "Activity"),
            ("privacy", "Privacy"),
            ("settings", "Settings"),
            ("diagnostics", "Diagnostics"),
            ("about", "About"),
        )
        for row, (name, label) in enumerate(pages, start=1):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                text_color=self.TEXT,
                font=self._font(14),
                height=43,
                anchor="w",
                corner_radius=10,
                fg_color="transparent",
                hover_color=("#DCE7F7", "#1D2A3D"),
                command=lambda n=name: self.select_page(n),
            )
            button.grid(row=row, column=0, sticky="ew", padx=13, pady=3)
            self.nav[name] = button

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=10, column=0, sticky="sew", padx=14, pady=15)
        ctk.CTkLabel(
            footer,
            text="Appearance",
            text_color=self.MUTED,
            font=self._font(12),
            anchor="w",
        ).pack(fill="x", padx=4, pady=(0, 5))
        self.theme_menu = ctk.CTkOptionMenu(
            footer,
            values=["System", "Light", "Dark"],
            command=ctk.set_appearance_mode,
            width=196,
            height=36,
            fg_color=self.SURFACE_ALT,
            button_color=self.PRIMARY,
            button_hover_color=self.PRIMARY_HOVER,
            text_color=self.TEXT,
            dropdown_fg_color=self.SURFACE,
            dropdown_text_color=self.TEXT,
        )
        self.theme_menu.pack(fill="x", pady=(0, 9))
        ctk.CTkButton(
            footer,
            text="Save changes",
            font=self._font(14, "bold"),
            height=40,
            fg_color=self.PRIMARY,
            hover_color=self.PRIMARY_HOVER,
            command=self.save_settings,
        ).pack(fill="x")

    def _page(self, name: str, title: str, subtitle: str):
        page = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
            fg_color=self.BG,
            scrollbar_button_color=("#C9D5E3", "#334155"),
            scrollbar_button_hover_color=("#AAB9CB", "#475569"),
        )
        self.pages[name] = page
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=34, pady=(28, 15))
        ctk.CTkLabel(
            header,
            text=title,
            text_color=self.TEXT,
            font=self._font(31, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=subtitle,
            text_color=self.MUTED,
            font=self._font(13),
            justify="left",
            wraplength=880,
        ).pack(anchor="w", pady=(5, 0))
        return page

    def _section(self, parent, title: str, subtitle: str = ""):
        box = ctk.CTkFrame(
            parent,
            corner_radius=14,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
        )
        box.pack(fill="x", padx=34, pady=9)
        ctk.CTkLabel(
            box,
            text=title,
            text_color=self.TEXT,
            font=self._font(17, "bold"),
        ).pack(anchor="w", padx=21, pady=(18, 2))
        if subtitle:
            ctk.CTkLabel(
                box,
                text=subtitle,
                text_color=self.MUTED,
                font=self._font(13),
                justify="left",
                wraplength=850,
            ).pack(anchor="w", padx=21, pady=(0, 10))
        return box

    def _status_card(self, parent, title: str, value: str):
        card = ctk.CTkFrame(
            parent,
            corner_radius=13,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
        )
        ctk.CTkLabel(
            card,
            text=title,
            text_color=self.MUTED,
            font=self._font(12),
        ).pack(anchor="w", padx=17, pady=(15, 4))
        label = ctk.CTkLabel(
            card,
            text=value,
            text_color=self.TEXT,
            font=self._font(16, "bold"),
            justify="left",
            wraplength=250,
        )
        label.pack(anchor="w", padx=17, pady=(0, 15))
        return card, label

    # --------------------------------------------------------------- dashboard
    def _build_dashboard(self):
        page = self._page(
            "dashboard",
            "Overview",
            "Live status for the local service, Discord connection, current activity and integrations.",
        )

        hero = ctk.CTkFrame(
            page,
            corner_radius=16,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
        )
        hero.pack(fill="x", padx=34, pady=9)

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=23, pady=21)
        self.status_label = ctk.CTkLabel(
            left,
            text="● Service stopped",
            text_color=self.MUTED,
            font=self._font(22, "bold"),
        )
        self.status_label.pack(anchor="w")
        self.activity_label = ctk.CTkLabel(
            left,
            text="No activity is being published.",
            text_color=self.MUTED,
            font=self._font(14),
            justify="left",
            anchor="w",
            wraplength=690,
        )
        self.activity_label.pack(anchor="w", pady=(9, 0), fill="x")

        controls = ctk.CTkFrame(hero, fg_color="transparent")
        controls.pack(side="right", padx=19, pady=18)
        self.start_button = ctk.CTkButton(
            controls,
            text="Start service",
            width=158,
            height=40,
            font=self._font(13, "bold"),
            fg_color=self.PRIMARY,
            hover_color=self.PRIMARY_HOVER,
            command=self.start_service,
        )
        self.start_button.pack(pady=4)
        self.stop_button = ctk.CTkButton(
            controls,
            text="Stop service",
            width=158,
            height=40,
            font=self._font(13, "bold"),
            fg_color="transparent",
            hover_color=("#FEE2E2", "#431A1A"),
            border_width=1,
            border_color=self.DANGER,
            text_color=self.DANGER,
            command=self.stop_service,
        )
        self.stop_button.pack(pady=4)

        metrics = ctk.CTkFrame(page, fg_color="transparent")
        metrics.pack(fill="x", padx=34, pady=5)
        for column in range(3):
            metrics.grid_columnconfigure(column, weight=1, uniform="metric")

        rpc_card, self.rpc_value = self._status_card(metrics, "Discord RPC", "Disconnected")
        rpc_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        browser_card, self.browser_value = self._status_card(metrics, "Browser Companion", "Checking…")
        browser_card.grid(row=0, column=1, sticky="nsew", padx=6)
        cs2_card, self.cs2_value = self._status_card(metrics, "Counter-Strike 2", "Checking…")
        cs2_card.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        runtime = self._section(page, "Runtime details")
        self.heartbeat_label = ctk.CTkLabel(
            runtime, text="Heartbeat: —", text_color=self.TEXT, font=self._font(13), justify="left"
        )
        self.heartbeat_label.pack(anchor="w", padx=21, pady=(8, 4))
        self.state_label = ctk.CTkLabel(
            runtime, text="State: stopped", text_color=self.TEXT, font=self._font(13), justify="left"
        )
        self.state_label.pack(anchor="w", padx=21, pady=4)
        self.error_label = ctk.CTkLabel(
            runtime,
            text="Last error: none",
            text_color=self.MUTED,
            font=self._font(13),
            justify="left",
            wraplength=850,
        )
        self.error_label.pack(anchor="w", padx=21, pady=(4, 18))

        quick = ctk.CTkFrame(page, fg_color="transparent")
        quick.pack(fill="x", padx=34, pady=(6, 21))
        for label, command in (
            ("Test Discord", self.test_rpc),
            ("Run diagnostics", self.run_diagnostics),
            ("Open logs", self.open_logs),
        ):
            ctk.CTkButton(
                quick,
                text=label,
                command=command,
                font=self._font(13, "bold"),
                height=38,
                fg_color="transparent",
                hover_color=("#E8F0FE", "#172554"),
                border_width=1,
                border_color=self.PRIMARY,
                text_color=self.PRIMARY,
            ).pack(side="left", padx=(0, 9))

    # -------------------------------------------------------------- navigation
    def select_page(self, name: str):
        for page_name, page in self.pages.items():
            if page_name == name:
                page.grid(row=0, column=1, sticky="nsew")
            else:
                page.grid_forget()
        for button_name, button in self.nav.items():
            selected = button_name == name
            button.configure(
                fg_color=("#DCE7F7", "#1D2A3D") if selected else "transparent",
                text_color=self.PRIMARY if selected else self.TEXT,
            )

    # ----------------------------------------------------------- service state
    def restart_service(self):
        active = self.runtime.read_active()
        if active and not self.runtime.terminate_active(timeout=5):
            from tkinter import messagebox

            messagebox.showerror(
                "Restart error",
                "The running service could not be stopped. Open Diagnostics or Logs for details.",
            )
            return
        self.service_process = None
        self.after(350, self.start_service)

    def _poll_service(self):
        if getattr(self, "_closing", False):
            return
        try:
            active = self.runtime.read_active()
            if not active:
                self.status_label.configure(text="● Service stopped", text_color=self.MUTED)
                self.rpc_value.configure(text="Disconnected", text_color=self.MUTED)
                self.activity_label.configure(text="No activity is being published.")
                self.heartbeat_label.configure(text="Heartbeat: —")
                self.state_label.configure(text="State: stopped")
                self.error_label.configure(text="Last error: none")
                self.start_button.configure(
                    text="Start service",
                    command=self.start_service,
                    state="normal",
                    fg_color=self.PRIMARY,
                    hover_color=self.PRIMARY_HOVER,
                )
                self.stop_button.configure(state="disabled")
            else:
                state = str(active.get("state") or "running")
                pid = active.get("pid", "?")
                connected = bool(active.get("connected", False))
                presence_active = bool(active.get("presence_active", False))
                activity = active.get("activity") or (
                    "No publishable activity" if not presence_active else "Active"
                )
                updated = float(active.get("updated_at") or 0)
                age = max(0.0, time.time() - updated) if updated else 0.0
                stale = bool(
                    updated
                    and age
                    > max(15.0, float(self.config.get("update_interval_secs", 2)) * 3)
                )

                if stale:
                    self.status_label.configure(
                        text=f"● Heartbeat stale · PID {pid}", text_color=self.WARNING
                    )
                elif state in {"rpc_error", "loop_error", "configuration_error"}:
                    self.status_label.configure(
                        text=f"● Running with an error · PID {pid}", text_color=self.DANGER
                    )
                else:
                    self.status_label.configure(
                        text=f"● Service running · PID {pid}", text_color=self.SUCCESS
                    )

                if state == "dry_run":
                    self.rpc_value.configure(text="Dry-run mode", text_color=self.WARNING)
                elif connected:
                    self.rpc_value.configure(text="Connected", text_color=self.SUCCESS)
                else:
                    self.rpc_value.configure(text="Disconnected", text_color=self.DANGER)

                self.activity_label.configure(text=display_text(activity))
                self.heartbeat_label.configure(text=f"Heartbeat: {age:.1f}s ago")
                self.state_label.configure(text=f"State: {state}")
                last_error = str(active.get("last_error") or "").strip()
                self.error_label.configure(
                    text=display_text(
                        f"Last error: {last_error[:220] if last_error else 'none'}"
                    )
                )
                self.start_button.configure(
                    text="Restart service",
                    command=self.restart_service,
                    state="normal",
                    fg_color=self.PRIMARY,
                    hover_color=self.PRIMARY_HOVER,
                )
                self.stop_button.configure(state="normal")
        finally:
            if not getattr(self, "_closing", False):
                self.after(1000, self._poll_service)


if __name__ == "__main__":
    app = ModernControlPanel(Config())
    app.mainloop()
