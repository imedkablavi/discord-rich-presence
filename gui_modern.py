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
        self.title(f'Discord Rich Presence Manager · {__version__}')
        self.geometry('1080x760')
        self.minsize(900, 640)
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_pages()
        self.select_page('dashboard')
        self.after(500, self._poll_service)

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.grid_rowconfigure(7, weight=1)
        ctk.CTkLabel(
            sidebar,
            text='DRP Manager',
            font=ctk.CTkFont(size=23, weight='bold'),
        ).grid(row=0, column=0, padx=20, pady=(30, 4))
        ctk.CTkLabel(
            sidebar,
            text=f'v{__version__}',
            text_color='gray',
        ).grid(row=1, column=0, padx=20, pady=(0, 18))

        self.nav = {}
        for row, (name, label) in enumerate((
            ('dashboard', 'Dashboard'),
            ('activity', 'Activity'),
            ('privacy', 'Privacy'),
            ('settings', 'Settings'),
            ('about', 'About'),
        ), start=2):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                anchor='w',
                corner_radius=0,
                fg_color='transparent',
                command=lambda n=name: self.select_page(n),
            )
            button.grid(row=row, column=0, sticky='ew', padx=0, pady=2)
            self.nav[name] = button

        self.theme_menu = ctk.CTkOptionMenu(
            sidebar,
            values=['System', 'Light', 'Dark'],
            command=ctk.set_appearance_mode,
        )
        self.theme_menu.grid(row=8, column=0, padx=20, pady=10)
        ctk.CTkButton(sidebar, text='Save Changes', command=self.save_settings).grid(
            row=9, column=0, padx=20, pady=(10, 25)
        )

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
            font=ctk.CTkFont(size=28, weight='bold'),
        ).pack(anchor='w', padx=30, pady=(25, 4))
        if subtitle:
            ctk.CTkLabel(
                page,
                text=subtitle,
                text_color='gray',
                justify='left',
                wraplength=780,
            ).pack(anchor='w', padx=30, pady=(0, 12))
        return page

    def _build_dashboard(self):
        page = self._page(
            'dashboard',
            'Service Dashboard',
            'Live service health, Discord connection, and trusted foreground-detection capability.',
        )
        card = ctk.CTkFrame(page)
        card.pack(fill='x', padx=30, pady=10)
        self.status_label = ctk.CTkLabel(
            card,
            text='● Service stopped',
            font=ctk.CTkFont(size=16, weight='bold'),
        )
        self.status_label.pack(anchor='w', padx=20, pady=(20, 5))
        self.rpc_label = ctk.CTkLabel(card, text='Discord RPC: —', justify='left', wraplength=800)
        self.rpc_label.pack(anchor='w', padx=20, pady=3)
        self.activity_label = ctk.CTkLabel(
            card,
            text='Activity: —',
            justify='left',
            wraplength=800,
        )
        self.activity_label.pack(anchor='w', padx=20, pady=3)
        self.capability_label = ctk.CTkLabel(
            card,
            text=self._capability_text(self.window_capability),
            justify='left',
            wraplength=800,
            text_color='gray',
        )
        self.capability_label.pack(anchor='w', padx=20, pady=3)
        self.heartbeat_label = ctk.CTkLabel(card, text='Heartbeat: —', text_color='gray')
        self.heartbeat_label.pack(anchor='w', padx=20, pady=(3, 15))

        controls = ctk.CTkFrame(card, fg_color='transparent')
        controls.pack(fill='x', padx=15, pady=(0, 20))
        self.start_button = ctk.CTkButton(controls, text='Start Service', command=self.start_service)
        self.start_button.pack(side='left', padx=5)
        self.stop_button = ctk.CTkButton(controls, text='Stop Service', command=self.stop_service)
        self.stop_button.pack(side='left', padx=5)
        ctk.CTkButton(controls, text='Test Discord RPC', command=self.test_rpc).pack(side='left', padx=5)
        ctk.CTkButton(controls, text='Check Update', command=self.check_update).pack(side='left', padx=5)
        ctk.CTkButton(controls, text='Open Logs', command=self.open_logs).pack(side='left', padx=5)

        update_card = ctk.CTkFrame(page)
        update_card.pack(fill='x', padx=30, pady=10)
        ctk.CTkLabel(
            update_card,
            text='Release & Update Status',
            font=ctk.CTkFont(size=16, weight='bold'),
        ).pack(anchor='w', padx=20, pady=(16, 4))
        self.update_status_label = ctk.CTkLabel(
            update_card,
            text=self._initial_update_text(),
            justify='left',
            wraplength=800,
            text_color='gray',
        )
        self.update_status_label.pack(anchor='w', padx=20, pady=(2, 16))

    def _build_activity(self):
        page = self._page(
            'activity',
            'Activity Detectors',
            'Unknown applications are never inferred from background process lists on unsupported Wayland sessions.',
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
        box = ctk.CTkFrame(page)
        box.pack(fill='x', padx=30, pady=10)
        for key, label in labels.items():
            var = ctk.BooleanVar(value=bool(enabled.get(key, True)))
            self.detector_vars[key] = var
            ctk.CTkCheckBox(box, text=label, variable=var).pack(anchor='w', padx=20, pady=10)
        ctk.CTkLabel(
            box,
            text='Disable “Other applications” to publish only recognized activity types.',
            text_color='gray',
        ).pack(anchor='w', padx=20, pady=(5, 15))

    def _build_privacy(self):
        page = self._page(
            'privacy',
            'Privacy & Security',
            'Browser companion data stays local. Private/incognito payloads are stripped before detection.',
        )
        box = ctk.CTkFrame(page)
        box.pack(fill='x', padx=30, pady=10)
        self.privacy_mode = tk.StringVar(value=str(self.config.get('privacy.mode', 'balanced')))
        descriptions = (
            ('off', 'Off — no activity redaction'),
            ('balanced', 'Balanced — redact secrets and reduce path exposure'),
            ('strict', 'Strict — generic activity only, no browser URLs/buttons'),
        )
        for value, label in descriptions:
            ctk.CTkRadioButton(box, text=label, variable=self.privacy_mode, value=value).pack(
                anchor='w', padx=20, pady=10
            )
        self.hide_home = ctk.BooleanVar(value=bool(self.config.get('privacy.hide_home_paths', True)))
        ctk.CTkSwitch(
            box,
            text='Redact home directory in Balanced mode',
            variable=self.hide_home,
        ).pack(anchor='w', padx=20, pady=(15, 8))
        self.clear_on_lock = ctk.BooleanVar(
            value=bool(self.config.get('rules.clear_on_lock_screen', True))
        )
        ctk.CTkSwitch(
            box,
            text='Clear Rich Presence when a lock screen is detected',
            variable=self.clear_on_lock,
        ).pack(anchor='w', padx=20, pady=(8, 20))

        companion = ctk.CTkFrame(page)
        companion.pack(fill='x', padx=30, pady=10)
        ctk.CTkLabel(
            companion,
            text='Browser Companion',
            font=ctk.CTkFont(size=16, weight='bold'),
        ).pack(anchor='w', padx=20, pady=(16, 5))
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
            text='Enable authenticated loopback companion (127.0.0.1 only)',
            variable=self.companion_enabled,
        ).pack(anchor='w', padx=20, pady=7)
        ctk.CTkSwitch(
            companion,
            text='Allow page titles',
            variable=self.companion_titles,
        ).pack(anchor='w', padx=20, pady=7)
        ctk.CTkSwitch(
            companion,
            text='Allow site origin (scheme + host)',
            variable=self.companion_origin,
        ).pack(anchor='w', padx=20, pady=7)
        ctk.CTkSwitch(
            companion,
            text='Allow exact URL path/query (explicit privacy opt-in)',
            variable=self.companion_exact_url,
        ).pack(anchor='w', padx=20, pady=7)
        ctk.CTkLabel(
            companion,
            text='Private/incognito tabs never expose title, service, or URL. URL fragments are always removed.',
            text_color='gray',
            justify='left',
            wraplength=800,
        ).pack(anchor='w', padx=20, pady=(4, 16))

    def _build_settings(self):
        page = self._page(
            'settings',
            'Application Settings',
            'Changes are validated transactionally before they are saved.',
        )
        box = ctk.CTkFrame(page)
        box.pack(fill='x', padx=30, pady=10)

        ctk.CTkLabel(box, text='Discord Client ID').pack(anchor='w', padx=20, pady=(20, 5))
        self.client_id = tk.StringVar(value=str(self.config.get('discord.client_id', '')))
        ctk.CTkEntry(box, textvariable=self.client_id, width=380).pack(
            anchor='w', padx=20, pady=(0, 15)
        )

        ctk.CTkLabel(box, text='Update interval (seconds)').pack(anchor='w', padx=20, pady=(5, 5))
        self.update_interval = tk.StringVar(value=str(self.config.get('update_interval_secs', 5)))
        ctk.CTkEntry(box, textvariable=self.update_interval, width=150).pack(
            anchor='w', padx=20, pady=(0, 15)
        )

        buttons = self.config.get('discord.buttons', []) or []
        self.button_fields = []
        ctk.CTkLabel(box, text='Custom Rich Presence buttons (up to 2)').pack(
            anchor='w', padx=20, pady=(10, 5)
        )
        for index in range(2):
            current = buttons[index] if index < len(buttons) else {}
            row = ctk.CTkFrame(box, fg_color='transparent')
            row.pack(fill='x', padx=15, pady=5)
            label_var = tk.StringVar(value=str(current.get('label', '')))
            url_var = tk.StringVar(value=str(current.get('url', '')))
            ctk.CTkEntry(row, textvariable=label_var, placeholder_text='Label', width=200).pack(
                side='left', padx=5
            )
            ctk.CTkEntry(row, textvariable=url_var, placeholder_text='https://...', width=470).pack(
                side='left', padx=5
            )
            self.button_fields.append((label_var, url_var))

        self.autostart = ctk.BooleanVar(value=startup_is_enabled())
        if sys.platform == 'win32' or sys.platform.startswith('linux'):
            ctk.CTkSwitch(
                box,
                text='Start with the desktop session',
                variable=self.autostart,
            ).pack(anchor='w', padx=20, pady=(15, 20))

        update_box = ctk.CTkFrame(page)
        update_box.pack(fill='x', padx=30, pady=10)
        ctk.CTkLabel(
            update_box,
            text='Signed Updates',
            font=ctk.CTkFont(size=16, weight='bold'),
        ).pack(anchor='w', padx=20, pady=(16, 5))
        self.updates_enabled = ctk.BooleanVar(value=bool(self.config.get('updates.enabled', False)))
        self.auto_install_updates = ctk.BooleanVar(
            value=bool(self.config.get('updates.auto_install', False))
        )
        ctk.CTkSwitch(
            update_box,
            text='Enable signed update checks',
            variable=self.updates_enabled,
        ).pack(anchor='w', padx=20, pady=7)
        ctk.CTkSwitch(
            update_box,
            text='Automatically stage verified portable updates at startup',
            variable=self.auto_install_updates,
        ).pack(anchor='w', padx=20, pady=7)
        ctk.CTkLabel(update_box, text='Manifest URL').pack(anchor='w', padx=20, pady=(8, 4))
        self.update_manifest_url = tk.StringVar(
            value=str(self.config.get('updates.manifest_url', ''))
        )
        ctk.CTkEntry(update_box, textvariable=self.update_manifest_url, width=720).pack(
            anchor='w', padx=20, pady=(0, 8)
        )
        ctk.CTkLabel(update_box, text='Ed25519 public key (base64)').pack(
            anchor='w', padx=20, pady=(8, 4)
        )
        self.update_public_key = tk.StringVar(
            value=str(self.config.get('updates.public_key', ''))
        )
        ctk.CTkEntry(update_box, textvariable=self.update_public_key, width=720).pack(
            anchor='w', padx=20, pady=(0, 8)
        )
        ctk.CTkLabel(
            update_box,
            text='The private signing key belongs only in the GitHub Actions secret. Source checkouts are never self-replaced.',
            text_color='gray',
            justify='left',
            wraplength=800,
        ).pack(anchor='w', padx=20, pady=(3, 16))

        ctk.CTkButton(page, text='Reset to Defaults', command=self.reset_settings).pack(
            anchor='w', padx=30, pady=25
        )

    def _build_about(self):
        page = self._page('about', 'About')
        ctk.CTkLabel(
            page,
            text=(
                f'Discord Rich Presence Service · {__version__}\n'
                'Local activity detection with configurable privacy controls.\n\n'
                'Wayland policy: use compositor-native trusted APIs when available; otherwise publish no foreground app.'
            ),
            justify='left',
            wraplength=800,
        ).pack(anchor='w', padx=30, pady=10)
        link = ctk.CTkLabel(page, text='GitHub repository', text_color='#3b8ed0', cursor='hand2')
        link.pack(anchor='w', padx=30, pady=10)
        link.bind(
            '<Button-1>',
            lambda _: webbrowser.open('https://github.com/imedkablavi/discord-rich-presence'),
        )

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
                'Saved',
                'Settings saved and validated. The running service will hot-reload the file.',
            )
        except Exception as e:
            self.config.data = snapshot
            messagebox.showerror('Validation Error', str(e))

    def reset_settings(self):
        if not messagebox.askyesno('Reset Settings', 'Reset all settings to defaults?'):
            return
        snapshot = copy.deepcopy(self.config.data)
        self.config.data = copy.deepcopy(DEFAULT_CONFIG)
        try:
            self.config.save()
            messagebox.showinfo(
                'Reset Complete',
                'Defaults restored. Reopen the panel to refresh all controls.',
            )
        except Exception as e:
            self.config.data = snapshot
            messagebox.showerror('Reset Error', str(e))

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
        except Exception as e:
            messagebox.showerror('Start Error', str(e))

    def stop_service(self):
        active = self.runtime.read_active()
        if not active:
            messagebox.showinfo('Service', 'No running service instance was found.')
            return
        if not self.runtime.terminate_active(timeout=5):
            messagebox.showerror(
                'Stop Error',
                'The service could not be stopped. Check permissions or the log file.',
            )
        self.service_process = None

    def _poll_service(self):
        active = self.runtime.read_active()
        if not active:
            self.status_label.configure(text='● Service stopped', text_color='gray')
            self.rpc_label.configure(text='Discord RPC: —')
            self.activity_label.configure(text='Activity: —')
            self.capability_label.configure(text=self._capability_text(self.window_capability))
            self.heartbeat_label.configure(text='Heartbeat: —')
            self.start_button.configure(state='normal')
            self.stop_button.configure(state='disabled')
        else:
            state = str(active.get('state') or 'running')
            pid = active.get('pid', '?')
            connected = bool(active.get('connected', False))
            presence_active = bool(active.get('presence_active', False))
            activity = active.get('activity') or (
                'No publishable activity' if not presence_active else 'Active'
            )
            updated = float(active.get('updated_at') or 0)
            age = max(0.0, time.time() - updated) if updated else 0.0
            stale = bool(
                updated
                and age > max(15.0, float(self.config.get('update_interval_secs', 5)) * 3)
            )

            if stale:
                self.status_label.configure(
                    text=f'● Service heartbeat stale (PID {pid})', text_color='#f39c12'
                )
            elif state in {'rpc_error', 'loop_error', 'configuration_error', 'update_error'}:
                self.status_label.configure(
                    text=f'● Service running with error (PID {pid})', text_color='#e74c3c'
                )
            else:
                self.status_label.configure(
                    text=f'● Service running (PID {pid})', text_color='#2ecc71'
                )

            if state == 'dry_run':
                rpc_text = 'Discord RPC: dry-run mode'
            else:
                rpc_text = 'Discord RPC: connected' if connected else 'Discord RPC: disconnected'
            last_error = str(active.get('last_error') or '').strip()
            if last_error:
                rpc_text += f' — {last_error[:150]}'
            self.rpc_label.configure(text=rpc_text)
            self.activity_label.configure(text=f'Activity: {activity}')
            capability = active.get('foreground_capability') or self.window_capability
            self.capability_label.configure(text=self._capability_text(capability))
            self.heartbeat_label.configure(text=f'Heartbeat: {age:.1f}s ago · state={state}')
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
                    lambda: messagebox.showinfo('Discord RPC', 'RPC connection succeeded.'),
                )
            except Exception as e:
                error_message = str(e)
                self.after(
                    0,
                    lambda msg=error_message: messagebox.showerror(
                        'Discord RPC', f'Connection failed: {msg}'
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
        self.update_status_label.configure(text='Checking signed update manifest…')

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
                        text=f'Update check failed closed: {value}'
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
            messagebox.showerror('Logs', str(e))

    def _initial_update_text(self) -> str:
        if not self.config.get('updates.enabled', False):
            return f'Current version: {__version__} · signed update checks disabled'
        if not self.config.get('updates.public_key', ''):
            return f'Current version: {__version__} · signing public key not configured'
        auto = 'auto-stage enabled' if self.config.get('updates.auto_install', False) else 'manual check'
        return f'Current version: {__version__} · signed updates enabled · {auto}'

    @staticmethod
    def _capability_text(capability) -> str:
        if not isinstance(capability, dict):
            return 'Foreground detection: unknown capability state'
        backend = str(capability.get('backend') or 'unavailable')
        session = str(capability.get('session') or 'unknown')
        if capability.get('supported'):
            return f'Foreground detection: {backend} · session={session}'
        reason = str(capability.get('reason') or 'No trusted foreground API available')
        return f'Foreground detection: unavailable · session={session} · {reason}'


if __name__ == '__main__':
    app = ModernControlPanel(Config())
    app.mainloop()
