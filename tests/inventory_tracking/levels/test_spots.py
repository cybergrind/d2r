"""Marks on the warp itself (the preset's DS1 warp tiles, levels/data/preset_warps.json) instead of
the room centre; arriving by stairs puts the player next to the way-back warp."""

import math

import pytest

from inventory_tracking.levels.geometry import pointer
from inventory_tracking.levels.level_map import build_map
from inventory_tracking.levels.model import LevelSnapshot, Location, Poi, Room
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.levels.spots import pinpoint
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.levels.fixtures import replay


@pytest.mark.parametrize('name', ['jail_2', 'jail_3', 'catacombs_3', 'worldstone_keep_3'])
def test_the_way_back_is_marked_where_the_player_arrived(name):
    snapshot = replay(name)
    guidance = handler_for(snapshot.location.area_id).guide(snapshot)
    [back] = [pinpoint(poi) for poi in guidance.pois if poi.kind == 'previous']
    px, py = snapshot.location.x / TILE_UNITS, snapshot.location.y / TILE_UNITS

    assert back.spot is not None
    assert math.dist(back.spot, (px, py)) < 1.5  # tiles
    centre = (back.room.x + back.room.width / 2, back.room.y + back.room.height / 2)
    assert math.dist(centre, (px, py)) > math.dist(back.spot, (px, py))


CAVE_ENTRANCE = 51  # 'Act 1 - Cave Entrance': CaveDr1.ds1 (variant 0) warp tile (3, 4), CaveDr2.ds1 the same


def test_the_spot_is_the_warp_tile_centre_from_the_preset_origin():
    room = Room(CAVE_ENTRANCE, 100, 200, 8, 8, 0, (100, 200, 8, 8))

    assert pinpoint(Poi('Cave', room, 'stairs')).spot == (103.5, 204.5)


def test_without_a_known_variant_or_a_single_warp_there_is_no_spot():
    unknown = Room(CAVE_ENTRANCE, 100, 200, 8, 8, None, None)
    graveyard = Room(108, 0, 0, 24, 32, 0, (0, 0, 24, 32))  # 'Act 1 - Graveyard': two warps

    assert pinpoint(Poi('Cave', unknown, 'stairs')).spot is None
    assert pinpoint(Poi('Crypt', graveyard, 'stairs')).spot is None


@pytest.mark.parametrize('name', ['halls_of_vaught_nihle', 'halls_of_vaught_nihlw'])
def test_a_boss_in_a_preset_with_a_warp_keeps_its_place(name):
    # Nihlathak's 'Temple Final Room' also holds the way back; the handler puts him across it.
    snapshot = replay(name)
    [boss] = handler_for(snapshot.location.area_id).guide(snapshot).pois

    assert pinpoint(boss) == boss


def test_an_entrance_kept_as_a_target_is_marked_on_its_warp():
    # Crystalline Passage: Anya's Frozen River is a side trip (target colour) behind 'Ice Down W'
    # (1026, DS1 variant 0: slot 2 at 10.0, 5.5).
    entrance = Room(1026, 300, 400, 16, 16, 0, (300, 400, 16, 16))
    snapshot = LevelSnapshot(Location(113, 0, 0, 0), (entrance,))

    [river] = [poi for poi in handler_for(113).guide(snapshot).pois if poi.label == 'Frozen River']

    assert (river.kind, river.spot) == ('target', (310.0, 405.5))


def test_arrows_and_map_dots_aim_at_the_spot():
    room = Room(CAVE_ENTRANCE, 100, 200, 8, 8, 0, (100, 200, 8, 8))
    poi = pinpoint(Poi('Cave', room, 'stairs'))
    location = Location(3, 0, 500, 1000)

    arrow = pointer(poi, location)
    card = build_map(LevelSnapshot(location, (room,)), [poi])

    assert (arrow.dx, arrow.dy) == (103.5 * TILE_UNITS - 500, 204.5 * TILE_UNITS - 1000)
    assert (card.pois[0].x, card.pois[0].y) == (103.5, 204.5)
