from ui_text import display_text, repair_utf8_mojibake


def test_plain_english_text_is_unchanged():
    value = "Watching · Brave"
    assert repair_utf8_mojibake(value) == value
    assert display_text(value) == value


def test_common_utf8_arabic_mojibake_is_repaired():
    broken = "Ù…Ø±Ø­Ø¨Ø§ Ø¨Ùƒ"
    repaired = repair_utf8_mojibake(broken)
    assert repaired == "مرحبا بك"
    assert "Ø" not in repaired
    assert "Ù" not in repaired


def test_mixed_arabic_and_latin_keeps_latin_identity():
    value = "Watching · مشاهدة محتوى على Brave"
    rendered = display_text(value)
    assert "Watching" in rendered
    assert "Brave" in rendered
    assert "Ø" not in rendered
    assert "Ù" not in rendered


def test_display_text_never_corrupts_non_arabic_unicode():
    value = "Connected · Spotify ✓"
    assert display_text(value) == value
