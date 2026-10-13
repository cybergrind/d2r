"""The pocket of 13:05 and the pack by the seal of 09:06 as situations (rca/2026-10-13/run-1303-findings.md
Part 1, kp4-findings.md §1 and §4), for the pursuit loop's side by side with today's keys
(rca/2026-10-13/pursuit-v1.md).

`POCKET` is the game of 13:01 on 2026-10-13 (take 20261013T100315Z-108, schema 4), from 13:05:02 for 20.5 s:
the character in the Infector's wing of the Chaos Sanctuary, the route at "use Vizier seal 1" 270 units west,
the Teleport staff at 0 of 69 charges, attack mode on, no hostile within 60. 26 presses of the teleport key
made 12 Blade Warps and 4 walks between two places 20 units apart, and the walked way to the seal went from
318 to 314 units. Everything is the take's own but the seals themselves: a take holds the objects the client
shows round the character, and the Vizier's seals were never in sight, so a closed one is put on each mark
that names an object and has none (written into `assumed`). The scene keeps the level's ground POCKET_REACH
round the character: the whole way to the seal has to be in it.

`SEAL_PACK` is the game of 09:06 (take 20261013T060607Z-108, schema 3), 12.08 s in for 26 s: the landing 33
units from Vizier seal 1 with a pack by it, sixteen presses in 6.4 s and the first strike 7.1 s after the
landing. It is kp4.py's SEAL_PACK cut through record.py, as vizier.py cuts BOSS_AWAY; that morning's rule
("the fight first", withdrawn the same day) is the fixture's `as_it_was`.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.pocket [--cut]
"""

import argparse
import functools
import math
from collections.abc import Sequence
from dataclasses import replace

from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.scenarios.arena.kp4 import MADE_UP, SEAL_PACK
from tests.inventory_tracking.scenarios.arena.scene import Prop
from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Situation, dump, held, load
from tests.inventory_tracking.scenarios.arena.situations.vizier import BOSSES


POCKET, PACK = 'pocket', 'seal-pack'
POCKET_TAKE = '20261013T100315Z-108'
POCKET_FROM, POCKET_SECONDS = '13:05:02', 20.5  # the back-and-forth ran from 13:05:02.0 to 13:05:22.4
POCKET_REACH = 340.0  # units: the walked way from the pocket to the seal is 318 (run-1303-findings.md)
SEAL = 'Vizier seal 1'  # the mark the route was at
NO_OBJECT = 3.0  # units from a mark: no object of the scene this near is none on the mark
A, B = (7907.5, 5318.5), (7926.5, 5304.5)  # the two places of the back-and-forth; A is the pocket's end
POCKET_UNITS = 12.0  # units from A: in the pocket (the walked way out of it leads east past B, 24 units off)


def cut_pocket() -> Situation:
    found = from_take(
        TAKES / POCKET_TAKE, POCKET_FROM, POCKET_SECONDS, name=POCKET, reach=POCKET_REACH, bosses=BOSSES,
        about=(
            'Chaos Sanctuary, 2026-10-13 13:05:02: the Teleport staff empty, the route at "use Vizier seal 1" 270 '
            'units west. 26 presses of the teleport key made 12 Blade Warps and 4 walks between two places 20 '
            'units apart; the walked way to the seal went from 318 to 314 units.'
        ),
    )  # fmt: skip
    things = list(found.scene.things)
    for index, mark in enumerate(found.marks):
        spot = (mark.spot[0] * TILE_UNITS, mark.spot[1] * TILE_UNITS)
        if mark.use and not any(math.dist(prop.at, spot) <= NO_OBJECT for prop in things):
            things.append(Prop(MADE_UP + index, mark.use, spot, 0))
            found.assumed[f'scene.things.{mark.label}'] = (
                'never in sight in the take: a closed object put on the mark (the route had not used it)'
            )
    found.scene.things = things
    return found


def cut_pack() -> Situation:
    incident = SEAL_PACK.incident
    return from_take(
        TAKES / incident.take, incident.start, incident.seconds, name=PACK, about=incident.about,
        reach=SEAL_PACK.reach, bosses=BOSSES,
        by_hand={
            'why': 'probe.log of session 20261013T060446Z-aa50e0b0, as kp4.py SEAL_PACK has it',
            'hero': dict(incident.hero),
            'presses': incident.presses,
            'opened': SEAL_PACK.opened,
            'units': dict(SEAL_PACK.units),
            'attack': False,  # the first press of the burst turned it on ("the fight first")
            'as_it_was': True,
        },
    )  # fmt: skip


def cut() -> None:
    """Write both fixtures again from their takes."""
    FIXTURES.mkdir(exist_ok=True)
    dump(cut_pocket(), FIXTURES / f'{POCKET}.json')
    dump(cut_pack(), FIXTURES / f'{PACK}.json')


@functools.cache
def stored(name: str) -> Situation:
    return load(FIXTURES / f'{name}.json')


def seal_place(situation: Situation) -> tuple[float, float]:
    """Where the mark the route was at is, in world units."""
    mark = next(mark for mark in situation.marks if mark.label == SEAL)
    return (mark.spot[0] * TILE_UNITS, mark.spot[1] * TILE_UNITS)


def pocket_variants() -> list[tuple[str, Situation, list | None]]:
    base = stored(POCKET)
    key = [held('teleport', every=0.3)]
    return [
        ('as recorded (26 presses): today', base, None),
        ('as recorded (26 presses): new', base.logic('new'), None),
        ('KP_4 held, every 0.3 s: today', base, key),
        ('KP_4 held, every 0.3 s: new', base.logic('new'), key),
    ]


def pack_variants() -> list[tuple[str, Situation, list | None]]:
    base = stored(PACK)
    today = replace(base.variant(), as_it_was=False)
    return [
        ('as recorded, with the rule of that morning ("the fight first")', base, None),
        ('as recorded: today', today, None),
        ('as recorded: new', today.logic('new'), None),
        ('attack mode on + KP_4 held, every 0.3 s: today', today.variant(attack=True), [held('teleport', every=0.3)]),
        (
            'attack mode on + KP_4 held, every 0.3 s: new',
            today.variant(attack=True).logic('new'),
            [held('teleport', every=0.3)],
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help='cut the fixtures again from the takes')
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args(argv)
    if args.cut:
        cut()
    for name, variants in ((POCKET, pocket_variants()), (PACK, pack_variants())):
        for label, situation, presses in variants:
            outcome = situation.play(presses, seed=args.seed)
            end = outcome.track[-1][1:]
            print(f'{name}: {label}: moved {outcome.moved:.0f}, ends at ({end[0]:.1f}, {end[1]:.1f}), '
                  f'life lost {outcome.taken:.0f}, stage {outcome.stage}')  # fmt: skip
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
