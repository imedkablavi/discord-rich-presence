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



def test_empty_state_explains_scan_failure_instead_of_claiming_no_games():
    from game_library import library_empty_message

    message = library_empty_message(0, scan_error="permission denied")

    assert "could not be read" in message.lower()
    assert "no supported local game installs" not in message.lower()


def test_empty_state_distinguishes_no_installs_from_no_search_matches():
    from game_library import library_empty_message

    assert library_empty_message(0) == "No supported local game installs were found."
    assert library_empty_message(5, "does-not-exist") == (
        "No matching games. Try a different search term."
    )
