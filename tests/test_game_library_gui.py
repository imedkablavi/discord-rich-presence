from game_library import GameLibraryEntry
import game_library_gui


def test_scan_library_returns_local_entries_without_error(monkeypatch):
    expected = [
        GameLibraryEntry(
            key="steam:730",
            name="Counter-Strike 2",
            source="Steam",
            app_id="730",
            enhanced=True,
        )
    ]
    monkeypatch.setattr(game_library_gui, "discover_games", lambda: expected)

    entries, error = game_library_gui.GameLibraryWindow._scan_library()

    assert entries == expected
    assert error is None


def test_scan_library_contains_discovery_errors(monkeypatch):
    def fail_scan():
        raise OSError("library metadata unavailable")

    monkeypatch.setattr(game_library_gui, "discover_games", fail_scan)

    entries, error = game_library_gui.GameLibraryWindow._scan_library()

    assert entries == []
    assert error == "library metadata unavailable"
