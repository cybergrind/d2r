"""The player's constructed example (2026-10-13): "we are in the middle of 4 packs of dangerous mobs from each
side (dolls, souls, death lords, ...), there is a valuable drop and all are aggroed at us, we have 30% hp,
what we will do and how we will die". Attack mode is on ("auto-attack is pressed").

`example()` is that situation in the builder's words; `VARIANTS` are the experiments on it, each the base
with one thing changed; `python -m ...situations.example [--seeds 30]` prints the table of
rca/2026-10-13/situations.md and one story.

What the numbers are and are not is in bestiary.py (`python -m ...situations.bestiary`): the dolls are the
undead ones, whose corpses explode (the living do not, by monstats); a Soul's lightning lands with the
pooled chance of a shooter's missile (0.024) unless a variant says `lands=`; Death Lords and Minions of
Destruction swing at the pooled rate.
"""

import argparse
import sys
from collections.abc import Sequence

from tests.inventory_tracking.scenarios.arena.situations.bestiary import txt_of
from tests.inventory_tracking.scenarios.arena.situations.situation import (
    ROW_HEAD,
    Situation,
    east,
    held,
    north,
    once,
    open_field,
    south,
    west,
)  # fmt: skip
from tests.inventory_tracking.scenarios.arena.situations.stage import EVERYONE
from tests.inventory_tracking.scenarios.arena.situations.story import story


SECONDS = 20.0
PACKS_AT = 18.0  # units from the character to each pack's middle
SOUL_LANDS = 0.5  # an assumption for the "lightning lands" variants: half the bolts sent at the character take life


def example() -> Situation:
    return (
        Situation.on(open_field(60), name='four packs at 30% life')
        .hero(life=0.30, ward=False)
        .pack('Undead Stygian Doll', 8, at=north(PACKS_AT), spread=5)
        .pack('Burning Soul', 6, at=east(PACKS_AT), spread=5)
        .pack('Death Lord', 5, at=south(PACKS_AT), spread=5)
        .pack('Minion of Destruction', 5, at=west(PACKS_AT), spread=5)
        .drop('a valuable rune', at=(4.0, 4.0))
        .mark('the way out', at=east(55))
        .aggro(EVERYONE)
        .attack_mode(True)
        .variant(seconds=SECONDS)
    )


def variants() -> dict[str, tuple[Situation, list]]:
    """name -> (the situation, its presses)."""
    base = example()
    lightning = {txt_of('Burning Soul'): SOUL_LANDS}
    return {
        'attack on': (base, []),
        'attack on + pickup key at 0.5 s': (base, [once('pickup', at=0.5)]),
        'attack on + KP_4 held (every 0.3 s) toward a mark beyond the Souls': (base, [held('teleport', every=0.3)]),
        'attack on + KP_4 every 1 s': (base, [held('teleport', every=1.0)]),
        'attack on, the ward up': (example().hero(ward=True), []),
        'attack on, 100% life': (example().hero(life=1.0), []),
        'attack on, an empty belt': (example().hero(belt=(None,) * 16), []),
        f'attack on, lightning lands {SOUL_LANDS:.0%} (assumed)': (base.variant(lands=lightning), []),
        f'attack on, 100% life, lightning lands {SOUL_LANDS:.0%} (assumed)': (
            example().hero(life=1.0).variant(lands=lightning),
            [],
        ),
        'attack OFF (contrast)': (base.variant(attack=False), []),
    }


def table(seeds: Sequence[int]) -> str:
    lines = [f'| variant | {ROW_HEAD} |', '| --- | ---: | ---: | ---: | ---: | --- |']
    for name, (situation, presses) in variants().items():
        lines.append(f'| {name} | {situation.trials(seeds, presses).row()} |')
        print(lines[-1], file=sys.stderr, flush=True)
    return '\n'.join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--seeds', type=int, default=30)
    parser.add_argument('--story', type=int, default=3, help='the seed of the story printed')
    args = parser.parse_args(argv)
    print(table(range(1, args.seeds + 1)), '\n')
    for name in ('attack on', 'attack on + pickup key at 0.5 s'):
        situation, presses = variants()[name]
        print(story(situation.variant(f'{situation.name} ({name})').play(presses, seed=args.story)), '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
