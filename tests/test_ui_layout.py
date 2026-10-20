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



@pytest.mark.parametrize(
    ("content_width", "expected"),
    [
        (0, 2),
        (320, 2),
        (578, 2),
        (639, 2),
        (640, 4),
        (702, 4),
        (1100, 4),
    ],
)
def test_dashboard_metrics_choose_columns_from_available_content(content_width, expected):
    from ui_layout import dashboard_metric_columns

    assert dashboard_metric_columns(content_width) == expected


def test_dashboard_metric_columns_defaults_to_compact_for_invalid_width():
    from ui_layout import dashboard_metric_columns

    assert dashboard_metric_columns("unavailable") == 2



@pytest.mark.parametrize(
    ("screen_width", "screen_height", "expected_width", "expected_height"),
    [
        (640, 480, 600, 400),
        (800, 600, 760, 520),
        (1024, 600, 984, 520),
    ],
)
def test_compact_window_leaves_space_for_desktop_chrome(
    screen_width, screen_height, expected_width, expected_height
):
    result = control_panel_geometry(screen_width, screen_height)

    assert result.width == expected_width
    assert result.height == expected_height
    assert result.x >= 0
    assert result.y >= 0
    assert result.x + result.width <= screen_width
    assert result.y + result.height <= screen_height



@pytest.mark.parametrize(
    ("content_width", "expected"),
    [
        (0, True),
        (320, True),
        (546, True),
        (639, True),
        (640, False),
        (702, False),
    ],
)
def test_dashboard_hero_stacks_when_content_is_compact(content_width, expected):
    from ui_layout import dashboard_hero_stacked

    assert dashboard_hero_stacked(content_width) is expected


def test_dashboard_hero_uses_compact_layout_for_invalid_width():
    from ui_layout import dashboard_hero_stacked

    assert dashboard_hero_stacked(None) is True



def test_compact_layout_threshold_is_reused_for_runtime_panels():
    from ui_layout import dashboard_hero_stacked

    # The Overview runtime cards share the same tested compact-layout decision
    # as the hero controls, preventing an untested second breakpoint.
    assert dashboard_hero_stacked(372) is True
    assert dashboard_hero_stacked(639) is True
    assert dashboard_hero_stacked(702) is False
