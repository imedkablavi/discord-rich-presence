import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import webbrowser
import threading
import sys
import os
try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    _WINREG_AVAILABLE = False
from PIL import Image

# Import Config
try:
    from config import Config
except ImportError:
    import importlib.util
    _p = os.path.join(os.path.dirname(__file__), 'config.py')
    _spec = importlib.util.spec_from_file_location('config_fallback', _p)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    Config = _mod.Config

# Set initial Theme defaults before app init
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ModernControlPanel(ctk.CTk):
    def __init__(self, config: Config):
        super().__init__()

        self.config = config
        self._apply_saved_theme()
        self.title("Discord Rich Presence - Professional Edition")
        self.geometry("1100x750")
        self.minsize(900, 600)
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create Navigation Sidebar
        self._create_sidebar()
        self.appearance_mode_menu.set(getattr(self, '_appearance_mode_value', 'System'))
        self.color_theme_menu.set(getattr(self, '_color_theme_value', 'Blue'))

        # Create Main Area
        self.main_frames = {}
        self._create_frames()

        # Select default
        self.select_frame("home")
        
        # Check autostart status from registry to sync UI
        self._check_registry_autostart()

    def _create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # App Logo / Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="DRP Manager\nPro Edition", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Navigation Buttons
        self.nav_buttons = {}
        
        self.nav_buttons["home"] = self._create_nav_btn("Dashboard", "home", 1)
        self.nav_buttons["activity"] = self._create_nav_btn("Activity Rules", "activity", 2)
        self.nav_buttons["privacy"] = self._create_nav_btn("Privacy & Security", "privacy", 3)
        self.nav_buttons["settings"] = self._create_nav_btn("Settings", "settings", 4)
        self.nav_buttons["about"] = self._create_nav_btn("About & Legal", "about", 5)

        # Appearance Mode
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Theme:", anchor="w")
        self.appearance_mode_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            self.sidebar_frame, 
            values=["System", "Light", "Dark"],
            command=self.change_appearance_mode_event
        )
        self.appearance_mode_menu.grid(row=8, column=0, padx=20, pady=(10, 20))

        self.color_theme_label = ctk.CTkLabel(self.sidebar_frame, text="Color Theme:", anchor="w")
        self.color_theme_label.grid(row=9, column=0, padx=20, pady=(0, 0))
        self.color_theme_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Blue", "Green", "Dark-Blue"],
            command=self.change_color_theme_event
        )
        self.color_theme_menu.grid(row=10, column=0, padx=20, pady=(10, 20))
        
        # Save Button
        self.save_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Save Changes",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            font=ctk.CTkFont(weight="bold"),
            command=self.save_settings
        )
        self.save_btn.grid(row=11, column=0, padx=20, pady=20)

    def _create_nav_btn(self, text, name, row):
        btn = ctk.CTkButton(
            self.sidebar_frame,
            corner_radius=0,
            height=45,
            border_spacing=15,
            text=text,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=ctk.CTkFont(size=14),
            command=lambda: self.select_frame(name)
        )
        btn.grid(row=row, column=0, sticky="ew")
        return btn

    def _create_frames(self):
        # 1. Home Dashboard
        self.home_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frames["home"] = self.home_frame
        
        ctk.CTkLabel(self.home_frame, text="System Status", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=30, pady=20)
        
        # Status Card
        status_card = ctk.CTkFrame(self.home_frame, fg_color=("gray85", "gray20"))
        status_card.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(status_card, text="Service Status:", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=20, pady=20)
        self.status_label = ctk.CTkLabel(status_card, text="● Running", text_color="#2ecc71", font=ctk.CTkFont(size=16, weight="bold"))
        self.status_label.pack(side="left", padx=10)
        
        # Test Connection Button
        ctk.CTkButton(status_card, text="Test Discord Connection", command=self._test_connection, width=200).pack(side="right", padx=20, pady=20)
        
        # Quick Toggles
        ctk.CTkLabel(self.home_frame, text="Quick Actions", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", padx=30, pady=(30, 10))
        
        q_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        q_frame.pack(fill="x", padx=30)
        
        self.q_autostart = ctk.BooleanVar(value=bool(self.config.get('system.auto_start', False)))
        as_switch = ctk.CTkSwitch(q_frame, text="Start with Windows (Registry)", variable=self.q_autostart, font=ctk.CTkFont(size=14))
        as_switch.pack(anchor="w", pady=10)
        
        self.q_tray = ctk.BooleanVar(value=bool(self.config.get('system.start_minimized', False)))
        tray_switch = ctk.CTkSwitch(q_frame, text="Start Minimized to Tray", variable=self.q_tray, font=ctk.CTkFont(size=14))
        tray_switch.pack(anchor="w", pady=10)
        
        # Tips
        tip_frame = ctk.CTkFrame(self.home_frame, border_width=1, border_color=("gray70", "gray30"))
        tip_frame.pack(fill="x", padx=30, pady=30)
        ctk.CTkLabel(tip_frame, text="💡 Pro Tip: Use 'Activity Rules' to exclude specific apps or games you don't want to show.", justify="left", wraplength=600).pack(padx=20, pady=15, anchor="w")

        # 2. Activity Rules
        self.activity_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frames["activity"] = self.activity_frame
        
        ctk.CTkLabel(self.activity_frame, text="Activity Detection Rules", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=30, pady=20)
        ctk.CTkLabel(self.activity_frame, text="Select which activities are broadcast to Discord.", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=30, pady=(0, 20))
        
        # Detectors
        det_frame = ctk.CTkFrame(self.activity_frame)
        det_frame.pack(fill="x", padx=30, pady=10)
        
        enabled = self.config.get('rules.enabled_detectors', {}) or {}
        self.detectors_vars = {
            'gaming': ('Game Detection', bool(enabled.get('gaming', True))),
            'coding': ('Code Editors (VS Code, Trae, JetBrains)', bool(enabled.get('coding', True))),
            'browser': ('Web Browsers (Chrome, Edge, etc.)', bool(enabled.get('browser', True))),
            'media': ('Media Players (VLC, Spotify)', bool(enabled.get('media', True))),
            'terminal': ('Terminal / Console', bool(enabled.get('terminal', True))),
            'plugins': ('Community Plugins', bool(enabled.get('plugins', True))),
        }
        
        for key, (label, val) in self.detectors_vars.items():
            var = ctk.BooleanVar(value=val)
            self.detectors_vars[key] = var # Store var
            ctk.CTkCheckBox(det_frame, text=label, variable=var, font=ctk.CTkFont(size=14)).pack(anchor="w", padx=20, pady=12)

        # 3. Privacy
        self.privacy_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frames["privacy"] = self.privacy_frame
        
        ctk.CTkLabel(self.privacy_frame, text="Privacy & Security", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=30, pady=20)
        
        p_frame = ctk.CTkFrame(self.privacy_frame)
        p_frame.pack(fill="x", padx=30, pady=10)
        
        self.privacy_mode_var = tk.StringVar(value=str(self.config.get('privacy.mode', 'balanced')))
        
        ctk.CTkLabel(p_frame, text="Privacy Mode:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        modes = [
            ("Off", "off", "Share everything (Filename, Project Name, URL)"),
            ("Balanced", "balanced", "Hide sensitive paths, secrets, and private browsing"),
            ("Strict", "strict", "Hide all filenames, details, and buttons")
        ]
        
        for label, val, desc in modes:
            rb = ctk.CTkRadioButton(p_frame, text=f"{label} - {desc}", variable=self.privacy_mode_var, value=val, font=ctk.CTkFont(size=14))
            rb.pack(anchor="w", padx=20, pady=8)
            
        ctk.CTkLabel(p_frame, text="File System Privacy:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(30, 10))
        self.hide_home_var = ctk.BooleanVar(value=bool(self.config.get('privacy.hide_home_paths', True)))
        ctk.CTkSwitch(p_frame, text="Auto-redact Home Directory (e.g. C:/Users/Name -> ~)", variable=self.hide_home_var, font=ctk.CTkFont(size=14)).pack(anchor="w", padx=20, pady=(10, 20))

        # 4. Settings
        self.settings_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frames["settings"] = self.settings_frame
        
        ctk.CTkLabel(self.settings_frame, text="Application Settings", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=30, pady=20)
        
        # Client ID
        id_frame = ctk.CTkFrame(self.settings_frame)
        id_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(id_frame, text="Discord Client ID (Advanced):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.client_id_var = tk.StringVar(value=str(self.config.get('discord.client_id', '')))
        ctk.CTkEntry(id_frame, textvariable=self.client_id_var, width=350, state="disabled").pack(anchor="w", padx=20, pady=5)
        ctk.CTkLabel(id_frame, text="Application ID is optional. A built-in fallback is used automatically.", text_color="gray").pack(anchor="w", padx=20, pady=(0, 20))

        # Buttons
        btn_frame = ctk.CTkFrame(self.settings_frame)
        btn_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(btn_frame, text="Custom Buttons (Optional):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        buttons = self.config.get('discord.buttons', []) or []
        btn1 = buttons[0] if len(buttons) > 0 else {}
        
        self.btn1_label = tk.StringVar(value=btn1.get('label', ''))
        self.btn1_url = tk.StringVar(value=btn1.get('url', ''))
        
        b1 = ctk.CTkFrame(btn_frame, fg_color="transparent")
        b1.pack(fill="x", padx=10)
        ctk.CTkEntry(b1, textvariable=self.btn1_label, placeholder_text="Label (e.g. My Website)", width=180).pack(side="left", padx=5)
        ctk.CTkEntry(b1, textvariable=self.btn1_url, placeholder_text="URL (https://...)", width=300).pack(side="left", padx=5)

        ctk.CTkLabel(btn_frame, text="Leave empty to use dynamic buttons (YouTube, GitHub, etc.)", text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(5, 20))
        
        # Reset Button
        ctk.CTkButton(self.settings_frame, text="Reset All Settings to Default", fg_color="#e74c3c", hover_color="#c0392b", command=self._reset_settings).pack(anchor="w", padx=30, pady=30)

        # 5. About & Legal
        self.about_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frames["about"] = self.about_frame
        
        ctk.CTkLabel(self.about_frame, text="About & Legal", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=30, pady=20)
        
        # Credits
        cred_frame = ctk.CTkFrame(self.about_frame)
        cred_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(cred_frame, text="Developed by CYBREX@TECH", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 5))
        link = ctk.CTkLabel(cred_frame, text="SITE: imedkablavi.info", text_color="#3498db", cursor="hand2", font=ctk.CTkFont(size=14, underline=True))
        link.pack(pady=(0, 20))
        link.bind("<Button-1>", lambda e: webbrowser.open("https://imedkablavi.info"))
        
        # Legal Text
        legal_text = """
TERMS OF USE
----------------
This software is provided "as is", without warranty of any kind. 
By using this software, you agree that the developer (CYBREX@TECH) 
is not liable for any damages or account issues arising from its use.

PRIVACY POLICY
----------------
1. Data Collection: This application runs locally on your machine.
2. No Cloud Upload: We do not upload your personal files or activity to any external server.
3. Discord RPC: Activity data (window titles, app names) is sent to Discord's servers 
   ONLY to display your Rich Presence status, in accordance with Discord's Terms of Service.
4. Sensitive Data: The application includes a "Privacy Mode" to automatically redact 
   passwords, API keys, and sensitive paths before sending data to Discord.

LICENSE
----------------
Copyright (c) 2024 CYBREX@TECH. All rights reserved.
MIT License (See LICENSE file for full details).
        """
        
        textbox = ctk.CTkTextbox(self.about_frame, height=350, font=ctk.CTkFont(family="Consolas", size=12))
        textbox.pack(fill="x", padx=30, pady=10)
        textbox.insert("0.0", legal_text)
        textbox.configure(state="disabled")

    def select_frame(self, name):
        # Update buttons color
        for n, btn in self.nav_buttons.items():
            btn.configure(fg_color=("gray75", "gray25") if n == name else "transparent")

        # Show frame
        for n, frame in self.main_frames.items():
            if n == name:
                frame.grid(row=0, column=1, sticky="nsew")
            else:
                frame.grid_forget()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def change_color_theme_event(self, new_color_theme: str):
        ctk.set_default_color_theme(new_color_theme.lower())

    def _apply_saved_theme(self):
        appearance_mode = str(self.config.get('ui.appearance_mode', 'System') or 'System')
        color_theme = str(self.config.get('ui.color_theme', 'blue') or 'blue')
        color_theme_title = color_theme.title() if color_theme != 'dark-blue' else 'Dark-Blue'
        ctk.set_appearance_mode(appearance_mode)
        ctk.set_default_color_theme(color_theme)
        self._appearance_mode_value = appearance_mode
        self._color_theme_value = color_theme_title

    def save_settings(self):
        try:
            # Validate URL
            url = self.btn1_url.get().strip()
            if url and not (url.startswith('http://') or url.startswith('https://')):
                 messagebox.showwarning("Validation Error", "Button URL must start with http:// or https://")
                 return

            # System
            self.config.set('system.start_minimized', self.q_tray.get())
            self.config.set('system.auto_start', self.q_autostart.get())
            self.config.set('ui.appearance_mode', self.appearance_mode_menu.get())
            self.config.set('ui.color_theme', self.color_theme_menu.get().lower())
            
            # Apply Registry Autostart
            self._update_autostart_registry(self.q_autostart.get())
            
            # Detectors
            detectors = {}
            for k, var in self.detectors_vars.items():
                if isinstance(var, ctk.BooleanVar):
                    detectors[k] = var.get()
            self.config.set('rules.enabled_detectors', detectors)
            
            # Privacy
            self.config.set('privacy.mode', self.privacy_mode_var.get())
            self.config.set('privacy.hide_home_paths', self.hide_home_var.get())
            
            # Buttons
            btns = []
            if self.btn1_label.get() and url:
                btns.append({'label': self.btn1_label.get(), 'url': url})
            self.config.set('discord.buttons', btns)
            
            # Save
            self.config.save()
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _reset_settings(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all settings to default?"):
            try:
                # Reset config logic here (simplified)
                self.config.data = {
                    'discord': {'client_id': '', 'fallback_client_ids': ['1437867564762923028'], 'buttons': []},
                    'privacy': {'mode': 'balanced', 'hide_home_paths': True},
                    'system': {'auto_start': False, 'start_minimized': False},
                    'ui': {'appearance_mode': 'System', 'color_theme': 'blue'},
                    'plugins': {'directory': '', 'enabled': []},
                    'rules': {'enabled_detectors': {'gaming': True, 'coding': True, 'browser': True, 'media': True, 'terminal': True, 'plugins': True}}
                }
                self.config.save()
                messagebox.showinfo("Reset Complete", "Settings have been reset. Please restart the application.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _test_connection(self):
        # Simple test to see if Discord is running
        import psutil
        discord_running = False
        for proc in psutil.process_iter(['name']):
            try:
                if 'discord' in proc.info['name'].lower():
                    discord_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if discord_running:
            messagebox.showinfo("Connection Test", "Discord process detected! RPC should work.")
        else:
            messagebox.showwarning("Connection Test", "Discord process NOT found. Please start Discord first.")

    def _update_autostart_registry(self, enable):
        """Update Windows Registry for Auto-Start"""
        if not _WINREG_AVAILABLE:
            return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            app_name = "DiscordRichPresence"
            
            if enable:
                # Determine path
                if getattr(sys, 'frozen', False):
                    # Running as exe
                    exe_path = sys.executable
                    cmd = f'"{exe_path}" --tray'
                else:
                    # Running as script
                    python_exe = sys.executable.replace("python.exe", "pythonw.exe") # Use no-console python
                    script = os.path.abspath(sys.argv[0])
                    # Assuming running from root dir
                    script_dir = os.path.dirname(script)
                    main_script = os.path.join(script_dir, "main.py")
                    if not os.path.exists(main_script):
                         main_script = script # Fallback
                    cmd = f'"{python_exe}" "{main_script}" --tray'
                
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass # Already deleted
            
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Registry error: {e}")
            # Non-fatal, just log

    def _check_registry_autostart(self):
        """Check if registry key exists and sync UI"""
        if not _WINREG_AVAILABLE:
            return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "DiscordRichPresence")
                # Key exists
                self.q_autostart.set(True)
            except FileNotFoundError:
                self.q_autostart.set(False)
            winreg.CloseKey(key)
        except Exception:
            pass

if __name__ == "__main__":
    try:
        cfg = Config()
        app = ModernControlPanel(cfg)
        app.appearance_mode_menu.set(getattr(app, '_appearance_mode_value', 'System'))
        app.color_theme_menu.set(getattr(app, '_color_theme_value', 'Blue'))
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
