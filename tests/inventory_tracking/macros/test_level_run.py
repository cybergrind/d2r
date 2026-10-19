"""The pickup key's level run (rca/2026-10-13/kp1-level-run.md): one press sets the leash FULL on its level,
and the pursuit loop then works the route's stages of that level in order, holding what is in reach, taking
a drop on the way, waiting out what a seal brings and fighting what stands at an object first, until what is
left is not its own (the loot, the leaving) or the level is left (macros/pursuit.py, macros/goals.py).

The goal sequence is played here on facts alone: the Chaos Sanctuary's script (routes/catalog/act4.py), its
level card's marks, the bosses as monsters, and `decide` with a press that is no longer fresh.
"""

import logging
import math
import threading
from dataclasses import replace

import pytest

from inventory_tracking.builds import pursuing
from inventory_tracking.levels.model import Ground, Target
from inventory_tracking.macros import goals
from inventory_tracking.macros.actuator import Cancelled
from inventory_tracking.macros.build import NoWay, Step
from inventory_tracking.macros.game.layout import NO_OWNER
from inventory_tracking.macros.game.records import HEALING, VALUABLE, Drop, Monster
from inventory_tracking.macros.goals import PICK_UP, Goal, first_fight, goal_of, in_the_way, nearer
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.pursuit import (
    FRESH,
    FULL,
    NONE,
    Defer,
    Ended,
    Facts,
    Hold,
    Move,
    Operate,
    Pursuit,
    decide,
)
from inventory_tracking.macros.route import PERFORMED, staged
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import FIGHT, LOOT
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.bosses import SUPER_UNIQUE_FLAG
from tests.inventory_tracking.macros.fakes import BUILD


AREA = 108  # the Chaos Sanctuary
REACH = 20.0
STEP = Step((1.0, 1.0), None)
RUN = Pursuit('pickup', 0.0, advance=False, leash=FULL, area=AREA)  # pressed long ago: the leash alone
MARKS = {  # tiles, as the level card holds them
    'Vizier seal 1': ((1531.0, 1063.0), 396),
    'Vizier seal 2': ((1531.0, 1073.0), 395),
    'De Seis seal': ((1556.0, 1032.0), 394),
    'Infector seal 1': ((1583.0, 1063.0), 392),
    'Infector seal 2': ((1583.0, 1055.0), 393),
    'Diablo': ((1559.0, 1058.0), 0),
}
BOSSES = {
    'Grand Vizier of Chaos': (306, 1),
    'Lord De Seis': (312, 2),
    'Infector of Souls': (362, 3),
    'Diablo': (243, 4),
}


def card(label: str) -> Target:
    tile, use_ = MARKS[label]
    return Target(AREA, (), tile, label, 'target', False, (), use_)


def boss(name: str, at: tuple[float, float]) -> Monster:
    txt, unit = BOSSES[name]
    return Monster(unit, txt, 1, at[0], at[1], NO_OWNER, 0 if txt == 243 else SUPER_UNIQUE_FLAG)


def facts(goal, *, there=False, in_reach=False, settling=False, area=AREA, way=lambda: STEP, now=100.0) -> Facts:
    return Facts(now, goal, there, in_reach, True, way, area, settling)


class Level:
    """The route's progress on the level, as the tracker and the hands tell it, with the card leading by it."""

    def __init__(self) -> None:
        self.dead: set[str] = set()
        self.progress = Progress(ROUTES, PERFORMED, dead=lambda: frozenset(self.dead))
        self.progress.note('game', AREA)

    def goal(self, here=(7800.0, 5600.0), foes=(), side=None) -> Goal | None:
        found = staged(self.progress, AREA)
        stage = found[1] if found is not None else None
        lead = self.progress.lead(AREA)
        mark = card(lead.label) if lead is not None else None
        return goal_of(
            here, spend=PRESSED, reach=REACH, stage=stage, route=found[0] if found else '', card=mark, foes=foes,
            side=side,
        )  # fmt: skip

    def found(self, here=(7800.0, 5600.0), foes=(), side=None) -> Goal:
        """The goal where the test expects one."""
        goal = self.goal(here, foes, side)
        assert goal is not None
        return goal

    def use(self, label: str) -> None:
        tile = MARKS[label][0]
        self.progress.used(AREA, label, tile, (tile,))


def test_one_pickup_press_is_a_level_run_that_asks_for_nothing_now() -> None:
    press = Pursuit('pickup', 10.0, advance=False, leash=FULL)
    assert press.runs
    assert not press.advance
    assert press.fresh(10.0 + FRESH)
    assert not press.fresh(10.0 + FRESH + 0.01)
    assert not replace(press, spent=True).fresh(10.0)  # a press handed to a routine asks for nothing more
    assert not Pursuit('teleport', 10.0).runs
    assert Pursuit('teleport', 10.0).leash == NONE


def test_the_run_goes_through_every_stage_of_the_chaos_sanctuary_in_order_with_no_press() -> None:
    """The goal sequence of one press of the pickup key: each seal used where it stands, each seal boss and
    Diablo fought where they are, in the script's order; then the loot ends the run (it takes a press)."""
    level = Level()
    seen: list[tuple[str, str, str]] = []

    def look(goal: Goal | None, **given) -> object:
        act = decide(facts(goal, **given), RUN)
        stage = goal.stage.text() if goal is not None and goal.stage is not None else '-'
        seen.append((type(act).__name__, goal.do if goal is not None else '-', stage))
        return act

    for seal in ('Vizier seal 1', 'Vizier seal 2'):
        goal = level.goal()
        assert isinstance(look(goal), Move)  # far from the seal: the next move toward it
        assert isinstance(look(goal, there=True), Operate)  # at it: used
        level.use(seal)
    vizier = boss('Grand Vizier of Chaos', (7660.0, 5320.0))
    goal = level.found(foes=[vizier])
    assert (goal.do, goal.unit) == (FIGHT, 1)
    assert isinstance(look(goal), Move)
    assert isinstance(look(goal, there=True, in_reach=True), Hold)
    level.dead.add('Grand Vizier of Chaos')
    assert isinstance(look(level.goal(), there=True), Operate)
    level.use('De Seis seal')
    assert isinstance(look(level.goal(foes=[boss('Lord De Seis', (7780.0, 5160.0))]), in_reach=True), Hold)
    level.dead.add('Lord De Seis')
    for seal in ('Infector seal 1', 'Infector seal 2'):
        assert isinstance(look(level.goal(), there=True), Operate)
        level.use(seal)
    assert isinstance(look(level.goal(foes=[boss('Infector of Souls', (7925.0, 5276.0))]), in_reach=True), Hold)
    level.dead.add('Infector of Souls')
    star = level.found()  # Diablo not come yet: his mark
    assert (star.do, star.unit, star.label) == (FIGHT, None, 'Diablo, by its mark Diablo')
    waiting = look(star, there=True)
    assert isinstance(waiting, NoWay)
    assert waiting.arrived
    assert 'nothing in reach here yet' in waiting.reason
    assert isinstance(look(level.goal(foes=[boss('Diablo', (7796.0, 5290.0))]), in_reach=True), Hold)
    level.dead.add('Diablo')
    over = look(level.goal())
    assert isinstance(over, Ended)
    assert 'loot' in over.reason
    assert list(dict.fromkeys(stage for _, _, stage in seen)) == [
        'use Vizier seal 1', 'use Vizier seal 2', 'fight Grand Vizier of Chaos', 'use De Seis seal',
        'fight Lord De Seis', 'use Infector seal 1', 'use Infector seal 2', 'fight Infector of Souls',
        'fight Diablo', 'loot',
    ]  # fmt: skip
    assert seen[-1][:2] == ('Ended', LOOT)


def test_what_is_in_reach_comes_before_the_route_and_a_drop_before_the_next_stage() -> None:
    level = Level()
    goal = level.found()
    assert decide(facts(goal, in_reach=True, way=unasked), RUN) == Hold(goal)
    potion = Drop(9, 7810.0, 5600.0, 'a super healing potion', HEALING)
    side = level.found(side=potion)
    assert (side.do, side.unit) == (PICK_UP, 9)
    assert decide(facts(side, there=True, way=unasked), RUN) == Operate(side)
    # Beyond a click the drop is gone to by the navigator with the movement in hand, not by the pickup's own
    # Teleport hops (2026-10-13: run-2110-findings.md §2.3, the Amn Rune left twice with the staff empty)
    assert side.near == goals.PICK_REACH
    assert decide(facts(side), RUN) == Move(STEP, side)
    assert decide(facts(side, in_reach=True, way=unasked), RUN) == Hold(side)  # the fight first


def test_nothing_is_begun_while_a_seal_brings_its_pack() -> None:
    goal = Level().found()
    waited = decide(facts(goal, settling=True, way=unasked), RUN)
    assert isinstance(waited, NoWay)
    assert waited.arrived
    assert decide(facts(goal, settling=True, in_reach=True, way=unasked), RUN) == Hold(goal)
    # A fresh press of the teleport key waits the same second, said (an act in flight), and then moves
    press = replace(RUN, key='teleport', pressed_at=100.0, advance=True)
    held = decide(facts(goal, settling=True, way=unasked), press)
    assert isinstance(held, NoWay)
    assert held.arrived
    assert decide(facts(goal), press) == Move(STEP, goal)


def test_in_lower_kurast_a_chests_drop_is_taken_before_the_next_chest() -> None:
    # lower-kurast-plan.md task 3: the camp's chests under one label; what the first lets fall is taken before the
    # run goes on to the second. The drops show with the chest's mode (teleport.py CHEST_BRINGS).
    from inventory_tracking.levels.model import UNIQUE_CHEST
    from inventory_tracking.macros.teleport import CHEST_BRINGS, USES
    from inventory_tracking.routes.model import USE

    progress = Progress(ROUTES, PERFORMED)
    progress.note('game', 79)
    chests = ((1000.0, 1000.0), (1003.0, 1000.0))  # tiles

    def goal(side=None) -> Goal:
        found, lead = staged(progress, 79), progress.lead(79)
        assert found is not None
        assert lead is not None
        tile = next(chest for chest in chests if chest not in lead.skip)
        mark = Target(79, (), tile, 'Super chests', 'target', False, (), UNIQUE_CHEST)
        made = goal_of(
            (5000.0, 5000.0), spend=PRESSED, reach=REACH, stage=found[1], route=found[0], card=mark, side=side
        )
        assert made is not None
        return made

    first = goal()
    assert (first.do, first.place) == (USE, (5000.0, 5000.0))
    progress.used(79, 'Super chests', chests[0], chests)
    # A little over the 14 ms the macro's own reads saw the drops after the open (01:38:04 on 2026-10-17)
    assert USES[UNIQUE_CHEST].brings == CHEST_BRINGS >= 0.05
    waited = decide(facts(goal(), settling=True, area=79, way=unasked), replace(RUN, area=79))
    assert isinstance(waited, NoWay)
    assert waited.arrived
    ring = Drop(9, 5004.0, 5002.0, 'Ring', VALUABLE)
    taken = goal(side=ring)
    assert (taken.do, taken.unit) == (PICK_UP, 9)
    assert (goal().do, goal().place) == (USE, (5015.0, 5000.0))  # with the ground clean, the second chest


def test_in_lower_kurast_without_a_camp_the_run_ends_where_it_stands() -> None:
    # lower-kurast-plan.md task 5: not a walk to the card's first mark (the Kurast Bazaar gate) and a stop there
    progress = Progress(ROUTES, PERFORMED)
    progress.note('game', 79)
    gate = Target(79, (), (10.0, 10.0), 'Kurast Bazaar', 'stairs', True)
    progress.absent(79, 'Super chests')

    found = staged(progress, 79)
    assert found is not None
    goal = goal_of((5000.0, 5000.0), spend=PRESSED, reach=REACH, stage=found[1], route=found[0], card=gate)
    assert goal is not None
    assert (goal.do, goal.place) == (LOOT, (5000.0, 5000.0))
    ended = decide(facts(goal, area=79, way=unasked), replace(RUN, area=79))
    assert isinstance(ended, Ended)
    assert 'loot' in ended.reason


def test_the_run_ends_where_its_leash_does() -> None:
    goal = Level().found()
    assert decide(facts(goal, area=107, way=unasked), RUN) == Ended('the level was left')
    nothing = decide(facts(None, way=unasked), RUN)
    assert isinstance(nothing, Ended)
    loot = Goal('loot', (0.0, 0.0), LOOT, math.inf, PRESSED, route='Diablo')
    assert isinstance(decide(facts(loot, way=unasked), RUN), Ended)
    # A fresh pickup press there is the key's old step: the loot and then the leaving, as before the run
    fresh = replace(RUN, pressed_at=100.0)
    assert decide(facts(loot, way=unasked), fresh) == Defer(loot)
    assert decide(facts(None, way=unasked), fresh) == Defer(None)


def test_a_level_with_no_route_is_no_run_and_the_key_is_its_old_step() -> None:
    exit_ = Goal('the stairs', (50.0, 0.0), 'reach', goals.PLACE_NEAR, PRESSED)  # the card's mark, no stage
    assert decide(facts(exit_, way=unasked), replace(RUN, pressed_at=100.0)) == Defer(None)
    assert isinstance(decide(facts(exit_, way=unasked), RUN), Ended)


def test_a_teleport_press_during_the_run_asks_for_its_goal_now_and_the_run_goes_on_after() -> None:
    goal = Level().found()
    press = replace(RUN, key='teleport', pressed_at=100.0, advance=True)
    assert decide(facts(goal, in_reach=True), press) == Move(STEP, goal)  # the press's goal, before the fight
    assert decide(facts(goal, in_reach=True, now=101.0, way=unasked), press) == Hold(goal)  # stale: the run's


def test_without_the_leash_the_unpressed_loop_goes_to_no_seal() -> None:
    goal = Level().found()
    assert isinstance(decide(facts(goal, way=unasked), None), NoWay)


def unasked():
    raise AssertionError('the navigator was asked')


# -- what bars an act: the fight first ----------------------------------------------------------------


def monster(unit: int, at: tuple[float, float]) -> Monster:
    return Monster(unit, 362, 1, at[0], at[1], NO_OWNER, 0)


def test_the_fight_first_is_with_the_nearest_of_what_bars_the_goal_and_keeps_its_stage() -> None:
    seal = Level().found()
    pack = [monster(31, (seal.place[0] + 3.0, seal.place[1])), monster(32, (seal.place[0] - 20.0, seal.place[1]))]
    here = (seal.place[0] - 60.0, seal.place[1])
    found = first_fight(seal, here, pack, REACH)
    assert (found.do, found.unit, found.near, found.stage) == (FIGHT, 32, REACH, seal.stage)
    assert found.label == 'Vizier seal 1: the fight first (2 in the way)'
    assert found.known


def test_only_an_objects_stand_has_what_is_in_the_way() -> None:
    seal = Level().found()
    near = monster(31, (seal.place[0] + goals.USE_NEAR - 1.0, seal.place[1]))
    far = monster(32, (seal.place[0] + goals.USE_NEAR + 1.0, seal.place[1]))
    assert in_the_way(seal, [near, far]) == [near]
    vizier = Level()
    vizier.use('Vizier seal 1')
    vizier.use('Vizier seal 2')
    fight = vizier.found(foes=[boss('Grand Vizier of Chaos', (7660.0, 5320.0))])
    assert in_the_way(fight, [near, far]) == []


def test_an_act_that_did_not_take_is_made_from_nearer() -> None:
    seal = Level().found()
    assert nearer(seal).near == goals.PLACE_NEAR < seal.near
    fight = replace(seal, do=FIGHT, near=REACH)
    assert nearer(fight) is fight


# -- the mailbox and the runner -------------------------------------------------------------------------


def test_a_teleport_press_keeps_the_runs_leash_and_the_end_of_the_run_keeps_the_press() -> None:
    hunter = Hunter(build=pursuing(BUILD))
    hunter.post(Pursuit('pickup', 10.0, advance=False, leash=FULL, area=AREA))
    hunter.post(Pursuit('teleport', 11.0))
    assert hunter.pursuit is not None
    assert (hunter.pursuit.key, hunter.pursuit.leash, hunter.pursuit.area, hunter.pursuit.advance) == (
        'teleport', FULL, AREA, True,
    )  # fmt: skip
    hunter.end_run(None, 'attack mode off')
    assert hunter.pursuit == Pursuit('teleport', 11.0)  # the press stays, the run is over
    hunter.post(Pursuit('pickup', 12.0, advance=False, leash=FULL))
    hunter.end_run(None, 'attack mode off')
    assert hunter.pursuit is None


def test_a_pickup_press_posted_during_a_look_is_not_dropped_and_the_next_look_hands_it_on(caplog) -> None:
    """The River of Flame, 00:26:32.19 on 2026-10-14 (rca/2026-10-14/run-0025-findings.md §2.1): the look took its
    clock, the press came 28 ms later while the goal was being named, and `decide` read the mailbox only then: the
    press was newer than the look's clock (not fresh), the route's "enter Chaos Sanctum" takes a press, the run
    `Ended`, and `end_run` dropped the press with it. 6 of the game's 20 pickup presses were lost so. The look reads
    the mailbox once with its clock; a press posted during it stays for the next look, which hands it on. Since the
    run mode of 2026-10-14 the run goes to the River's door itself (test_runmode.py): the route's own press here is
    the loot."""
    from tests.inventory_tracking.macros.test_hunt import game, hunter

    play = game()
    hunt = hunter(play)
    hunt.build = pursuing(hunt.build)
    run = play.run()
    sanctum = Goal('loot', (5000.0, 5300.0), LOOT, math.inf, PRESSED, route='Diablo')
    hunt.post(Pursuit('pickup', play.clock.now - 30.0, advance=False, leash=FULL, area=101))  # the run, long ago
    pressed: list[Pursuit] = []

    def named(run_, world, foes, pressing, *rest):
        if not pressed:  # the player's press lands while the look names its goal
            play.clock.now += 0.028
            pressed.append(Pursuit('pickup', play.clock.now, advance=False, leash=FULL))
            hunt.post(pressed[0])
        return sanctum

    hunt.goal = named  # type: ignore[method-assign]
    handed: list[str] = []
    hunt.hand_over = handed.append
    ground = Ground(())
    with caplog.at_level(logging.INFO):
        assert not hunt.pursue(run, play.world, [], ground, None, in_reach=False)
        assert hunt.pursuit is not None
        assert hunt.pursuit.pressed_at == pressed[0].pressed_at  # not dropped
        assert 'the level run ends' not in caplog.text
        with pytest.raises(Cancelled):
            hunt.pursue(run, play.world, [], ground, None, in_reach=False)
    assert handed == ['pickup']  # the next look hands the press to the route's own step


def test_the_mailbox_takes_the_loops_write_only_over_what_it_read() -> None:
    hunter_ = Hunter(build=pursuing(BUILD))
    first = Pursuit('pickup', 10.0, advance=False, leash=FULL)
    hunter_.post(first)
    read = hunter_.pursuit
    assert read is not None
    hunter_.post(Pursuit('pickup', 11.0, advance=False, leash=FULL))  # a press during the look
    assert not hunter_.swap(read, replace(read, area=AREA))
    assert hunter_.pursuit is not None
    assert hunter_.pursuit.pressed_at == 11.0
    hunter_.end_run(None, 'the route takes a press', seen=read)  # the look's answer, over the press it read
    assert hunter_.pursuit is not None
    assert hunter_.pursuit.leashed  # the newer press keeps the run
    hunter_.end_run(None, 'attack mode off')
    assert hunter_.pursuit is None


@pytest.fixture
def runner(monkeypatch, tmp_path):
    started = []

    def execute(cancelled, routine):
        started.append(routine)
        cancelled.wait(5)

    made = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=tmp_path, display=lambda lines: None, execute=execute
    )
    build = pursuing(BUILD)
    made.build = made.fallback = build
    made.hunter = Hunter(build=build)
    yield made, started
    made.close()


def test_the_pickup_key_with_the_pursuit_on_starts_attack_mode_with_the_level_run(runner) -> None:
    made, started = runner
    assert made.request(10.0, 10.1, 'pickup')
    posted = made.hunter.pursuit
    assert posted is not None
    assert (posted.key, posted.leash, posted.advance) == ('pickup', FULL, False)
    assert made.attack_mode
    assert not made.attack_declined
    for _ in range(100):
        if started:
            break
        made.thread.join(0.02)
    assert started == ['hunt any']  # attack mode, not the pickup step
    assert made.request(10.5, 10.6, 'pickup')  # a second press renews the run and starts nothing more
    assert started == ['hunt any']
    assert made.request(11.0, 11.1, 'hunt any')  # KP_3 off ends the run
    assert made.hunter.pursuit is None
    assert not made.attack_mode


def test_without_the_pursuit_the_pickup_key_is_its_old_step(monkeypatch, tmp_path) -> None:
    started = []
    made = MacroRunner(
        None,
        capture_lock=threading.Lock(),
        saved_games=tmp_path,
        execute=lambda cancelled, routine: started.append(routine),
    )
    made.build = made.fallback = BUILD
    made.hunter = Hunter(build=BUILD)
    assert made.request(10.0, 10.1, 'pickup')
    assert made.thread is not None
    made.thread.join(5)
    assert started == ['pickup']
    assert made.hunter.pursuit is None


def test_the_tiles_of_the_marks_are_in_world_units_where_the_goals_are() -> None:
    goal = Level().found()
    assert goal.place == (MARKS['Vizier seal 1'][0][0] * TILE_UNITS, MARKS['Vizier seal 1'][0][1] * TILE_UNITS)
