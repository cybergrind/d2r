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
  cut.py MAIN has them (fire, cold and lightning at the cap, physical not known and let through whole).
"""

from collections.abc import Mapping, Sequence
from typing import Any

from inventory_tracking.combat.sim.monsters import (
    CHAMPION_FLAG,
    HIT_FRAME,
    PHYSICAL,
    REACH,
    STRIKE_FRAMES,
    SUPER_FLAG,
    UNIQUE_FLAG,
    Traits,
    Walker,
)
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.macros.world import MINION_FLAG
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
