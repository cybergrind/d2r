"""Ground marks: map tiles → game-window pixels, arrows for marks out of view, and which map dots get a mark."""

import pytest

from inventory_tracking.config import HudGroundConfig
from inventory_tracking.hud.ground import arrow_reach, arrow_shown, ground_marks, ground_payload, place_mark, project
from inventory_tracking.osd.level_map import MapCard, MapPoi


CONFIG = HudGroundConfig(
    player_x=0.5,
    player_y=0.5,
    tile_height=0.1,
    edge_inset=0.05,
    arrow_near=0.1,
    arrow_rest=0.3,
    arrow_hold=1.0,
    arrow_seconds=2.0,
)
SIZE = (2000, 1000)


def test_the_player_is_the_origin_and_the_axes_are_isometric():
    assert project(0, 0, *SIZE, CONFIG) == (1000, 500)
    assert project(1, 0, *SIZE, CONFIG) == (1100, 550)  # +x: down-right, 2:1
    assert project(0, 1, *SIZE, CONFIG) == (900, 550)  # +y: down-left
    assert project(1, 1, *SIZE, CONFIG) == (1000, 600)  # one whole tile diamond down


def test_a_mark_in_view_stays_where_it_projects():
    assert place_mark(2, 0, *SIZE, CONFIG) == (1200, 600, True)


@pytest.mark.parametrize(
    ('dx', 'dy', 'reach', 'expected'),
    [
        (20, -20, None, (1300, 500)),  # far right: on the resting ring, level with the player
        (-20, -20, None, (1000, 200)),  # far up
        (40, 0, None, (1268, 634)),  # down-right, along the 2:1 floor axis
        (20, -20, 0.1, (1100, 500)),  # just after entering the level: close to the player
    ],
)
def test_a_mark_beyond_the_view_becomes_an_arrow_on_a_ring_around_the_player(dx, dy, reach, expected):
    x, y, on_screen = place_mark(dx, dy, *SIZE, CONFIG, reach)

    assert (round(x), round(y), on_screen) == (*expected, False)


def test_the_arrow_ring_grows_from_near_the_player_to_its_resting_size_after_entering_a_level():
    assert arrow_reach(0.0, CONFIG) == 0.1
    assert arrow_reach(1.0, CONFIG) == 0.1  # held near the player first
    assert 0.1 < arrow_reach(1.25, CONFIG) < arrow_reach(1.75, CONFIG) < 0.3
    assert arrow_reach(2.0, CONFIG) == arrow_reach(99.0, CONFIG) == arrow_reach(None, CONFIG) == 0.3


def test_only_monsters_near_the_player_get_an_arrow_and_ways_on_always_do():
    config = HudGroundConfig(arrow_range={'leader': 30})

    assert arrow_shown('leader', 18, -24, config)  # 30 tiles away
    assert not arrow_shown('leader', 20, -24, config)
    assert arrow_shown('stairs', 200, 200, config)
    assert arrow_shown('herald', 200, 200, config)


def test_the_payload_names_the_level_by_its_rooms():
    dot = (MapPoi('Level 2', 'stairs', 6.0, 7.0),)
    here = ground_payload(MapCard(((0, 0, 8, 8),), (4.0, 4.0), dot), HudGroundConfig())
    moved = ground_payload(MapCard(((0, 0, 8, 8),), (5.0, 4.0), dot), HudGroundConfig())
    below = ground_payload(MapCard(((0, 0, 8, 8), (8, 0, 8, 8)), (4.0, 4.0), dot), HudGroundConfig())

    assert here['level'] == moved['level'] != below['level']


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


def test_a_dot_with_a_path_address_keeps_it_in_its_mark_and_on_the_map_card():
    card = MapCard(
        ((0, 0, 8, 8),),
        (4.0, 4.0),
        (MapPoi('unique', 'leader', 2.0, 3.0, 0x5000), MapPoi('Level 2', 'stairs', 6.0, 7.0)),
    )

    payload = ground_payload(card, HudGroundConfig())

    assert payload['marks'] == [['leader', 2.0, 3.0, 0x5000], ['stairs', 6.0, 7.0]]
    assert ground_marks(payload)[1] == [('leader', 2.0, 3.0), ('stairs', 6.0, 7.0)]
    assert MapCard.from_payload(card.to_payload()) == card


def test_a_malformed_payload_is_rejected():
    with pytest.raises(ValueError, match='Invalid ground payload'):
        ground_marks({'player': [1.0], 'marks': []})


def test_the_ground_payload_names_where_the_canvas_can_read_the_player():
    card = MapCard(((0, 0, 8, 8),), (4.0, 4.0), (MapPoi('unique', 'leader', 2.0, 3.0),), live=(4242, 0x7F00))

    assert ground_payload(card, HudGroundConfig())['live'] == [4242, 0x7F00]
    assert MapCard.from_payload(card.to_payload()).live == (4242, 0x7F00)
