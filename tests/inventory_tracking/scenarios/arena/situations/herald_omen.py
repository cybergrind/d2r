"""Herald fights from their omen (2026-10-23, rca/2026-10-23/omen-opening-findings.md): the heraldspawner missile
(737, macros/hunting/base.py HERALD_OMEN) in the arena's missiles before the pack shows, as in the game.

The takes of 2026-10-21..23 (350 omens with a pack): the pack shows a median 5.00 s after the omen's first frame
(p05 4.95, p95 5.04), every member in the same frame, a median 3.6 units from the omen's spot (p90 7.2); the omen
missile is read until the frame before.

- `omened`: situations/herald.py's tier 5 Bramble Hulk pack as a `Spawn` SPAWN_AFTER s after an omen at OMEN_AT, the
  character `stand` units from the spot (herald.py's 20, H-A's; the pack tactic's stand is 24, combat/pack.py
  PACK_OMEN_STAND). Attack mode alone, as herald.py, the omens read in its quiet (macros/hunt.py OMEN_READ_ALONE, as
  a level run's agenda reads them); `play` and `measures`: herald.py's, the kill time from the spawn, the first hit
  on the pack, its members that staggered in their first second.
- `manaburn_summary`: situations/manaburn_death.py's play (its pace, blows, mana and falls) of the death's fight cut
  EARLY s sooner, from 18:57:24.6, as its omen was read (18:57:24.70; its first frame 0.1 s into the cut, the pack
  5.14 s in): the omen in the missiles from MANABURN_OMEN until the spawn, the level run reading it. The death
  scene's own cut starts 0.73 s before the spawn, after the omen's time to act.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.herald_omen --seeds 3
"""

import argparse
import contextlib
import functools
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from inventory_tracking.combat.sim.monsters import STAGGER
from inventory_tracking.macros import hunt
from inventory_tracking.macros.hunting.base import HERALD_OMEN, OMEN_SECONDS
from tests.inventory_tracking.scenarios.arena.situations import herald, manaburn_death
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome, Situation, east
from tests.inventory_tracking.scenarios.arena.situations.stage import Spawn, Stage


NAME = 'herald-t5-omen'
OMEN_AT = 1.0  # s into the play the omen shows
SPAWN_AFTER = 5.0  # s from the omen to the pack (the takes' median, module text)
OMEN_UNIT = 0x7E000001  # the omen missile's unit
SECONDS = 90.0
# The death of 18:57:45 (manaburn_death.py's take): its omen's spot, the cut EARLY s before the scene's
MANABURN_SPOT = (10157.5, 8190.5)
EARLY = 4.4
MANABURN_FIGHT = (manaburn_death.TAKE, '2026-10-23T18:57:24.6')
MANABURN_OMEN = 34.062 - (manaburn_death.START - EARLY)  # the omen's first frame in the take, s into the cut


def omened(*, stand: float = herald.STAND, seconds: float = SECONDS, **changes: Any) -> Situation:
    """The situation (the module text); `changes` go to herald.py `t5_hulks`."""
    situation = herald.t5_hulks(seconds=seconds, **changes)
    situation.name = f'{NAME}-{stand:.0f}'
    situation.about = f'a tier 5 Bramble Hulk Herald and 14 minions {SPAWN_AFTER:.0f} s after an omen {stand:.0f} off'
    shift = stand - herald.STAND
    pack = [replace(mob, at=(mob.at[0] + shift, mob.at[1])) for mob in situation.scene.mobs if mob.tier]
    situation.scene.mobs = [mob for mob in situation.scene.mobs if not mob.tier]
    situation.spawns.append(Spawn(pack, OMEN_AT + SPAWN_AFTER, label='the Herald pack'))
    situation.omen = situation.spot(east(stand))  # type: ignore[attr-defined]
    situation.assumed['the omen'] = f'missile 737 at the pack centre from {OMEN_AT} s, the pack {SPAWN_AFTER} s on'
    return situation


class Omen:
    """An `each_tick`: the omen in the arena's missiles from `shows` until `spawn` (`Mobs.flights`); with `read`, the
    hunter's record of it read at that clock (`Hunter.omens`), set at the first tick; the pack's first staggers."""

    def __init__(self, spot: tuple[float, float], shows: float, spawn: float, read: float | None = None) -> None:
        self.spot, self.shows, self.spawn, self.read = spot, shows, spawn, read
        self.staggers: dict[int, float] = {}  # unit -> the clock it first staggered at
        self.hooked = False

    def __call__(self, stage: Stage, routed: Any) -> None:
        if not self.hooked:
            self.hooked = True
            inner = stage.cast.flights

            def flights(kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
                found = inner(kinds)
                if HERALD_OMEN in kinds and self.shows <= stage.clock.now < self.spawn:
                    found = (*found, (OMEN_UNIT, HERALD_OMEN, *self.spot))
                return found

            stage.cast.flights = flights  # type: ignore[method-assign]
            hunter = getattr(routed, 'hunter', None)
            if self.read is not None and hunter is not None and stage.world.player is not None:
                hunter.omens, hunter.omen_area = {self.spot: self.read + OMEN_SECONDS}, stage.world.player.area
        for unit, walker in stage.cast.pack.walkers.items():
            mob = stage.cast.mobs.get(unit)
            if walker.doing == STAGGER and unit not in self.staggers and mob is not None and mob.tier:
                self.staggers[unit] = stage.clock.now


@contextlib.contextmanager
def read_alone() -> Iterator[None]:
    """Attack mode reads the omens in its quiet (macros/hunt.py OMEN_READ_ALONE) for the play."""
    old = hunt.OMEN_READ_ALONE
    hunt.OMEN_READ_ALONE = True  # pyrefly: ignore[bad-assignment] a switch flipped for the play
    try:
        yield
    finally:
        hunt.OMEN_READ_ALONE = old


@dataclass(frozen=True)
class Measures:
    """herald.py `Measures` of the play, and the omen's own."""

    fight: herald.Measures
    killed: float | None  # s from the spawn to the Herald's death; None: alive at the end
    first_hit: float | None  # s from the spawn to the first life the pack lost
    staggered: int  # the pack's members that staggered within 1 s of the spawn
    dead: float | None
    kills: int


def play(situation: Situation, seed: int) -> tuple[Measures, Outcome]:
    """One play of `omened` (the module text)."""
    spawn = OMEN_AT + SPAWN_AFTER
    omen = Omen(situation.omen, OMEN_AT, spawn)  # type: ignore[attr-defined]
    lost: list[float] = []

    def each_tick(stage: Stage, routed: Any) -> None:
        omen(stage, routed)
        herald.sampled(stage, routed)
        if not lost and any(stage.cast.mobs[u].tier and stage.cast.mobs[u].life < stage.cast.mobs[u].full
                            for u in stage.cast.live()):  # fmt: skip
            lost.append(stage.clock.now)

    with read_alone():
        outcome = situation.play(seed=seed, keep=True, each_tick=each_tick)
    fight = herald.measures(outcome)
    stage = outcome.stage_  # type: ignore[attr-defined]
    pack = {unit for unit, mob in stage.cast.mobs.items() if mob.tier}
    return Measures(
        fight=fight,
        killed=None if fight.herald_dead is None else round(fight.herald_dead - spawn, 2),
        first_hit=round(lost[0] - spawn, 2) if lost else None,
        staggered=sum(1 for unit, at in omen.staggers.items() if unit in pack and at - spawn <= 1.0),
        dead=outcome.dead_at,
        kills=len(outcome.kills),
    ), outcome


@functools.cache
def manaburn_cut() -> Situation:
    """manaburn_death.py `cut` from MANABURN_FIGHT, EARLY s before its own, as long again (the module text)."""
    scene = manaburn_death
    old = scene.FIGHT, scene.SECONDS, scene.DIED_AT
    # pyrefly: ignore[bad-assignment] the scene's cut moved for one call
    scene.FIGHT, scene.SECONDS, scene.DIED_AT = MANABURN_FIGHT, old[1] + EARLY, old[2] + EARLY
    try:
        found = scene.cut()
    finally:
        scene.FIGHT, scene.SECONDS, scene.DIED_AT = old
    found.name = 'manaburn-omen-1857'
    return found


def manaburn_summary(seed: int, values: Mapping[str, bool] = ALL_ON) -> dict[str, Any]:
    """manaburn_death.py `summary` of `manaburn_cut` with its omen (the module text)."""
    scene = manaburn_death
    cut = manaburn_cut()
    spawn = min(spawn.at for spawn in cut.spawns if spawn.at is not None)
    omen = Omen(MANABURN_SPOT, MANABURN_OMEN, spawn)
    falls, gone = scene.falls, dict(scene.FALLS)

    def with_omen(stage: Stage, routed: Any) -> None:
        omen(stage, routed)
        falls(stage, routed)

    scene.falls = with_omen  # type: ignore[assignment]
    scene.FALLS.update({txt: at + EARLY for txt, at in gone.items()})  # the Defiler's fall at the take's time
    try:
        measured, dip, outcome, mana = scene.play(values, seed, cut, lap=0.02)
    finally:
        scene.falls = falls  # type: ignore[assignment]
        scene.FALLS.clear()
        scene.FALLS.update(gone)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    return {
        'seed': seed, 'dead': measured.dead_at, 'low': dip, 'kills': measured.kills, 'rejuv': measured.rejuvenations,
        'hops': measured.hops, 'burns': len(mana.burns), 'first_burn': mana.burns[0][0] if mana.burns else None,
        'herald': stage.fell.get(scene.HERALD), 'spawn': spawn,
        'staggered': sum(1 for at in omen.staggers.values() if at - spawn <= 1.0),
    }  # fmt: skip


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--seeds', type=int, default=3)
    parser.add_argument('--stand', type=float, default=herald.STAND)
    parser.add_argument('--manaburn', action='store_true')
    args = parser.parse_args(argv)
    for seed in range(1, args.seeds + 1):
        print(seed, manaburn_summary(seed) if args.manaburn else play(omened(stand=args.stand), seed)[0])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
