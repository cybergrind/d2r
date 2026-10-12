"""Four hand-built arena scenes: the least a test of the arena or of a play needs, kept for later tasks.

All are in Durance of Hate Level 2 (area 101, the level of macros/test_pickup.py), with monsters of
that area's level and their type's life there (combat/mechanics/tables.py `points_of`, as the stance
and revivers harnesses give a body its points). The character is the one macros/routines.py
CHARACTERS (builds/characters.py) knows, with the fakes' two weapon sets and skill keys (macros/fakes.py).

What is assumed, not read from anything: the life (LIFE), and the resistances of the two sets. The
main set lets a quarter of each element through (the cap of 75); the teleport set lets 0.92 of
lightning and 0.82 of cold through (macros/hunt.py `tough`: "the teleport set leaves lightning at 8
and cold at 18 in Hell"). Nothing is taken off physical damage.
"""

from dataclasses import asdict

from inventory_tracking.builds.characters import CHARACTERS
from inventory_tracking.combat.mechanics.tables import points_of, tables
from inventory_tracking.levels.model import Walkable, pack_cells
from inventory_tracking.macros.world import FULL_REJUVENATION, SUPER_HEALING
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, OTHER_SET, PREBUFF_SET
from tests.inventory_tracking.scenarios.arena.game import POTIONS
from tests.inventory_tracking.scenarios.arena.scene import Drop, Hero, Mob, Scene, WeaponSet


AREA = 101
LEVEL = int(tables()['areas'][str(AREA)])  # the monster level of the area in Hell
NAME = next(iter(CHARACTERS))
HERE = (5020.0, 5020.0)
LIFE = 1800.0  # assumed
# txt ids, each a row of threat_table.json (test_mobs.py names the same ones)
HELL_BOVINE = 391  # melee, physical
RETURNED_ARCHER = 578  # ranged, physical and cold
GLOAM = 118  # ranged, lightning
MAIN = WeaponSet(PREBUFF_SET, {'fire': 0.25, 'cold': 0.25, 'lightning': 0.25})
STAFF = WeaponSet(OTHER_SET, {'fire': 0.25, 'cold': 0.82, 'lightning': 0.92}, teleport_charges=20)
BELT = (SUPER_HEALING, SUPER_HEALING, FULL_REJUVENATION, FULL_REJUVENATION) * 4  # as test_pickup.py FULL
EMPTY_BELT: tuple[int | None, ...] = (None,) * 16
SIDE = 8  # tiles of a walled scene's ground, from tile (1000, 1000): world 5000 to 5040


def hero(life: float = LIFE, *, hand: int = 0, belt: tuple[int | None, ...] = BELT, at=HERE) -> Hero:
    """The character with `life` of LIFE, the main set first and the teleport set second, `hand` in hand."""
    return Hero(NAME, at, AREA, life, LIFE, 500.0, 500.0, belt, (MAIN, STAFF), hand, HUNT_SLOTS, True, True, True)


def mob(unit: int, txt: int, dx: float, dy: float, **more) -> Mob:
    """A monster of the area's level `dx`, `dy` units from HERE, at its type's full life there."""
    full = points_of(txt, AREA)
    return Mob(unit, txt, (HERE[0] + dx, HERE[1] + dy), LEVEL, more.pop('life', full), full, **more)


def walled(barred) -> list[dict]:
    """A square of ground whose unit cells `barred(x, y)` (units from its corner) are walls, to walk
    and to fly (as test_mobs.py builds its walls)."""
    units = SIDE * TILE_UNITS
    cells = pack_cells(''.join('0' if barred(x, y) else '1' for y in range(units) for x in range(units)))
    return [asdict(Walkable(1000, 1000, SIDE, SIDE, cells, cells))]


def one_in_the_open() -> Scene:
    """One Hell Bovine twelve units off on open ground."""
    return Scene('one in the open', hero(), [mob(1, HELL_BOVINE, 12.0, 0.0)], [], [])


def pack_at_low_life() -> Scene:
    """Eight Hell Bovines in contact round a character with a sixth of its life and an empty belt."""
    ring = [(1.5, 0.0), (-1.5, 0.0), (0.0, 1.5), (0.0, -1.5), (1.1, 1.1), (-1.1, 1.1), (1.1, -1.1), (-1.1, -1.1)]
    mobs = [mob(1 + n, HELL_BOVINE, dx, dy) for n, (dx, dy) in enumerate(ring)]
    return Scene('a pack at low life', hero(LIFE / 6, belt=EMPTY_BELT), mobs, [], [])


def archer_behind_a_wall() -> Scene:
    """A Returned Archer fourteen units off behind a wall that ends ten units down: no shot either
    way until one of the two has gone round its end."""
    ground = walled(lambda x, y: x == 27 and y < 30)
    return Scene('an archer behind a wall', hero(), [mob(1, RETURNED_ARCHER, 14.0, -5.0)], ground, [])


def gloams() -> Scene:
    """Two Gloams eighteen units off, the teleport set in hand: the lightning comes through it."""
    mobs = [mob(1, GLOAM, 18.0, 0.0), mob(2, GLOAM, 16.0, 6.0)]
    return Scene('two gloams', hero(hand=1), mobs, [], [])


def potion_on_the_ground() -> Scene:
    """Nothing to fight: a super healing potion six units off and a belt short of one."""
    belt = (*BELT[:4], None, *BELT[5:])
    return Scene(
        'a potion on the ground',
        hero(belt=belt),
        [],
        [],
        [],
        drops=[Drop(50, POTIONS[SUPER_HEALING]['code'], (5026.0, 5016.0))],
    )


SCENES = (one_in_the_open, pack_at_low_life, archer_behind_a_wall, gloams)
