"""Level map card: payload round trip through the overlay, iso fit, and a real cairo render."""

import cairo
import pytest

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
    card = MapCard(((0, 0, 8, 8),), (0.0, 8.0), walkable=((0, 0, 8, 8, ('1' * 4 + '0' * 4) * 8),))
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
    card = MapCard(((0, 0, 8, 8),), (0.0, 8.0), walkable=((0, 0, 8, 8, ('1' * 4 + '0' * 4) * 8),))
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


def test_unvisited_rooms_and_their_floor_are_drawn_dimmer():
    floor = ('1' * 8) * 8
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
