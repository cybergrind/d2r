"""The decision goldens' cases: one production decision each, over fixtures already in the tree.

This module is the only adapter between `decisions.json` and production code (framework-plan.md,
Task 0.2). When a later stage moves a decision or changes a signature, this file changes and the
stored outputs must not. Every case builds its own game and hunter, so no case sees another's state.

A stance fixture becomes the macro's `World` as the memory read gives one: the life as a share of 128
(scenarios/threat/harness.py `records`), an elite as a unique, the companions as the character's own
units; its `Ground` is the fixture's grids (scenarios/stance/harness.py `load`).
"""

import json
import math
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass, replace
from functools import cache
from pathlib import Path

from inventory_tracking.builds.warlock.buffs import Rotation
from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.combat.policy import REACH
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros import pickup, teleport, view
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.sight import in_reach
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import (
    DEFILER_CLASS,
    GOLD,
    NO_OWNER,
    VALUABLE,
    Drop,
    Loot,
    Monster,
    Player,
    Teleport as Staff,
    World,
)
from tests.inventory_tracking.macros import test_pickup as drops
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, WINDOW, Game, warlock
from tests.inventory_tracking.scenarios.loop.helpers import CHAMPION, foe
from tests.inventory_tracking.scenarios.navigation import harness as navigation
from tests.inventory_tracking.scenarios.stance import harness as stance
from tests.inventory_tracking.scenarios.threat import harness as threat
from tests.inventory_tracking.scenarios.threat.scenes import HELL_BOVINE, SCENES


STANCE_FIXTURES = Path(stance.__file__).parent / 'fixtures'
ASPECT = WINDOW[2] / WINDOW[3]  # the fakes' window: what `Run` reads as the focused window's rect
NOW = 100.0  # the fakes' clock in every case: late enough for "never cast" and "just cast" to differ
JUST = 0.1  # seconds ago a cast was made that is still in its delay
LONG = 90.0  # seconds ago: past every delay and distrust
CHARACTER = 1  # the player's unit id
# The staff the character wears: None is Teleport as its own skill (fakes.py `Game.staff`).
STAFFS: dict[str, Staff | None] = {
    'none': None,
    'hand69': Staff(69, 69, True),
    'hand15': Staff(15, 69, True),
    'hand14': Staff(14, 69, True),
    'hand10': Staff(10, 69, True),
    'hand9': Staff(9, 69, True),
    'hand0': Staff(0, 69, True),
    'away69': Staff(69, 69, False),  # in the other weapon set
}
STAND_VARIANTS = tuple((staff, warp) for staff in ('none', 'hand69', 'hand9') for warp in ('ready', 'delay'))
STEP_VARIANTS = (('hand69', 'ready'), ('hand9', 'ready'), ('hand9', 'delay'))
JUMP_STATES = ('ready', 'delay', 'failed', 'teleport-failed')


@dataclass(frozen=True)
class Case:
    name: str  # '<kind>:<fixture>:<variant>', unique
    run: Callable[[], object]  # JSON-serialisable output of one production decision


def plain(value: object) -> object:
    """`value` as JSON holds it: records as dicts, floats to 3 places, an infinity as 'inf'."""
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        if math.isinf(value):
            return 'inf' if value > 0 else '-inf'
        return round(value, 3) + 0.0  # no -0.0
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    raise TypeError(f'no JSON form for {type(value).__name__}')


# --- the games --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Moment:
    world: World
    ground: Ground


@cache
def moment(name: str) -> Moment:
    """One stance fixture as the world the macro reads and the ground under it."""
    scene = stance.load(STANCE_FIXTURES / f'{name}.json')
    assert scene.ground is not None, f'{name}: no grids'
    player = Player(CHARACTER, 'golden', 1, scene.area, scene.origin[0], scene.origin[1], False, right_skill=388)
    monsters = [
        Monster(
            b.unit, b.txt, 1, b.at[0], b.at[1], NO_OWNER, threat.UNIQUE_FLAG if b.elite else 0, False,
            max(round(128 * b.life), 1), 128,
        )
        for b in scene.bodies
    ]  # fmt: skip
    companions = [
        Monster(c['unit'], c['txt'], 1, float(c['at'][0]), float(c['at'][1]), CHARACTER, ally=True)
        for c in json.loads((STANCE_FIXTURES / f'{name}.json').read_text()).get('companions', ())
    ]
    world = World(True, (), 'golden', HUNT_SLOTS, player=player, monsters=(*monsters, *companions), doors=scene.doors)
    return Moment(world, scene.ground)


def stance_names() -> list[str]:
    return sorted(path.stem for path in STANCE_FIXTURES.glob('*.json'))


@cache
def threat_moment(name: str) -> Moment:
    """One threat scene as the world the macro reads, on a level with no walls read."""
    player, monsters = threat.records(SCENES[name].scene())
    return Moment(World(True, (), 'golden', HUNT_SLOTS, player=player, monsters=tuple(monsters)), Ground(()))


def hunting(world: World, staff: str = 'hand69', warp: str = 'ready'):
    """A fresh hunter, the fakes' game holding `world` and its `Run`, with the staff and the state of
    the jumps a variant names: Blade Warp 'ready', in its casting 'delay', 'failed' a moment ago, or
    Teleport failed ('teleport-failed')."""
    game = Game(world)
    game.clock.now = NOW
    game.staff = STAFFS[staff]
    hunter = Hunter(build=warlock(world))
    if warp == 'delay':
        hunter.travel.warped_at = NOW - JUST
    elif warp == 'failed':
        hunter.travel.jump_failed[BLADE_WARP] = NOW - JUST
    elif warp == 'teleport-failed':
        hunter.travel.jump_failed[TELEPORT] = NOW - JUST
    return hunter, game.run()


def reachable(hunter: Hunter, at: Moment) -> tuple[list[Monster], list[Monster]]:
    """(the hostiles the hunt goes for, the ones in the blades' reach), as hunt.py `fight` counts them."""
    player = at.world.player
    assert player is not None
    foes = hunter.foes(at.world, NOW)
    here = (player.x, player.y)
    return foes, [m for m in foes if in_reach(at.ground, here, (m.x, m.y), REACH, at.world.doors)]


# --- the decisions ----------------------------------------------------------------------------------------


def stand(name: str, staff: str, warp: str) -> object:
    at = moment(name)
    hunter, run = hunting(at.world, staff, warp)
    foes, _ = reachable(hunter, at)
    return plain(hunter.better_stand(at.world, foes, at.ground, ASPECT, run=run))


def step(name: str, staff: str, warp: str) -> object:
    """The sweep's look for a move; `fighting` as the fight has it: something is in reach."""
    at = moment(name)
    hunter, run = hunting(at.world, staff, warp)
    foes, near = reachable(hunter, at)
    return plain(hunter.next_step(run, at.world, foes, at.ground, ASPECT, fighting=bool(near)))


def aim(at: Moment) -> object:
    """Where the cast goes; None with nothing in reach (`choose` is asked only with something)."""
    hunter, _ = hunting(at.world)
    foes, near = reachable(hunter, at)
    if not near:
        return None
    return plain(hunter.choose(at.world, foes, near, at.ground, Viewport(ASPECT)))


def tough(name: str) -> object:
    at = moment(name)
    hunter, _ = hunting(at.world)
    return hunter.tough(at.world, reachable(hunter, at)[1])


def jumps(staff: str, state: str) -> object:
    world = moment(stance_names()[0]).world
    hunter, run = hunting(world, staff, state)
    return plain(hunter.travel.jumps(run, world))


@contextmanager
def corners(on: bool) -> Iterator[None]:
    """The aims beside the skill bar on or off (view.py `CORNERS`: on in the game, off under the
    scenarios' conftest), so a landing reads the same from the builder and from pytest."""
    before = view.CORNERS[0]
    view.CORNERS[0] = on
    teleport.way_for.cache_clear()
    try:
        yield
    finally:
        view.CORNERS[0] = before
        teleport.way_for.cache_clear()


def landing(name: str, far: bool, beside_the_bar: bool) -> object:
    situation = navigation.load(name)
    player = navigation.player(situation.area, x=situation.start[0], y=situation.start[1])
    target = situation.target
    with corners(beside_the_bar):
        way = teleport.way_for(target, situation.view, far)
        return plain(teleport.landing(target, player, way, situation.aspect))


# --- a stride toward a hostile, and the walked way round a wall ---

# The moments with hostiles in sight and none in reach from where the character stood: where the sweep
# asks `toward`. Named, not computed, so the list of cases does not move with the reach it tests.
QUIET_MOMENTS = (
    '20261010T204733Z-25-234739',
    '20261010T204733Z-25-234805',
    '20261010T204733Z-25-234807',
    '20261010T204733Z-25-234810',
    '20261010T205120Z-25-235126',
    '20261010T205314Z-21-235333',
    '20261010T205432Z-25-235451',
    '20261010T205557Z-22-235601',
    '20261010T205557Z-22-235612',
    '20261010T205629Z-23-235645',
    '20261010T205629Z-23-235652',
    '20261010T205658Z-24-235701',
    '20261010T205658Z-24-235706',
    '20261010T205658Z-24-235707',
    '20261010T205720Z-25-235731',
)
TOWARD_VARIANTS = tuple(
    (staff, warp) for staff in ('none', 'hand69', 'hand14', 'hand9', 'hand0') for warp in ('ready', 'delay')
)
# One hostile alone on a fixture's real ground, the character where it stood (known footing): the
# strides the recorded packs do not ask for. Units from the character: 18 leaves 4 to go (under
# JUMP_LEAST, walked), 24 and 34 a jump, 46 more than JUMP_REACH. At 3 of the 32 spots a wall in the
# line refuses the Blade Warp where Teleport still goes.
LONE_MOMENT = '20261010T204733Z-25-234739'
LONE_UNITS = (18, 24, 34, 46)
BEARINGS = 8
# Goals with footing and a wall in the straight line, as (units, bearing) from where the character stood.
WALLED_GOALS = {
    '20261010T205314Z-21-235321': (
        (14, 0), (14, 3), (14, 4), (20, 0), (20, 1), (20, 3), (20, 4), (20, 7), (26, 0),
        (26, 1), (26, 3), (26, 4), (26, 5), (26, 7), (32, 0), (32, 1), (32, 3), (32, 4),
    ),
    '20261010T205557Z-22-235612': ((14, 5), (14, 6), (20, 5), (20, 6), (26, 1), (26, 5), (26, 6), (32, 6)),
    '20261010T205557Z-22-235614': ((14, 2), (20, 2), (20, 5), (20, 6), (26, 2), (26, 6), (32, 2), (32, 6)),
}  # fmt: skip


def away(at: Moment, units: float, bearing: int) -> tuple[float, float]:
    """The point `units` from the character, `bearing` eighths of a turn round."""
    player = at.world.player
    assert player is not None
    angle = 2 * math.pi * bearing / BEARINGS
    return player.x + units * math.cos(angle), player.y + units * math.sin(angle)


def toward(name: str, staff: str, warp: str) -> object:
    """The stride toward the nearest of the moment's own hostiles."""
    at = moment(name)
    hunter, run = hunting(at.world, staff, warp)
    foes, _ = reachable(hunter, at)
    return plain(hunter.toward(run, at.world, foes, at.ground, ASPECT))


def toward_lone(units: int, bearing: int, staff: str, warp: str) -> object:
    at = moment(LONE_MOMENT)
    x, y = away(at, units, bearing)
    lone = Monster(900, 19, 1, x, y, NO_OWNER, 0, False, 128, 128)
    world = replace(at.world, monsters=(lone,))
    hunter, run = hunting(world, staff, warp)
    return plain(hunter.toward(run, world, [lone], at.ground, ASPECT))


def around(name: str, units: int, bearing: int, warp: str) -> object:
    """The move along the walked way to a goal behind a wall, the staff empty."""
    at = moment(name)
    hunter, run = hunting(at.world, 'hand0', warp)
    return plain(hunter.travel.around(run, at.world, at.ground, ASPECT, away(at, units, bearing)))


def stride_cases() -> list[Case]:
    found = []
    for staff, warp in TOWARD_VARIANTS:
        variant = f'staff-{staff}+warp-{warp}'
        for name in QUIET_MOMENTS:
            found.append(Case(f'toward:{name}:{variant}', lambda n=name, s=staff, w=warp: toward(n, s, w)))
        for units in LONE_UNITS:
            for bearing in range(BEARINGS):
                found.append(
                    Case(
                        f'toward:lone-{units}-units-bearing-{bearing}:{variant}',
                        lambda u=units, b=bearing, s=staff, w=warp: toward_lone(u, b, s, w),
                    )
                )
    for name, goals in WALLED_GOALS.items():
        for units, bearing in goals:
            for warp in ('ready', 'delay'):
                found.append(
                    Case(
                        f'around:{name}:goal-{units}-units-bearing-{bearing}+warp-{warp}',
                        lambda n=name, u=units, b=bearing, w=warp: around(n, u, b, w),
                    )
                )
    return found


# --- the casts under the strike (synthetic worlds) ---

ROTATION_AREA = 101  # as scenarios/loop/helpers.py `game`
COW_LEVEL = 39  # the Moo Moo Farm, as scenarios/threat/scenes.py has it
SEEN = {'present': True, 'absent': False, 'unknown': None}
CAST = {'never': None, 'just': JUST, '4s': 4.0, 'long': LONG}  # seconds since the last cast


def rotation_world(*monsters: Monster, area: int = ROTATION_AREA, **player) -> World:
    stand = replace(Player(CHARACTER, 'golden', 1, area, 5000.0, 5000.0, False), **player)
    return World(True, (), 'golden', HUNT_SLOTS, player=stand, monsters=tuple(monsters))


def since(ago: float | None) -> float:
    return -math.inf if ago is None else NOW - ago


def purge_due(state: str, cast: str, unseen: int) -> object:
    world = rotation_world(hex_purge=SEEN[state])
    hunter, run = hunting(world)
    Rotation(hunter.buffs).purged_at, Rotation(hunter.buffs).purges_unseen = since(CAST[cast]), unseen
    return Rotation(hunter.buffs).purge_due(run, world)


def ward_due(state: str, cast: str, unseen: int, fighting: bool) -> object:
    world = rotation_world(ward=SEEN[state])
    hunter, run = hunting(world)
    Rotation(hunter.buffs).warded_at, Rotation(hunter.buffs).wards_unseen = since(CAST[cast]), unseen
    return Rotation(hunter.buffs).ward_due(run, world, fighting=fighting)


PREY = {'plain': foe(7, 5010.0, 5000.0), 'champion': foe(7, 5010.0, 5000.0, CHAMPION)}


def sigil_due(prey: str, cast: str) -> object:
    target = PREY[prey]
    world = rotation_world(target)
    hunter, run = hunting(world)
    if CAST[cast] is not None:
        Rotation(hunter.buffs).sigiled[target.unit_id] = since(CAST[cast])
    return Rotation(hunter.buffs).sigil_due(run, target)


DEMONS: dict[str, tuple[Monster, ...]] = {
    'no-demon': (),
    'demon-whole': (Monster(20, DEFILER_CLASS, 1, 5004.0, 5000.0, CHARACTER, ally=True, life=100, max_life=100),),
    'demon-hurt': (Monster(20, DEFILER_CLASS, 1, 5004.0, 5000.0, CHARACTER, ally=True, life=60, max_life=100),),
    'demon-unread': (Monster(20, DEFILER_CLASS, 1, 5004.0, 5000.0, CHARACTER, ally=True),),
}


def engorge_due(demons: str, cast: str, corpses: bool) -> object:
    world = rotation_world(*DEMONS[demons])
    hunter, run = hunting(world)
    run.corpses = (lambda: ()) if corpses else None
    Rotation(hunter.buffs).engorged_at = since(CAST[cast])
    return Rotation(hunter.buffs).engorge_due(run, world)


def worth_a_mark(flags: int, life: int) -> object:
    """A Hell Bovine in the Moo Moo Farm: a champion at full life is the one monster here worth a mark."""
    target = foe(7, 5010.0, 5000.0, flags, HELL_BOVINE, life=life, max_life=128)
    world = rotation_world(target, area=COW_LEVEL)
    hunter, _ = hunting(world)
    return Rotation(hunter.buffs).worth_a_mark(world, target)


def due_cases() -> list[Case]:
    found = []
    for state in SEEN:
        for cast in ('never', 'just', '4s', 'long'):
            for unseen in (0, 2):
                name = f'{state}+cast-{cast}+unseen-{unseen}'
                found.append(Case(f'due:purge:{name}', lambda s=state, c=cast, u=unseen: purge_due(s, c, u)))
                for fighting in (False, True):
                    mode = 'fighting' if fighting else 'idle'
                    found.append(
                        Case(
                            f'due:ward:{name}+{mode}',
                            lambda s=state, c=cast, u=unseen, f=fighting: ward_due(s, c, u, f),
                        )
                    )
    for prey in PREY:
        for cast in ('never', 'just', 'long'):
            found.append(Case(f'due:sigil:{prey}+cast-{cast}', lambda p=prey, c=cast: sigil_due(p, c)))
    for demons in DEMONS:
        for cast in ('never', 'just', '4s', 'long'):
            found.append(Case(f'due:engorge:{demons}+cast-{cast}', lambda d=demons, c=cast: engorge_due(d, c, True)))
    found.append(
        Case('due:engorge:demon-hurt+cast-never+corpses-unread', lambda: engorge_due('demon-hurt', 'never', False))
    )
    for kind, flags in (('plain', 0), ('champion', CHAMPION)):
        for life in (128, 64, 8):
            found.append(Case(f'due:mark:{kind}+life-{life}', lambda f=flags, n=life: worth_a_mark(f, n)))
    return found


# --- the pickup step: the worlds of tests/inventory_tracking/macros/test_pickup.py, by its test ---

FAR_RUNE = Drop(60, 5060.0, 5000.0, 'Jah Rune', VALUABLE)
FAR_POTION = Drop(61, 5000.0 + pickup.POTION_UNITS + 1, 5000.0, 'a healing potion', drops.HEALING)
FAR_GOLD = Drop(61, 5040.0, 5000.0, '9000 gold', GOLD, (0, 0))
CHARM = Drop(70, 5008.0, 5003.0, 'Large Charm', VALUABLE, (1, 2))
NO_ROOM = ('##########',) * 4
ONE_CELL = ('##########', '#####.####', '##########', '##########')
NO_JUV_COLUMN = (drops.HP, drops.HP, drops.JUV, None) * 4
PICKUPS: dict[str, Loot] = {
    'valuable-before-potion-nearest-first': Loot((drops.HP_NEAR, FAR_RUNE, drops.RUNE), drops.SHORT_HP, 500, 1000),
    'potion-the-belt-misses': Loot((drops.HP_NEAR, drops.JUV_NEAR), drops.SHORT_HP, 1000, 1000),
    'potion-the-belt-has': Loot((drops.JUV_NEAR,), drops.SHORT_HP, 1000, 1000),
    'potions-full-belt': Loot((drops.HP_NEAR, drops.JUV_NEAR), drops.FULL, 1000, 1000),
    'potion-too-far': Loot((FAR_POTION,), drops.SHORT_HP, 400, 1000),
    'drink-for-healing': Loot((drops.HP_NEAR,), drops.FULL, 600, 1000),
    'drink-for-rejuvenation': Loot((drops.JUV_NEAR,), drops.FULL, 600, 1000),
    'not-hurt-enough-to-drink': Loot((drops.HP_NEAR,), drops.FULL, 800, 1000),
    'life-unreadable': Loot((drops.HP_NEAR,), drops.FULL, 0, 0),
    'rune-no-room': Loot((drops.RUNE,), drops.FULL, 1000, 1000, NO_ROOM),
    'rune-and-charm-one-cell': Loot((drops.RUNE, CHARM), drops.FULL, 1000, 1000, ONE_CELL),
    'charm-one-cell': Loot((CHARM,), drops.FULL, 1000, 1000, ONE_CELL),
    'charm-room-unread': Loot((CHARM,), drops.FULL, 1000, 1000, None),
    'potion-with-no-room': Loot((drops.RUNE, drops.HP_NEAR), drops.SHORT_HP, 1000, 1000, NO_ROOM),
    'gold-before-potion': Loot((drops.PILE, FAR_GOLD, drops.JUV_NEAR), NO_JUV_COLUMN, 1000, 1000),
    'valuable-before-gold': Loot((drops.PILE, drops.RUNE)),
    'gold-too-far': Loot((FAR_GOLD,)),
    'gold-with-no-room': Loot((drops.PILE,), room=NO_ROOM),
}


def picked(name: str) -> object:
    return plain(pickup.choose(PICKUPS[name], drops.ORIGIN))


# --- all of them ------------------------------------------------------------------------------------------


def cases() -> list[Case]:
    found: list[Case] = []
    for name in stance_names():
        for staff, warp in STAND_VARIANTS:
            found.append(
                Case(f'stand:{name}:staff-{staff}+warp-{warp}', lambda n=name, s=staff, w=warp: stand(n, s, w))
            )
        for staff, warp in STEP_VARIANTS:
            found.append(Case(f'step:{name}:staff-{staff}+warp-{warp}', lambda n=name, s=staff, w=warp: step(n, s, w)))
        found.append(Case(f'aim:{name}:-', lambda n=name: aim(moment(n))))
        found.append(Case(f'tough:{name}:-', lambda n=name: tough(n)))
    for name in SCENES:
        found.append(Case(f'aim:threat-{name}:-', lambda n=name: aim(threat_moment(n))))
    for staff in STAFFS:
        for state in JUMP_STATES:
            found.append(Case(f'jumps:synthetic:staff-{staff}+warp-{state}', lambda s=staff, w=state: jumps(s, w)))
    for name in navigation.names():
        for far in (False, True):
            for bar in (True, False):
                variant = f'{"far" if far else "near"}+corners-{"on" if bar else "off"}'
                found.append(Case(f'landing:{name}:{variant}', lambda n=name, f=far, b=bar: landing(n, f, b)))
    found += stride_cases()
    found += due_cases()
    for name in PICKUPS:
        found.append(Case(f'pickup:{name}:-', lambda n=name: picked(n)))
    return found
