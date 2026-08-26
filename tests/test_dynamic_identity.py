from config import Config
from dynamic_identity import activity_display_name
from icon_resolver import IconResolver
from social_sdk_protocol import activity_fields, decode_message, encode_update


def test_dynamic_identity_prefers_actual_program_over_browser_service():
    assert activity_display_name(
        {
            "type": "browser",
            "browser_name": "Brave",
            "service": "YouTube",
        }
    ) == "Brave"


def test_dynamic_identity_uses_real_game_and_editor_names():
    assert activity_display_name(
        {"type": "gaming", "game_name": "Counter-Strike 2", "launcher": "Steam"}
    ) == "Counter-Strike 2"
    assert activity_display_name(
        {"type": "coding", "editor": "Visual Studio Code", "project": "demo"}
    ) == "Visual Studio Code"


def test_dynamic_identity_normalizes_kde_reverse_domain_name():
    assert activity_display_name(
        {"type": "application", "app_name": "org.kde.konsole"}
    ) == "Konsole"


def test_social_sdk_protocol_carries_explicit_program_name_and_sanitizes_urls():
    line = encode_update(
        {
            "details": "Watching · Example",
            "state": "YouTube · Brave",
            "details_url": "http://localhost:8080/private",
        },
        name="Brave",
    )
    op, fields = decode_message(line)
    assert op == "UPDATE"
    assert fields["name"] == "Brave"
    assert fields["details"] == "Watching · Example"
    assert "details_url" not in fields


def test_social_sdk_activity_fields_keep_two_safe_buttons_only():
    fields = activity_fields(
        {
            "details": "Counter-Strike 2",
            "buttons": [
                {"label": "Steam", "url": "https://store.steampowered.com/app/730/"},
                {"label": "Invalid", "url": "http://127.0.0.1:32192/private"},
                {"label": "Extra", "url": "https://example.com/extra"},
            ],
        },
        name="Counter-Strike 2",
    )
    assert fields["name"] == "Counter-Strike 2"
    assert fields["button1_label"] == "Steam"
    assert fields["button1_url"] == "https://store.steampowered.com/app/730/"
    assert "button2_label" not in fields


def test_icon_resolver_normalizes_common_program_aliases(tmp_path):
    config = Config(tmp_path / "config.yaml")
    resolver = IconResolver(config)
    brave = resolver.resolve_optional("brave-browser")
    vscode = resolver.resolve_optional("code.exe")
    konsole = resolver.resolve_optional("org.kde.konsole")

    assert brave and "brave.com" in brave
    assert vscode and "code.visualstudio.com" in vscode
    assert konsole and "kde.org" in konsole
