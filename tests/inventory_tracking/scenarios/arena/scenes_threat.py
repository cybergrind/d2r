"""The 16 threat scenes (scenarios/threat/scenes.py) as arena scenes the production macro can be played in.

Every scene is built from the threat scene object itself (`SCENES` of the threat module, `.scene()`), so
the two stay in step; nothing is retyped. Open ground (no grids, no doors), the character at the threat
scene's origin with its life in the area the threat scene names.

What carries over from a threat `Hostile` to an arena `Mob`: `txt`, `at`, `life`, `full`, `immune`; `elite`
becomes the flags value the threat harness itself puts in `records` (`UNIQUE_FLAG`); the monster level is
the area's, as scenes_basic derives it (`LEVEL` is that of the basic scenes' area, here taken for the
scene's own area). What does NOT carry: `ranged`, `speed`, `blast` and `dps`, which the arena derives from
the monster type (mobs.py `is_ranged`, `explodes`, `shot_parts`, the walker's traits); nor a Herald's
`tier` (the threat scene gives a life and damage factor, the Mob a tier; the life carries in `full`).

`boost` other than 1.0 goes to the arena as an aura by unit (`auras()`, passed through `driver.play` and
`Arena` to `Mobs(scene, rng, auras=...)`).

The report compares, per hostile, what the arena derives with what the threat scene said, by playing one
such monster alone against a still character for `PROBE_SECONDS` (the rate) and reading mobs.py's own
tables (ranged, explodes).

Run `uv run --offline python -m tests.inventory_tracking.scenarios.arena.scenes_threat` to write
fixtures/THREAT-in-arena.md.
"""

import random
from dataclasses import replace
from functools import cache
from pathlib import Path

from inventory_tracking.combat.mechanics.tables import points_of, tables
from inventory_tracking.macros.runner import ATTACK
from inventory_tracking.takes.timeline import GAME_RATE
from tests.inventory_tracking.scenarios.arena.driver import Press, play
from tests.inventory_tracking.scenarios.arena.mobs import Mobs, explodes, is_ranged
from tests.inventory_tracking.scenarios.arena.result import Result, scorecard
from tests.inventory_tracking.scenarios.arena.scene import Mob, Scene
from tests.inventory_tracking.scenarios.arena.scenes_basic import LIFE, hero
from tests.inventory_tracking.scenarios.threat import harness as threat_harness
from tests.inventory_tracking.scenarios.threat.harness import TICKS, UNIQUE_FLAG, Hostile, today
from tests.inventory_tracking.scenarios.threat.scenes import SCENES, Spec
from tests.inventory_tracking.scenarios.threat.table import TERROR_LEVEL


FIXTURE = Path(__file__).parent / 'fixtures' / 'THREAT-in-arena.md'
PROBE_SECONDS = 20  # how long one monster is played alone to read its rate in the arena
MELEE_PROBE_GAP = 1.5  # units a melee probe starts from the character (scenes_basic's pack ring)
RANGED_PROBE_GAP = 10.0  # units a ranged probe stands from the character, inside RANGED_REACH
RATE_FACTOR = 2.0  # a rate is called a mismatch beyond this factor either way


def level_of(area: int) -> int:
    """The monster level of an area in Hell, as scenes_basic derives it for its own area."""
    return int(tables()['areas'][str(area)])


def mob_of(h: Hostile, area: int) -> Mob:
    """The arena monster for a threat `Hostile`: type, place, life, immunity and rank carry over."""
    return Mob(
        h.unit, h.txt, h.at, level_of(area), h.life, h.full,
        flags=UNIQUE_FLAG if h.elite else 0, immune=h.immune,
    )  # fmt: skip


def arena_scene(name: str, spec: Spec) -> Scene:
    """One threat scene as an arena scene on open ground."""
    source = spec.scene()
    base = hero(source.life, at=source.origin)
    # LIFE is the arena's maximum unless this scene starts with more.
    character = replace(base, area=source.area, max_life=max(LIFE, source.life))
    return Scene(name, character, [mob_of(h, source.area) for h in source.hostiles], [], [])


def threat_scenes() -> dict[str, Scene]:
    """Every threat scene as an arena scene, under the threat scene's name."""
    return {name: arena_scene(name, spec) for name, spec in SCENES.items()}


def horizons() -> dict[str, float]:
    """Each scene's horizon in seconds (the threat harness counts ticks, TICKS a second)."""
    return {name: spec.horizon / TICKS for name, spec in SCENES.items()}


def auras() -> dict[str, dict[int, float]]:
    """Scene name -> unit -> factor, for the scenes that have a booster. Not passed to the arena (no way to)."""
    found: dict[str, dict[int, float]] = {}
    for name, spec in SCENES.items():
        boosts = {h.unit: h.boost for h in spec.scene().hostiles if h.boost != 1.0}
        if boosts:
            found[name] = boosts
    return found


# --- what the arena derives, against what the threat scene said ----------------------------------------


@cache
def arena_rate(txt: int, elite: bool, area: int) -> float:
    """Points a second one such monster deals alone to a character standing still with no resistance,
    in the arena's own monsters, over PROBE_SECONDS."""
    ranged = is_ranged(txt)
    gap = RANGED_PROBE_GAP if ranged else MELEE_PROBE_GAP
    here = (5000.0, 5000.0)
    full = points_of(txt, area)
    mob = Mob(1, txt, (here[0] + gap, here[1]), level_of(area), full, full, flags=UNIQUE_FLAG if elite else 0)
    mobs = Mobs(Scene('probe', hero(at=here), [mob], [], []), random.Random(1))
    taken = sum(mobs.tick(here, [], {}) for _ in range(int(PROBE_SECONDS * GAME_RATE)))
    return taken / PROBE_SECONDS


def mismatches(spec: Spec) -> list[str]:
    """What the arena derives differently from the threat scene, one line per difference."""
    source = spec.scene()
    found: list[str] = []
    for h in source.hostiles:
        who = f'{h.name} (unit {h.unit}{", elite" if h.elite else ""})'
        if is_ranged(h.txt) != h.ranged:
            found.append(f'{who}: ranged in the threat scene {h.ranged}, in the arena {is_ranged(h.txt)}')
        if explodes(h.txt) != bool(h.blast):
            found.append(f'{who}: explodes in the threat scene {bool(h.blast)}, in the arena {explodes(h.txt)}')
        rate = arena_rate(h.txt, h.elite, source.area)
        if h.dps > 0 and not 1 / RATE_FACTOR <= rate / h.dps <= RATE_FACTOR:
            found.append(f'{who}: {h.dps:.0f} points a second in the threat scene, {rate:.0f} in the arena')
        elif h.dps == 0 and rate > 0:
            found.append(f'{who}: no damage in the threat scene, {rate:.0f} a second in the arena')
    if any(h.boost != 1.0 for h in source.hostiles):
        boosters = ', '.join(f'unit {h.unit} x{h.boost}' for h in source.hostiles if h.boost != 1.0)
        found.append(f'boost carried as an aura ({boosters})')
    level = level_of(source.area)
    if level != TERROR_LEVEL:
        found.append(
            f'monster level {level} (area {source.area}) in the arena; the threat scene is built at {TERROR_LEVEL}'
        )
    return found


# --- the plays and the report ----------------------------------------------------------------------------


def play_all() -> list[Result]:
    """Every scene played once, ATTACK pressed at 0, to its horizon."""
    scenes, until = threat_scenes(), horizons()
    given = auras()
    return [play(scene, [Press(0.0, ATTACK)], until[name], auras=given.get(name)) for name, scene in scenes.items()]


def threat_outcome(spec: Spec) -> tuple[bool, float, int, int, int]:
    """(alive, taken, kills, casts, hostiles) of the threat harness with today's controller."""
    source = spec.scene()
    result = threat_harness.run(source, today, spec.horizon)
    return result.alive, result.taken, len(result.kills), len(result.casts), len(source.hostiles)


def _word(alive: bool) -> str:
    return 'alive' if alive else 'dead'


def report() -> str:
    """The scorecard of the 16 plays, a paragraph per scene and the agreement table, as markdown."""
    results = play_all()
    lines = [
        '# Threat scenes in the arena',
        '',
        'Each of the 16 scenes of `scenarios/threat/scenes.py` converted by `scenes_threat.py` and played by the',
        "production macro (ATTACK pressed at 0.0 s, seed 1) to the scene's horizon. The threat harness column",
        'is `threat.harness.run(spec.scene(), today, spec.horizon)`, which never moves and only casts.',
        'The threat harness counts damage on past the death; the arena stops at it, so a dead arena play',
        "shows at most the character's life. A Herald's tier is not carried (only its life, in `full`); a",
        'boost is carried as an aura by unit. Rates are probed: one such monster alone, 20 s.',
        '',
        '```',
        scorecard(results),
        '```',
        '',
    ]
    rows: list[str] = []
    for result, (name, spec) in zip(results, SCENES.items(), strict=True):
        alive, taken, kills, casts, total = threat_outcome(spec)
        same = alive == result.alive
        swaps, pots, moved = result.swaps, len(result.potions), round(result.moved)
        lines += [
            f'## {name}',
            '',
            f'Threat harness: {_word(alive)}, {taken:.0f} taken, {kills}/{total} killed, {casts} casts. '
            f'Arena: {_word(result.alive)}'
            + (f' at {result.dead_at:.1f} s' if result.dead_at is not None else '')
            + f', {result.taken:.0f} taken, {len(result.kills)}/{total} killed, {result.casts} casts, '
            f'moved {moved} units, {swaps} swaps, {pots} potions, ran {result.seconds:.1f} s'
            + (f', cleared at {result.cleared_at:.1f} s' if result.cleared_at is not None else '')
            + f'. Direction: {"agree" if same else "differ"}.',
            '',
        ]
        found = mismatches(spec)
        lines += ['Conversion mismatches: ' + ('; '.join(found) if found else 'none') + '.', '']
        rows.append(
            f'| {name} | {_word(alive)}, {taken:.0f} taken, {kills}/{total} killed '
            f'| {_word(result.alive)}, {result.taken:.0f} taken, {len(result.kills)}/{total} killed '
            f'| {"yes" if same else "no"} |'
        )
    lines += [
        '## Agreement',
        '',
        '| scene | threat-harness outcome | arena outcome | same direction? |',
        '|---|---|---|---|',
        *rows,
        '',
    ]
    return '\n'.join(lines)


if __name__ == '__main__':
    FIXTURE.write_text(report(), encoding='utf-8')
