"""Refined CYBREX desktop control panel with icon-led hierarchy."""

from __future__ import annotations

import time

import customtkinter as ctk

from app_version import APP_VERSION
from config import Config
from gui_modern_v3 import ModernControlPanel as ResourceAwareControlPanel
from social_sdk_transport import social_sdk_available
from ui_icons import icon


class ModernControlPanel(ResourceAwareControlPanel):
    """Modern desktop surface without changing service/config behavior."""

    SIDEBAR_WIDTH = 252

    def __init__(self, config: Config):
        super().__init__(config)
        self.geometry("1320x840")
        self.minsize(1080, 720)
        self.after(700, self._poll_identity_surface)

    # ---------------------------------------------------------------- layout
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self,
            width=self.SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=self.SIDEBAR,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(9, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(26, 22))

        mark = ctk.CTkFrame(
            brand,
            width=44,
            height=44,
            corner_radius=13,
            fg_color=self.PRIMARY,
        )
        mark.pack(side="left", padx=(0, 12))
        mark.pack_propagate(False)
        ctk.CTkLabel(
            mark,
            text="C",
            text_color="#FFFFFF",
            font=self._font(20, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            brand_text,
            text="CYBREX",
            text_color=self.TEXT,
            font=self._font(23, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_text,
            text="Presence",
            text_color=self.MUTED,
            font=self._font(12),
        ).pack(anchor="w", pady=(0, 1))

        self.nav = {}
        pages = (
            ("dashboard", "Overview", "overview"),
            ("integrations", "Integrations", "integrations"),
            ("activity", "Activity", "activity"),
            ("privacy", "Privacy", "privacy"),
            ("settings", "Settings", "settings"),
            ("diagnostics", "Diagnostics", "diagnostics"),
            ("about", "About", "about"),
        )
        for row, (name, label, icon_name) in enumerate(pages, start=1):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                image=icon(icon_name, 18),
                compound="left",
                text_color=self.TEXT,
                font=self._font(14, "bold" if name == "dashboard" else "normal"),
                height=44,
                anchor="w",
                corner_radius=11,
                border_spacing=10,
                fg_color="transparent",
                hover_color=("#DFE9F7", "#1A2940"),
                command=lambda n=name: self.select_page(n),
            )
            button.grid(row=row, column=0, sticky="ew", padx=13, pady=3)
            self.nav[name] = button

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=10, column=0, sticky="sew", padx=14, pady=15)

        build = ctk.CTkFrame(
            footer,
            corner_radius=11,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
        )
        build.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            build,
            text=f"CYBREX {APP_VERSION}",
            text_color=self.TEXT,
            font=self._font(12, "bold"),
        ).pack(anchor="w", padx=12, pady=(9, 1))
        self.transport_hint = ctk.CTkLabel(
            build,
            text="Dynamic activity names ready" if social_sdk_available() else "Legacy Discord naming",
            text_color=self.SUCCESS if social_sdk_available() else self.MUTED,
            font=self._font(11),
        )
        self.transport_hint.pack(anchor="w", padx=12, pady=(0, 9))

        ctk.CTkLabel(
            footer,
            text="Appearance",
            text_color=self.MUTED,
            font=self._font(11),
            anchor="w",
        ).pack(fill="x", padx=4, pady=(0, 5))
        self.theme_menu = ctk.CTkOptionMenu(
            footer,
            values=["System", "Light", "Dark"],
            command=ctk.set_appearance_mode,
            width=210,
            height=36,
            corner_radius=9,
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
            image=icon("settings", 16),
            compound="left",
            font=self._font(13, "bold"),
            height=40,
            corner_radius=10,
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
        header.pack(fill="x", padx=36, pady=(28, 16))
        copy = ctk.CTkFrame(header, fg_color="transparent")
        copy.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            copy,
            text=title,
            text_color=self.TEXT,
            font=self._font(31, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            copy,
            text=subtitle,
            text_color=self.MUTED,
            font=self._font(13),
            justify="left",
            wraplength=820,
        ).pack(anchor="w", pady=(5, 0))

        pill = ctk.CTkFrame(
            header,
            corner_radius=16,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
        )
        pill.pack(side="right", padx=(16, 0), pady=7)
        ctk.CTkLabel(
            pill,
            text=f"v{APP_VERSION}",
            text_color=self.MUTED,
            font=self._font(11, "bold"),
        ).pack(padx=12, pady=6)
        return page

    def _status_card(self, parent, title: str, value: str):
        icon_name = {
            "Discord RPC": "discord",
            "Browser Companion": "browser",
            "Counter-Strike 2": "game",
            "Current app": "app",
        }.get(title, "app")
        card = ctk.CTkFrame(
            parent,
            corner_radius=14,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
        )
        heading = ctk.CTkFrame(card, fg_color="transparent")
        heading.pack(fill="x", padx=15, pady=(14, 6))
        ctk.CTkLabel(heading, text="", image=icon(icon_name, 18)).pack(side="left")
        ctk.CTkLabel(
            heading,
            text=title,
            text_color=self.MUTED,
            font=self._font(12, "bold"),
        ).pack(side="left", padx=(8, 0))
        label = ctk.CTkLabel(
            card,
            text=value,
            text_color=self.TEXT,
            font=self._font(16, "bold"),
            justify="left",
            anchor="w",
            wraplength=230,
        )
        label.pack(fill="x", padx=16, pady=(0, 15))
        return card, label

    # --------------------------------------------------------------- dashboard
    def _build_dashboard(self):
        page = self._page(
            "dashboard",
            "Overview",
            "Your current Discord presence, foreground activity and local integrations at a glance.",
        )

        hero = ctk.CTkFrame(
            page,
            corner_radius=18,
            fg_color=self.SURFACE,
            border_width=1,
            border_color=self.BORDER,
        )
        hero.pack(fill="x", padx=36, pady=(8, 10))

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=24, pady=22)
        ctk.CTkLabel(
            left,
            text="SERVICE",
            text_color=self.MUTED,
            font=self._font(10, "bold"),
        ).pack(anchor="w")
        self.status_label = ctk.CTkLabel(
            left,
            text="● Service stopped",
            text_color=self.MUTED,
            font=self._font(23, "bold"),
        )
        self.status_label.pack(anchor="w", pady=(4, 0))
        self.activity_label = ctk.CTkLabel(
            left,
            text="No activity is being published.",
            text_color=self.MUTED,
            font=self._font(14),
            justify="left",
            anchor="w",
            wraplength=680,
        )
        self.activity_label.pack(anchor="w", pady=(9, 0), fill="x")

        controls = ctk.CTkFrame(hero, fg_color="transparent")
        controls.pack(side="right", padx=20, pady=18)
        self.start_button = ctk.CTkButton(
            controls,
            text="Start service",
            image=icon("activity", 17),
            compound="left",
            width=168,
            height=42,
            corner_radius=10,
            font=self._font(13, "bold"),
            fg_color=self.PRIMARY,
            hover_color=self.PRIMARY_HOVER,
            command=self.start_service,
        )
        self.start_button.pack(pady=4)
        self.stop_button = ctk.CTkButton(
            controls,
            text="Stop service",
            width=168,
            height=40,
            corner_radius=10,
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
        metrics.pack(fill="x", padx=36, pady=4)
        for column in range(4):
            metrics.grid_columnconfigure(column, weight=1, uniform="metric")

        rpc_card, self.rpc_value = self._status_card(metrics, "Discord RPC", "Disconnected")
        rpc_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        browser_card, self.browser_value = self._status_card(metrics, "Browser Companion", "Checking…")
        browser_card.grid(row=0, column=1, sticky="nsew", padx=5)
        cs2_card, self.cs2_value = self._status_card(metrics, "Counter-Strike 2", "Checking…")
        cs2_card.grid(row=0, column=2, sticky="nsew", padx=5)
        app_card, self.identity_value = self._status_card(metrics, "Current app", "Waiting…")
        app_card.grid(row=0, column=3, sticky="nsew", padx=(5, 0))

        runtime = self._section(page, "Runtime details")
        runtime_grid = ctk.CTkFrame(runtime, fg_color="transparent")
        runtime_grid.pack(fill="x", padx=15, pady=(7, 17))
        runtime_grid.grid_columnconfigure(0, weight=1)
        runtime_grid.grid_columnconfigure(1, weight=1)

        left_runtime = ctk.CTkFrame(runtime_grid, fg_color="transparent")
        left_runtime.grid(row=0, column=0, sticky="nsew", padx=(5, 18))
        self.heartbeat_label = ctk.CTkLabel(
            left_runtime, text="Heartbeat: —", text_color=self.TEXT, font=self._font(13)
        )
        self.heartbeat_label.pack(anchor="w", pady=3)
        self.state_label = ctk.CTkLabel(
            left_runtime, text="State: stopped", text_color=self.TEXT, font=self._font(13)
        )
        self.state_label.pack(anchor="w", pady=3)
        self.error_label = ctk.CTkLabel(
            left_runtime,
            text="Last error: none",
            text_color=self.MUTED,
            font=self._font(13),
            justify="left",
            wraplength=520,
        )
        self.error_label.pack(anchor="w", pady=3)

        right_runtime = ctk.CTkFrame(
            runtime_grid,
            corner_radius=12,
            fg_color=self.SURFACE_ALT,
        )
        right_runtime.grid(row=0, column=1, sticky="nsew", padx=(18, 5))
        ctk.CTkLabel(
            right_runtime,
            text="Discord activity identity",
            text_color=self.MUTED,
            font=self._font(11, "bold"),
        ).pack(anchor="w", padx=14, pady=(11, 2))
        self.transport_label = ctk.CTkLabel(
            right_runtime,
            text="Legacy RPC · registered app name",
            text_color=self.TEXT,
            font=self._font(13, "bold"),
            justify="left",
        )
        self.transport_label.pack(anchor="w", padx=14, pady=(0, 3))
        self.transport_explainer = ctk.CTkLabel(
            right_runtime,
            text="Dynamic top-level names activate automatically when the Discord Social SDK helper is installed.",
            text_color=self.MUTED,
            font=self._font(11),
            justify="left",
            wraplength=420,
        )
        self.transport_explainer.pack(anchor="w", padx=14, pady=(0, 11))

        quick = ctk.CTkFrame(page, fg_color="transparent")
        quick.pack(fill="x", padx=36, pady=(7, 22))
        for label, icon_name, command in (
            ("Test Discord", "discord", self.test_rpc),
            ("Run diagnostics", "diagnostics", self.run_diagnostics),
            ("Open logs", "activity", self.open_logs),
        ):
            ctk.CTkButton(
                quick,
                text=label,
                image=icon(icon_name, 16),
                compound="left",
                command=command,
                font=self._font(13, "bold"),
                height=39,
                corner_radius=10,
                fg_color="transparent",
                hover_color=("#E8F0FE", "#172554"),
                border_width=1,
                border_color=self.BORDER,
                text_color=self.TEXT,
            ).pack(side="left", padx=(0, 9))

    def _poll_identity_surface(self):
        if getattr(self, "_closing", False):
            return
        try:
            active = self.runtime.read_active() or {}
            identity = str(active.get("activity_name") or "").strip()
            activity = str(active.get("activity") or "").strip()
            if not identity and activity:
                identity = activity.split(" · ", 1)[-1].split(" — ", 1)[0].strip()
            self.identity_value.configure(
                text=identity[:64] if identity else "Waiting for activity…",
                text_color=self.TEXT if identity else self.MUTED,
            )

            transport = str(active.get("transport") or "legacy_rpc").strip()
            if transport == "social_sdk":
                self.transport_label.configure(
                    text="Social SDK · dynamic app name",
                    text_color=self.SUCCESS,
                )
                self.transport_explainer.configure(
                    text="Discord receives the real current activity name instead of the registered CYBREX application name."
                )
                self.transport_hint.configure(
                    text="Dynamic activity names active",
                    text_color=self.SUCCESS,
                )
            elif transport == "legacy_rpc_fallback":
                self.transport_label.configure(
                    text="Legacy RPC fallback",
                    text_color=self.WARNING,
                )
                self.transport_explainer.configure(
                    text="The Social SDK helper was unavailable or failed, so CYBREX kept Presence running through legacy RPC."
                )
            else:
                self.transport_label.configure(
                    text="Legacy RPC · registered app name",
                    text_color=self.MUTED,
                )
        except Exception:
            pass
        finally:
            self.after(1200, self._poll_identity_surface)


if __name__ == "__main__":
    app = ModernControlPanel(Config())
    app.mainloop()
