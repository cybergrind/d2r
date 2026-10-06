"""Widget renderers draw headlessly with cairo; the guide card composes arrow rows and the map."""

import cairo
import pytest

from inventory_tracking.hud.payloads import guide_payload
from inventory_tracking.hud.scene import Widget
from inventory_tracking.hud.widgets import RENDERERS, draw_scene, measure
from inventory_tracking.osd.level_map import MapCard, MapPoi
from inventory_tracking.presentation import StyledLine


MAP = MapCard(((0, 0, 12, 12), (12, 0, 12, 12)), (6.0, 6.0), (MapPoi('Summoner', 'target', 18.0, 6.0),))
LINES = [StyledLine('↗  Summoner: north', arrow='↗'), StyledLine('•  Waypoint: here')]


def painted(surface):
    surface.flush()
    return any(surface.get_data())


def test_guide_card_grows_with_its_rows_and_holds_the_map():
    one = measure(Widget('g', 'guide', 'guide', guide_payload(LINES[:1], MAP)), scale=1.0)
    two = measure(Widget('g', 'guide', 'guide', guide_payload(LINES, MAP)), scale=1.0)
    without_map = measure(Widget('g', 'guide', 'guide', guide_payload(LINES, None)), scale=1.0)

    assert two[1] > one[1]
    assert without_map[1] < two[1]
    assert two[0] >= 260  # the map's width


def test_guide_card_payload_round_trips_the_display_lines_and_map():
    payload = guide_payload(LINES, MAP)

    lines, card = RENDERERS['guide'].decode(payload)

    assert lines == LINES
    assert card == MAP


@pytest.mark.parametrize('scale', [0.6, 1.0, 2.0])
def test_scene_draws_into_an_image_surface(scale):
    widget = Widget('g', 'guide', 'guide', guide_payload(LINES, MAP))
    w, h = measure(widget, scale=scale)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w + 20, h + 20)

    draw_scene(cairo.Context(surface), [(widget, (10, 10, w, h))], scale=scale)

    assert painted(surface)


def test_unknown_widget_kind_is_skipped():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 50, 50)

    draw_scene(cairo.Context(surface), [(Widget('x', 'nope', 's', {}), (0, 0, 50, 50))], scale=1.0)

    assert not painted(surface)


def text_widget(lines):
    from inventory_tracking.hud.payloads import card_payload

    return Widget('card', 'text', 'assessment', card_payload(lines))


def test_text_card_wraps_within_the_slot_width_and_is_cut_at_its_height():
    long = [StyledLine('Grand Charm of Vita +40 to Life, 12% Faster Hit Recovery ' * 3)] + [
        f'line {i}' for i in range(60)
    ]
    widget = text_widget(long)

    free_width, _ = measure(widget, scale=1.0)
    width, height = measure(widget, scale=1.0, limit=(400, 300))

    assert free_width > 400
    assert width <= 400
    assert height <= 300


def test_text_card_draws_plain_and_styled_lines():
    from inventory_tracking.presentation import Tone

    widget = text_widget(['Ring', StyledLine('Offline ask estimate: ~2 Ist', Tone.UNIQUE)])
    w, h = measure(widget, scale=1.0, limit=(600, 400))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)

    draw_scene(cairo.Context(surface), [(widget, (0, 0, w, h))], scale=1.0)

    assert painted(surface)


def test_guide_arrows_are_drawn_in_their_row_colour():
    from inventory_tracking.presentation import Tone

    widget = Widget(
        'g', 'guide', 'guide', guide_payload([StyledLine('→  Next level: east', Tone.LEVEL_NEXT, arrow='→')], None)
    )
    w, h = measure(widget, scale=1.0)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)

    draw_scene(cairo.Context(surface), [(widget, (0, 0, w, h))], scale=1.0)

    surface.flush()
    data, stride = surface.get_data(), surface.get_stride()
    guide = RENDERERS['guide']
    centre = (h // 2) * stride + (guide.PAD + guide.ARROW_WIDTH // 2) * 4
    blue, green, red = data[centre], data[centre + 1], data[centre + 2]
    assert green > max(red, blue) + 60


def test_a_map_only_guide_card_has_no_box():
    widget = Widget('g', 'guide', 'guide', guide_payload([], MAP))
    w, h = measure(widget, scale=1.0)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)

    draw_scene(cairo.Context(surface), [(widget, (0, 0, w, h))], scale=1.0)

    surface.flush()
    assert surface.get_data()[3] == 0  # top-left corner: no card background or border


def test_ground_marks_fill_the_game_window_and_stay_translucent():
    from inventory_tracking.config import HudGroundConfig
    from inventory_tracking.hud.ground import place_mark

    config = HudGroundConfig()
    payload = {'player': [10.0, 10.0], 'marks': [['leader', 11.0, 10.0], ['stairs', 90.0, 10.0]]}
    widget = Widget('ground', 'ground', 'ground', payload)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 800, 450)

    assert measure(widget, scale=1.0, limit=(800, 450)) == (800, 450)
    draw_scene(cairo.Context(surface), [(widget, (0, 0, 800, 450))], scale=1.0)
    surface.flush()

    def alpha(x, y):
        return surface.get_data()[round(y) * surface.get_stride() + round(x) * 4 + 3]

    near_x, near_y, near_on_screen = place_mark(1, 0, 800, 450, config)
    far_x, far_y, far_on_screen = place_mark(80, 0, 800, 450, config)
    assert (near_on_screen, far_on_screen) == (True, False)
    assert 0 < alpha(near_x, near_y) < 128  # the faint fill: the monster under it stays visible
    assert alpha(far_x, far_y) > 128  # the arrow towards it: easy to spot, unlike the mark under a monster
    assert alpha(5, 5) == 0

    far_leader = Widget('ground', 'ground', 'ground', {**payload, 'marks': [['leader', 90.0, 10.0]]})
    blank = cairo.ImageSurface(cairo.FORMAT_ARGB32, 800, 450)
    draw_scene(cairo.Context(blank), [(far_leader, (0, 0, 800, 450))], scale=1.0)
    blank.flush()
    assert not any(blank.get_data())  # a pack that far away gets no arrow
