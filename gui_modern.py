"""Modern configuration/control panel for Discord Rich Presence."""

import copy
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from config import Config, DEFAULT_CONFIG
from detectors.window import WindowDetector
from runtime_state import RuntimeState
from startup import is_enabled as startup_is_enabled
from startup import set_enabled as startup_set_enabled
from update_agent import check_for_update
from version import __version__


ctk.set_appearance_mode('System')
ctk.set_default_color_theme('blue')


class ModernControlPanel(ctk.CTk):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.runtime = RuntimeState()
        self.service_process: subprocess.Popen | None = None
        self.window_capability = WindowDetector().capability()
        self.title(f'Discord Rich Presence · {__version__}')
        self.geometry('1120x790')
        self.minsize(940, 660)
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_pages()
        self.select_page('dashboard')
        self.after(500, self._poll_service)

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=232, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.grid_rowconfigure(7, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            sidebar,
            text='Discord Presence',
            font=ctk.CTkFont(size=23, weight='bold'),
        ).grid(row=0, column=0, sticky='w', padx=22, pady=(30, 3))
        ctk.CTkLabel(
            sidebar,
            text=f'Local activity · v{__version__}',
            text_color='gray',
        ).grid(row=1, column=0, sticky='w', padx=22, pady=(0, 20))

        self.nav = {}
        for row, (name, label) in enumerate((
            ('dashboard', 'Overview'),
            ('activity', 'Activity'),
            ('privacy', 'Privacy'),
            ('settings', 'Preferences'),
            ('about', 'About'),
        ), start=2):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                anchor='w',
                height=40,
                corner_radius=8,
                fg_color='transparent',
                command=lambda n=name: self.select_page(n),
            )
            button.grid(row=row, column=0, sticky='ew', padx=12, pady=3)
            self.nav[name] = button

        ctk.CTkLabel(sidebar, text='Appearance', text_color='gray').grid(
            row=8, column=0, sticky='w', padx=22, pady=(8, 4)
        )
        self.theme_menu = ctk.CTkOptionMenu(
            sidebar,
            values=['System', 'Light', 'Dark'],
            command=ctk.set_appearance_mode,
            height=36,
        )
        self.theme_menu.grid(row=9, column=0, sticky='ew', padx=16, pady=(0, 8))
        ctk.CTkButton(
            sidebar,
            text='Save settings',
            height=40,
            command=self.save_settings,
        ).grid(row=10, column=0, sticky='ew', padx=16, pady=(8, 24))

    def _build_pages(self):
        self.pages = {}
        self._build_dashboard()
        self._build_activity()
        self._build_privacy()
        self._build_settings()
        self._build_about()

    def _page(self, name: str, title: str, subtitle: str = ''):
        page = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color='transparent')
        self.pages[name] = page
        ctk.CTkLabel(
            page,
            text=title,
            font=ctk.CTkFont(size=30, weight='bold'),
        ).pack(anchor='w', padx=34, pady=(28, 4))
        if subtitle:
            ctk.CTkLabel(
                page,
                text=subtitle,
                text_color='gray',
                justify='left',
                wraplength=800,
            ).pack(anchor='w', padx=34, pady=(0, 14))
        return page

    @staticmethod
    def _card(page, title: str, description: str = ''):
        card = ctk.CTkFrame(page)
        card.pack(fill='x', padx=34, pady=9)
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=17, weight='bold'),
        ).pack(anchor='w', padx=22, pady=(18, 3))
        if description:
            ctk.CTkLabel(
                card,
                text=description,
                text_color='gray',
                justify='left',
                wraplength=790,
            ).pack(anchor='w', padx=22, pady=(0, 10))
        return card

    @staticmethod
    def _field(parent, title: str, description: str = ''):
        ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=13, weight='bold'),
        ).pack(anchor='w', padx=22, pady=(10, 3))
        if description:
            ctk.CTkLabel(
                parent,
                text=description,
                text_color='gray',
                justify='left',
                wraplength=790,
            ).pack(anchor='w', padx=22, pady=(0, 5))

    def _build_dashboard(self):
        page = self._page(
            'dashboard',
            'Overview',
            'See what is running and what your Discord profile is showing.',
        )

        card = self._card(page, 'Service')
        self.status_label = ctk.CTkLabel(
            card,
            text='● Stopped',
            font=ctk.CTkFont(size=18, weight='bold'),
        )
        self.status_label.pack(anchor='w', padx=22, pady=(4, 7))
        self.rpc_label = ctk.CTkLabel(
            card,
            text='Discord: Not connected',
            justify='left',
            wraplength=790,
        )
        self.rpc_label.pack(anchor='w', padx=22, pady=3)
        self.activity_label = ctk.CTkLabel(
            card,
            text='Now showing: Nothing',
            justify='left',
            wraplength=790,
        )
        self.activity_label.pack(anchor='w', padx=22, pady=3)
        self.capability_label = ctk.CTkLabel(
            card,
            text=self._capability_text(self.window_capability),
            justify='left',
            wraplength=790,
            text_color='gray',
        )
        self.capability_label.pack(anchor='w', padx=22, pady=3)
        self.heartbeat_label = ctk.CTkLabel(
            card,
            text='Last update: —',
            text_color='gray',
        )
        self.heartbeat_label.pack(anchor='w', padx=22, pady=(3, 13))

        controls = ctk.CTkFrame(card, fg_color='transparent')
        controls.pack(fill='x', padx=17, pady=(0, 20))
        self.start_button = ctk.CTkButton(
            controls,
            text='Start',
            width=115,
            command=self.start_service,
        )
        self.start_button.pack(side='left', padx=5)
        self.stop_button = ctk.CTkButton(
            controls,
            text='Stop',
            width=115,
            command=self.stop_service,
        )
        self.stop_button.pack(side='left', padx=5)
        ctk.CTkButton(
            controls,
            text='Test Discord',
            width=130,
            command=self.test_rpc,
        ).pack(side='left', padx=5)
        ctk.CTkButton(
            controls,
            text='Open logs',
            width=120,
            command=self.open_logs,
        ).pack(side='left', padx=5)

        update_card = self._card(
            page,
            'Updates',
            'Update files are checked before they are used.',
        )
        self.update_status_label = ctk.CTkLabel(
            update_card,
            text=self._initial_update_text(),
            justify='left',
            wraplength=790,
            text_color='gray',
        )
        self.update_status_label.pack(anchor='w', padx=22, pady=(1, 10))
        ctk.CTkButton(
            update_card,
            text='Check for updates',
            width=155,
            command=self.check_update,
        ).pack(anchor='w', padx=22, pady=(0, 18))

    def _build_activity(self):
        page = self._page(
            'activity',
            'Activity',
            'Choose which activity types can appear on Discord.',
        )
        enabled = self.config.get('rules.enabled_detectors', {}) or {}
        self.detector_vars = {}
        labels = {
            'gaming': 'Games',
            'coding': 'Code editors',
            'browser': 'Browsers',
            'media': 'Media players',
            'terminal': 'Terminal',
            'application': 'Other apps',
        }

        box = self._card(
            page,
            'Detection',
            'Turn off anything you do not want shown on your profile.',
        )
        for key, label in labels.items():
            var = ctk.BooleanVar(value=bool(enabled.get(key, True)))
            self.detector_vars[key] = var
            ctk.CTkSwitch(
                box,
                text=label,
                variable=var,
            ).pack(anchor='w', padx=22, pady=8)
        ctk.CTkLabel(
            box,
            text=(
                'On Wayland, app detection only runs when your desktop provides a reliable '
                'active-window source. Background processes are not used as a guess.'
            ),
            text_color='gray',
            justify='left',
            wraplength=790,
        ).pack(anchor='w', padx=22, pady=(7, 18))

    def _build_privacy(self):
        page = self._page(
            'privacy',
            'Privacy',
            'Choose how much activity detail can be sent to Discord.',
        )

        box = self._card(
            page,
            'Activity details',
            'Balanced is a good default for everyday use.',
        )
        self.privacy_mode = tk.StringVar(value=str(self.config.get('privacy.mode', 'balanced')))
        descriptions = (
            ('off', 'Off — show detected details as-is'),
            ('balanced', 'Balanced — hide secrets and shorten personal paths'),
            ('strict', 'Strict — share only general activity, without browser links or buttons'),
        )
        for value, label in descriptions:
            ctk.CTkRadioButton(
                box,
                text=label,
                variable=self.privacy_mode,
                value=value,
            ).pack(anchor='w', padx=22, pady=9)

        self.hide_home = ctk.BooleanVar(value=bool(self.config.get('privacy.hide_home_paths', True)))
        ctk.CTkSwitch(
            box,
            text='Hide my home folder from activity details',
            variable=self.hide_home,
        ).pack(anchor='w', padx=22, pady=(15, 8))
        self.clear_on_lock = ctk.BooleanVar(
            value=bool(self.config.get('rules.clear_on_lock_screen', True))
        )
        ctk.CTkSwitch(
            box,
            text='Clear my Discord status when the screen locks',
            variable=self.clear_on_lock,
        ).pack(anchor='w', padx=22, pady=(8, 20))

        companion = self._card(
            page,
            'Browser details',
            'Optional browser details come from a small companion on this computer. '
            'They are not sent to a separate web service.',
        )
        self.companion_enabled = ctk.BooleanVar(
            value=bool(self.config.get('browser_companion.enabled', False))
        )
        self.companion_titles = ctk.BooleanVar(
            value=bool(self.config.get('browser_companion.allow_titles', True))
        )
        self.companion_origin = ctk.BooleanVar(
            value=bool(self.config.get('browser_companion.allow_origin', True))
        )
        self.companion_exact_url = ctk.BooleanVar(
            value=bool(self.config.get('browser_companion.allow_exact_url', False))
        )
        ctk.CTkSwitch(
            companion,
            text='Use browser companion',
            variable=self.companion_enabled,
        ).pack(anchor='w', padx=22, pady=8)
        ctk.CTkSwitch(
            companion,
            text='Share page title',
            variable=self.companion_titles,
        ).pack(anchor='w', padx=22, pady=8)
        ctk.CTkSwitch(
            companion,
            text='Share website address',
            variable=self.companion_origin,
        ).pack(anchor='w', padx=22, pady=8)
        ctk.CTkSwitch(
            companion,
            text='Share full page path and query',
            variable=self.companion_exact_url,
        ).pack(anchor='w', padx=22, pady=8)
        ctk.CTkLabel(
            companion,
            text=(
                'Private and incognito tabs are always hidden. Full URLs can contain private '
                'information, so that option stays off by default.'
            ),
            text_color='gray',
            justify='left',
            wraplength=790,
        ).pack(anchor='w', padx=22, pady=(7, 18))

    def _build_settings(self):
        page = self._page(
            'settings',
            'Preferences',
            'General Discord, startup, and update settings.',
        )

        discord_box = self._card(
            page,
            'Discord',
            'Connection settings used by the background service.',
        )
        self._field(
            discord_box,
            'Client ID',
            'The numeric application ID from the Discord Developer Portal.',
        )
        self.client_id = tk.StringVar(value=str(self.config.get('discord.client_id', '')))
        ctk.CTkEntry(
            discord_box,
            textvariable=self.client_id,
            width=390,
            placeholder_text='Discord application ID',
        ).pack(anchor='w', padx=22, pady=(0, 10))

        self._field(
            discord_box,
            'Refresh every',
            'How often the service checks for a new activity.',
        )
        interval_row = ctk.CTkFrame(discord_box, fg_color='transparent')
        interval_row.pack(fill='x', padx=17, pady=(0, 18))
        self.update_interval = tk.StringVar(value=str(self.config.get('update_interval_secs', 5)))
        ctk.CTkEntry(
            interval_row,
            textvariable=self.update_interval,
            width=100,
        ).pack(side='left', padx=5)
        ctk.CTkLabel(interval_row, text='seconds', text_color='gray').pack(side='left', padx=4)

        buttons_box = self._card(
            page,
            'Profile buttons',
            'Optional links shown with your Rich Presence. Discord allows up to two.',
        )
        buttons = self.config.get('discord.buttons', []) or []
        self.button_fields = []
        for index in range(2):
            current = buttons[index] if index < len(buttons) else {}
            row = ctk.CTkFrame(buttons_box, fg_color='transparent')
            row.pack(fill='x', padx=17, pady=(5, 6))
            label_var = tk.StringVar(value=str(current.get('label', '')))
            url_var = tk.StringVar(value=str(current.get('url', '')))
            ctk.CTkEntry(
                row,
                textvariable=label_var,
                placeholder_text=f'Button {index + 1} text',
                width=220,
            ).pack(side='left', padx=5)
            ctk.CTkEntry(
                row,
                textvariable=url_var,
                placeholder_text='https://example.com',
                width=480,
            ).pack(side='left', padx=5)
            self.button_fields.append((label_var, url_var))
        ctk.CTkLabel(
            buttons_box,
            text='Leave a row empty if you do not need that button.',
            text_color='gray',
        ).pack(anchor='w', padx=22, pady=(5, 18))

        behavior_box = self._card(page, 'App behavior')
        self.autostart = ctk.BooleanVar(value=startup_is_enabled())
        if sys.platform == 'win32' or sys.platform.startswith('linux'):
            ctk.CTkSwitch(
                behavior_box,
                text='Start automatically when I sign in',
                variable=self.autostart,
            ).pack(anchor='w', padx=22, pady=(8, 18))
        else:
            ctk.CTkLabel(
                behavior_box,
                text='Automatic startup is not available on this platform yet.',
                text_color='gray',
            ).pack(anchor='w', padx=22, pady=(8, 18))

        update_box = self._card(
            page,
            'Updates',
            'Verified updates are accepted only when their release signature and file checksum match.',
        )
        self.updates_enabled = ctk.BooleanVar(value=bool(self.config.get('updates.enabled', False)))
        self.auto_install_updates = ctk.BooleanVar(
            value=bool(self.config.get('updates.auto_install', False))
        )
        ctk.CTkSwitch(
            update_box,
            text='Check for verified updates',
            variable=self.updates_enabled,
        ).pack(anchor='w', padx=22, pady=8)
        ctk.CTkSwitch(
            update_box,
            text='Prepare verified portable updates when the app starts',
            variable=self.auto_install_updates,
        ).pack(anchor='w', padx=22, pady=8)

        self._field(
            update_box,
            'Advanced update source',
            'Change these only if you manage the release feed for this app.',
        )
        self.update_manifest_url = tk.StringVar(
            value=str(self.config.get('updates.manifest_url', ''))
        )
        ctk.CTkEntry(
            update_box,
            textvariable=self.update_manifest_url,
            width=735,
            placeholder_text='Signed manifest URL',
        ).pack(anchor='w', padx=22, pady=(0, 8))

        self.update_public_key = tk.StringVar(
            value=str(self.config.get('updates.public_key', ''))
        )
        ctk.CTkEntry(
            update_box,
            textvariable=self.update_public_key,
            width=735,
            placeholder_text='Release public key (base64)',
        ).pack(anchor='w', padx=22, pady=(0, 8))
        ctk.CTkLabel(
            update_box,
            text='Only the public key belongs here. The private release key must never be stored in the app.',
            text_color='gray',
            justify='left',
            wraplength=790,
        ).pack(anchor='w', padx=22, pady=(3, 18))

        reset_box = ctk.CTkFrame(page, fg_color='transparent')
        reset_box.pack(fill='x', padx=34, pady=(8, 28))
        ctk.CTkButton(
            reset_box,
            text='Restore defaults',
            fg_color='transparent',
            border_width=1,
            command=self.reset_settings,
        ).pack(anchor='w')

    def _build_about(self):
        page = self._page(
            'about',
            'About',
            'Version, project links, and platform behavior.',
        )
        info = self._card(page, f'Discord Rich Presence {__version__}')
        ctk.CTkLabel(
            info,
            text=(
                'Runs locally and sends only the activity details you choose to Discord.\n'
                'If the desktop cannot provide a reliable active window, app detection stays off instead of guessing.'
            ),
            justify='left',
            wraplength=790,
        ).pack(anchor='w', padx=22, pady=(5, 15))

        links = ctk.CTkFrame(info, fg_color='transparent')
        links.pack(fill='x', padx=17, pady=(0, 18))
        ctk.CTkButton(
            links,
            text='Open GitHub',
            width=130,
            command=lambda: webbrowser.open('https://github.com/imedkablavi/discord-rich-presence'),
        ).pack(side='left', padx=5)
        ctk.CTkButton(
            links,
            text='Release notes',
            width=130,
            command=lambda: webbrowser.open(
                'https://github.com/imedkablavi/discord-rich-presence/blob/main/CHANGELOG.md'
            ),
        ).pack(side='left', padx=5)

        platform_card = self._card(page, 'App detection on this computer')
        ctk.CTkLabel(
            platform_card,
            text=self._capability_text(self.window_capability),
            justify='left',
            wraplength=790,
        ).pack(anchor='w', padx=22, pady=(4, 18))

    def select_page(self, name: str):
        for page_name, page in self.pages.items():
            if page_name == name:
                page.grid(row=0, column=1, sticky='nsew')
            else:
                page.grid_forget()
        for button_name, button in self.nav.items():
            button.configure(
                fg_color=('gray75', 'gray25') if button_name == name else 'transparent'
            )

    def save_settings(self):
        snapshot = copy.deepcopy(self.config.data)
        try:
            self.config.set('discord.client_id', self.client_id.get().strip())
            self.config.set('privacy.mode', self.privacy_mode.get())
            self.config.set('privacy.hide_home_paths', self.hide_home.get())
            self.config.set('rules.clear_on_lock_screen', self.clear_on_lock.get())
            self.config.set('update_interval_secs', float(self.update_interval.get()))
            self.config.set(
                'rules.enabled_detectors',
                {key: var.get() for key, var in self.detector_vars.items()},
            )
            self.config.set('browser_companion.enabled', self.companion_enabled.get())
            self.config.set('browser_companion.allow_titles', self.companion_titles.get())
            self.config.set('browser_companion.allow_origin', self.companion_origin.get())
            self.config.set('browser_companion.allow_exact_url', self.companion_exact_url.get())
            self.config.set('updates.enabled', self.updates_enabled.get())
            self.config.set('updates.auto_install', self.auto_install_updates.get())
            self.config.set('updates.manifest_url', self.update_manifest_url.get().strip())
            self.config.set('updates.public_key', self.update_public_key.get().strip())
            self.config.set('system.auto_start', self.autostart.get())

            buttons = []
            for label_var, url_var in self.button_fields:
                label = label_var.get().strip()
                url = url_var.get().strip()
                if label or url:
                    buttons.append({'label': label, 'url': url})
            self.config.set('discord.buttons', buttons)
            self.config.save()
            if sys.platform == 'win32' or sys.platform.startswith('linux'):
                startup_set_enabled(self.autostart.get())
            self.update_status_label.configure(text=self._initial_update_text())
            messagebox.showinfo(
                'Settings saved',
                'Your changes are saved. The running service will pick them up automatically.',
            )
        except Exception as e:
            self.config.data = snapshot
            messagebox.showerror('Could not save settings', str(e))

    def reset_settings(self):
        if not messagebox.askyesno(
            'Restore defaults',
            'Restore the default settings? Your current preferences will be replaced.',
        ):
            return
        snapshot = copy.deepcopy(self.config.data)
        self.config.data = copy.deepcopy(DEFAULT_CONFIG)
        try:
            self.config.save()
            messagebox.showinfo(
                'Defaults restored',
                'Default settings are back. Reopen this window to refresh every control.',
            )
        except Exception as e:
            self.config.data = snapshot
            messagebox.showerror('Could not restore defaults', str(e))

    def start_service(self):
        active = self.runtime.read_active()
        if active:
            messagebox.showinfo('Already running', 'The service is already running.')
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
        except Exception as e:
            messagebox.showerror('Could not start', str(e))

    def stop_service(self):
        active = self.runtime.read_active()
        if not active:
            messagebox.showinfo('Already stopped', 'The service is not running.')
            return
        if not self.runtime.terminate_active(timeout=5):
            messagebox.showerror(
                'Could not stop',
                'The service did not stop. Check the logs or your permissions and try again.',
            )
        self.service_process = None

    def _poll_service(self):
        active = self.runtime.read_active()
        if not active:
            self.status_label.configure(text='● Stopped', text_color='gray')
            self.rpc_label.configure(text='Discord: Not connected')
            self.activity_label.configure(text='Now showing: Nothing')
            self.capability_label.configure(text=self._capability_text(self.window_capability))
            self.heartbeat_label.configure(text='Last update: —')
            self.start_button.configure(state='normal')
            self.stop_button.configure(state='disabled')
        else:
            state = str(active.get('state') or 'running')
            pid = active.get('pid', '?')
            connected = bool(active.get('connected', False))
            presence_active = bool(active.get('presence_active', False))
            activity = active.get('activity') or (
                'Nothing to show right now' if not presence_active else 'Active'
            )
            updated = float(active.get('updated_at') or 0)
            age = max(0.0, time.time() - updated) if updated else 0.0
            stale = bool(
                updated
                and age > max(15.0, float(self.config.get('update_interval_secs', 5)) * 3)
            )

            if stale:
                self.status_label.configure(
                    text='● Needs attention',
                    text_color='#f39c12',
                )
            elif state in {'rpc_error', 'loop_error', 'configuration_error', 'update_error'}:
                self.status_label.configure(
                    text='● Running with an error',
                    text_color='#e74c3c',
                )
            else:
                self.status_label.configure(
                    text='● Running',
                    text_color='#2ecc71',
                )

            if state == 'dry_run':
                rpc_text = 'Discord: Test mode'
            else:
                rpc_text = 'Discord: Connected' if connected else 'Discord: Disconnected'
            last_error = str(active.get('last_error') or '').strip()
            if last_error:
                rpc_text += f' — {last_error[:150]}'
            self.rpc_label.configure(text=rpc_text)
            self.activity_label.configure(text=f'Now showing: {activity}')
            capability = active.get('foreground_capability') or self.window_capability
            self.capability_label.configure(text=self._capability_text(capability))
            self.heartbeat_label.configure(
                text=f'Last update: {age:.1f}s ago · PID {pid}'
            )
            self.start_button.configure(state='disabled')
            self.stop_button.configure(state='normal')

        self.after(1000, self._poll_service)

    def test_rpc(self):
        client_id = self.client_id.get().strip()

        def worker():
            rpc = None
            try:
                from pypresence import Presence
                rpc = Presence(client_id)
                rpc.connect()
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        'Discord connection',
                        'Connection successful.',
                    ),
                )
            except Exception as e:
                error_message = str(e)
                self.after(
                    0,
                    lambda msg=error_message: messagebox.showerror(
                        'Discord connection',
                        f'Could not connect: {msg}',
                    ),
                )
            finally:
                if rpc:
                    try:
                        rpc.close()
                    except Exception:
                        pass

        threading.Thread(target=worker, daemon=True, name='rpc-test').start()

    def check_update(self):
        self.update_status_label.configure(text='Checking for updates…')

        def worker():
            try:
                status = check_for_update(self.config)
                text = status.message
                if status.available and status.asset:
                    text += f' · {status.asset.name}'
                self.after(0, lambda value=text: self.update_status_label.configure(text=value))
            except Exception as e:
                error = str(e)
                self.after(
                    0,
                    lambda value=error: self.update_status_label.configure(
                        text=f'Could not check for updates: {value}'
                    ),
                )

        threading.Thread(target=worker, daemon=True, name='update-check').start()

    def open_logs(self):
        if sys.platform == 'win32':
            base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
            path = Path(base) / 'discord-rich-presence' / 'logs'
        else:
            path = Path.home() / '.local' / 'state' / 'discord-rich-presence'
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == 'win32':
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(path)])
            else:
                subprocess.Popen(['xdg-open', str(path)])
        except Exception as e:
            messagebox.showerror('Could not open logs', str(e))

    def _initial_update_text(self) -> str:
        if not self.config.get('updates.enabled', False):
            return f'Version {__version__} · Update checks are off'
        if not self.config.get('updates.public_key', ''):
            return f'Version {__version__} · Release public key is not configured'
        mode = (
            'Prepare updates on startup'
            if self.config.get('updates.auto_install', False)
            else 'Manual updates'
        )
        return f'Version {__version__} · Verified updates on · {mode}'

    @staticmethod
    def _capability_text(capability) -> str:
        if not isinstance(capability, dict):
            return 'App detection: Status unavailable'

        backend = str(capability.get('backend') or 'unavailable')
        session = str(capability.get('session') or 'unknown')
        reason = str(capability.get('reason') or '')
        names = {
            'win32': 'Windows',
            'x11-xprop': 'X11',
            'kdotool': 'KDE Wayland',
            'swaymsg': 'Sway',
        }
        if capability.get('supported'):
            return f'App detection: {names.get(backend, backend)}'

        lower_reason = reason.lower()
        if 'gnome wayland' in lower_reason:
            return 'App detection: Not available on GNOME Wayland'
        if 'kdotool' in lower_reason:
            return 'App detection: Install kdotool to enable it on KDE Wayland'
        if 'swaymsg' in lower_reason:
            return 'App detection: Install swaymsg to enable it on Sway'
        if 'xprop' in lower_reason:
            return 'App detection: Install xprop (x11-utils) to enable it on X11'
        if session and session != 'unknown':
            return f'App detection: Not available on this {session} session'
        return 'App detection: Not available on this desktop'


if __name__ == '__main__':
    app = ModernControlPanel(Config())
    app.mainloop()
