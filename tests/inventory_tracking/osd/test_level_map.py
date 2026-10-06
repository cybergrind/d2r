"""Level map card: payload round trip through the overlay, iso fit, and a real cairo render."""

import cairo
import pytest

from inventory_tracking.levels.model import pack_cells, pack_tiles
from inventory_tracking.osd.level_map import MapCard, MapPoi, draw_map, fit, project


CARD = MapCard(
    rooms=((0, 0, 12, 12), (12, 0, 12, 12), (0, 12, 12, 12)),
    player=(6.0, 6.0),
    pois=(MapPoi('Summoner', 'target', 18.0, 6.0), MapPoi('Waypoint', 'waypoint', 6.0, 18.0)),
    route=((6.0, 6.0), (18.0, 6.0)),
)


def test_payload_round_trips():
    assert MapCard.from_payload(CARD.to_payload()) == CARD


def test_malformed_map_payload_is_rejected():
    with pytest.raises(ValueError, match='map'):
        MapCard.from_payload({'map': {'rooms': 'x'}})


def test_iso_projection_matches_the_arrow_convention():
    # +x runs down-right, +y down-left: map east is screen right-and-down.
    assert project(1, 0) == (1, 0.5)
    assert project(0, -1) == (1, -0.5)


def test_fit_keeps_every_room_corner_inside_the_box():
    transform = fit(CARD, 240, 160, margin=10)

    corners = [(x + dx, y + dy) for x, y, w, h in CARD.rooms for dx in (0, w) for dy in (0, h)]
    for x, y in corners:
        sx, sy = transform(x, y)
        assert 10 - 1e-9 <= sx <= 230 + 1e-9
        assert 10 - 1e-9 <= sy <= 150 + 1e-9


def test_draw_map_renders_rooms_and_dots():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 160)

    draw_map(cairo.Context(surface), 240, 160, CARD)

    surface.flush()
    assert any(surface.get_data())  # something was painted


def test_card_without_route_still_round_trips_old_payloads():
    payload = CARD.to_payload()
    del payload['map']['route']

    assert MapCard.from_payload(payload).route == ()


def test_room_kinds_round_trip_and_default_to_plain_rooms():
    card = MapCard(((0, 0, 8, 8), (8, 0, 8, 8)), (4.0, 4.0), room_kinds=('edge', 'room'))
    payload = card.to_payload()

    assert MapCard.from_payload(payload) == card
    del payload['map']['room_kinds']
    assert MapCard.from_payload(payload).room_kinds == ()


def test_edge_rooms_are_drawn_darker_than_plain_rooms():
    card = MapCard(((0, 0, 8, 8), (8, 0, 8, 8)), (0.0, 16.0), room_kinds=('edge', 'room'))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 160)

    draw_map(cairo.Context(surface), 240, 160, card)

    surface.flush()
    transform = fit(card, 240, 160)

    def brightness(x, y):
        sx, sy = (round(v) for v in transform(x, y))
        b, g, r, _ = surface.get_data()[(sy * surface.get_stride()) + sx * 4 : (sy * surface.get_stride()) + sx * 4 + 4]
        return r + g + b

    assert brightness(4, 4) < brightness(12, 4)


def test_walkable_tiles_round_trip_and_default_to_none():
    card = MapCard(((0, 0, 8, 8),), (4.0, 4.0), walkable=((0, 0, 2, 1, '10'),))
    payload = card.to_payload()

    assert MapCard.from_payload(payload) == card
    del payload['map']['walkable']
    assert MapCard.from_payload(payload).walkable == ()


def test_walkable_tiles_are_drawn_lighter_than_rock():
    card = MapCard(((0, 0, 8, 8),), (0.0, 8.0), walkable=((0, 0, 8, 8, pack_tiles(('1' * 4 + '0' * 4) * 8, 8)),))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 160)

    draw_map(cairo.Context(surface), 240, 160, card)

    surface.flush()
    transform = fit(card, 240, 160)

    def brightness(x, y):
        sx, sy = (round(v) for v in transform(x, y))
        b, g, r, _ = surface.get_data()[(sy * surface.get_stride()) + sx * 4 : (sy * surface.get_stride()) + sx * 4 + 4]
        return r + g + b

    assert brightness(2, 4) > brightness(6, 4) + 60


def alpha(surface, x, y):
    surface.flush()
    return surface.get_data()[y * surface.get_stride() + x * 4 + 3]


def test_the_map_has_no_background_square():
    card = MapCard(((0, 0, 8, 8),), (4.0, 4.0))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 160)

    draw_map(cairo.Context(surface), 240, 160, card)

    assert alpha(surface, 1, 1) == 0  # corner outside the level diamond


def test_rock_in_rooms_with_known_walls_is_transparent():
    card = MapCard(((0, 0, 8, 8),), (0.0, 8.0), walkable=((0, 0, 8, 8, pack_tiles(('1' * 4 + '0' * 4) * 8, 8)),))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 160)

    draw_map(cairo.Context(surface), 240, 160, card)

    transform = fit(card, 240, 160)
    rock = tuple(round(v) for v in transform(6, 4))
    floor = tuple(round(v) for v in transform(2, 4))
    assert alpha(surface, *rock) == 0
    assert alpha(surface, *floor) > 0


def test_visited_rooms_round_trip_and_default_to_none():
    card = MapCard(((0, 0, 8, 8), (8, 0, 8, 8)), (4.0, 4.0), visited=(1, 0))
    payload = card.to_payload()

    assert MapCard.from_payload(payload) == card
    del payload['map']['visited']
    assert MapCard.from_payload(payload).visited == ()


def test_room_fill_dims_unvisited_rooms_slightly():
    from inventory_tracking.osd.level_map import ROOM_STYLES, room_fill

    base = ROOM_STYLES['room'][0]
    visited, unvisited = room_fill(base, True), room_fill(base, False)

    assert visited == base
    assert 0 < sum(visited) - sum(unvisited) < 0.5  # a slight difference


def pixel_at(surface, sx, sy):
    surface.flush()
    offset = sy * surface.get_stride() + sx * 4
    b, g, r, a = surface.get_data()[offset : offset + 4]
    return r, g, b, a


def pixel(surface, card, x, y):
    return pixel_at(surface, *(round(v) for v in fit(card, 240, 160)(x, y)))


def test_a_wall_one_sub_tile_thick_shows_as_a_gap_in_the_floor():
    # User, 2026-10-06: the thin walls of a Lower Kurast hut were missing from the map.
    wall_row = 12  # sub-tile row 12 of 40 is rock: y 2.4..2.6 tiles
    cells = pack_cells(''.join(('0' if row == wall_row else '1') * 40 for row in range(40)))
    card = MapCard(((0, 0, 8, 8),), (0.0, 8.0), walkable=((0, 0, 8, 8, cells),))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 960, 640)

    draw_map(cairo.Context(surface), 960, 640, card)

    transform = fit(card, 960, 640)
    assert alpha(surface, *(round(v) for v in transform(4, 2.5))) == 0
    assert alpha(surface, *(round(v) for v in transform(4, 2.0))) > 0
    assert alpha(surface, *(round(v) for v in transform(4, 3.0))) > 0


def test_unvisited_rooms_and_their_floor_are_drawn_dimmer():
    floor = pack_tiles('1' * 64, 8)
    for walkable in ((), ((0, 0, 8, 8, floor), (8, 0, 8, 8, floor))):
        card = MapCard(((0, 0, 8, 8), (8, 0, 8, 8)), (0.0, 16.0), walkable=walkable, visited=(0, 1))
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 160)

        draw_map(cairo.Context(surface), 240, 160, card)

        unvisited, visited = pixel(surface, card, 4, 4), pixel(surface, card, 12, 4)
        assert sum(unvisited) < sum(visited)


def test_monsters_are_small_dots_at_their_position_leaders_in_their_own_colour():
    from inventory_tracking.osd.level_map import KIND_COLOURS, KIND_RADII, MapPoi

    card = MapCard(
        ((0, 0, 16, 8),),
        (0.0, 8.0),
        pois=(MapPoi('monster', 'mob', 4.0, 4.0), MapPoi('unique', 'leader', 12.0, 4.0)),
    )
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 160)

    draw_map(cairo.Context(surface), 240, 160, card)

    mob, leader = pixel(surface, card, 4, 4), pixel(surface, card, 12, 4)
    assert mob[:3] == tuple(round(255 * c) for c in KIND_COLOURS['mob'])
    assert leader[:3] == tuple(round(255 * c) for c in KIND_COLOURS['leader'])
    assert KIND_RADII['mob'] < KIND_RADII['leader'] < KIND_RADII['herald']
    assert len({KIND_COLOURS[kind] for kind in ('mob', 'leader', 'herald')}) == 3
    # Leaders: bright magenta; plain mobs: a toned-down red; no rings (user, 2026-10-03).
    transform = fit(card, 240, 160)
    cx, cy = transform(12.0, 4.0)
    edge = pixel_at(surface, round(cx + KIND_RADII['leader']), round(cy))
    assert min(edge[:3]) < 200  # no white ring
    r, g, b = KIND_COLOURS['mob']
    assert r > max(g, b) + 0.2  # red
    assert r < 0.75  # muted
    assert sum(KIND_COLOURS['leader']) > sum(KIND_COLOURS['mob']) + 0.6  # magenta, bright


def test_herald_dots_have_their_own_colour():
    from inventory_tracking.osd.level_map import KIND_COLOURS

    assert KIND_COLOURS['herald'] not in [colour for kind, colour in KIND_COLOURS.items() if kind != 'herald']


def test_a_monster_dot_far_outside_the_level_does_not_shrink_the_map():
    # 2026-10-06, Far Oasis: a monster first seen at (0, 0), before it had a position, made the
    # whole level a speck in the middle of the card.
    stray = MapCard(CARD.rooms, CARD.player, (*CARD.pois, MapPoi('monster', 'mob', 0.0, -5000.0)))

    assert fit(stray, 240, 160)(18.0, 6.0) == fit(CARD, 240, 160)(18.0, 6.0)


BIG = MapCard(
    rooms=tuple((x, y, 8, 8) for x in range(0, 160, 8) for y in range(0, 80, 8)),
    player=(100.0, 40.0),
    pois=(MapPoi('Flayer Jungle', 'stairs', 62.0, 78.0), MapPoi('monster', 'mob', 101.0, 41.0)),
)


def test_a_big_level_is_drawn_around_the_player_at_the_least_scale():
    # 2026-10-06, Great Marsh: fitted to the card, the level was too small to tell monsters apart.
    transform = fit(BIG, 390, 270, min_scale=7, local_scale=12)

    assert transform(*BIG.player) == pytest.approx((195, 135))
    (ax, ay), (bx, by) = transform(100, 40), transform(101, 40)
    assert (bx - ax, by - ay) == pytest.approx((12, 6))
    # A level that fits at the least scale is laid out as before.
    assert fit(CARD, 390, 270, min_scale=7, local_scale=12)(18.0, 6.0) == fit(CARD, 390, 270)(18.0, 6.0)


def test_the_local_view_stops_at_the_level_edge():
    corner = MapCard(BIG.rooms, (1.0, 1.0))

    transform = fit(corner, 390, 270, min_scale=12, margin=10)

    assert transform(0, 0)[1] == pytest.approx(10)  # the level's top corner at the margin, not mid-card
    assert 10 <= transform(1.0, 1.0)[1] < 135


def test_pin_moves_a_point_outside_the_box_to_its_edge_towards_it():
    from inventory_tracking.osd.level_map import pin

    assert pin((195, 135), (200, 100), 390, 270, inset=9) == (200, 100, False)
    assert pin((195, 135), (995, 135), 390, 270, inset=9) == pytest.approx((381, 135, True))
    x, y, pinned = pin((195, 135), (-605, 935), 390, 270, inset=9)
    assert pinned
    assert (x, y) == pytest.approx((69, 261))  # leaves through the bottom, on the line to the point


def test_a_poi_beyond_the_local_view_is_an_arrowhead_on_the_edge_and_far_monsters_are_not_drawn():
    from inventory_tracking.osd.level_map import KIND_COLOURS

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 390, 270)
    far_pack = MapCard(BIG.rooms, BIG.player, (*BIG.pois, MapPoi('unique', 'leader', 150.0, 4.0)))

    draw_map(cairo.Context(surface), 390, 270, far_pack, min_scale=12)

    surface.flush()
    green = tuple(round(255 * c) for c in KIND_COLOURS['stairs'])
    leader = tuple(round(255 * c) for c in KIND_COLOURS['leader'])
    seen = {pixel_at(surface, x, y)[:3] for x in range(390) for y in range(270)}
    assert green in seen
    assert leader not in seen
    assert pixel_at(surface, 14, 135)[:3] == green  # the exit is due screen-left: mid left edge


def test_dangerous_packs_have_their_own_dot_colours_and_the_pack_point_is_not_drawn():
    from inventory_tracking.osd.level_map import KIND_COLOURS, KIND_RADII, MapPoi

    card = MapCard(
        ((0, 0, 16, 8),),
        (0.0, 8.0),
        pois=(
            MapPoi('monster', 'danger', 4.0, 4.0),
            MapPoi('monster', 'caution', 8.0, 4.0),
            MapPoi('Dark Ranger x8 · Fanaticism', 'pack', 12.0, 4.0),
            MapPoi('unique', 'elite', 4.0, 6.0),
        ),
    )
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 240, 160)

    draw_map(cairo.Context(surface), 240, 160, card)

    def rgb(kind):
        return tuple(round(255 * c) for c in KIND_COLOURS[kind])

    assert pixel(surface, card, 4, 4)[:3] == rgb('danger')
    assert pixel(surface, card, 8, 4)[:3] == rgb('caution')
    assert pixel(surface, card, 12, 4)[:3] not in (rgb('danger'), rgb('pack'), rgb('target'))
    assert len({KIND_COLOURS[kind] for kind in ('mob', 'leader', 'herald', 'danger', 'caution')}) == 5
    assert KIND_RADII['mob'] < KIND_RADII['caution'] <= KIND_RADII['danger']
    # A deadly pack's leader: the leader's colour inside the pack's, and the biggest monster dot.
    assert pixel(surface, card, 4, 6)[:3] == rgb('leader')
    x, y = (round(v) for v in fit(card, 240, 160)(4, 6))
    assert pixel_at(surface, x + round(KIND_RADII['elite']), y)[:3] != rgb('leader')
    assert KIND_RADII['elite'] > max(KIND_RADII['leader'], KIND_RADII['danger'])


def test_a_whole_card_keeps_the_fitted_level_and_the_local_view_is_fainter():
    from dataclasses import replace

    whole = replace(BIG, whole=True)
    assert MapCard.from_payload(whole.to_payload()).whole is True
    assert fit(whole, 390, 270, min_scale=7, local_scale=12)(100, 40) == fit(BIG, 390, 270)(100, 40)

    def floor_alpha(card):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 390, 270)
        draw_map(cairo.Context(surface), 390, 270, card, min_scale=7, local_scale=12)
        x, y = fit(card, 390, 270, min_scale=7, local_scale=12)(96.0, 44.0)  # inside a room, off every dot
        return pixel_at(surface, round(x), round(y))[3]

    assert 0 < floor_alpha(BIG) < floor_alpha(whole)  # user, 2026-10-06: too much colour when zoomed in
