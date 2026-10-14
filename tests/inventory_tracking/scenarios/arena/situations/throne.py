"""The Throne of Destruction's five waves as a situation (rca/2026-10-14/baal-sim.md section 6): the game of 00:12 on
2026-10-11 (take 20261011T001204Z-131, schema 2), from 2 s before the first wave (24.0 s into the take) for 98 s,
through Lister's wave (100.9 s in) and the walk to the portal (the take left the level at 122.9 s).

The waves appear when and where the take first saw them (record.py: a play-back of the appearance, not of why they
come: in the game a wave comes when the one before is dead), the Council Members' hydras among them. Each type plays
by what the arena has for it: the Venom Lords by their read AI (sim/casters.py), the others by the takes' fit
(sim/monsters.py; the Council's Hydra and heal, the minions' Smite and the mummies' are not read).

Not played: Baal on his throne (543, AI BaalThrone, not read). He casts S3 every 5 to 9 s in both takes (37 casts of
21 to 22 frames: Decrepify, Baal Corpse Explode, Defense Curse, Blood Mana by his row) and never moves; the arena
would play him as a melee walker, so he is taken out (`assumed`). Schema 2 holds no presses: the variants are attack
mode alone by today's keys and by the pursuit loop.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.throne [--cut] [--seeds 10]
"""

import argparse
import functools
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Situation, dump, load


NAME = 'throne-waves'
TAKE = '20261011T001204Z-131'
START, SECONDS = 22.0, 98.0
THRONE = (543, 559)  # Baal on his throne, and walking to his stairs (monstats `baalthrone`, `baalcrabstairs`)
ABOUT = "the Throne's five waves from the fighting stand, attack mode (00:12, 2026-10-11)"


def cut() -> Situation:
    situation = from_take(
        TAKES / TAKE, START, SECONDS, name=NAME,
        about=(
            "Throne of Destruction, 2026-10-11 00:12: the five waves (Colenzo's, Achmel's, Bartuc's, Ventar's, "
            "Lister's) as the take saw them come; Baal on his throne left out."
        ),
        by_hand={'attack': True, 'why': 'schema 2 holds no presses: attack mode on from the start'},
    )  # fmt: skip
    situation.scene.mobs = [mob for mob in situation.scene.mobs if mob.txt not in THRONE]
    situation.spawns = [
        replace(spawn, mobs=[mob for mob in spawn.mobs if mob.txt not in THRONE]) for spawn in situation.spawns
    ]
    situation.assumed['scene.mobs'] = (
        'Baal on his throne (543) taken out: his AI (BaalThrone) is not read, he never moves and only curses '
        '(S3 every 5 to 9 s in the takes); the arena would play him as a melee walker'
    )
    return situation


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def variants() -> list[tuple[str, Situation, list | None]]:
    base = stored()
    return [
        ('attack mode alone: today', base, []),
        ('attack mode alone: new', base.logic('new'), []),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help='cut the fixture again from the take')
    parser.add_argument('--seeds', type=int, default=10)
    args = parser.parse_args(argv)
    if args.cut:
        FIXTURES.mkdir(exist_ok=True)
        dump(cut(), FIXTURES / f'{NAME}.json')
    recorded = stored().recorded or {}
    print(f'recorded: lowest life {recorded.get("low")}, kills {len(recorded.get("kills", []))}')
    for label, situation, presses in variants():
        plays = [situation.play(presses, seed=seed) for seed in range(1, args.seeds + 1)]
        by: Counter[tuple[str, str]] = Counter()
        for play in plays:
            by.update(play.taken_by())
        top = ', '.join(f'{name} {kind} {points / len(plays):.0f}' for (name, kind), points in by.most_common(6))
        print(
            f'{label}: deaths {sum(o.dead for o in plays)} of {len(plays)}, lost median '
            f'{statistics.median(o.taken for o in plays):.0f}, lowest life median '
            f'{statistics.median(o.low for o in plays):.0f}, alive at the end median '
            f'{statistics.median(o.alive for o in plays):.0f} of {plays[0].hostiles}, potions median '
            f'{statistics.median(len(o.potions) for o in plays):.0f}; lost by (mean): {top}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
