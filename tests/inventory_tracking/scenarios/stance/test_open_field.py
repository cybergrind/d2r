"""The sweep on an open field: five packs of ten of Black Marsh's monsters (the types the log of the
run of 2026-10-11 00:25 names, at the area's life) scattered over 90 units, no walls. That run had no
take; its log shows 49 hostiles, 25 presses of the pickup request and 5 of the teleport step in 60 s,
59 kills, fights picking at one or two of fifty in reach. Monsters stand still here, as in the
harness everywhere.

Measured 2026-10-11, six fields, 60 s each:

| strategy                                              | kills of 50 | seconds |
| no step                                               |  3.5        | 60 |
| the first rule, pressed at every decision             | 26.7        | 60 |
| `camp` at every decision, no stride                   | 38.8        | 55 (one field cleared) |
| the sweep: `camp`, else a stride toward the nearest   | 50          | 32.6 |

Of the sweep's 32.6 s about 18 are its 49 casts and the rest its 12 walks (213 units). With teleport
hops for the strides over 12 units it took as long: a hop with the staff costs what the walk does.
"""

import math
import random
from functools import cache

from inventory_tracking.combat import stance
from inventory_tracking.combat.policy import LinePolicy
from inventory_tracking.macros.hunt import STAND_OFF, STRIDE
from inventory_tracking.macros.view import Viewport

from .first_rule import stand
from .harness import ASPECT, Move, Result, Scene, Strategy, View, body, play, scene


BLACK_MARSH = 6
TYPES = (20, 20, 24, 1, 59)  # monstats ids of the hostiles the run's log names, the commonest twice
POLICY = LinePolicy(yields=True)
SEEDS = (0, 1, 2)
SECONDS = 60.0


def field(seed: int, packs: int = 5, per: int = 10, spread: float = 7.0, across: float = 45.0) -> Scene:
    rnd = random.Random(seed)
    bodies = []
    for _ in range(packs):
        cx, cy = rnd.uniform(-across, across), rnd.uniform(-across, across)
        if math.hypot(cx, cy) < 15:
            cx += 25
        for _ in range(per):
            at = (5000 + cx + rnd.gauss(0, spread), 5000 + cy + rnd.gauss(0, spread))
            bodies.append(body(len(bodies) + 1, rnd.choice(TYPES), at, BLACK_MARSH))
    return scene(f'field {seed}', BLACK_MARSH, (5000.0, 5000.0), tuple(bodies))


def pressed_all_along() -> Strategy:
    aimable = Viewport(ASPECT).reachable_focal

    def strategy(view: View) -> Move | None:
        found = stand(view.seen, POLICY, view.barred, aimable)
        return None if found is None else Move(found.spot)

    return strategy


def sweep() -> Strategy:
    """macros/hunt.py's sweep: a better place whenever there is one; with nothing in reach, a stride
    toward the nearest hostile, STAND_OFF short of it."""

    def strategy(view: View) -> Move | None:
        seen = view.seen
        found = stance.camp(seen, POLICY, view.barred)
        if found is not None:
            return Move(found.spot, False, found.walk)
        if not seen.foes or stance.taken(seen, POLICY, stance.Field(seen.blocked, None), seen.origin, 0.0)[0]:
            return None
        nearest = min(seen.foes.values(), key=lambda foe: math.dist(foe.at, seen.origin))
        away = math.dist(nearest.at, seen.origin)
        stride = min(away - STAND_OFF, STRIDE)
        if stride < 1:
            return None
        to = (
            seen.origin[0] + (nearest.at[0] - seen.origin[0]) * stride / away,
            seen.origin[1] + (nearest.at[1] - seen.origin[1]) * stride / away,
        )
        return Move(to, False, stride)

    return strategy


@cache
def outcome(seed: int, strategy: str) -> Result:
    make = {'pressed': pressed_all_along, 'sweep': sweep}[strategy]
    return play(field(seed), make(), seconds=SECONDS, near=200.0)


def test_the_sweep_clears_the_field_and_the_first_rule_pressed_all_along_half_of_it():
    for seed in SEEDS:
        swept, pressed = outcome(seed, 'sweep'), outcome(seed, 'pressed')
        assert swept.cleared, seed
        assert swept.seconds is not None
        assert swept.seconds < 45
        assert not pressed.cleared
        assert pressed.alive >= 15


def test_most_of_the_sweeps_time_is_casting():
    for seed in SEEDS:
        swept = outcome(seed, 'sweep')
        assert swept.seconds is not None
        assert swept.casts * stance.CAST_SECONDS >= 0.45 * swept.seconds
        assert swept.walked < 300
