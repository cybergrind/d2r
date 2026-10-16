"""The KP_6 loop's games of 2026-10-16 19:55 and 19:59 (rca/2026-10-16/loop-chests-findings.md): the requirements
they showed unmet, as strict xfail tests until their fix. The player: "we spent too much time killing things that
were not attacking us and not even directly visible"; "focus on reaching chests as fast as possible and looting
them"."""

import threading
import time
from dataclasses import replace
from pathlib import Path

from inventory_tracking.combat.harm import Harm
from inventory_tracking.macros import pursuit as p, runner as runner_module
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.build import Step
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.pursuit import FULL, Pursuit
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.travel import PRESSED
from tests.inventory_tracking.macros.fakes import BUILD, Game, world


SAVED_GAMES = Path('/nonexistent/Saved Games')


def test_a_hostile_that_costs_no_life_does_not_keep_the_loops_chest_run_from_its_chest():
    # 19:56:07.2 (take 20261016T165556Z-79, the decision at t 192526.234): on the way to the chest at (4507, 2932),
    # 16 away, Hell Buzzards (class 112) within the blades' 22.1 units, idle or walking, none striking. Priced: the
    # move to the chest 0.81 s, the hold 2.17 s, both with no harm. The hold was made, as at 33 other looks of the
    # game: 8.7 s of holds and 6.8 s of moves to firing spots in 43 s of chests.
    chests = Goal('Super chests', (4507.0, 2932.0), 'use', 2.0, PRESSED)
    hold = p.Candidate(p.Hold(chests), 2.166, Harm(0.0, 0.0), unstruck=0.0, strikes=True)
    move = p.Candidate(p.Move(Step((4507.0, 2932.0)), chests), 0.81, Harm(0.0, 0.0), unstruck=0.81)
    facts = p.Facts(
        192526.1, chests, False, True, True, lambda: Step((4507.0, 2932.0)), candidates=(hold, move), priced=True,
        budget=624.4, life=1784.0, near=True, quiet=1.9, rush=True,
    )  # fmt: skip
    run = Pursuit('pickup', 192501.4, advance=False, leash=FULL, rush=True)

    assert p.decide(facts, run) == move.act
    # The player's ruling: for the loop only. KP_1's run elsewhere (the Chaos Sanctuary, Baal) keeps the strike gap (I2)
    assert p.decide(replace(facts, rush=False), replace(run, rush=False)) == hold.act
    # A hostile that costs life on the way is still fought: the move dearer than the hold by its harm
    hurt = replace(facts, candidates=(hold, replace(move, harm=Harm(300.0, 500.0))), kappa=0.01)
    assert p.decide(hurt, run) == hold.act


def test_the_loop_goes_on_once_the_level_run_of_its_chests_is_over(monkeypatch):
    # 20:00:51.6 "Level run over: what is left of the route is loot, which takes a press"; attack mode went on
    # sweeping (29 s) and then idled (15 s) until the player pressed KP_6 twice (20:01:35, 20:01:38).
    monkeypatch.setattr(runner_module, 'CARD_SECONDS', 0)
    made, shown, swept = [], [], []
    hunter = Hunter(build=BUILD)
    runner = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, display=shown.append,
        execute=lambda cancelled, routine: execute(cancelled, routine),
    )  # fmt: skip
    runner.hunter = hunter

    def execute(cancelled, routine):
        made.append(routine)
        if routine == 'loop' and len(made) == 1:
            runner._loop_level_run(hunter)  # the chests' leg (`Loop.leg`'s `level_run`)
            assert hunter.rushing  # the loop's run: no strike gap, no better place in a fight (§1)
        elif routine == 'hunt any':
            # Attack mode as the hunt plays it: its level run ends, and the mode itself goes on (the sweep, the idle
            # look) until it is stopped
            hunter.end_run(Game(world()).run(), 'what is left of the route is loot, which takes a press')
            began = time.monotonic()
            cancelled.wait(3)
            swept.append(time.monotonic() - began)
            raise Cancelled
        elif routine == 'loop':
            raise Abort('enough')

    assert runner.request(10.0, 10.1, 'loop')
    deadline = time.monotonic() + 5
    while len(made) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    runner.close()

    assert made[:3] == ['loop', 'hunt any', 'loop']
    assert swept
    assert swept[0] < 1.0  # the next leg, not the sweep, once the run is over
