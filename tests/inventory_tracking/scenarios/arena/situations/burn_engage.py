"""Mana Burn packs the keep range never let us engage, as situations for combat/pack.py BURN_ENGAGE
(rca/2026-10-25/tactics/apply-burn.md). danger_fights.py `cut` of

- `throne-lister-1410`: the Throne of Destruction, 14:10:35 on 2026-10-25 (take 20261025T110846Z-131, terrorized act 5,
  game 125): Lister the Tormentor's pack with Mana Burn under the waves' stand. 7 jumps round (15087, 5018) within 22
  in 11 s with no kill ("toward Lister the Tormentor" x5, "keeping range: mana burn" x4, "the stand for the waves"
  x2), MARK_HOLDS_JUMPS live;
- `throne-lister-1427`: the same at 14:27:05 (take 20261025T112537Z-131, game 129): 9 jumps round (15082, 5031) in
  14:27:10-23 with no kill ("toward Lister the Tormentor" x7, "keeping range: mana burn" x4);

and door_pack.py's two cases (`door-pack-1112`, `door-viper-0326`), played as the live run did (the TZ run's pursuit,
one pickup press, the level a terror zone), with the arena's doors opened by a click (game.py DOORS_OPEN) and the pets
as the game plays them.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.burn_engage --cut
"""

import argparse
import functools
from collections.abc import Mapping
from typing import Any

from tests.inventory_tracking.scenarios.arena import game
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights, door_pack
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import Dips
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON, play as fane_play
from tests.inventory_tracking.scenarios.arena.situations.halls_death import Legs
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


SECONDS = 40.0
CUTS: dict[str, tuple[str, str]] = {
    'throne-lister-1410': ('20261025T110846Z-131', '2026-10-25T14:10:35.0'),
    'throne-lister-1427': ('20261025T112537Z-131', '2026-10-25T14:27:05.0'),
}
NAMES = ('throne-lister-1410', 'throne-lister-1427', 'door-pack-1112', 'door-viper-0326')


def cut(name: str) -> Situation:
    return fights.cut(
        name, fight=CUTS[name], seconds=SECONDS,
        about=f'{CUTS[name][1]}: a Mana Burn pack the keep range never let us engage (burn_engage.py)',
    )  # fmt: skip


@functools.cache
def stored(name: str) -> Situation:
    return load(FIXTURES / f'{name}.json')


def play(seed: int, name: str, values: Mapping[str, bool] = ALL_ON) -> tuple[Outcome, float]:
    """One play of `name` with the switches as they stand (the caller sets them; the arena's doors open by a click,
    its pets as the game plays them, every one taken along): the outcome and the lowest share of life."""
    dips, legs = Dips(), Legs()

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        legs(stage, routed)
        dips(stage, routed)

    names = ('DOORS_OPEN', 'ALONG_ALL', *game.PETS_AS_GAME)
    saved = {attr: getattr(game, attr) for attr in names}
    for attr in names:
        setattr(game, attr, True)
    try:
        outcome = fane_play(door_pack.pursued(stored(name), SECONDS), values, seed, lap=0.02, extra=extra)
    finally:
        for attr, value in saved.items():
            setattr(game, attr, value)
    return outcome, round(max(dips.low, 0.0), 3)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cut', action='store_true', help='cut the situations from their takes into the fixtures')
    args = parser.parse_args(argv)
    if args.cut:
        for name in CUTS:
            dump(cut(name), FIXTURES / f'{name}.json')
        stored.cache_clear()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
