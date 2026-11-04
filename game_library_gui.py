"""Standalone Game Library window for CYBREX Rich Presence."""

from __future__ import annotations

import queue
import threading
from typing import Optional

import customtkinter as ctk

from config import Config
from game_library import (
    GameLibraryEntry,
    gamer_mode_enabled,
    is_game_enabled,
    library_counts,
    library_empty_message,
    set_game_enabled,
    set_gamer_mode,
    scan_library_safely,
)
from ui_layout import control_panel_geometry


class GameLibraryWindow(ctk.CTk):
    """Searchable local game library with privacy-first per-game controls."""

    def __init__(self, config: Optional[Config] = None):
        resolved_config = config or Config()
        appearance = str(resolved_config.get('ui.appearance', 'System'))
        if appearance not in {'System', 'Light', 'Dark'}:
            appearance = 'System'
        ctk.set_appearance_mode(appearance)
        super().__init__()
        self.config = resolved_config
        self.entries: list[GameLibraryEntry] = []
        self._loading = False
        self._scan_error: Optional[str] = None
        self._closed = False
        # Worker threads publish plain Python results only. All Tk operations
        # stay on the main/UI thread to avoid calls into a destroyed interpreter.
        self._refresh_results = queue.SimpleQueue()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        self.title('CYBREX Game Library')
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        geometry = control_panel_geometry(screen_width, screen_height)
        window_width = min(940, geometry.width)
        window_height = min(680, geometry.height)
        window_x = max(0, (screen_width - window_width) // 2)
        window_y = max(0, (screen_height - window_height) // 2)
        self._compact_layout = window_width < 900
        self._window_width = window_width
        self.minsize(min(560, window_width), min(360, window_height))
        self.geometry(
            f'{window_width}x{window_height}+{window_x}+{window_y}'
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text='Game Library',
            font=ctk.CTkFont(size=22 if self._compact_layout else 26, weight='bold'),
            anchor='w',
        ).grid(
            row=0, column=0,
            padx=16 if self._compact_layout else 24,
            pady=(14, 2) if self._compact_layout else (18, 2),
            sticky='ew',
        )
        ctk.CTkLabel(
            header,
            text='Local Steam, Epic and Heroic games. Disabled games are never published to Discord.',
            anchor='w',
            justify='left',
            wraplength=max(180, window_width - 48),
            font=ctk.CTkFont(size=12 if self._compact_layout else 13),
        ).grid(
            row=1, column=0,
            padx=16 if self._compact_layout else 24,
            pady=(0, 10) if self._compact_layout else (0, 18),
            sticky='ew',
        )

        self.gamer_mode_var = ctk.BooleanVar(value=gamer_mode_enabled(self.config))
        self.gamer_mode = ctk.CTkSwitch(
            header,
            text='Gamer Mode · publish games only',
            variable=self.gamer_mode_var,
            command=self._toggle_gamer_mode,
        )
        if self._compact_layout:
            self.gamer_mode.grid(
                row=2, column=0, columnspan=2,
                padx=16, pady=(0, 12), sticky='w',
            )
        else:
            self.gamer_mode.grid(
                row=0, column=1, rowspan=2, padx=24, pady=18, sticky='e'
            )

        toolbar = ctk.CTkFrame(self, corner_radius=0)
        toolbar.grid(row=1, column=0, sticky='ew')
        toolbar.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add('write', lambda *_: self._render())
        self.search = ctk.CTkEntry(
            toolbar,
            textvariable=self.search_var,
            placeholder_text='Search games or launcher…',
            height=38,
        )
        self.search.grid(
            row=0, column=0,
            padx=(16, 8) if self._compact_layout else (24, 12),
            pady=10 if self._compact_layout else 12,
            sticky='ew',
        )

        self.refresh_button = ctk.CTkButton(
            toolbar,
            text='Refresh',
            width=100,
            command=self.refresh_library,
        )
        self.refresh_button.grid(
            row=0, column=1,
            padx=(0, 16) if self._compact_layout else (0, 24),
            pady=10 if self._compact_layout else 12,
        )

        self.list_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.list_frame.grid(row=2, column=0, sticky='nsew')
        self.list_frame.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self, corner_radius=0)
        footer.grid(row=3, column=0, sticky='ew')
        footer.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(
            footer,
            text='Scanning local game libraries…',
            anchor='w',
            justify='left',
            wraplength=max(180, window_width - 48),
        )
        self.status.grid(
            row=0, column=0,
            padx=16 if self._compact_layout else 24,
            pady=10 if self._compact_layout else 12,
            sticky='ew',
        )

        self.after(80, self.refresh_library)
        self.after(100, self._poll_refresh_results)

    def _on_close(self) -> None:
        self._closed = True
        self.destroy()

    def _poll_refresh_results(self) -> None:
        """Apply completed scans on the Tk main thread."""
        if self._closed:
            return
        try:
            entries, error = self._refresh_results.get_nowait()
        except queue.Empty:
            pass
        else:
            self._finish_refresh(entries, error)
        if not self._closed:
            self.after(100, self._poll_refresh_results)

    def _toggle_gamer_mode(self) -> None:
        desired = bool(self.gamer_mode_var.get())
        try:
            set_gamer_mode(self.config, desired)
            self.status.configure(
                text='Gamer Mode enabled: only game activity is published.'
                if desired else 'Gamer Mode disabled: previous detector preferences restored.'
            )
        except Exception as exc:
            self.gamer_mode_var.set(gamer_mode_enabled(self.config))
            self.status.configure(text=f'Could not change Gamer Mode: {exc}')

    def refresh_library(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.refresh_button.configure(state='disabled', text='Scanning…')
        self.status.configure(text='Scanning Steam, Epic and Heroic metadata locally…')

        def worker() -> None:
            result = scan_library_safely()
            self._refresh_results.put(result)

        threading.Thread(target=worker, daemon=True, name='cybrex-game-library-scan').start()

    def _finish_refresh(self, entries: list[GameLibraryEntry], error: Optional[str]) -> None:
        if self._closed:
            return
        self._loading = False
        self.refresh_button.configure(state='normal', text='Refresh')
        self._scan_error = error
        if error:
            self.entries = []
            self.status.configure(text=f'Game library scan failed: {error}')
        else:
            self.entries = entries
            total, enhanced = library_counts(entries)
            self.status.configure(text=f'{total} installed games found · {enhanced} enhanced integrations')
        self._render()

    def _filtered_entries(self) -> list[GameLibraryEntry]:
        query = self.search_var.get().strip().casefold()
        if not query:
            return self.entries
        return [
            entry for entry in self.entries
            if query in entry.name.casefold() or query in entry.source.casefold()
        ]

    def _render(self) -> None:
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        entries = self._filtered_entries()
        if not entries:
            message = library_empty_message(
                len(self.entries),
                self.search_var.get(),
                self._scan_error,
            )
            ctk.CTkLabel(self.list_frame, text=message).grid(
                row=0, column=0, padx=24, pady=32, sticky='w'
            )
            return

        for row_index, entry in enumerate(entries):
            row = ctk.CTkFrame(self.list_frame)
            row.grid(
                row=row_index, column=0,
                padx=8 if self._compact_layout else 12,
                pady=4 if self._compact_layout else 5,
                sticky='ew',
            )
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row,
                text=entry.name,
                font=ctk.CTkFont(size=14 if self._compact_layout else 15, weight='bold'),
                anchor='w',
            ).grid(
                row=0, column=0,
                padx=(12, 6) if self._compact_layout else (16, 8),
                pady=(9, 1) if self._compact_layout else (11, 1),
                sticky='ew',
            )

            badge = 'Enhanced' if entry.enhanced else 'Standard'
            ctk.CTkLabel(
                row,
                text=f'{entry.source} · {badge}',
                anchor='w',
            ).grid(
                row=1, column=0,
                padx=(12, 6) if self._compact_layout else (16, 8),
                pady=(0, 9) if self._compact_layout else (0, 11),
                sticky='ew',
            )

            enabled_var = ctk.BooleanVar(value=is_game_enabled(self.config, entry.name))
            toggle = ctk.CTkSwitch(
                row,
                text='Presence' if self._compact_layout else 'Discord Presence',
                variable=enabled_var,
                command=lambda e=entry, v=enabled_var: self._toggle_game(e, v),
            )
            toggle.grid(
                row=0, column=1, rowspan=2,
                padx=8 if self._compact_layout else 16,
                pady=9 if self._compact_layout else 11,
                sticky='e',
            )

    def _toggle_game(self, entry: GameLibraryEntry, variable: ctk.BooleanVar) -> None:
        desired = bool(variable.get())
        try:
            set_game_enabled(self.config, entry.name, desired)
            self.status.configure(
                text=f'{entry.name}: Discord Presence {"enabled" if desired else "disabled"}.'
            )
        except Exception as exc:
            variable.set(is_game_enabled(self.config, entry.name))
            self.status.configure(text=f'Could not update {entry.name}: {exc}')


def main() -> int:
    app = GameLibraryWindow(Config())
    app.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
