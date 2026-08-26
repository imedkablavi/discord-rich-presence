"""Standalone Game Library window for CYBREX Rich Presence."""

from __future__ import annotations

import threading
from typing import Optional

import customtkinter as ctk

from config import Config
from game_library import (
    GameLibraryEntry,
    discover_games,
    gamer_mode_enabled,
    is_game_enabled,
    library_counts,
    set_game_enabled,
    set_gamer_mode,
)


class GameLibraryWindow(ctk.CTk):
    """Searchable local game library with privacy-first per-game controls."""

    def __init__(self, config: Optional[Config] = None):
        super().__init__()
        self.config = config or Config()
        self.entries: list[GameLibraryEntry] = []
        self._loading = False

        self.title('CYBREX Game Library')
        self.geometry('940x680')
        self.minsize(760, 540)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text='Game Library',
            font=ctk.CTkFont(size=26, weight='bold'),
            anchor='w',
        ).grid(row=0, column=0, padx=24, pady=(18, 2), sticky='ew')
        ctk.CTkLabel(
            header,
            text='Local Steam, Epic and Heroic games. Disabled games are never published to Discord.',
            anchor='w',
        ).grid(row=1, column=0, padx=24, pady=(0, 18), sticky='ew')

        self.gamer_mode_var = ctk.BooleanVar(value=gamer_mode_enabled(self.config))
        self.gamer_mode = ctk.CTkSwitch(
            header,
            text='Gamer Mode · publish games only',
            variable=self.gamer_mode_var,
            command=self._toggle_gamer_mode,
        )
        self.gamer_mode.grid(row=0, column=1, rowspan=2, padx=24, pady=18, sticky='e')

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
        self.search.grid(row=0, column=0, padx=(24, 12), pady=12, sticky='ew')

        self.refresh_button = ctk.CTkButton(
            toolbar,
            text='Refresh',
            width=100,
            command=self.refresh_library,
        )
        self.refresh_button.grid(row=0, column=1, padx=(0, 24), pady=12)

        self.list_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.list_frame.grid(row=2, column=0, sticky='nsew')
        self.list_frame.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self, corner_radius=0)
        footer.grid(row=3, column=0, sticky='ew')
        footer.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(footer, text='Scanning local game libraries…', anchor='w')
        self.status.grid(row=0, column=0, padx=24, pady=12, sticky='ew')

        self.after(80, self.refresh_library)

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
            try:
                entries = discover_games()
                error = None
            except Exception as exc:  # UI boundary: show one contained error.
                entries = []
                error = str(exc)
            self.after(0, lambda: self._finish_refresh(entries, error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_refresh(self, entries: list[GameLibraryEntry], error: Optional[str]) -> None:
        self._loading = False
        self.refresh_button.configure(state='normal', text='Refresh')
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
            message = 'No matching games.' if self.entries else 'No supported local game installs were found.'
            ctk.CTkLabel(self.list_frame, text=message).grid(
                row=0, column=0, padx=24, pady=32, sticky='w'
            )
            return

        for row_index, entry in enumerate(entries):
            row = ctk.CTkFrame(self.list_frame)
            row.grid(row=row_index, column=0, padx=12, pady=5, sticky='ew')
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row,
                text=entry.name,
                font=ctk.CTkFont(size=15, weight='bold'),
                anchor='w',
            ).grid(row=0, column=0, padx=(16, 8), pady=(11, 1), sticky='ew')

            badge = 'Enhanced' if entry.enhanced else 'Standard'
            ctk.CTkLabel(
                row,
                text=f'{entry.source} · {badge}',
                anchor='w',
            ).grid(row=1, column=0, padx=(16, 8), pady=(0, 11), sticky='ew')

            enabled_var = ctk.BooleanVar(value=is_game_enabled(self.config, entry.name))
            toggle = ctk.CTkSwitch(
                row,
                text='Discord Presence',
                variable=enabled_var,
                command=lambda e=entry, v=enabled_var: self._toggle_game(e, v),
            )
            toggle.grid(row=0, column=1, rowspan=2, padx=16, pady=11, sticky='e')

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
