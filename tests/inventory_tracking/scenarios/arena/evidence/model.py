"""What the arena's monsters do at present, as numbers to lay beside the takes' (nothing is played:
each is read off the model's own parameters).

- a melee monster with its target in reach strikes with a roll under `aip3`, else stands `aip2`
  frames, and thinks again when the strike's STRIKE_FRAMES are over (combat/sim/monsters.py
  `Pack._think`; the row's `aidel` is read into `Traits.delay` and used nowhere). So in reach it
  swings GAME_RATE / (STRIKE_FRAMES + (100 - aip3) / aip3 x aip2) times a second, and every swing
  whose target is still within REACH at HIT_FRAME lands: no chance to hit, no block;
- its blow is a roll in `Traits.damage`, with each elemental enchantment's share on top;
- a ranged monster lands one shot every SHOT_FRAMES on a target within RANGED_REACH in a clear
  line (scenarios/arena/mobs.py `Horde._shoot`): no missile flies, none misses;
- what the character takes of either is cut by its weapon set's resistances: the main set's as
  cut.py MAIN has them (fire, cold and lightning at the cap, physical not known and let through whole);
- the sparks of a Lightning Enchanted monster: SPARKS_BEFORE is how they were played before they were
  fitted, `sparks` what the fit and the missile's row give now.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim.monsters import (
    CHAMPION_FLAG,
    ELEMENTS,
    HIT_FRAME,
    LIGHTNING,
    PHYSICAL,
    REACH,
    SPARK_MISSILE,
    STRIKE_FRAMES,
    SUPER_FLAG,
    UNIQUE_FLAG,
    Traits,
    Walker,
    fitted,
    spark_points,
)
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.macros.game.layout import MINION_FLAG
from tests.inventory_tracking.scenarios.arena.cut import MAIN
from tests.inventory_tracking.scenarios.arena.evidence.blows import CHAMPION, MINION, SUPER, UNIQUE
from tests.inventory_tracking.scenarios.arena.mobs import SHOT_FRAMES, SHOT_LANDS, is_ranged, shot_parts
from tests.inventory_tracking.scenarios.threat.harness import RANGED_REACH


FLAGS = {MINION: MINION_FLAG, CHAMPION: CHAMPION_FLAG, UNIQUE: UNIQUE_FLAG, SUPER: SUPER_FLAG}  # a rank's type flag
CONSTANTS = {
    'REACH': REACH,
    'STRIKE_FRAMES': STRIKE_FRAMES,
    'HIT_FRAME': HIT_FRAME,
    'SHOT_FRAMES': SHOT_FRAMES,
    'SHOT_LANDS': SHOT_LANDS,
    'RANGED_REACH': RANGED_REACH,
    'melee_hit_chance': 1.0,
    'shot_hit_chance': 1.0,
    'shots_per_second': GAME_RATE / SHOT_FRAMES,
}


def flags_of(rank: str) -> int:
    return FLAGS.get(rank, 0)


def swings_per_second(traits: Traits) -> float | None:
    """Swings a second of a melee monster that stays within reach of its target; None for one that
    never strikes."""
    if traits.strikes <= 0:
        return None
    chance = min(traits.strikes, 100) / 100
    return GAME_RATE / (STRIKE_FRAMES + (1 - chance) / chance * max(traits.idles, 1))


def taken(parts: Mapping[str, float], resist: Mapping[str, float] | None = None) -> float:
    """What the character loses of a blow's parts: each cut to the share its set lets through (a
    kind the set does not name: all of it), as mobs.py `Mobs.tick` does. Default: the main set."""
    resist = MAIN.resist if resist is None else resist
    return sum(points * resist.get(kind, 1.0) for kind, points in parts.items())


# The sparks of a Lightning Enchanted monster as sim/monsters.py played them before they were fitted
# (its constants at 34b2a79, 2026-10-12, from the Herald of Tower Cellar 5): what evidence/sparks.py and
# refit_check.py lay the takes and the refit against.
SPARKS_BEFORE: dict[str, Any] = {
    'ranks': ('plain', 'minion', 'champion', 'unique'),  # whoever carried the enchantment
    'count': 8,
    'chance': 0.33,  # of a release at a frame the monster is struck in
    'gap': 10,  # frames at least between two releases
    'frames': 77,
    'turn': 6,
    'contact': 2.0,
    'meets': 1.0,  # a spark within `contact` of the character ended on it
    'takes_life': 1.0,  # and took its points
}
# Struck in every frame, that model let sparks go every `gap` frames and the wait for the roll.
# evidence/refit_check.py `spark_plays` with that module (`git show 34b2a79:inventory_tracking/combat/sim/
# monsters.py`) against sparks.json's check half, 2026-10-12: what the spark rows' `before` is.
SPARKS_BEFORE['played'] = {
    'level': 75,
    'rate': 2.06,
    'per_release': 0.491,
    'per_release_bands': {'0-4': 3.2, '4-8': 1.022, '8-12': 0.599, '12-16': 0.42, '16-20': 0.348, '20-40': 0.217},
    'life': 29.65,
    'life_near': 130.15,
    'out': 27.9,
    'points': 37.2,
}
SPARKS_BEFORE['rate'] = round(
    GAME_RATE / (SPARKS_BEFORE['gap'] + (1 - SPARKS_BEFORE['chance']) / SPARKS_BEFORE['chance']), 2
)


# The model's swings as they were fitted on 2026-10-12, before a swing was told by how it ended
# (swings.py): one chance for every swing of half its length or more, struck or not, a share of swings
# cut short by a roll, the blow at the middle, a rest that made the measured rate, and no stagger.
SWINGS_BEFORE: dict[str, Any] = {'takes_life': 0.161, 'cut': 0.286, 'rest': 10.47, 'blow': 0.5, 'stagger': 0.0}


def sparks(level: int) -> dict[str, Any]:
    """The model's sparks at present, read off its parameters (data/monsters_fit.json `sparks` and the
    missile's row), with a spark's points at monster `level`, raw and as the main set takes them."""
    found = fitted()['sparks']
    raw = spark_points(level)
    return {
        'ranks': tuple(found['ranks']),
        'count': found['count']['value'],
        'rate': found['release']['rate']['value'],  # releases a second of being struck
        'window': found['release']['window'],
        'gap': found['release']['gap']['value'],
        'frames': found['flight']['frames']['value'],
        'turn': found['flight']['turn']['value'],
        'stride': float(tables()['missiles'][str(SPARK_MISSILE)]['Vel']) / GAME_RATE,
        'contact': found['contact'],
        'meets': found['meets']['value'],
        'takes_life': found['takes_life']['value'],
        'points_raw': raw,
        'points': round(taken({ELEMENTS[LIGHTNING]: raw}), 1),
    }


def blow(txt: int, level: int | None, flags: int = 0, mods: Sequence[int] = (), tier: int = 0) -> dict[str, Any]:
    """The model's melee blow of such a monster: the mean and the most, raw and as the main set takes
    them, with the swing rate in reach."""
    traits = Traits.of(txt, level or None, flags, tuple(mods), tier)
    least, most = traits.damage
    top = {PHYSICAL: most}
    middle = {PHYSICAL: (least + most) / 2}
    for element, low, high in traits.elements:
        top[element] = top.get(element, 0.0) + most * high
        middle[element] = middle.get(element, 0.0) + (least + most) / 2 * (low + high) / 2
    rate = swings_per_second(traits)
    return {
        'level': traits.level,
        'melee': traits.melee,
        'most_raw': round(sum(top.values()), 1),
        'most': round(taken(top), 1),
        'mean': round(taken(middle), 1),
        'swings_per_second': None if rate is None else round(rate, 3),
        'points_per_second': None if rate is None else round(rate * taken(middle), 1),
        'aip': [traits.walks, traits.idles, traits.strikes, traits.delay],
    }


def shot(txt: int, level: int | None, flags: int = 0, mods: Sequence[int] = (), tier: int = 0) -> dict[str, Any]:
    """The model's shot of such a monster, if the arena plays it as ranged (the threat table's flag):
    its points raw and as the main set takes them, one every SHOT_FRAMES."""
    walker = Walker(0, txt, 0.0, 0.0, level=level or None, flags=flags, mods=tuple(mods), tier=tier)
    parts = shot_parts(walker)
    for element, _low, high in walker.traits.elements:  # the most of an enchantment's part (mobs.py `_shot`)
        parts[element] = parts.get(element, 0.0) + parts.get(PHYSICAL, 0.0) * high
    rate = GAME_RATE / SHOT_FRAMES
    return {
        'level': walker.traits.level,
        'ranged': is_ranged(txt),
        'most_raw': round(sum(parts.values()), 1),
        'most': round(taken(parts), 1),
        'shots_per_second': rate,
        'points_per_second': round(rate * taken(parts), 1),
    }


def most(suspect: Mapping[str, Any]) -> float:
    """The heaviest blow the model lets this suspect of a drop (blows.py `by`) deal the main set: its
    shot if the arena plays the type as ranged, else its strike."""
    args = (suspect['txt'], suspect['level'], suspect['flags'], suspect['mods'] or (), suspect['tier'])
    return shot(*args)['most'] if is_ranged(suspect['txt']) else blow(*args)['most']
