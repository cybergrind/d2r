"""The newest recorded Diablo fight as a situation (rca/2026-10-13/diablo.md section 3): the game of 21:49 on
2026-10-13 (take 20261013T184953Z-108, schema 4), from 2 s before Diablo's first sight (204.7 s in) for 16 s. The
character stands at (7813.5, 5286.5), 21 units from where he rises, strikes from 2.4 s on and holds there; he casts
his red lightning once (23.5 in the AI's metric) and his fire wall; the take lost 255 points (172 to the lightning,
the rest to the wall) and he died 8.97 s into the window.

In the arena Diablo is sim/diablo.py's (his think, stream, ring, wall and swings by the client's rules); the keys
are the recording's (`as recorded`) or none (`attack mode alone`), each by today's keys and by the pursuit loop
(`Situation.logic('new')`), side by side in the viewer's Situations tab.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.diablo [--cut] [--seeds 10]
"""

import argparse
import functools
import statistics
from collections.abc import Sequence

from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Situation, dump, load


NAME = 'diablo-fight'
TAKE = '20261013T184953Z-108'
START, SECONDS = 204.7, 20.0  # Diablo first seen 206.66 s into the take; dead 213.6
ABOUT = (
    'Diablo rises 21 units off and the character holds and strikes; one red lightning cast, one fire wall '
    '(21:49, 2026-10-13)'
)


def cut() -> Situation:
    return from_take(
        TAKES / TAKE, START, SECONDS, name=NAME,
        about=(
            'Chaos Sanctuary, 2026-10-13 21:52: Diablo rises 21 units from the character, which holds and strikes; '
            'his red lightning once, his fire wall once; 255 points lost, Diablo dead 8.97 s into the window.'
        ),
    )  # fmt: skip


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def variants() -> list[tuple[str, Situation, list | None]]:
    base = stored()
    return [
        ('as recorded: today', base.logic('today'), None),
        ('as recorded: new', base.logic('new'), None),
        ('attack mode alone: today', base.logic('today'), []),
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
    print(f'recorded: lost {recorded.get("taken")}, Diablo dead at {[k[0] for k in recorded.get("kills", [])]}')
    for label, situation, presses in variants():
        plays = [situation.play(presses, seed=seed) for seed in range(1, args.seeds + 1)]
        spells = [
            sum(h.points for h in o.hurts if h.kind == 'spell') for o in plays
        ]  # his missiles: stream, wall, ring
        dead = [next((k[0] for k in o.kills if k[2] == 'Diablo'), None) for o in plays]
        killed = [d for d in dead if d is not None]
        print(
            f'{label}: lost {statistics.median(o.taken for o in plays):.0f} (median), his missiles '
            f'{statistics.mean(spells):.0f} (mean), Diablo dead in {len(killed)} of {len(plays)} '
            f'(median {statistics.median(killed) if killed else float("nan"):.1f} s), moved '
            f'{statistics.median(o.moved for o in plays):.0f}, deaths {sum(o.dead for o in plays)}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
