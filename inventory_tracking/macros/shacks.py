"""The shacks' other containers on the KP_6 chest run (routes/lower-kurast-loop-plan.md phase 6c).

The player: "yes, baskets/armor stands too. but do not hunt them, only if we encounter them in shacks and direct
visibility + close"; 2026-10-17: "maybe we need to interact only with interactables directly visible from
superchests within small radius".

So a container is a side goal only when the character and it stand in the same camp, closed, in sight, within REACH,
and within BY_CHEST of a chest spot in sight of it (in practice the weapon rack; rca/2026-10-16/loop-chests-findings.md
§5). The chest spots themselves are the route's. Pure: the hunt hands in what the game shows (choice.py `shack_goal`).
"""

import math
from collections.abc import Callable, Iterable, Sequence

from inventory_tracking.game.decode import usable
from inventory_tracking.game.records import Thing
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import UNIQUE_CHEST, Room
from inventory_tracking.levels.presets import PRESET_NAMES, object_spots
from inventory_tracking.native.layout import TILE_UNITS


__all__ = ['BY_CHEST', 'CAMP', 'OPENED', 'REACH', 'camps', 'shack_thing']

Block = tuple[int, int, int, int]  # a preset's x, y, width, height in tiles (`Room.block`)

CAMP = ('Act 3 - Slums 16x16', 1)  # the bonfire camp, preset name and DS1 variant (lower_kurast.py)
# Containers opened in a camp, by objects.txt id (classes seen in the camps on 2026-10-16)
OPENED = {
    181: 'Jungle chest',  # JungleChest
    183: 'Jungle chest',  # JungleChest2
    104: 'Armor stand',  # ArmorStand1
    106: 'Weapon rack',  # WeaponRack1
    107: 'Weapon rack',  # WeaponRack2
    208: 'Basket',  # Basket1
    209: 'Basket',  # Basket2
}
# Units: clicked from where the character stands (goals.py USE_NEAR), no move of its own
REACH = 25.0
BY_CHEST = 15.0  # units from a camp's chest spot, in sight of it
SPOT = 1.0  # units: a container this near a chest spot of the camp is that spot's, the route's own


def camps(rooms: Iterable[Room]) -> tuple[Block, ...]:
    """The camps among the level's rooms: the bounds of each bonfire camp preset, once."""
    name, variant = CAMP
    found = {
        room.block
        for room in rooms
        if room.block is not None and room.variant == variant and PRESET_NAMES.get(room.preset) == name
    }
    return tuple(sorted(found))


def _preset(rooms: Iterable[Room], block: Block) -> int | None:
    return next((room.preset for room in rooms if room.block == block), None)


def _inside(block: Block, at: Point) -> bool:
    x, y, width, height = block
    return x * TILE_UNITS <= at[0] < (x + width) * TILE_UNITS and y * TILE_UNITS <= at[1] < (y + height) * TILE_UNITS


def _chest_spots(rooms: Sequence[Room], block: Block) -> tuple[Point, ...]:
    preset = _preset(rooms, block)
    if preset is None:
        return ()
    x, y = block[0] * TILE_UNITS, block[1] * TILE_UNITS
    return tuple((x + dx, y + dy) for dx, dy in object_spots(preset, CAMP[1], UNIQUE_CHEST))


def shack_thing(
    things: Iterable[Thing],
    rooms: Sequence[Room],
    here: Point,
    seen: Callable[[Point, Point], bool],
    skip: frozenset[int] = frozenset(),
) -> tuple[Thing, str] | None:
    """The nearest container to open now, with its name, per the module rules; `seen(from, to)`: a clear line;
    `skip`: tried and not opened. None: not in a camp, or none qualifies."""
    camp = next((block for block in camps(rooms) if _inside(block, here)), None)
    if camp is None:
        return None
    spots = _chest_spots(rooms, camp)
    found = [
        thing
        for thing in things
        if thing.txt_id in OPENED
        and thing.unit_id not in skip
        and usable(thing)
        and _inside(camp, (thing.x, thing.y))
        and math.dist(here, (thing.x, thing.y)) <= REACH
        and not any(math.dist((thing.x, thing.y), spot) <= SPOT for spot in spots)
        and any(math.dist((thing.x, thing.y), spot) <= BY_CHEST and seen(spot, (thing.x, thing.y)) for spot in spots)
        and seen(here, (thing.x, thing.y))
    ]
    if not found:
        return None
    thing = min(found, key=lambda t: math.dist(here, (t.x, t.y)))
    return thing, OPENED[thing.txt_id]
