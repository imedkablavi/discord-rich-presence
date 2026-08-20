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
from runtime_state import RuntimeState

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    _WINREG_AVAILABLE = False


ctk.set_appearance_mode('System')
ctk.set_default_color_theme('blue')


class ModernControlPanel(ctk.CTk):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.runtime = RuntimeState()
        self.service_process: subprocess.Popen | None = None
        self.title('Discord Rich Presence Manager')
        self.geometry('1000x720')
        self.minsize(850, 600)
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_pages()
        self.select_page('dashboard')
        self.after(500, self._poll_service)

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=210, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.grid_rowconfigure(7, weight=1)
        ctk.CTkLabel(sidebar, text='DRP Manager', font=ctk.CTkFont(size=23, weight='bold')).grid(row=0, column=0, padx=20, pady=(30, 20))

        self.nav = {}
        for row, (name, label) in enumerate((
            ('dashboard', 'Dashboard'), ('activity', 'Activity'),
            ('privacy', 'Privacy'), ('settings', 'Settings'), ('about', 'About')
        ), start=1):
            button = ctk.CTkButton(
                sidebar, text=label, anchor='w', corner_radius=0,
                fg_color='transparent', command=lambda n=name: self.select_page(n)
            )
            button.grid(row=row, column=0, sticky='ew', padx=0, pady=2)
            self.nav[name] = button

        self.theme_menu = ctk.CTkOptionMenu(
            sidebar, values=['System', 'Light', 'Dark'], command=ctk.set_appearance_mode
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

    def _page(self, name: str, title: str):
        page = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color='transparent')
        self.pages[name] = page
        ctk.CTkLabel(page, text=title, font=ctk.CTkFont(size=28, weight='bold')).pack(
            anchor='w', padx=30, pady=(25, 15)
        )
        return page

    def _build_dashboard(self):
        page = self._page('dashboard', 'Service Dashboard')
        card = ctk.CTkFrame(page)
        card.pack(fill='x', padx=30, pady=10)
        self.status_label = ctk.CTkLabel(
            card, text='● Service stopped', font=ctk.CTkFont(size=16, weight='bold')
        )
        self.status_label.pack(anchor='w', padx=20, pady=(20, 5))
        self.rpc_label = ctk.CTkLabel(card, text='Discord RPC: —')
        self.rpc_label.pack(anchor='w', padx=20, pady=3)
        self.activity_label = ctk.CTkLabel(card, text='Activity: —', justify='left', wraplength=780)
        self.activity_label.pack(anchor='w', padx=20, pady=3)
        self.heartbeat_label = ctk.CTkLabel(card, text='Heartbeat: —', text_color='gray')
        self.heartbeat_label.pack(anchor='w', padx=20, pady=(3, 15))

        controls = ctk.CTkFrame(card, fg_color='transparent')
        controls.pack(fill='x', padx=15, pady=(0, 20))
        self.start_button = ctk.CTkButton(controls, text='Start Service', command=self.start_service)
        self.start_button.pack(side='left', padx=5)
        self.stop_button = ctk.CTkButton(controls, text='Stop Service', command=self.stop_service)
        self.stop_button.pack(side='left', padx=5)
        ctk.CTkButton(controls, text='Test Discord RPC', command=self.test_rpc).pack(side='left', padx=5)
        ctk.CTkButton(controls, text='Open Logs', command=self.open_logs).pack(side='left', padx=5)

    def _build_activity(self):
        page = self._page('activity', 'Activity Detectors')
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
        page = self._page('privacy', 'Privacy & Security')
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
            box, text='Redact home directory in Balanced mode', variable=self.hide_home
        ).pack(anchor='w', padx=20, pady=(15, 8))
        self.clear_on_lock = ctk.BooleanVar(
            value=bool(self.config.get('rules.clear_on_lock_screen', True))
        )
        ctk.CTkSwitch(
            box,
            text='Clear Rich Presence when a lock screen is detected',
            variable=self.clear_on_lock,
        ).pack(anchor='w', padx=20, pady=(8, 20))

    def _build_settings(self):
        page = self._page('settings', 'Application Settings')
        box = ctk.CTkFrame(page)
        box.pack(fill='x', padx=30, pady=10)

        ctk.CTkLabel(
            box,
            text='Discord connection',
            font=ctk.CTkFont(size=16, weight='bold'),
        ).pack(anchor='w', padx=20, pady=(20, 5))
        ctk.CTkLabel(
            box,
            text='Automatic — uses the CYBREX application identity and the Discord Desktop account currently running on this computer.',
            text_color='gray',
            justify='left',
            wraplength=760,
        ).pack(anchor='w', padx=20, pady=(0, 15))

        ctk.CTkLabel(box, text='Update interval (seconds)').pack(anchor='w', padx=20, pady=(5, 5))
        self.update_interval = tk.StringVar(value=str(self.config.get('update_interval_secs', 2)))
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
            ctk.CTkEntry(row, textvariable=url_var, placeholder_text='https://...', width=430).pack(
                side='left', padx=5
            )
            self.button_fields.append((label_var, url_var))

        self.autostart = ctk.BooleanVar(value=self._registry_autostart_enabled())
        if _WINREG_AVAILABLE:
            ctk.CTkSwitch(box, text='Start with Windows', variable=self.autostart).pack(
                anchor='w', padx=20, pady=(15, 20)
            )

        ctk.CTkButton(page, text='Reset to Defaults', command=self.reset_settings).pack(
            anchor='w', padx=30, pady=25
        )

    def _build_about(self):
        page = self._page('about', 'About')
        ctk.CTkLabel(
            page,
            text='Discord Rich Presence Service\nLocal activity detection with configurable privacy controls.',
            justify='left',
        ).pack(anchor='w', padx=30, pady=10)
        link = ctk.CTkLabel(page, text='GitHub repository', text_color='#3b8ed0', cursor='hand2')
        link.pack(anchor='w', padx=30, pady=10)
        link.bind('<Button-1>', lambda _: webbrowser.open('https://github.com/imedkablavi/discord-rich-presence'))

    def select_page(self, name: str):
        for page_name, page in self.pages.items():
            if page_name == name:
                page.grid(row=0, column=1, sticky='nsew')
            else:
                page.grid_forget()
        for button_name, button in self.nav.items():
            button.configure(fg_color=('gray75', 'gray25') if button_name == name else 'transparent')

    def save_settings(self):
        snapshot = copy.deepcopy(self.config.data)
        try:
            self.config.set('privacy.mode', self.privacy_mode.get())
            self.config.set('privacy.hide_home_paths', self.hide_home.get())
            self.config.set('rules.clear_on_lock_screen', self.clear_on_lock.get())
            self.config.set('update_interval_secs', float(self.update_interval.get()))
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
            messagebox.showinfo(
                'Saved', 'Settings saved and validated. The service will hot-reload the file.'
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
            messagebox.showinfo('Reset Complete', 'Defaults restored. Reopen the panel to refresh all controls.')
        except Exception as e:
            self.config.data = snapshot
            messagebox.showerror('Reset Error', str(e))

    def start_service(self):
        active = self.runtime.read_active()
        if active:
            messagebox.showinfo('Service', f"Service is already running (PID {active.get('pid', '?')}).")
            return
        try:
            script = Path(__file__).with_name('main.py')
            python = sys.executable
            if sys.platform == 'win32' and python.lower().endswith('python.exe'):
                pythonw = python[:-10] + 'pythonw.exe'
                if os.path.exists(pythonw):
                    python = pythonw
            self.service_process = subprocess.Popen([python, str(script)], cwd=str(script.parent))
        except Exception as e:
            messagebox.showerror('Start Error', str(e))

    def stop_service(self):
        active = self.runtime.read_active()
        if not active:
            messagebox.showinfo('Service', 'No running service instance was found.')
            return
        if not self.runtime.terminate_active(timeout=5):
            messagebox.showerror(
                'Stop Error', 'The service could not be stopped. Check permissions or the log file.'
            )
        self.service_process = None

    def _poll_service(self):
        active = self.runtime.read_active()
        if not active:
            self.status_label.configure(text='● Service stopped', text_color='gray')
            self.rpc_label.configure(text='Discord RPC: —')
            self.activity_label.configure(text='Activity: —')
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
                and age > max(15.0, float(self.config.get('update_interval_secs', 2)) * 3)
            )

            if stale:
                self.status_label.configure(
                    text=f'● Service heartbeat stale (PID {pid})', text_color='#f39c12'
                )
            elif state in {'rpc_error', 'loop_error', 'configuration_error'}:
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
            self.heartbeat_label.configure(text=f'Heartbeat: {age:.1f}s ago · state={state}')
            self.start_button.configure(state='disabled')
            self.stop_button.configure(state='normal')

        self.after(1000, self._poll_service)

    def test_rpc(self):
        # The public CYBREX application identity is built into Config. Normal
        # users do not need to create a Discord Developer Portal application.
        client_id = str(self.config.get('discord.client_id', '')).strip()

        def worker():
            try:
                from pypresence import Presence
                rpc = Presence(client_id)
                rpc.connect()
                rpc.close()
                self.after(0, lambda: messagebox.showinfo('Discord RPC', 'RPC connection succeeded.'))
            except Exception as e:
                error_message = str(e)
                self.after(
                    0,
                    lambda msg=error_message: messagebox.showerror(
                        'Discord RPC', f'Connection failed: {msg}'
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

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
