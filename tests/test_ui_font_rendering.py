from ui_font_rendering import choose_font_family, parse_scalable_font_families


def test_parse_scalable_font_families_ignores_bitmap_faces_and_normalizes_aliases():
    output = (
        "Bitmap Display\tFalse\n"
        "DejaVu Sans,DejaVu Sans Condensed\tTrue\n"
        "Liberation Mono\ttrue\n"
    )

    assert parse_scalable_font_families(output) == {
        "dejavu sans",
        "dejavu sans condensed",
        "liberation mono",
    }


def test_choose_font_family_skips_non_scalable_preferred_family():
    available = ["Noto Sans", "DejaVu Sans", "TkDefaultFont"]
    scalable = {"dejavu sans"}

    assert choose_font_family(
        available,
        ("Noto Sans", "DejaVu Sans"),
        scalable,
    ) == "DejaVu Sans"


def test_choose_font_family_matches_tk_family_names_case_insensitively():
    assert choose_font_family(
        ["liberation sans", "DejaVu Sans"],
        ("DejaVu Sans", "Liberation Sans"),
        {"dejavu sans", "liberation sans"},
    ) == "DejaVu Sans"


def test_choose_font_family_uses_any_available_scalable_face_as_fallback():
    assert choose_font_family(
        ["TkDefaultFont", "Liberation Sans", "DejaVu Sans"],
        ("Inter", "Noto Sans"),
        {"liberation sans", "dejavu sans"},
    ) == "DejaVu Sans"


def test_choose_font_family_falls_back_to_tk_list_when_fontconfig_is_unavailable():
    assert choose_font_family(
        ["TkDefaultFont", "Liberation Sans"],
        ("Inter", "Liberation Sans"),
        None,
    ) == "Liberation Sans"


def test_choose_font_family_returns_none_instead_of_fabricating_a_family():
    assert choose_font_family([], ("DejaVu Sans",), {"dejavu sans"}) is None
