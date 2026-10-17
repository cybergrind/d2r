"""The attack mode's look offers a Blade Warp that takes the mercenary out of a place it dies at (macros/hunt.py
`escorted`, combat/escort.py), as an act the arbiter prices with the others."""

import math
from dataclasses import replace

from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.combat import escort
from inventory_tracking.combat.harm import Hostile, Look
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.build import NoWay
from inventory_tracking.macros.pursuit import Facts, Move, decide
from inventory_tracking.macros.world import Monster
from inventory_tracking.native.layout import HIRELING_CLASS_ID
from tests.inventory_tracking.macros.test_hunt import game, hunter, me


DIABLO = 243
HERE, MERC, HIM = (5000.0, 5000.0), (5020.0, 5000.0), (5022.0, 5001.0)


def scene(life: int):
    play = game()
    merc = Monster(7, HIRELING_CLASS_ID, 1, *MERC, me(play.world).unit_id, ally=True, life=life, max_life=1450)
    play.world = replace(play.world, monsters=(merc,))
    hunt = hunter(play)
    look = Look((Hostile(1, DIABLO, HIM, active=True),), companions=(MERC,), life=1800.0)
    facts = Facts(
        play.clock.now, None, False, False, True, lambda: NoWay('nothing to go to'), priced=True, budget=900.0
    )
    return play, hunt, look, facts


def test_a_blade_warp_away_from_diablo_is_offered_for_the_mercenary_beside_him_and_chosen() -> None:
    play, hunt, look, facts = scene(life=26)
    run = play.run()
    rect = run.actuator.keys.focused_window_rect()
    found = hunt.escorted(run, play.world, Ground(()), rect, look, facts)
    added = [c.act for c in found.candidates if isinstance(c.act, Move) and c.act.reason.startswith(escort.ESCORTING)]
    assert added
    assert {move.step.skill for move in added} == {BLADE_WARP}
    assert all(move.dodge for move in added)
    assert all(math.dist(move.step.spot, HIM) > math.dist(MERC, HIM) for move in added)
    chosen = decide(found, None)
    assert isinstance(chosen, Move)
    assert chosen.reason.startswith(escort.ESCORTING)


def test_nothing_is_offered_for_a_mercenary_out_of_danger_or_with_nothing_priced() -> None:
    play, hunt, look, facts = scene(life=128)
    run = play.run()
    rect = run.actuator.keys.focused_window_rect()
    far = Look((Hostile(1, DIABLO, (5200.0, 5000.0), active=True),), companions=(MERC,), life=1800.0)
    assert hunt.escorted(run, play.world, Ground(()), rect, far, facts) is facts
    unpriced = Facts(play.clock.now, None, False, False, True, lambda: NoWay('nothing to go to'))
    assert hunt.escorted(run, play.world, Ground(()), rect, look, unpriced) is unpriced
