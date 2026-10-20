from game_library import GameLibraryEntry, scan_library_safely
import game_library


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
    monkeypatch.setattr(game_library, "discover_games", lambda: expected)

    entries, error = scan_library_safely()

    assert entries == expected
    assert error is None


def test_scan_library_contains_discovery_errors(monkeypatch):
    def fail_scan():
        raise OSError("library metadata unavailable")

    monkeypatch.setattr(game_library, "discover_games", fail_scan)

    entries, error = scan_library_safely()

    assert entries == []
    assert error == "library metadata unavailable"
