"""Baal in the Worldstone Chamber as a situation (rca/2026-10-14/baal-sim.md): constructed, as no combat take of the
Chamber exists. Baal is sim/baal.py's (his think as read in the client, rca/2026-10-14/re/baal-ai.md; his missiles,
tentacles and clone by the code and the tables); the character, its mercenary and its demons are the repo's default
(cut.py DEFAULT_HERO).

What the scene takes from the probe of eight Baal kills (2026-10-08 to 10-11): the character comes out of the portal
at (15173, 5888) and Baal stands at (15135, 5920), 50 units south-west (every visit); during the fights the character
stood 14 to 20 units from him (quartiles), after its own teleports. What it assumes (`assumed`): open ground (the
Chamber's walls are not in any take), the companions standing where they start (the arena's never move), the start
`START` units from him on the line from the portal.

Variants: attack mode alone from START units off, by today's keys and by the pursuit loop; and from the portal with
the pickup key once (the pursuit loop's run of the level: the level card's mark is Baal's place, boss_lairs.py).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.baal [--seeds 10]
"""

import argparse
import functools
import itertools
import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field

from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.combat.sim import baal as rules
from inventory_tracking.combat.sim.monsters import UNIQUE_FLAG
from inventory_tracking.combat.stance import CAST_SECONDS
from tests.inventory_tracking.scenarios.arena.mobs import SUMMONED
from tests.inventory_tracking.scenarios.arena.scene import Mob
from tests.inventory_tracking.scenarios.arena.situations.bestiary import name_of
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome, Situation, once, open_field
from tests.inventory_tracking.scenarios.arena.situations.stage import Hurt


NAME = 'baal-fight'
AREA = 132  # the Worldstone Chamber
BAAL = 544
PORTAL_TO_BAAL = (-38.0, 32.0)  # [probe] from where the portal leaves the character to where Baal stands
START = 20.0  # units from him at the start of the `attack mode` variants (the probe's third quartile while fighting)
SECONDS = 60.0
COMPANIONS = ((338, (2.5, 2.0)), (361, (-2.0, 3.0)), (744, (1.0, -2.5)))  # mercenary, Defiler, demon (the takes' txt)
ABOUT = 'Baal (constructed: his think as read in the client, his places by the probe), attack mode from 20 units off'
NAMES = {
    rules.INFERNO_MISSILE: 'inferno',
    rules.NOVA_MISSILE: 'nova',
    rules.COLD_MAKER: 'cold missiles',
    rules.COLD_TRAIL: 'cold missiles',
}


def build(start: float | None = START) -> Situation:
    """The Chamber with Baal at his place; the character `start` units from him on the line to the portal (None: at
    the portal), its companions by it."""
    ground = open_field(70.0)
    situation = Situation.on(ground, name=NAME, area=AREA)
    portal = situation.scene.hero.at
    baal_at = (portal[0] + PORTAL_TO_BAAL[0], portal[1] + PORTAL_TO_BAAL[1])
    if start is not None:
        gap = math.dist(portal, baal_at)
        here = (
            baal_at[0] + (portal[0] - baal_at[0]) / gap * start,
            baal_at[1] + (portal[1] - baal_at[1]) / gap * start,
        )
        situation.scene.hero.at = here
    full = points_of(BAAL, AREA)  # a boss: no elite multiplier on his life
    unit = situation.unit()
    situation.scene.mobs.append(Mob(unit, BAAL, baal_at, 0, full, full, flags=UNIQUE_FLAG))
    for txt, offset in COMPANIONS:
        situation.companions(offset, txt=txt)
    situation.bosses = ((unit, 'Baal'),)
    situation.seconds = SECONDS
    situation.about = ABOUT
    situation.assumed = {
        'ground': 'open ground 70 units to each side: the Chamber has no take; its walls are not played',
        'scene.hero.at': f'{start} units from Baal on the line to the portal (None: at the portal)',
        'companions': 'the mercenary, the Defiler and a demon stand where they start (the arena never moves them)',
        'baal': 'sim/baal.py: his think as read in the client (rca/2026-10-14/re/baal-ai.md); the arena knows no '
        "stats of the bodies, so his target score weighs only melee, sight and the character's threat",
    }
    return situation


@functools.cache
def stored(start: float | None = START) -> Situation:
    return build(start)


def variants() -> list[tuple[str, Situation, list | None]]:
    near, portal = stored().variant(attack=True), stored(None)
    return [
        ('attack mode alone: today', near.logic('today'), []),
        ('attack mode alone: new', near.logic('new'), []),
        ('from the portal, KP_1 once: today', portal.logic('today'), [once('pickup', 0.2)]),
        ('from the portal, KP_1 once: new', portal.logic('new'), [once('pickup', 0.2)]),
    ]


# -- what a play came to --------------------------------------------------------------------------------------


@dataclass
class Fight:
    seed: int
    killed_at: float | None
    dead_at: float | None
    lost: float
    by: dict[str, float] = field(default_factory=dict)  # the character's life lost by source
    mates: dict[str, float] = field(default_factory=dict)  # raw points on the companions by source
    strikes: int = 0
    uptime: float = 0.0  # the share of the fight spent in a strike
    dodges: int = 0  # steps the decision loop took out of or across his inferno
    moved: float = 0.0
    least_gap: float | None = None
    tentacles: int = 0
    clone: bool = False
    falls: float = 0.0  # the probe's measure: the life's falls between looks a second apart, summed (`PROBE_FALLS`)


def source(txt: int, kind: str, missile: int) -> str:
    if missile in NAMES:
        return NAMES[missile]
    if txt == rules.CLONE:
        return 'clone'
    return f'{name_of(txt)} {kind}'


def summed(hurts: Sequence[Hurt], end: float) -> dict[str, float]:
    """Points by source up to `end`, the most first."""
    found: dict[str, float] = {}
    for hurt in hurts:
        if hurt.at <= end:
            key = source(hurt.txt, hurt.kind, hurt.missile)
            found[key] = found.get(key, 0.0) + hurt.points
    return {key: round(points, 1) for key, points in sorted(found.items(), key=lambda item: -item[1])}


def fight(outcome: Outcome) -> Fight:
    killed = outcome.boss_dead.get('Baal')
    end = killed if killed is not None else outcome.dead_at if outcome.dead_at is not None else outcome.seconds
    by = summed(outcome.hurts, end)
    stage = getattr(outcome, 'stage_', None)
    mates = summed(stage.cast.mates, end) if stage is not None else {}
    strikes = [at for at in outcome.strikes if at <= end]
    first = strikes[0] if strikes else end
    span = max(end - first, 1e-6)
    gaps = outcome.gaps.get('Baal')
    raised = [mob for unit, mob in (stage.cast.mobs.items() if stage is not None else ()) if unit > SUMMONED]
    return Fight(
        seed=outcome.seed,
        killed_at=killed,
        dead_at=outcome.dead_at,
        lost=round(sum(by.values()), 1),
        by=by,
        mates=mates,
        strikes=len(strikes),
        uptime=min(len(strikes) * CAST_SECONDS / span, 1.0),
        dodges=outcome.said_count("Baal's inferno"),
        moved=outcome.moved,
        least_gap=gaps[1] if gaps else None,
        tentacles=sum(1 for mob in raised if mob.txt != rules.CLONE),
        clone=any(mob.txt == rules.CLONE for mob in raised),
        falls=falls(outcome.life, end),
    )


# [probe] the same measure over the eight kills: the life's falls between looks a second apart, from Baal's first
# sight to his death (potions and regeneration between two looks hide what they gave back)
PROBE_FALLS = (427, 1170, 961, 496, 1328, 338, 276, 214)


def falls(life: Sequence[tuple[float, float]], end: float) -> float:
    looks = [points for at, points in life if at <= end and abs(at - round(at)) < 0.05]
    return round(sum(max(a - b, 0.0) for a, b in itertools.pairwise(looks)), 1)


def measure(situation: Situation, presses: list | None, seeds: Sequence[int]) -> list[Fight]:
    return [fight(situation.play(presses, seed=seed, keep=True)) for seed in seeds]


def ranked(points: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(points.items(), key=lambda item: -item[1])


def table(label: str, fights: list[Fight]) -> list[str]:
    killed = [f.killed_at for f in fights if f.killed_at is not None]
    sources: dict[str, float] = {}
    mates: dict[str, float] = {}
    for f in fights:
        for into, part in ((sources, f.by), (mates, f.mates)):
            for key, points in part.items():
                into[key] = into.get(key, 0.0) + points
    n = len(fights)
    lost = [f.lost for f in fights]
    gaps = [f.least_gap for f in fights if f.least_gap is not None]
    spread = f'{min(killed):.1f} / {statistics.median(killed):.1f} / {max(killed):.1f}' if killed else '-'
    probe = f'{statistics.median(PROBE_FALLS):.0f}, {min(PROBE_FALLS)} to {max(PROBE_FALLS)}'
    return [
        f'### {label}',
        f'- Baal dead in {len(killed)} of {n}; fight s min / median / max: {spread}',
        f'- deaths {sum(f.dead_at is not None for f in fights)}; life lost median {statistics.median(lost):.0f} '
        f'(min {min(lost):.0f}, max {max(lost):.0f}); falls a second apart median '
        f'{statistics.median(f.falls for f in fights):.0f} (the probe: {probe})',
        '- life lost by source (mean a fight): ' + ', '.join(f'{k} {v / n:.0f}' for k, v in ranked(sources)),
        '- companions, raw points by source (mean a fight): ' + ', '.join(f'{k} {v / n:.0f}' for k, v in ranked(mates)),
        f'- strike uptime median {statistics.median(f.uptime for f in fights):.0%}; strikes median '
        f'{statistics.median(f.strikes for f in fights):.0f}; moved median '
        f'{statistics.median(f.moved for f in fights):.0f}',
        f'- dodges of the inferno (steps) mean {statistics.mean(f.dodges for f in fights):.1f}; least gap to Baal '
        f'median {statistics.median(gaps) if gaps else float("nan"):.1f}; tentacles a fight mean '
        f'{statistics.mean(f.tentacles for f in fights):.1f}; clone in {sum(f.clone for f in fights)} of {n}',
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--seeds', type=int, default=10)
    parser.add_argument('--only', default='', help='play only the variants whose label holds this')
    args = parser.parse_args(argv)
    for label, situation, presses in variants():
        if args.only in label:
            print('\n'.join(table(label, measure(situation, presses, range(1, args.seeds + 1)))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
