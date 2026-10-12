"""One moment of a recorded battle as an arena scene (framework-plan.md, Task 1.8; architecture.md
§6.2 C): the general form of scenarios/stance/build_fixtures.py `build`.

Where each field of a `Scene` comes from, checked against the takes of 2026-10-10, -11 and -12
(20261010T204733Z-25, 20261011T195037Z-25, 20261012T063030Z-115) and counted over all 743:

| Scene field | From | Otherwise |
| --- | --- | --- |
| `hero.at`, `area` | the frame's `p` row | no row: refused |
| `hero.life`, `max_life` | `p` (schema 2: whole points) | schema 1 (74 takes), or 0 of 0 (not read): refused |
| `hero.mana`, `max_mana` | `p` (schema 2) | most mana 0: the defaults', `mana` assumed |
| `hero.name` | the manifest's `character` (all takes) | the defaults', `name` assumed |
| `hero.left_skill`, `right_skill` | `p` (the skill on each mouse button) | - |
| `hero.hand` | the character's resistances (1) | the defaults', `hand` assumed |
| `hero.belt`, `sets`, `slots`, the buffs | not in a take (2) | the defaults', each assumed |
| mob `unit`, `txt`, `at`, `flags`, `mode`, `owner`, `ally` | the frame's `m` rows | - |
| mob `life` | the row's share of life (0-128) times `full` | share not read: full life, `life` assumed |
| mob `full` | not in a take: the type's points in the area (3) | no row of the type: `full` assumed |
| mob `level` | the unit's stat 12 at first sight (`units.jsonl`) | the area's level, `level` assumed |
| mob `tier` | the unit's stat 367 at first sight | no row of the unit: 0, `tier` assumed |
| mob `mods` | the unit's `mods` (`units.jsonl`), else the `mods` given (4) | none, `mods` assumed |
| mob `immune` | not in a take (the hunt learns it from casts that take nothing) | False, `immune` assumed |
| `ground`, `rooms` | the take's `level.json`, within `reach` of the character | refused (5) |
| `doors` | the frame's `d` rows (schema 2) | none |
| `drops` | not in a take | none, `drops` assumed |

(1) The set of the defaults whose resistances are nearest the character's own at the last `hurt`
    event before the frame (`resists`), else at the take's start (the manifest's `character_stats`).
    Only the takes since 2026-10-11 22:23 UTC hold either (35 of 743).
(2) The manifest's `slots` is the game's slot table (all takes), but with Echoing Strike on the right
    button and on no key; the arena's game is macros/fakes.py, which casts it from a key.
(3) The mean of the type's range at the area's level (mechanics/tables.py `points_of`), ELITE_LIFE
    times for a leader, as the stance harness gives a body its points, and with the life boost of
    its Herald's tier (the tables' `heralds`). A type without a monstats row has the area's base.
(4) A unit's stat list is there for 98.7% of the units, a tier on 57 units of 9 takes. `mods` are in
    `units.jsonl` since 2026-10-11 22:23 UTC (32 takes); before, they are looked up in the session's
    terror probe log (combat/hurts.py `enchantments`) and handed to `cut`.
(5) 27 takes have no level file. Also refused: a level file of another area than the character is
    in, and no ground within `reach`.

Which monsters: the hostiles alive within MOB_RANGE (the ground the scene keeps; a monster further
off has no ground to walk here), every companion of the character's wherever it is, and the corpses
within CORPSE_RANGE with their mode as recorded (Engorge is cast on a corpse). A companion's `life`
and `full` are the row's own numbers, not points: the arena does not hurt companions. Left out: a
row at (0, 0) (a unit without a place yet) and a live hostile with no life left (it dies in the next
frame).
"""

import gzip
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from inventory_tracking.builds.warlock.buffs import ENGORGE_REACH
from inventory_tracking.combat.mechanics.tables import area_level, monster_points, points_of, tables
from inventory_tracking.combat.record import RESIST_STATS
from inventory_tracking.combat.sim.monsters import MINION, PLAIN, rank_of
from inventory_tracking.combat.takes import MonsterRow, Take, monsters_of, player_of
from inventory_tracking.macros.rotation import ELITE_LIFE
from inventory_tracking.macros.routines import CHARACTERS, DEAD
from inventory_tracking.macros.world import FULL_REJUVENATION, HERALD_TIER_STAT, NO_OWNER, SUPER_HEALING
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.terror.monsters import LEVEL_STAT
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, OTHER_SET
from tests.inventory_tracking.scenarios.arena.scene import Hero, Mob, Scene, WeaponSet
from tests.inventory_tracking.scenarios.stance.build_fixtures import GROUND_RANGE


Point = tuple[float, float]
MOB_RANGE = GROUND_RANGE  # units: hostiles further from the character than the ground kept are left out
CORPSE_RANGE = 2 * ENGORGE_REACH  # units: a corpse in Engorge's reach from anywhere a reach from the start
# The resistances as the stat list holds them are before the Hell penalty of 100, and count up to the
# cap of 75 (combat/plan.md, the note of 2026-10-12 02:10).
HELL_PENALTY, CAP = 100, 75
KINDS = ('physical', 'fire', 'lightning', 'cold')  # RESIST_STATS in order, without poison (nothing here deals it)


def through(percent: float) -> float:
    """The share of damage a resistance of `percent` (in Hell, the penalty taken off) lets through."""
    return round(1.0 - min(percent, CAP) / 100, 2)


NAME = next(iter(CHARACTERS))  # the one character macros/routines.py knows
# The main set, as base codes (routines.py CHARACTERS: Heart of the Oak on a Flail and Spirit on a
# Monarch). Fire, cold and lightning "at the cap" (macros/hunt.py `Hunter.tough`; combat/plan.md
# 2026-10-12 02:10 has them 90/79/89 in Hell). Physical: not known for this set, so not named
# (the arena lets a kind a set does not name through whole).
MAIN = WeaponSet(
    tuple(sorted(CHARACTERS[NAME].battle)),
    {'fire': through(CAP), 'cold': through(CAP), 'lightning': through(CAP)},
)
# The other set: Naj's Puzzler, worn for its Teleport charges (routines.py, the comment on
# CHARACTERS; the base codes are macros/fakes.py OTHER_SET). Lightning 8 and cold 18 in Hell
# (`Hunter.tough`). Fire 54 and physical 10 are not in that docstring but in the stat lists it was
# written from (combat/plan.md 2026-10-12 01:45 and 02:10: fire 154, lightning 108, cold 118 before
# the penalty, physical 10, in the `character_stats` of 16 takes). 69 charges: the staff when full
# (macros/plan.md: "took the staff from 69 charges to none").
STAFF = WeaponSet(
    OTHER_SET,
    {'fire': through(54), 'cold': through(18), 'lightning': through(8), 'physical': through(10)},
    teleport_charges=69,
)
# What of the two sets nobody has read: the main set's physical resistance (10 on the staff's set, and
# no item of the main set is known to change it), and poison on both (no monster of the arena deals it).
UNKNOWN = ("the main set's physical resistance",)
# The character as far as the repo knows it. Its place, area, life and mana are a frame's and stand at
# nothing here. The belt is what the logs of 2026-10-11 showed (scenarios/battle/tower_cellar5.py BELT:
# full, healing potions in the third column, the first two taken as full rejuvenations). The skill keys
# are the fakes', with Echoing Strike on a key as since 2026-10-09. The three buffs are taken as up: the
# prebuff casts them (routines.py SKILLS) and the hunt keeps them.
DEFAULT_HERO = Hero(
    name=NAME,
    at=(0.0, 0.0),
    area=0,
    life=0.0,
    max_life=0.0,
    mana=0.0,
    max_mana=0.0,
    belt=(FULL_REJUVENATION, FULL_REJUVENATION, SUPER_HEALING, SUPER_HEALING) * 4,
    sets=(MAIN, STAFF),
    hand=0,
    slots=HUNT_SLOTS,
    hex_purge=True,
    ward=True,
    consume=True,
)
ALWAYS_ASSUMED = ('belt', 'sets', 'slots', 'hex_purge', 'ward', 'consume', 'drops', 'immune')


class Refused(ValueError):
    """A frame that cannot make a sound scene; `reason` is the kind of refusal, without the take and the numbers."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason


def level_of(take: Take) -> dict[str, Any] | None:
    """The take's level file (`area`, `rooms`, `ground`), plain or gzipped as a trim leaves it; None without one."""
    plain, packed = take.directory / 'level.json', take.directory / 'level.json.gz'
    if plain.exists():
        return json.loads(plain.read_text(encoding='utf-8'))
    if packed.exists():
        with gzip.open(packed, 'rt', encoding='utf-8') as handle:
            return json.load(handle)
    return None


def near(grids: Sequence[dict[str, Any]], origin: Point, reach: float = GROUND_RANGE) -> list[dict[str, Any]]:
    """The grids (or rooms) whose tile rectangle comes within `reach` units of `origin`, without their
    raw masks: scenarios/stance/build_fixtures.py `ground_near`, with the reach a parameter."""
    kept = []
    for grid in grids:
        x0, y0 = grid['x'] * TILE_UNITS, grid['y'] * TILE_UNITS
        x1, y1 = x0 + grid['width'] * TILE_UNITS, y0 + grid['height'] * TILE_UNITS
        dx = max(x0 - origin[0], 0.0, origin[0] - x1)
        dy = max(y0 - origin[1], 0.0, origin[1] - y1)
        if math.hypot(dx, dy) <= reach:
            kept.append({k: v for k, v in grid.items() if k != 'masks'})
    return kept


def resists_at(take: Take, t: float) -> list[int] | None:
    """The character's resistances (RESIST_STATS, as the stat list holds them) at the last reading up
    to time `t`: a `hurt` event's, else the manifest's at the take's start. None in a take without either."""
    found = None
    stats = take.manifest.get('character_stats')
    if stats:
        found = [int(stats.get(str(stat), 0)) for stat in RESIST_STATS]
    for event in take.events:
        if event['t'] > t:
            break
        if event['event'] == 'hurt' and event.get('resists'):
            found = [int(value) for value in event['resists']]
    return found


def hand_of(resists: Sequence[int], sets: Sequence[WeaponSet]) -> int:
    """The index of the set whose resistances are nearest the reading (a curse moves all of a reading
    one way, so the nearest still tells the two apart)."""
    shares = {kind: through(resists[index] - (HELL_PENALTY if index else 0)) for index, kind in enumerate(KINDS)}

    def apart(found: WeaponSet) -> float:
        return sum(
            abs(shares[kind] - share) for kind, share in found.resist.items() if kind in shares and kind != 'physical'
        )

    return min(range(len(sets)), key=lambda index: (apart(sets[index]), index))


def full_points(row: MonsterRow, area: int, tier: int = 0) -> float:
    """A monster's points at full life: its type's in the area (the mean of its range), ELITE_LIFE
    times for a leader, and with the life boost of the Herald's tier for a Herald (`life`) or one of
    its minions (`minion_life`), told apart by rank as sim/monsters.py `boost` does for the damage.
    For the tier 2 Herald of Tower Cellar 5 that is 4736.5 x 2 x 13.5 = 127,885 points, where the
    strikes of the take fit 105,800 (macros/plan.md, the baseline of scenarios/battle)."""
    full = points_of(row.txt, area) * (ELITE_LIFE if row.elite else 1.0)
    herald = tables()['heralds'].get(str(tier))
    if herald is not None:
        full *= 1 + herald['minion_life' if rank_of(row.flags) in (MINION, PLAIN) else 'life'] / 100
    return full


def cut(
    take: Take,
    frame: int,
    *,
    defaults: Hero,
    name: str | None = None,
    mods: Mapping[int, Sequence[int]] | None = None,
    reach: float = GROUND_RANGE,
) -> Scene:
    """The scene of frame `frame` (an index into `take.frames`). What a take does not hold is the
    `defaults`' and is named in the scene's `assumed`. `mods` (unit id -> monumod ids) are the
    enchantments of a take recorded before it held them (combat/hurts.py `enchantments`); `reach` is
    how far from the character ground and monsters are kept. A frame that cannot make a sound scene
    is refused with a ValueError that says why (`Refused`, whose `reason` is the kind)."""
    label = take.directory.name
    where = f'{label} frame {frame}'
    if not 0 <= frame < len(take.frames):
        raise Refused('no such frame', f'{label}: no frame {frame} (the take has {len(take.frames)})')
    row = take.frames[frame]
    player = player_of(row)
    if player is None:
        raise Refused('no character row', f'{where}: no character row')
    if take.schema < 2 or player.life is None or player.max_life is None:
        raise Refused('no vitals (schema 1)', f'{where}: no vitals (schema {take.schema})')
    if not player.max_life:
        raise Refused('vitals not read', f'{where}: vitals not read (life {player.life} of 0)')
    if player.life <= 0 or player.mode in DEAD:
        raise Refused('the character is dead', f'{where}: the character is dead')
    level = level_of(take)
    if level is None:
        raise Refused('no level file', f'{label}: no level file')
    if level.get('area') != player.area:
        found = level.get('area')
        raise Refused('another area', f'{where}: the character is in area {player.area}, the level file is of {found}')
    ground = near(level.get('ground', ()), player.at, reach)
    if not ground:
        raise Refused('no ground near', f'{where}: no ground within {reach:.0f} of the character')

    assumed = set(ALWAYS_ASSUMED)
    known = {unit['unit']: unit for unit in take.units}
    given = mods or {}
    area_lvl = area_level(player.area) or 0
    mobs: list[Mob] = []
    for monster in monsters_of(row):
        if monster.at == (0.0, 0.0):
            continue
        away = math.dist(monster.at, player.at)
        owner = None if monster.owner == NO_OWNER else monster.owner
        if monster.companion:
            mobs.append(
                Mob(monster.unit, monster.txt, monster.at, 0, float(monster.life), float(monster.max_life),
                    monster.flags, mode=monster.mode, owner=owner, ally=bool(monster.ally))
            )  # fmt: skip
            continue
        if owner is not None or monster.ally:
            continue  # a dead companion
        if monster.alive and (away > min(MOB_RANGE, reach) or (monster.max_life and not monster.life)):
            continue
        if not monster.alive and away > min(CORPSE_RANGE, reach):
            continue
        unit = known.get(monster.unit)
        stats = unit.get('stats', {}) if unit else {}
        level_seen = stats.get(str(LEVEL_STAT))
        if not level_seen:
            assumed.add('level')
        if unit is None:
            assumed.add('tier')
        if unit is not None and 'mods' in unit:
            found = tuple(unit['mods'])
        elif monster.unit in given:
            found = tuple(given[monster.unit])
        else:
            found = ()
            assumed.add('mods')
        if monster_points(monster.txt, player.area) is None:
            assumed.add('full')
        if monster.alive and not monster.max_life:
            assumed.add('life')
        tier = int(stats.get(str(HERALD_TIER_STAT), 0))
        full = full_points(monster, player.area, tier)
        mobs.append(
            Mob(
                monster.unit, monster.txt, monster.at,
                level=int(level_seen or area_lvl),
                life=round(full * monster.life_share, 1) if monster.alive else 0.0,
                full=full, flags=monster.flags, mods=found, tier=tier,
                mode=monster.mode,
            )
        )  # fmt: skip

    hero = replace(
        defaults,
        at=player.at,
        area=player.area,
        life=float(player.life),
        max_life=float(player.max_life),
        left_skill=player.left_skill,
        right_skill=player.right_skill,
    )
    if player.max_mana:
        hero = replace(hero, mana=float(player.mana or 0), max_mana=float(player.max_mana))
    else:
        assumed.add('mana')
    if take.manifest.get('character'):
        hero = replace(hero, name=take.manifest['character'])
    else:
        assumed.add('name')
    resists = resists_at(take, row['t'])
    if resists is None:
        assumed.add('hand')
    else:
        hero = replace(hero, hand=hand_of(resists, hero.sets))
    source = {'take': label, 'frame': frame, 't': round(row['t'] - take.frames[0]['t'], 3)}
    return Scene(
        name or f'{label}-{frame}',
        hero,
        mobs,
        ground,
        [list(door) for door in row.get('d', ())],
        near(level.get('rooms', ()), player.at, reach),
        [],
        tuple(sorted(assumed)),
        source,
    )
