"""Packs whose revivers raise them, played with the arena's rule REVIVERS_RAISE (game.py; combat/revivers.py
REVIVERS_FIRST, 2026-10-23): what the live fight of 2026-10-23 02:08:06-02:08:41 in Cold Plains was (session
20261022T223539Z-d878def0, JUMP_CLUSTER: 35 s, 15 jumps, 0 kills), built by hand, not cut.

- `fallen_herald`: a tier 5 Herald pack of Fallen (monstats 19 `fallen1`: the Herald a unique and FALLEN minions) with
  SHAMANS Fallen Shamans (58 `fallenshaman1`, Resurrect) among them, `back` units behind the Fallen, every one with
  the tier's life (combat/mechanics/life.py `tier_boost`), 20 units off in Cold Plains (area 3), the Defiler and the
  bound Urdar out beside the character, attack mode on;
- `unraveler_pack`: an Unraveler (103 `unraveler3`, Resurrect2) behind a pack of Burning Dead (skeleton4, the
  undead it raises) in Tal Rasha's Tomb, plain monsters, no Herald.

Every type is the production table's (combat/revivers.py, data/revivers.json), no id written from memory. The arena's
rules are those of a pack fight (herald.py RULES) and the raise.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.revivers [--seeds 20]
"""

import argparse
import statistics
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace

from inventory_tracking.combat import revivers
from inventory_tracking.combat.mechanics.life import tier_boost
from inventory_tracking.macros.hunting import revive
from tests.inventory_tracking.scenarios.arena.game import (
    BODIES_BLOCK,
    PET_POINTS,
    PETS_FIGHT,
    REVIVERS_RAISE,
    SIGIL_SLOWS,
)
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome, Situation, east, open_field
from tests.inventory_tracking.scenarios.revivers.table import raised, reviver


def area_of(monster_id: str, name: str) -> int:
    """The Hell area named `name` that spawns the reviver `monster_id` (levels.txt, by the scenarios' table)."""
    return next(a['area'] for a in reviver(monster_id)['areas'] if a['name'] == name)


SHAMAN = reviver('fallenshaman1')['txt']
FALLEN = raised('FallenShaman')['fallen1']
UNRAVELER = reviver('unraveler3')['txt']
BURNING_DEAD = raised('GreaterMummy')['skeleton4']
COLD_PLAINS = area_of('fallenshaman1', 'Cold Plains')
TOMB = area_of('unraveler3', "Tal Rasha's Tomb")
assert {FALLEN, SHAMAN} <= revivers.revivers()[SHAMAN].raises  # the production table agrees
assert BURNING_DEAD in revivers.revivers()[UNRAVELER].raises
URDAR, DEFILER = 189, 744  # herald.py's
TIER = 5
RULES = (SIGIL_SLOWS, PETS_FIGHT, BODIES_BLOCK, REVIVERS_RAISE)
SECONDS = 60.0
STAND = 20.0  # units from the pack: hunting/base.py OMEN_STAND


def fallen_herald(*, minions: int = 11, shamans: int = 3, back: float = 5.0, seconds: float = SECONDS) -> Situation:
    """The tier 5 Fallen Herald pack (the module text)."""
    situation = Situation.on(open_field(70), name='revivers-fallen-herald', area=COLD_PLAINS)
    situation.about = f'a tier 5 Fallen Herald, {minions} Fallen and {shamans} Fallen Shamans 20 off'
    situation.pack(FALLEN, 1 + minions, at=east(STAND), spread=5.0, rank='boss')
    situation.pack(SHAMAN, shamans, at=east(STAND + back), spread=3.0, rank='minion')
    mobs = []
    for mob in situation.scene.mobs:
        boost = tier_boost(mob.flags, TIER)
        mobs.append(replace(mob, tier=TIER, full=mob.full * boost, life=mob.life * boost))
    situation.scene.mobs = mobs
    situation.companions((1.5, -1.0), txt=DEFILER, life=PET_POINTS)
    situation.companions((-1.0, 1.5), txt=URDAR, life=PET_POINTS)
    situation.rules = RULES
    situation.seconds = seconds
    situation.assumed.update({
        'the pack': 'built by hand after the 02:08 Cold Plains fight of 2026-10-23, not cut from the take',
        'shamans': f'{shamans} Fallen Shamans {back} units behind the Fallen, minions of the Herald with its tier',
    })  # fmt: skip
    return situation.attack_mode(True)


def unraveler_pack(
    *, skeletons: int = 8, back: float = 6.0, champions: bool = False, seconds: float = SECONDS
) -> Situation:
    """The Unraveler behind its Burning Dead (the module text); `champions`: a champion pack of them, as the live
    LONG_FIGHT of 2026-10-23 02:23:53-02:24:41 (take 20261022T232258Z-72: an elite Burning Dead's pack with an
    Unraveler, 48 s, 43 strikes, 21 jumps; a Burning Dead's life 55 back to 125 of 128)."""
    situation = Situation.on(open_field(70), name='revivers-unraveler', area=TOMB)
    situation.about = f'an Unraveler {back} behind {skeletons} {"champion " if champions else ""}Burning Dead 18 off'
    situation.pack(BURNING_DEAD, skeletons, at=east(18.0), spread=4.0, rank='champion' if champions else 'plain')
    situation.pack(UNRAVELER, 1, at=east(18.0 + back), spread=0.0)
    situation.companions((1.5, -1.0), txt=DEFILER, life=PET_POINTS)
    situation.rules = RULES
    situation.seconds = seconds
    situation.assumed.update({'the pack': 'built by hand: an Unraveler behind its undead'})
    return situation.attack_mode(True)


def running(situation: Situation, *, beyond: float = 60.0) -> Situation:
    """`situation` as a level run plays it (the live fights were the loop's runs): a mark `beyond` units east, past the
    pack, and the pickup key at 0.5 s (runner.py: one press runs the level, leash FULL), so the run clears its way."""
    situation.mark('the way out', at=east(beyond))
    situation.presses = ((0.5, 'pickup'),)
    return situation


SITUATIONS: dict[str, Callable[[], Situation]] = {
    'fallen herald, shamans among the fallen': lambda: fallen_herald(back=0.0),
    'fallen herald, shamans 5 behind': fallen_herald,
    'unraveler': unraveler_pack,
    'unraveler, champion burning dead': lambda: unraveler_pack(champions=True),
    'run: fallen herald, shamans among the fallen': lambda: running(fallen_herald(back=0.0)),
    'run: fallen herald, shamans 5 behind': lambda: running(fallen_herald()),
    'run: fallen herald, shamans 10 behind': lambda: running(fallen_herald(back=10.0)),
    'run: unraveler': lambda: running(unraveler_pack()),
    'run: unraveler 10 behind': lambda: running(unraveler_pack(back=10.0)),
    'run: unraveler, champion burning dead': lambda: running(unraveler_pack(champions=True)),
}


@contextmanager
def first(on: bool, stand: bool | None = None) -> Iterator[None]:
    """combat/revivers.py REVIVERS_FIRST set to `on` and hunting/revive.py REVIVER_STAND to `stand` (None: `on`) for
    the plays within."""
    saved = revivers.REVIVERS_FIRST, revive.REVIVER_STAND
    revivers.REVIVERS_FIRST = on
    revive.REVIVER_STAND = on if stand is None else stand
    try:
        yield
    finally:
        revivers.REVIVERS_FIRST, revive.REVIVER_STAND = saved


@dataclass(frozen=True)
class Measures:
    """What a set of plays came to: deaths, the share cleared, time to clear (median of those cleared), kills a minute
    (each kill, a raised one killed again counted again), the units left dead at the end a minute (what lasts), and the
    casts."""

    plays: int
    deaths: int
    cleared: int
    clear_median: float | None
    kills_minute: float
    lasting_minute: float
    casts: float

    def row(self) -> str:
        clear = '-' if self.clear_median is None else f'{self.clear_median:.1f} s'
        return (
            f'{self.plays} plays, {self.deaths} deaths, cleared {self.cleared}, clear median {clear}, '
            f'{self.kills_minute:.1f} kills/min, {self.lasting_minute:.1f} lasting/min, {self.casts:.0f} casts'
        )


def measures(outcomes: Sequence[Outcome]) -> Measures:
    def minutes(o: Outcome) -> float:
        return max(o.seconds, 1e-9) / 60.0

    cleared = [o.cleared_at for o in outcomes if o.cleared_at is not None]
    return Measures(
        plays=len(outcomes),
        deaths=sum(o.dead for o in outcomes),
        cleared=len(cleared),
        clear_median=statistics.median(cleared) if cleared else None,
        kills_minute=statistics.mean(len(o.kills) / minutes(o) for o in outcomes),
        lasting_minute=statistics.mean((o.hostiles - o.alive) / minutes(o) for o in outcomes),
        casts=statistics.mean(len(o.strikes) for o in outcomes),
    )


def compare(build: Callable[[], Situation], seeds: Sequence[int]) -> tuple[Measures, Measures]:
    """(off, on): the situation played on `seeds` with REVIVERS_FIRST off, then on."""
    situation = build()
    found = []
    for on in (False, True):
        with first(on):
            found.append(measures([situation.play(seed=seed) for seed in seeds]))
    return found[0], found[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--seeds', type=int, default=20)
    args = parser.parse_args(argv)
    seeds = range(1, args.seeds + 1)
    for name, build in SITUATIONS.items():
        off, on = compare(build, seeds)
        print(f'{name}\n  off: {off.row()}\n  on:  {on.row()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
