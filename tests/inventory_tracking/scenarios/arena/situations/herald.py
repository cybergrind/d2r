"""A tier 5 Herald's pack of Bramble Hulks as a situation (rca/2026-10-21/herald-fight-findings.md §3.4): the H-A fight
of 09:30:41 on 2026-10-21 built by hand, not cut. The Herald (monstats 128 `thornhulk2`, a unique with an aura) and 14
minions of its kind, every one tier 5 with the tier's life (combat/mechanics/life.py `tier_boost`: x21 for the Herald,
x8.5 for a minion, on its type's points and the unique's RANK_LIFE), stand 20 units off, where the omen put the pack
of H-A (the stand OMEN_STAND 20); the Defiler and the bound Urdar out beside the character, attack mode on. It plays
by the arena's three rules (game.py RULES: the sigil slows, pets fight, bodies block), which a pack fight needs.

What it does not play (the arena's own lists aside, game.py and mobs.py): the omen and the wait for the spawn (the
pack is there at the start), H-A's mods but the aura (stoneskin, resist and fast: the "fast" speed is not verified,
findings "Not verified"; the arena's aura is Might's, mobs.py AURA_FACTOR, on the Herald alone), Health Link, the
pets' resistances and the summon's life bonus (game.py PET_POINTS), Bind Demon's capture chance.

`herald_back` puts the Herald that many units behind its minions, as H-A's stood 15-18 off behind them: past a
monster's awareness (20) it stands until the character comes near. `defiler_life` is the Defiler's points.
`demons_to_bind` puts plain Urdars (189, monstats `demon` 1) north of the character, demons Bind Demon can take;
`bound_life` is the bound Urdar's points (low: it dies early, and the rebind is played).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.herald [--seeds 5]
"""

import argparse
import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import pairwise

from inventory_tracking.builds.warlock.skills import CONSUME
from inventory_tracking.combat.mechanics.life import tier_boost
from tests.inventory_tracking.scenarios.arena.game import BODIES_BLOCK, PET_POINTS, PETS_FIGHT, SIGIL_SLOWS
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome, Situation, east, open_field


NAME = 'herald-t5-hulks'
HULK, URDAR, DEFILER = 128, 189, 744
MINIONS = 14
TIER = 5
RULES = (SIGIL_SLOWS, PETS_FIGHT, BODIES_BLOCK)
SECONDS = 30.0
STAND = 20.0  # units from the pack: hunting/base.py OMEN_STAND, where H-A's character stood
BOUND_POINTS = PET_POINTS  # the bound Urdar's points when not told (an assumption, as the Defiler's)
MELEE = 3.2  # units: a hostile this near is in melee (combat/sim/monsters.py REACH)
AWAY = 20.5  # units north of the character the demons to bind stand at


def t5_hulks(
    *,
    rules: Sequence[str] = RULES,
    bound_life: float = BOUND_POINTS,
    defiler_life: float = PET_POINTS,
    demons_to_bind: int = 0,
    herald_back: float = 0.0,
    seconds: float = SECONDS,
) -> Situation:
    """The situation (the module text)."""
    situation = Situation.on(open_field(70), name=NAME)
    situation.about = 'a tier 5 Bramble Hulk Herald and 14 minions 20 off, the Defiler and the bound Urdar out'
    situation.pack(HULK, 1 + MINIONS, at=east(STAND), spread=6.0, rank='boss')
    mobs = []
    for index, mob in enumerate(situation.scene.mobs):
        boost = tier_boost(mob.flags, TIER)
        mods = (30,) if index == 0 else ()  # monumod 30 `aura` (H-A's Herald: aura, stoneskin, resist, fast)
        at = (mob.at[0] + herald_back, mob.at[1]) if index == 0 else mob.at
        mobs.append(replace(mob, at=at, tier=TIER, full=mob.full * boost, life=mob.life * boost, mods=mods))
    situation.scene.mobs = mobs
    situation.companions((1.5, -1.0), txt=DEFILER, life=defiler_life)
    situation.companions((-1.0, 1.5), txt=URDAR, life=bound_life)
    for k in range(demons_to_bind):
        # North of the character, across the hops' way back from the pack (west), in the strike's reach (22.1) and
        # past a monster's awareness (20): they stand there
        situation.pack(URDAR, 1, at=(3.5 * k, -AWAY), spread=0.0)
    situation.rules = tuple(rules)
    situation.seconds = seconds
    situation.assumed.update({
        'the pack': 'built by hand after H-A (take 20261021T063019Z-77, 09:30:41), not cut from the take',
        'mods': "the Herald's aura alone (Might, the arena's); stoneskin, resist and fast not played",
        'pets': f'the Defiler and the bound Urdar of {PET_POINTS:.0f} points (game.py PET_POINTS)',
    })  # fmt: skip
    return situation.attack_mode(True)


def prebuffed(stage: object, play: object) -> None:
    """An `each_tick` for `Situation.play`: the hunter's buff record has the macro's Consume (`BuffFacts.took`), as
    after the loop's prebuff, so the Defiler's rows summon one when none is out (builds/warlock/defiler.py
    `defiler_missing`: "a character the macro never buffed is the player's to summon for")."""
    hunter = getattr(getattr(play, 'runner', None), 'hunter', None)
    if hunter is not None and CONSUME not in hunter.buffs.took:
        hunter.buffs.took[CONSUME] = 0.0


def sampled(stage: object, play: object) -> None:
    """`prebuffed`, and the pack's centre at every tick kept on the stage (`centres`: (clock, centre)) for where a
    summon landed (`summons_between`)."""
    prebuffed(stage, play)
    mobs = stage.mobs  # type: ignore[attr-defined]
    live = [mobs.mobs[unit].at for unit in mobs.live() if mobs.mobs[unit].tier]
    if not hasattr(stage, 'centres'):
        stage.centres = []  # type: ignore[attr-defined]
    if live:
        middle = (sum(p[0] for p in live) / len(live), sum(p[1] for p in live) / len(live))
        stage.centres.append((stage.clock.now, middle))  # type: ignore[attr-defined]


def summons_between(outcome: Outcome) -> list[tuple[float, float]]:
    """Each Defiler the macro summoned with the pack about: (its distance to the pack's centre, the character's), at
    the summon (`sampled` must have played)."""
    stage = outcome.stage_  # type: ignore[attr-defined]
    centres = getattr(stage, 'centres', [])
    found = []
    for at, where, here in stage.summons:
        near = [middle for clock, middle in centres if abs(clock - at) <= 0.05]
        if near:
            found.append((math.dist(where, near[0]), math.dist(here, near[0])))
    return found


def herald_of(outcome: Outcome) -> int:
    """The Herald's unit (the pack's first, its unique)."""
    stage = outcome.stage_  # type: ignore[attr-defined]
    return next(unit for unit in stage.mobs.hostile if stage.mobs.mobs[unit].tier and stage.mobs.mobs[unit].flags & 8)


def longest(flags: Sequence[tuple[float, bool]]) -> float:
    """The longest run of seconds the flag held, over samples (clock, flag) of every tick."""
    best, began = 0.0, None
    for at, held in flags:
        if held and began is None:
            began = at
        elif not held and began is not None:
            best, began = max(best, at - began), None
    if began is not None and flags:
        best = max(best, flags[-1][0] - began)
    return best


@dataclass(frozen=True)
class Measures:
    """The findings' measures of one play (§3.4)."""

    surrounded: float  # the longest spell, s, with 3+ hostiles within 5 of the character
    turned: float | None  # the share of the pack's aims on a companion 2 s after the first mark; None: no mark
    lost: float  # the life lost, a share of the most
    potions: int
    herald_dead: float | None  # when the Herald died; None: alive at the end
    still: float  # the longest spell, s, standing still with a hostile in melee (MELEE)
    covered: float | None  # the median share of the hostiles alive in the sigil
    binds: int
    pet_deaths: int


def measures(outcome: Outcome) -> Measures:
    """The `Measures` of a play kept with its stage (`Situation.play(keep=True)`)."""
    stage = outcome.stage_  # type: ignore[attr-defined]
    ticks = stage.ticks
    marked = stage.mark_casts[0][0] if stage.mark_casts else None
    turned = None
    if marked is not None:
        after = [t for t in ticks if t.at >= marked + 2.0]
        if after and after[0].on_hero + after[0].on_mates:
            turned = after[0].on_mates / (after[0].on_hero + after[0].on_mates)
    still = [(b.at, math.dist(a.here, b.here) < 0.01 and b.nearest <= MELEE) for a, b in pairwise(ticks)]
    lying = [t for t in ticks if t.alive]
    return Measures(
        surrounded=longest([(t.at, t.close >= 3) for t in ticks]),
        turned=turned,
        lost=outcome.taken / outcome.max_life,
        potions=len(outcome.potions),
        herald_dead=stage.fell.get(herald_of(outcome)),
        still=longest(still),
        covered=statistics.median([t.sigiled / t.alive for t in lying]) if lying else None,
        binds=len(stage.binds),
        pet_deaths=len(stage.pet_deaths),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--seeds', type=int, default=5)
    args = parser.parse_args(argv)
    for name, situation in (('default', t5_hulks()), ('rebind', t5_hulks(bound_life=3000.0, demons_to_bind=2))):
        for seed in range(1, args.seeds + 1):
            print(name, seed, measures(situation.play(seed=seed, keep=True, each_tick=sampled)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
