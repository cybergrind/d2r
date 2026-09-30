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
