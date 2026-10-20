import pytest

from ui_layout import control_panel_geometry


@pytest.mark.parametrize(
    ("screen_width", "screen_height"),
    [
        (1920, 1080),
        (1366, 768),
        (1280, 720),
        (1024, 600),
        (800, 600),
        (640, 480),
    ],
)
def test_control_panel_geometry_fits_and_centers_on_screen(screen_width, screen_height):
    result = control_panel_geometry(screen_width, screen_height)

    assert 0 < result.width <= screen_width
    assert 0 < result.height <= screen_height
    assert result.x >= 0
    assert result.y >= 0
    assert result.x + result.width <= screen_width
    assert result.y + result.height <= screen_height
    assert result.min_width <= result.width
    assert result.min_height <= result.height
    assert result.x == (screen_width - result.width) // 2
    assert result.y == (screen_height - result.height) // 2


def test_control_panel_geometry_uses_safe_fallback_for_invalid_dimensions():
    result = control_panel_geometry("invalid", None)

    assert result.width > 0
    assert result.height > 0
    assert result.width <= 1366
    assert result.height <= 768



@pytest.mark.parametrize(
    ("screen_width", "expected"),
    [
        (640, 156),
        (800, 184),
        (1024, 210),
        (1366, 252),
        (1920, 252),
    ],
)
def test_sidebar_width_scales_for_narrow_displays(screen_width, expected):
    from ui_layout import sidebar_width_for_screen

    assert sidebar_width_for_screen(screen_width) == expected


def test_sidebar_width_has_safe_fallback_for_invalid_width():
    from ui_layout import sidebar_width_for_screen

    assert sidebar_width_for_screen("bad") == 252
