"""Game-window-relative slots → canvas pixel boxes."""

import pytest

from inventory_tracking.hud.layout import GameRect, Slot, game_rect, place, scale_for, slot_limit
from inventory_tracking.hud.scene import Widget


def test_tiled_game_sits_at_the_bottom_left_of_the_working_area():
    # niri reports no position for tiled windows; same assumption as the repair mark.
    assert game_rect((2560, 1422), window_size=(1920, 1182), position=None) == GameRect(0, 240, 1920, 1182)


def test_floating_game_uses_its_reported_position():
    assert game_rect((2560, 1422), window_size=(1600, 900), position=(300.0, 120.5)) == GameRect(300, 120, 1600, 900)


def test_no_game_window_means_no_rect():
    assert game_rect((2560, 1422), window_size=None, position=None) is None


@pytest.mark.parametrize(('height', 'expected'), [(1422, 1.0), (711, 0.6), (5000, 2.0), (1066.5, 0.75)])
def test_scale_follows_window_height_within_bounds(height, expected):
    assert scale_for(height, reference_height=1422) == pytest.approx(expected)


def test_slot_fractions_map_into_the_game_window_and_stack():
    rect = GameRect(100, 200, 1000, 800)
    slots = {'guide': Slot(0.1, 0.25)}
    widgets = [Widget('a', 'guide', 'guide', {}), Widget('b', 'guide', 'guide', {}), Widget('c', 'x', 'nowhere', {})]
    sizes = {'a': (300, 120), 'b': (200, 50), 'c': (10, 10)}

    boxes = place(widgets, sizes, slots, rect, gap=8)

    assert boxes == [(widgets[0], (200, 400, 300, 120)), (widgets[1], (200, 528, 200, 50))]  # unknown slot skipped


def test_a_slot_near_the_bottom_keeps_its_widget_inside_the_game_window():
    rect = GameRect(0, 0, 1000, 800)

    [(_, box)] = place([Widget('a', 'k', 's', {})], {'a': (300, 200)}, {'s': Slot(0.9, 0.95)}, rect)

    x, y, w, h = box
    assert x + w <= 1000
    assert y + h <= 800


def test_slot_limit_is_the_room_left_in_the_game_window_capped_by_max_width():
    rect = GameRect(100, 200, 1000, 800)

    assert slot_limit(Slot(0.2, 0.25), rect) == (800, 600)
    assert slot_limit(Slot(0.2, 0.25, max_width=0.45), rect) == (450, 600)


def test_a_centred_slot_puts_the_middle_of_its_widgets_on_its_x():
    rect = GameRect(100, 200, 1000, 800)
    slot = Slot(0.5, 0.02, centered=True)

    [(_, box)] = place([Widget('a', 'k', 's', {})], {'a': (300, 200)}, {'s': slot}, rect)

    assert box == (450, 216, 300, 200)
    assert slot_limit(slot, rect) == (1000, 784)
