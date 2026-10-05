"""Ground marks: map tiles → game-window pixels, edge clamping, and which map dots get a mark."""

import pytest

from inventory_tracking.config import HudGroundConfig
from inventory_tracking.hud.ground import ground_marks, ground_payload, place_mark, project
from inventory_tracking.osd.level_map import MapCard, MapPoi


CONFIG = HudGroundConfig(player_x=0.5, player_y=0.5, tile_height=0.1, edge_inset=0.05)
SIZE = (2000, 1000)


def test_the_player_is_the_origin_and_the_axes_are_isometric():
    assert project(0, 0, *SIZE, CONFIG) == (1000, 500)
    assert project(1, 0, *SIZE, CONFIG) == (1100, 550)  # +x: down-right, 2:1
    assert project(0, 1, *SIZE, CONFIG) == (900, 550)  # +y: down-left
    assert project(1, 1, *SIZE, CONFIG) == (1000, 600)  # one whole tile diamond down


def test_a_mark_in_view_stays_where_it_projects():
    assert place_mark(2, 0, *SIZE, CONFIG) == (1200, 600, True)


@pytest.mark.parametrize(
    ('dx', 'dy', 'expected'),
    [
        (20, -20, (1950, 500)),  # far right: on the right inset, level with the player
        (-20, -20, (1000, 50)),  # far up
        (40, 0, (1900, 950)),  # down-right: leaves through the bottom first
    ],
)
def test_a_mark_beyond_the_view_is_pulled_to_the_window_edge_towards_it(dx, dy, expected):
    x, y, on_screen = place_mark(dx, dy, *SIZE, CONFIG)

    assert (round(x), round(y), on_screen) == (*expected, False)


def test_only_the_configured_kinds_of_map_dots_get_a_ground_mark():
    card = MapCard(
        ((0, 0, 8, 8),),
        (4.0, 4.0),
        (
            MapPoi('monster', 'mob', 1.0, 1.0),
            MapPoi('unique', 'leader', 2.0, 3.0),
            MapPoi('Level 2', 'stairs', 6.0, 7.0),
        ),
    )

    payload = ground_payload(card, HudGroundConfig(kinds=('leader', 'stairs')))

    assert ground_marks(payload) == ((4.0, 4.0), [('leader', 2.0, 3.0), ('stairs', 6.0, 7.0)])
    assert ground_payload(card, HudGroundConfig(kinds=('herald',))) is None
    assert ground_payload(card, HudGroundConfig(enabled=False)) is None


def test_a_malformed_payload_is_rejected():
    with pytest.raises(ValueError, match='Invalid ground payload'):
        ground_marks({'player': [1.0], 'marks': []})


def test_the_ground_payload_names_where_the_canvas_can_read_the_player():
    card = MapCard(((0, 0, 8, 8),), (4.0, 4.0), (MapPoi('unique', 'leader', 2.0, 3.0),), live=(4242, 0x7F00))

    assert ground_payload(card, HudGroundConfig())['live'] == [4242, 0x7F00]
    assert MapCard.from_payload(card.to_payload()).live == (4242, 0x7F00)
