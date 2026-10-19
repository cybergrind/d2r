"""The shacks' other containers on the KP_6 loop's chest run (routes/lower-kurast-loop-plan.md phase 6c).

The card marks a camp's three chest spots (levels/handlers/lower_kurast.py). In the five camps of the games of
2026-10-16 (rca/2026-10-16/loop-chests-findings.md §5) each camp also held, fixed by its file, a weapon rack at
(48, 12) and an armor stand at (12, 23) of the camp, and in some a rolled jungle chest or four baskets; the loop left
every one of them closed. The player: "we should loot other random chests in these two shacks + weapon rack", then
"yes, baskets/armor stands too. but do not hunt them, only if we encounter them in shacks and direct visibility +
close".

So one is opened only when the character stands in a camp and the container stands in the same camp, closed, in
sight and within REACH: a side goal of the run, as a drop on the way is, never a place gone to for its own sake. The
camp's chest spots are the card's marks, opened as the route's stage, and are left to it. Pure: the hunt hands in
what the game shows (hunting/choice.py `shack_goal`).

And only one beside a chest (2026-10-17, the player: "we often diverge from our activities to interact with baskets
well outside the shacks, maybe we need to interact only with interactables directly visible from superchests within
small radius"): within BY_CHEST of one of the camp's chest spots, with a clear line from that spot. In the camp's file
that is the weapon rack (12 units from the chest at (60, 12)); the armor stand (32 to 34 units), the rolled baskets
(27 to 29) and jungle chests (25 to 35) are left (rca/2026-10-16/loop-chests-findings.md §5).
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
# The containers opened in a camp, by objects.txt id: the classes the takes of 2026-10-16 showed in the camps, named
# as macros/data/containers.json (the installed game's objects.txt) names them
OPENED = {
    181: 'Jungle chest',  # JungleChest
    183: 'Jungle chest',  # JungleChest2
    104: 'Armor stand',  # ArmorStand1
    106: 'Weapon rack',  # WeaponRack1
    107: 'Weapon rack',  # WeaponRack2
    208: 'Basket',  # Basket1
    209: 'Basket',  # Basket2
}
# Units: a container this near is clicked from where the character stands (goals.py USE_NEAR), so none costs a move
# of its own. From the camp's three chest spots it reaches the rack (12 units) and most of the rest (25 to 35).
REACH = 25.0
BY_CHEST = 15.0  # units from a camp's chest spot, in sight of it: a container beside the chest (the module text)
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
    """The container of the camp the character stands in to open now, with its name: closed (`usable`), in the same
    camp, within REACH, in sight (`seen(from, to)`: a clear line from the character), within BY_CHEST of one of the
    camp's chest spots and in sight of it, not at one of them and not in `skip` (tried and not opened); the nearest of
    them. None: the character is in no camp, or none is."""
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
