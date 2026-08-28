"""Modern configuration/control panel for Discord Rich Presence."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from config import Config, DEFAULT_CONFIG, resolve_discord_application_id
from runtime_state import RuntimeState

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    _WINREG_AVAILABLE = False


ctk.set_appearance_mode('System')
ctk.set_default_color_theme('blue')


class ModernControlPanel(ctk.CTk):
    """Release-facing desktop control panel for service status and configuration."""

    BRAND = 'CYBREX Rich Presence'
    VERSION_LABEL = 'Desktop Control Center'

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.runtime = RuntimeState()
        self.service_process: subprocess.Popen | None = None
        self._integration_probe_busy = False

        self.title(self.BRAND)
        self.geometry('1180x760')
        self.minsize(980, 680)
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_pages()
        self.select_page('dashboard')
        self.after(400, self._poll_service)
        self.after(900, self._poll_integrations)

    # ------------------------------------------------------------------ layout
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=230, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(9, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color='transparent')
        brand.grid(row=0, column=0, sticky='ew', padx=20, pady=(28, 22))
        ctk.CTkLabel(
            brand,
            text='CYBREX',
            font=ctk.CTkFont(size=24, weight='bold'),
        ).pack(anchor='w')
        ctk.CTkLabel(
            brand,
            text='Rich Presence',
            text_color=('gray35', 'gray70'),
            font=ctk.CTkFont(size=13),
        ).pack(anchor='w', pady=(1, 0))

        self.nav = {}
        pages = (
            ('dashboard', 'Overview'),
            ('integrations', 'Integrations'),
            ('activity', 'Activity'),
            ('privacy', 'Privacy'),
            ('settings', 'Settings'),
            ('diagnostics', 'Diagnostics'),
            ('about', 'About'),
        )
        for row, (name, label) in enumerate(pages, start=1):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                height=42,
                anchor='w',
                corner_radius=8,
                fg_color='transparent',
                hover_color=('gray80', 'gray24'),
                command=lambda n=name: self.select_page(n),
            )
            button.grid(row=row, column=0, sticky='ew', padx=12, pady=3)
            self.nav[name] = button

        footer = ctk.CTkFrame(sidebar, fg_color='transparent')
        footer.grid(row=10, column=0, sticky='sew', padx=14, pady=14)
        self.theme_menu = ctk.CTkOptionMenu(
            footer,
            values=['System', 'Light', 'Dark'],
            command=ctk.set_appearance_mode,
            width=190,
        )
        self.theme_menu.pack(fill='x', pady=(0, 8))
        ctk.CTkButton(
            footer,
            text='Save changes',
            height=38,
            command=self.save_settings,
        ).pack(fill='x')

    def _build_pages(self):
        self.pages = {}
        self._build_dashboard()
        self._build_integrations()
        self._build_activity()
        self._build_privacy()
        self._build_settings()
        self._build_diagnostics()
        self._build_about()

    def _page(self, name: str, title: str, subtitle: str):
        page = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color='transparent')
        self.pages[name] = page
        header = ctk.CTkFrame(page, fg_color='transparent')
        header.pack(fill='x', padx=32, pady=(26, 14))
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=29, weight='bold'),
        ).pack(anchor='w')
        ctk.CTkLabel(
            header,
            text=subtitle,
            text_color=('gray35', 'gray68'),
            justify='left',
            wraplength=850,
        ).pack(anchor='w', pady=(4, 0))
        return page

    @staticmethod
    def _section(parent, title: str, subtitle: str = ''):
        box = ctk.CTkFrame(parent, corner_radius=14)
        box.pack(fill='x', padx=32, pady=9)
        ctk.CTkLabel(
            box,
            text=title,
            font=ctk.CTkFont(size=17, weight='bold'),
        ).pack(anchor='w', padx=20, pady=(18, 2))
        if subtitle:
            ctk.CTkLabel(
                box,
                text=subtitle,
                text_color=('gray35', 'gray68'),
                justify='left',
                wraplength=820,
            ).pack(anchor='w', padx=20, pady=(0, 10))
        return box

    @staticmethod
    def _status_card(parent, title: str, value: str):
        card = ctk.CTkFrame(parent, corner_radius=12)
        ctk.CTkLabel(card, text=title, text_color=('gray35', 'gray68')).pack(
            anchor='w', padx=16, pady=(14, 3)
        )
        label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=16, weight='bold'),
            justify='left',
            wraplength=240,
        )
        label.pack(anchor='w', padx=16, pady=(0, 14))
        return card, label

    # --------------------------------------------------------------- dashboard
    def _build_dashboard(self):
        page = self._page(
            'dashboard',
            'Overview',
            'Live status for the local service, Discord connection, current activity and integrations.',
        )

        hero = ctk.CTkFrame(page, corner_radius=16)
        hero.pack(fill='x', padx=32, pady=9)
        left = ctk.CTkFrame(hero, fg_color='transparent')
        left.pack(side='left', fill='both', expand=True, padx=22, pady=20)
        self.status_label = ctk.CTkLabel(
            left,
            text='● Service stopped',
            font=ctk.CTkFont(size=21, weight='bold'),
        )
        self.status_label.pack(anchor='w')
        self.activity_label = ctk.CTkLabel(
            left,
            text='No activity is being published.',
            justify='left',
            wraplength=650,
            text_color=('gray30', 'gray75'),
        )
        self.activity_label.pack(anchor='w', pady=(7, 0))

        controls = ctk.CTkFrame(hero, fg_color='transparent')
        controls.pack(side='right', padx=18, pady=18)
        self.start_button = ctk.CTkButton(
            controls, text='Start service', width=140, height=38, command=self.start_service
        )
        self.start_button.pack(pady=4)
        self.stop_button = ctk.CTkButton(
            controls,
            text='Stop service',
            width=140,
            height=38,
            fg_color=('gray65', 'gray30'),
            command=self.stop_service,
        )
        self.stop_button.pack(pady=4)

        metrics = ctk.CTkFrame(page, fg_color='transparent')
        metrics.pack(fill='x', padx=32, pady=4)
        for column in range(3):
            metrics.grid_columnconfigure(column, weight=1, uniform='metric')

        rpc_card, self.rpc_value = self._status_card(metrics, 'Discord RPC', 'Disconnected')
        rpc_card.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        browser_card, self.browser_value = self._status_card(metrics, 'Browser Companion', 'Checking…')
        browser_card.grid(row=0, column=1, sticky='nsew', padx=6)
        cs2_card, self.cs2_value = self._status_card(metrics, 'Counter-Strike 2', 'Checking…')
        cs2_card.grid(row=0, column=2, sticky='nsew', padx=(6, 0))

        runtime = self._section(page, 'Runtime details')
        self.heartbeat_label = ctk.CTkLabel(runtime, text='Heartbeat: —', justify='left')
        self.heartbeat_label.pack(anchor='w', padx=20, pady=(8, 4))
        self.state_label = ctk.CTkLabel(runtime, text='State: stopped', justify='left')
        self.state_label.pack(anchor='w', padx=20, pady=4)
        self.error_label = ctk.CTkLabel(
            runtime,
            text='Last error: none',
            justify='left',
            wraplength=820,
            text_color=('gray35', 'gray68'),
        )
        self.error_label.pack(anchor='w', padx=20, pady=(4, 18))

        quick = ctk.CTkFrame(page, fg_color='transparent')
        quick.pack(fill='x', padx=32, pady=(5, 20))
        ctk.CTkButton(quick, text='Test Discord', command=self.test_rpc).pack(side='left', padx=(0, 8))
        ctk.CTkButton(quick, text='Run diagnostics', command=self.run_diagnostics).pack(side='left', padx=8)
        ctk.CTkButton(quick, text='Open logs', command=self.open_logs).pack(side='left', padx=8)

    # ------------------------------------------------------------- integrations
    def _build_integrations(self):
        page = self._page(
            'integrations',
            'Integrations',
            'Configure the browser bridge, game detection and Counter-Strike 2 GSI from one place.',
        )

        browser = self._section(
            page,
            'Browser Companion',
            'Optional local extension bridge for exact browser tabs, services and media. Traffic stays on 127.0.0.1.',
        )
        self.browser_enabled = ctk.BooleanVar(
            value=bool(self.config.get('browser_companion.enabled', True))
        )
        ctk.CTkSwitch(browser, text='Enable Browser Companion bridge', variable=self.browser_enabled).pack(
            anchor='w', padx=20, pady=(6, 10)
        )
        row = ctk.CTkFrame(browser, fg_color='transparent')
        row.pack(fill='x', padx=15, pady=(0, 8))
        ctk.CTkLabel(row, text='Local port').pack(side='left', padx=5)
        self.browser_port = tk.StringVar(value=str(self.config.get('browser_companion.port', 32191)))
        ctk.CTkEntry(row, textvariable=self.browser_port, width=110).pack(side='left', padx=8)
        self.browser_status_label = ctk.CTkLabel(row, text='Status: checking…', text_color='gray')
        self.browser_status_label.pack(side='left', padx=16)
        ctk.CTkButton(row, text='Test bridge', width=110, command=self.test_browser_companion).pack(
            side='right', padx=5
        )
        ctk.CTkLabel(
            browser,
            text='The extension Options page must use the same port. Default: 32191.',
            text_color=('gray35', 'gray68'),
        ).pack(anchor='w', padx=20, pady=(0, 16))

        games = self._section(
            page,
            'Game detection',
            'Steam, Epic and Heroic/Legendary libraries are resolved from local manifests when available.',
        )
        self.game_detection_enabled = ctk.BooleanVar(
            value=bool(self.config.get('rules.enabled_detectors.gaming', True))
        )
        ctk.CTkSwitch(games, text='Publish recognized games', variable=self.game_detection_enabled).pack(
            anchor='w', padx=20, pady=(6, 8)
        )
        ctk.CTkLabel(
            games,
            text='Steam uses AppID + local appmanifest metadata. Epic/Heroic use local install manifests. No store account token is required.',
            justify='left',
            wraplength=820,
            text_color=('gray35', 'gray68'),
        ).pack(anchor='w', padx=20, pady=(0, 16))

        cs2 = self._section(
            page,
            'Counter-Strike 2 GSI',
            'Optional Valve Game State Integration for map, mode, team and score. No memory reading or game injection.',
        )
        self.cs2_enabled = ctk.BooleanVar(value=bool(self.config.get('cs2_gsi.enabled', True)))
        self.cs2_auto_install = ctk.BooleanVar(value=bool(self.config.get('cs2_gsi.auto_install', True)))
        ctk.CTkSwitch(cs2, text='Enable CS2 GSI listener', variable=self.cs2_enabled).pack(
            anchor='w', padx=20, pady=(6, 8)
        )
        ctk.CTkSwitch(cs2, text='Automatically configure CS2 when detected', variable=self.cs2_auto_install).pack(
            anchor='w', padx=20, pady=8
        )
        row = ctk.CTkFrame(cs2, fg_color='transparent')
        row.pack(fill='x', padx=15, pady=(4, 16))
        self.cs2_status_label = ctk.CTkLabel(row, text='Status: checking…', text_color='gray')
        self.cs2_status_label.pack(side='left', padx=5)
        ctk.CTkButton(row, text='Install / repair GSI', command=self.install_cs2_gsi).pack(
            side='right', padx=5
        )

    # ---------------------------------------------------------------- activity
    def _build_activity(self):
        page = self._page(
            'activity',
            'Activity',
            'Choose which activity types can publish and how conflicts such as background media are resolved.',
        )
        enabled = self.config.get('rules.enabled_detectors', {}) or {}
        self.detector_vars = {}
        labels = {
            'gaming': 'Games',
            'coding': 'Code editors',
            'browser': 'Browsers',
            'media': 'Media players',
            'terminal': 'Terminal / console',
            'application': 'Other applications',
        }
        box = self._section(page, 'Detectors')
        for key, label in labels.items():
            value = self.game_detection_enabled.get() if key == 'gaming' else bool(enabled.get(key, True))
            var = self.game_detection_enabled if key == 'gaming' else ctk.BooleanVar(value=value)
            self.detector_vars[key] = var
            ctk.CTkCheckBox(box, text=label, variable=var).pack(anchor='w', padx=20, pady=8)
        ctk.CTkLabel(
            box,
            text='Disable “Other applications” if you only want recognized games, media, browser, coding and terminal activity.',
            text_color=('gray35', 'gray68'),
            wraplength=820,
            justify='left',
        ).pack(anchor='w', padx=20, pady=(4, 16))

        priority = self._section(
            page,
            'Activity priority',
            'Smart is recommended: games stay strongest while foreground work beats unrelated background media.',
        )
        self.priority_policy = tk.StringVar(
            value=str(self.config.get('rules.activity_priority.policy', 'smart'))
        )
        ctk.CTkOptionMenu(
            priority,
            variable=self.priority_policy,
            values=['smart', 'foreground_first', 'media_first', 'custom'],
            width=220,
        ).pack(anchor='w', padx=20, pady=(8, 18))

    # ---------------------------------------------------------------- privacy
    def _build_privacy(self):
        page = self._page(
            'privacy',
            'Privacy',
            'Control how much local activity information can be published to Discord.',
        )
        box = self._section(page, 'Privacy mode')
        self.privacy_mode = tk.StringVar(value=str(self.config.get('privacy.mode', 'balanced')))
        descriptions = (
            ('off', 'Off — minimal redaction'),
            ('balanced', 'Balanced — redact secrets and reduce path/URL exposure'),
            ('strict', 'Strict — generic activity only; no browser URLs or buttons'),
        )
        for value, label in descriptions:
            ctk.CTkRadioButton(box, text=label, variable=self.privacy_mode, value=value).pack(
                anchor='w', padx=20, pady=8
            )

        browser = self._section(
            page,
            'Browser URL sharing',
            'Balanced mode defaults to domain only. Full URLs may contain sensitive query parameters even after redaction.',
        )
        self.browser_url_mode = tk.StringVar(
            value=str(self.config.get('privacy.browser_url_mode', 'domain'))
        )
        ctk.CTkOptionMenu(
            browser,
            variable=self.browser_url_mode,
            values=['none', 'domain', 'path', 'full'],
            width=220,
        ).pack(anchor='w', padx=20, pady=(8, 16))

        system = self._section(page, 'Local privacy protections')
        self.hide_home = ctk.BooleanVar(value=bool(self.config.get('privacy.hide_home_paths', True)))
        ctk.CTkSwitch(system, text='Redact home-directory paths', variable=self.hide_home).pack(
            anchor='w', padx=20, pady=(8, 8)
        )
        self.clear_on_lock = ctk.BooleanVar(
            value=bool(self.config.get('rules.clear_on_lock_screen', True))
        )
        ctk.CTkSwitch(system, text='Clear Presence on lock screen', variable=self.clear_on_lock).pack(
            anchor='w', padx=20, pady=(8, 18)
        )

    # ---------------------------------------------------------------- settings
    def _build_settings(self):
        page = self._page(
            'settings',
            'Settings',
            'General runtime, artwork and Windows startup settings.',
        )
        connection = self._section(
            page,
            'Discord connection',
            'Automatic — uses the built-in public CYBREX Discord Application ID and the local Discord Desktop account.',
        )
        ctk.CTkLabel(
            connection,
            text='No Discord Developer Portal setup, OAuth login or user token is required.',
            text_color=('gray35', 'gray68'),
        ).pack(anchor='w', padx=20, pady=(4, 16))

        runtime = self._section(page, 'Runtime')
        row = ctk.CTkFrame(runtime, fg_color='transparent')
        row.pack(fill='x', padx=15, pady=(6, 10))
        ctk.CTkLabel(row, text='Update interval (seconds)').pack(side='left', padx=5)
        self.update_interval = tk.StringVar(value=str(self.config.get('update_interval_secs', 2)))
        ctk.CTkEntry(row, textvariable=self.update_interval, width=120).pack(side='left', padx=12)
        self.external_icons = ctk.BooleanVar(value=bool(self.config.get('images.use_external_app_icons', True)))
        ctk.CTkSwitch(runtime, text='Allow external app/game artwork URLs', variable=self.external_icons).pack(
            anchor='w', padx=20, pady=(4, 16)
        )

        buttons = self._section(
            page,
            'Custom buttons',
            'Optional global Rich Presence buttons. Most users should leave these empty.',
        )
        configured_buttons = self.config.get('discord.buttons', []) or []
        self.button_fields = []
        for index in range(2):
            current = configured_buttons[index] if index < len(configured_buttons) else {}
            row = ctk.CTkFrame(buttons, fg_color='transparent')
            row.pack(fill='x', padx=15, pady=5)
            label_var = tk.StringVar(value=str(current.get('label', '')))
            url_var = tk.StringVar(value=str(current.get('url', '')))
            ctk.CTkEntry(row, textvariable=label_var, placeholder_text='Button label', width=220).pack(
                side='left', padx=5
            )
            ctk.CTkEntry(row, textvariable=url_var, placeholder_text='https://…', width=480).pack(
                side='left', padx=5, fill='x', expand=True
            )
            self.button_fields.append((label_var, url_var))
        ctk.CTkLabel(buttons, text='').pack(pady=3)

        windows = self._section(page, 'Startup')
        self.autostart = ctk.BooleanVar(value=self._registry_autostart_enabled())
        if _WINREG_AVAILABLE:
            ctk.CTkSwitch(windows, text='Start with Windows', variable=self.autostart).pack(
                anchor='w', padx=20, pady=(8, 16)
            )
        else:
            ctk.CTkLabel(
                windows,
                text='Windows startup registration is available in the Windows build.',
                text_color=('gray35', 'gray68'),
            ).pack(anchor='w', padx=20, pady=(8, 16))

        actions = ctk.CTkFrame(page, fg_color='transparent')
        actions.pack(fill='x', padx=32, pady=(8, 24))
        ctk.CTkButton(actions, text='Save changes', command=self.save_settings).pack(side='left', padx=(0, 8))
        ctk.CTkButton(
            actions,
            text='Reset defaults',
            fg_color=('gray65', 'gray30'),
            command=self.reset_settings,
        ).pack(side='left', padx=8)

    # ------------------------------------------------------------- diagnostics
    def _build_diagnostics(self):
        page = self._page(
            'diagnostics',
            'Diagnostics',
            'Run local checks before reporting a problem. No account credentials or browser history are uploaded.',
        )
        box = self._section(page, 'System checks')
        self.diag_labels = {}
        for key, title in (
            ('config', 'Configuration'),
            ('discord', 'Discord RPC'),
            ('browser', 'Browser Companion'),
            ('cs2', 'CS2 GSI'),
            ('games', 'Game catalogs'),
        ):
            row = ctk.CTkFrame(box, fg_color='transparent')
            row.pack(fill='x', padx=15, pady=5)
            ctk.CTkLabel(row, text=title, width=180, anchor='w').pack(side='left', padx=5)
            label = ctk.CTkLabel(row, text='Not checked', text_color='gray', anchor='w')
            label.pack(side='left', padx=8, fill='x', expand=True)
            self.diag_labels[key] = label
        ctk.CTkLabel(box, text='').pack(pady=3)

        actions = ctk.CTkFrame(page, fg_color='transparent')
        actions.pack(fill='x', padx=32, pady=8)
        ctk.CTkButton(actions, text='Run diagnostics', command=self.run_diagnostics).pack(side='left', padx=(0, 8))
        ctk.CTkButton(actions, text='Open logs', command=self.open_logs).pack(side='left', padx=8)
        ctk.CTkButton(actions, text='Open config', command=self.open_config).pack(side='left', padx=8)

        note = self._section(page, 'Known Discord limitation')
        ctk.CTkLabel(
            note,
            text=(
                'The current pypresence/legacy RPC transport can show the registered Discord Application name '
                '“CybrexTech” at the top of the card. Game/app details, artwork and state are still dynamic. '
                'A future Social SDK transport is required for a truly dynamic top-level application name.'
            ),
            justify='left',
            wraplength=820,
            text_color=('gray35', 'gray68'),
        ).pack(anchor='w', padx=20, pady=(8, 18))

    # ------------------------------------------------------------------- about
    def _build_about(self):
        page = self._page(
            'about',
            'About',
            'Local-first Discord Rich Presence for Windows and Linux.',
        )
        box = self._section(page, self.BRAND)
        ctk.CTkLabel(
            box,
            text=(
                'Browser, coding, terminal, media and game detection with local privacy controls.\n'
                'Steam/Epic/Heroic game catalogs and optional Counter-Strike 2 GSI are resolved locally.'
            ),
            justify='left',
            wraplength=820,
        ).pack(anchor='w', padx=20, pady=(8, 12))
        link = ctk.CTkLabel(box, text='github.com/imedkablavi/discord-rich-presence', text_color='#3b8ed0', cursor='hand2')
        link.pack(anchor='w', padx=20, pady=(0, 18))
        link.bind('<Button-1>', lambda _: webbrowser.open('https://github.com/imedkablavi/discord-rich-presence'))

    # -------------------------------------------------------------- navigation
    def select_page(self, name: str):
        for page_name, page in self.pages.items():
            if page_name == name:
                page.grid(row=0, column=1, sticky='nsew')
            else:
                page.grid_forget()
        for button_name, button in self.nav.items():
            button.configure(
                fg_color=('gray78', 'gray25') if button_name == name else 'transparent'
            )

    # --------------------------------------------------------------- settings
    def save_settings(self):
        snapshot = copy.deepcopy(self.config.data)
        try:
            self.config.set('privacy.mode', self.privacy_mode.get())
            self.config.set('privacy.browser_url_mode', self.browser_url_mode.get())
            self.config.set('privacy.hide_home_paths', self.hide_home.get())
            self.config.set('rules.clear_on_lock_screen', self.clear_on_lock.get())
            self.config.set('update_interval_secs', float(self.update_interval.get()))
            self.config.set('rules.activity_priority.policy', self.priority_policy.get())
            self.config.set('browser_companion.enabled', self.browser_enabled.get())
            self.config.set('browser_companion.port', int(self.browser_port.get()))
            self.config.set('cs2_gsi.enabled', self.cs2_enabled.get())
            self.config.set('cs2_gsi.auto_install', self.cs2_auto_install.get())
            self.config.set('images.use_external_app_icons', self.external_icons.get())
            self.config.set(
                'rules.enabled_detectors',
                {key: var.get() for key, var in self.detector_vars.items()},
            )

            buttons = []
            for label_var, url_var in self.button_fields:
                label = label_var.get().strip()
                url = url_var.get().strip()
                if label or url:
                    buttons.append({'label': label, 'url': url})
            self.config.set('discord.buttons', buttons)
            self.config.save()
            if _WINREG_AVAILABLE:
                self._set_registry_autostart(self.autostart.get())
            messagebox.showinfo('Saved', 'Settings saved. The running service will hot-reload them.')
        except Exception as exc:
            self.config.data = snapshot
            messagebox.showerror('Validation error', str(exc))

    def reset_settings(self):
        if not messagebox.askyesno('Reset settings', 'Reset all settings to defaults?'):
            return
        snapshot = copy.deepcopy(self.config.data)
        self.config.data = copy.deepcopy(DEFAULT_CONFIG)
        try:
            self.config.save()
            messagebox.showinfo(
                'Reset complete',
                'Defaults restored. Reopen the control panel to refresh every control.',
            )
        except Exception as exc:
            self.config.data = snapshot
            messagebox.showerror('Reset error', str(exc))

    # ----------------------------------------------------------- service state
    def start_service(self):
        active = self.runtime.read_active()
        if active:
            messagebox.showinfo('Service', f"Service is already running (PID {active.get('pid', '?')}).")
            return
        try:
            if getattr(sys, 'frozen', False):
                command = [sys.executable, '--tray']
                cwd = str(Path(sys.executable).resolve().parent)
            else:
                script = Path(__file__).with_name('main.py')
                python = sys.executable
                if sys.platform == 'win32' and python.lower().endswith('python.exe'):
                    pythonw = python[:-10] + 'pythonw.exe'
                    if os.path.exists(pythonw):
                        python = pythonw
                command = [python, str(script)]
                cwd = str(script.parent)
            self.service_process = subprocess.Popen(command, cwd=cwd)
        except Exception as exc:
            messagebox.showerror('Start error', str(exc))

    def stop_service(self):
        active = self.runtime.read_active()
        if not active:
            messagebox.showinfo('Service', 'No running service instance was found.')
            return
        if not self.runtime.terminate_active(timeout=5):
            messagebox.showerror('Stop error', 'The service could not be stopped. Open Diagnostics or Logs for details.')
        self.service_process = None

    def _poll_service(self):
        try:
            active = self.runtime.read_active()
            if not active:
                self.status_label.configure(text='● Service stopped', text_color='gray')
                self.rpc_value.configure(text='Disconnected', text_color='gray')
                self.activity_label.configure(text='No activity is being published.')
                self.heartbeat_label.configure(text='Heartbeat: —')
                self.state_label.configure(text='State: stopped')
                self.error_label.configure(text='Last error: none')
                self.start_button.configure(state='normal')
                self.stop_button.configure(state='disabled')
            else:
                state = str(active.get('state') or 'running')
                pid = active.get('pid', '?')
                connected = bool(active.get('connected', False))
                presence_active = bool(active.get('presence_active', False))
                activity = active.get('activity') or ('No publishable activity' if not presence_active else 'Active')
                updated = float(active.get('updated_at') or 0)
                age = max(0.0, time.time() - updated) if updated else 0.0
                stale = bool(updated and age > max(15.0, float(self.config.get('update_interval_secs', 2)) * 3))

                if stale:
                    self.status_label.configure(text=f'● Heartbeat stale · PID {pid}', text_color='#f39c12')
                elif state in {'rpc_error', 'loop_error', 'configuration_error'}:
                    self.status_label.configure(text=f'● Running with an error · PID {pid}', text_color='#e74c3c')
                else:
                    self.status_label.configure(text=f'● Service running · PID {pid}', text_color='#2ecc71')

                if state == 'dry_run':
                    self.rpc_value.configure(text='Dry-run mode', text_color='#f39c12')
                elif connected:
                    self.rpc_value.configure(text='Connected', text_color='#2ecc71')
                else:
                    self.rpc_value.configure(text='Disconnected', text_color='#e74c3c')

                self.activity_label.configure(text=str(activity))
                self.heartbeat_label.configure(text=f'Heartbeat: {age:.1f}s ago')
                self.state_label.configure(text=f'State: {state}')
                last_error = str(active.get('last_error') or '').strip()
                self.error_label.configure(text=f'Last error: {last_error[:220] if last_error else "none"}')
                self.start_button.configure(state='disabled')
                self.stop_button.configure(state='normal')
        finally:
            self.after(1000, self._poll_service)

    # --------------------------------------------------------------- probes
    @staticmethod
    def _probe_json(url: str, timeout: float = 1.25) -> tuple[bool, dict | None, str]:
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            return False, None, str(exc)
        if (
            parsed.scheme != 'http'
            or parsed.hostname != '127.0.0.1'
            or parsed.username is not None
            or parsed.password is not None
            or port is None
            or not 1024 <= port <= 65535
            or parsed.path not in {'/v1/health', '/v1/status'}
            or parsed.query
            or parsed.fragment
        ):
            return False, None, 'probe URL is outside the CYBREX loopback allowlist'
        request = urllib.request.Request(url, headers={'User-Agent': 'CYBREX-Rich-Presence-Control-Panel'})
        try:
            # URL components are constrained above to fixed IPv4 loopback and
            # the two read-only health paths.
            with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
                if response.status != 200:
                    return False, None, f'HTTP {response.status}'
                raw = response.read(64 * 1024)
            data = json.loads(raw.decode('utf-8'))
            return isinstance(data, dict) and bool(data.get('ok', False)), data, ''
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return False, None, str(exc)

    def _poll_integrations(self):
        if self._integration_probe_busy:
            self.after(4000, self._poll_integrations)
            return
        self._integration_probe_busy = True

        def worker():
            browser_port = self._safe_port(self.config.get('browser_companion.port', 32191), 32191)
            cs2_port = self._safe_port(self.config.get('cs2_gsi.port', 32192), 32192)
            browser_ok, _, _ = self._probe_json(f'http://127.0.0.1:{browser_port}/v1/health', 0.6)
            cs2_ok, cs2_data, _ = self._probe_json(f'http://127.0.0.1:{cs2_port}/v1/status', 0.6)

            def apply():
                self.browser_value.configure(
                    text='Connected' if browser_ok else 'Not connected',
                    text_color='#2ecc71' if browser_ok else 'gray',
                )
                self.browser_status_label.configure(
                    text='Status: connected' if browser_ok else 'Status: not connected',
                    text_color='#2ecc71' if browser_ok else 'gray',
                )
                if cs2_ok:
                    connected = bool((cs2_data or {}).get('connected', False))
                    label = 'Match data active' if connected else 'Listener ready'
                    color = '#2ecc71' if connected else '#3b8ed0'
                else:
                    label = 'Not connected'
                    color = 'gray'
                self.cs2_value.configure(text=label, text_color=color)
                self.cs2_status_label.configure(text=f'Status: {label.lower()}', text_color=color)
                self._integration_probe_busy = False

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()
        self.after(4000, self._poll_integrations)

    @staticmethod
    def _safe_port(value, default: int) -> int:
        try:
            port = int(value)
        except (TypeError, ValueError):
            return default
        return port if 1024 <= port <= 65535 else default

    # ------------------------------------------------------------- diagnostics
    def test_rpc(self):
        application_id = resolve_discord_application_id(self.config)

        def worker():
            try:
                from pypresence import Presence
                rpc = Presence(application_id)
                rpc.connect()
                rpc.close()
                self.after(0, lambda: messagebox.showinfo('Discord RPC', 'Connection succeeded.'))
            except Exception as exc:
                message = str(exc)
                self.after(0, lambda: messagebox.showerror('Discord RPC', f'Connection failed: {message}'))

        threading.Thread(target=worker, daemon=True).start()

    def test_browser_companion(self):
        port = self._safe_port(self.browser_port.get(), 32191)

        def worker():
            ok, data, error = self._probe_json(f'http://127.0.0.1:{port}/v1/status')
            if ok:
                records = int((data or {}).get('records', 0) or 0)
                text = f'Browser Companion is reachable on 127.0.0.1:{port}.\nActive records: {records}'
                self.after(0, lambda: messagebox.showinfo('Browser Companion', text))
            else:
                self.after(0, lambda: messagebox.showerror('Browser Companion', f'Bridge unavailable: {error or "not running"}'))

        threading.Thread(target=worker, daemon=True).start()

    def run_diagnostics(self):
        for label in self.diag_labels.values():
            label.configure(text='Checking…', text_color='#f39c12')

        def worker():
            results: dict[str, tuple[str, str]] = {}
            try:
                Config._validate(copy.deepcopy(self.config.data))
                results['config'] = ('Valid', '#2ecc71')
            except Exception as exc:
                results['config'] = (f'Invalid: {str(exc)[:140]}', '#e74c3c')

            try:
                from pypresence import Presence
                rpc = Presence(resolve_discord_application_id(self.config))
                rpc.connect()
                rpc.close()
                results['discord'] = ('Connected', '#2ecc71')
            except Exception as exc:
                results['discord'] = (f'Unavailable: {str(exc)[:120]}', '#e74c3c')

            browser_port = self._safe_port(self.config.get('browser_companion.port', 32191), 32191)
            ok, data, error = self._probe_json(f'http://127.0.0.1:{browser_port}/v1/status')
            if ok:
                results['browser'] = (f"Reachable · records={int((data or {}).get('records', 0) or 0)}", '#2ecc71')
            else:
                results['browser'] = (f'Not running: {error or "unreachable"}', 'gray')

            cs2_port = self._safe_port(self.config.get('cs2_gsi.port', 32192), 32192)
            ok, data, error = self._probe_json(f'http://127.0.0.1:{cs2_port}/v1/status')
            if ok:
                match = bool((data or {}).get('connected', False))
                results['cs2'] = ('Listener ready · match data active' if match else 'Listener ready', '#2ecc71')
            else:
                results['cs2'] = (f'Not running: {error or "unreachable"}', 'gray')

            game_parts = []
            try:
                from steam_catalog import SteamGameCatalog
                steam = SteamGameCatalog()
                game_parts.append(f'Steam {len(getattr(steam, "_games", {}))}')
            except Exception:
                game_parts.append('Steam unavailable')
            try:
                from epic_catalog import EpicGameCatalog
                epic = EpicGameCatalog()
                game_parts.append(f'Epic {len(getattr(epic, "_games", []))}')
            except Exception:
                game_parts.append('Epic unavailable')
            try:
                from heroic_catalog import HeroicGameCatalog
                heroic = HeroicGameCatalog()
                game_parts.append(f'Heroic {len(getattr(heroic, "_games", []))}')
            except Exception:
                game_parts.append('Heroic unavailable')
            results['games'] = (' · '.join(game_parts), '#3b8ed0')

            def apply():
                for key, (text, color) in results.items():
                    self.diag_labels[key].configure(text=text, text_color=color)
                self.select_page('diagnostics')

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def install_cs2_gsi(self):
        def worker():
            try:
                if getattr(sys, 'frozen', False):
                    command = [sys.executable, '--install-cs2-gsi']
                    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
                else:
                    script = Path(__file__).resolve().parent / 'scripts' / 'install-cs2-gsi.py'
                    completed = subprocess.run(
                        [sys.executable, str(script)],
                        cwd=str(script.parent.parent),
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                output = (completed.stdout or completed.stderr or '').strip()
                if completed.returncode == 0:
                    message = output or 'Counter-Strike 2 GSI installed successfully.'
                    self.after(0, lambda: messagebox.showinfo('CS2 GSI', message))
                else:
                    message = output or f'Installer exited with code {completed.returncode}'
                    self.after(0, lambda: messagebox.showerror('CS2 GSI', message))
            except Exception as exc:
                message = str(exc)
                self.after(0, lambda: messagebox.showerror('CS2 GSI', message))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------- open helpers
    @staticmethod
    def _open_path(path: Path):
        path = path.expanduser()
        try:
            if sys.platform == 'win32':
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(path)])
            else:
                subprocess.Popen(['xdg-open', str(path)])
        except Exception as exc:
            messagebox.showerror('Open path', str(exc))

    def open_logs(self):
        if sys.platform == 'win32':
            base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
            path = Path(base) / 'discord-rich-presence' / 'logs'
        else:
            path = Path.home() / '.local' / 'state' / 'discord-rich-presence'
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    def open_config(self):
        path = Path(self.config.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            try:
                self.config.save()
            except Exception as exc:
                messagebox.showerror('Config', str(exc))
                return
        self._open_path(path)

    # ----------------------------------------------------------- Windows startup
    def _registry_autostart_enabled(self) -> bool:
        if not _WINREG_AVAILABLE:
            return False
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run',
                0,
                winreg.KEY_READ,
            ) as key:
                winreg.QueryValueEx(key, 'DiscordRichPresence')
                return True
        except OSError:
            return False

    def _set_registry_autostart(self, enabled: bool):
        if not _WINREG_AVAILABLE:
            return
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                root = Path(__file__).resolve().parent
                if getattr(sys, 'frozen', False):
                    command = f'"{sys.executable}" --tray'
                else:
                    python = sys.executable
                    if python.lower().endswith('python.exe'):
                        candidate = python[:-10] + 'pythonw.exe'
                        if os.path.exists(candidate):
                            python = candidate
                    command = f'"{python}" "{root / "main.py"}" --tray'
                winreg.SetValueEx(key, 'DiscordRichPresence', 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, 'DiscordRichPresence')
                except FileNotFoundError:
                    pass


if __name__ == '__main__':
    app = ModernControlPanel(Config())
    app.mainloop()
