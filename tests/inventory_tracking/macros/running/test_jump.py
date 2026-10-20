"""The teleport press as a jump to the next goal (macros/running/jump.py; the player, 2026-10-19: "KP_4 - force jump to
the next goal, probably ignore mobs to make things faster"; asked to choose: "Ignore mobs, resume on arrival").

The scripted level is test_hunt.py's: the character at world (5000, 5000) in a room with a corridor east, a pack of
five on the way at (5030, 5000), the mark at tile (1030.5, 1000.5), 152 units east. `Scripted` stands in for the hunter
where a test is about the jump's own rules: its teleport key's looks are given, each moving the character."""

import logging
import threading
from dataclasses import replace
from typing import cast

import pytest

from inventory_tracking.builds import pursuing
from inventory_tracking.game.records import Loot
from inventory_tracking.levels.model import Target
from inventory_tracking.macros.actuator import Hand
from inventory_tracking.macros.build import NoWay, Step
from inventory_tracking.macros.drinking import Drinker
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.hunt import Hunter
from inventory_tracking.macros.hunting.base import Judged
from inventory_tracking.macros.pursuit import PASSAGE, Move, Operate
from inventory_tracking.macros.routines import Dead
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.running import jump as jump_module
from inventory_tracking.macros.running.base import TELEPORT
from inventory_tracking.macros.running.jump import Jump, leap_of
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.routes.model import FIGHT, STAND
from tests.inventory_tracking.macros import test_hunt as hunts
from tests.inventory_tracking.macros.fakes import BUILD, Game, character_of, warlock
from tests.inventory_tracking.macros.test_runner import SAVED_GAMES, building, joined


FAR = Target(101, hunts.ROOMS, (1030.5, 1000.5), 'the far mark', 'poi', False, ())
MARK = Goal('the mark', (5150.0, 5000.0), STAND, 5.0, PRESSED)
BOSS = Goal('the boss', (5150.0, 5000.0), FIGHT, 20.0, PRESSED)


def far_jump(play: Game, hunter: Hunter, *, pursuit: bool = True) -> tuple[MacroRunner, list[str]]:
    """The teleport press made on `play` toward FAR, the build's pursuit on or off; the runner and the lines said."""
    runner, run, _ = building(play, hunter, builds=(pursuing(warlock(play.world), pursuit),))
    runner.target = lambda: FAR
    runner.perform(run, run.actuator, TELEPORT, hunts.keys)
    return runner, play.said


def test_the_jump_hops_through_a_pack_to_the_goal_without_a_strike():
    play = hunts.game(*hunts.pack(5))
    runner, said = far_jump(play, hunts.hunter(play))
    player = character_of(play.world)
    assert abs(player.x - 5152.5) < 1.0  # at the mark, past the pack
    keys = play.pressed()
    assert len(keys) >= 6
    assert set(keys) == {hunts.KEYS[hunts.BLADE_WARP]}  # hops alone: no strike, no mark, no swap for a fight
    assert hunts.KEYS[hunts.ECHOING_STRIKE] not in keys
    assert said[-1] == f'jump: the far mark: {len(keys)} hops in ' + said[-1].split(' hops in ')[1]
    assert said[-1].endswith('arrived: at the far mark')
    assert runner.attack_mode is False  # it was off: nothing is fought on arrival either


def test_with_no_pursuit_the_jump_is_the_plain_step_again_and_again_to_the_cards_mark():
    play = hunts.game()
    _, said = far_jump(play, hunts.hunter(play, pursuit=False), pursuit=False)
    assert abs(character_of(play.world).x - 5152.5) < 1.0
    assert said[-1].endswith('arrived: the step moved nothing more')
    assert said[-1].startswith('jump: the far mark: ')


def test_with_the_life_under_the_safety_floor_no_hop_is_made():
    play = hunts.game(*hunts.pack(5))
    play.loot = Loot(life=300, max_life=1000)
    _, said = far_jump(play, hunts.hunter(play))
    assert play.pressed() == []
    assert said[-1] == 'jump: no goal named: 0 hops in 0.0 s, life 300/1000, under the safety floor of 65%'


def test_a_valuable_in_reach_is_picked_up_before_the_first_hop():
    from tests.inventory_tracking.macros import test_pickup as drops

    play = hunts.game()
    play.loot = Loot((drops.RUNE,), drops.FULL, 1000, 1000)
    calls = []
    runner, run, _ = building(play, hunts.hunter(play))
    runner.target = lambda: FAR

    def pick_up(*args, **kwargs):
        calls.append(len(play.pressed()))
        play.loot = Loot()  # taken
        return True

    jump_module.pick_up, saved = pick_up, jump_module.pick_up  # the pickup's own clicks are test_pickup's
    try:
        runner.perform(run, run.actuator, TELEPORT, hunts.keys)
    finally:
        jump_module.pick_up = saved
    assert calls == [0]  # before any hop
    assert abs(character_of(play.world).x - 5152.5) < 1.0


# --- the jump's rules, the hunter scripted ----------------------------------------------------------------------------


class Scripted:
    """A hunter whose teleport key's looks (hunting/moves.py `pursue_once`) are given: (act, goal, where the character
    is after it, what happens then)."""

    pursuing = True
    level = None

    def __init__(self, play: Game, looks, *, leashed: bool = False) -> None:
        self.play, self.looks, self.leashed = play, list(looks), leashed
        self.drinker = Drinker()
        self.build = BUILD
        self.asked: list[bool] = []  # `attacking` of each look
        self.ended: list[str] = []

    def use(self, build) -> None:
        self.build = build

    def end_run(self, run, reason, seen=True) -> None:
        self.ended.append(reason)

    def pursue_once(self, run, key_names, *, attacking: bool) -> Judged | None:
        self.asked.append(attacking)
        act, goal, spot, then = self.looks.pop(0)
        self.play.clock.sleep(0.5)
        if spot is not None:
            moved = replace(character_of(self.play.world), x=spot[0], y=spot[1])
            self.play.world = replace(self.play.world, player=moved)
        if then is not None:
            then()
        return Judged(act, goal, None)


def hop(x: float, goal: Goal = MARK, then=None):
    return Move(Step((x, 5000.0)), goal), goal, (x, 5000.0), then


def at(goal: Goal = MARK):
    return NoWay(f'at {goal.label}', arrived=True), goal, None, None


RUNS: dict[int, Run] = {}  # each scripted runner's run (`perform`)


def scripted(looks, **changes) -> tuple[MacroRunner, Scripted, Game, list[str]]:
    play = hunts.game()
    hunter = Scripted(play, looks, **changes)
    runner, run, _ = building(play, cast(Hunter, hunter))
    RUNS[id(runner)] = run
    return runner, hunter, play, play.said


def perform(runner: MacroRunner) -> None:
    run = RUNS[id(runner)]
    runner.perform(run, run.actuator, TELEPORT, hunts.keys)


def test_each_look_is_priced_with_attack_mode_off_and_the_jump_goes_on_to_the_arrival():
    runner, hunter, _, said = scripted([hop(5020.0), hop(5040.0), hop(5060.0), at()])
    perform(runner)
    assert hunter.asked == [False, False, False, False]  # "ignore mobs": no hold, no strike gap
    assert said[-1] == 'jump: the mark: 3 hops in 2.0 s, arrived: at the mark'
    assert runner.attack_mode is False


def test_a_retreat_the_safety_chooses_ends_the_jump_and_attack_mode_resumes():
    retreat = Move(Step((4990.0, 5000.0)), MARK, 'retreating: no progress act fits the life budget')
    runner, hunter, _, said = scripted([hop(5020.0), (retreat, MARK, (4990.0, 5000.0), None), hop(5060.0)])
    runner.attack_mode = True
    perform(runner)
    assert len(hunter.looks) == 1  # no hop after the safety's answer
    assert said[-1].endswith('safety: retreating: no progress act fits the life budget')
    assert runner.attack_mode is True  # it was on: `_follow` resumes it, and it fights


def test_a_safety_refusal_with_no_move_ends_the_jump():
    vetoed = NoWay('safety: every act is vetoed; the least lethal is standing here')
    runner, _, play, said = scripted([hop(5020.0), (vetoed, MARK, None, None), hop(5060.0)])
    perform(runner)
    assert character_of(play.world).x == 5020.0
    assert said[-1].endswith('safety: every act is vetoed; the least lethal is standing here')


def test_a_drop_taken_on_the_way_is_no_arrival():
    drop = Goal('a rune', (5025.0, 5000.0), 'pick up', 2.0, PRESSED, unit=7)
    runner, _, _, said = scripted([hop(5020.0), (Operate(drop), drop, None, None), hop(5040.0), at()])
    perform(runner)
    assert said[-1].endswith('arrived: at the mark')


def test_on_arrival_attack_mode_is_on_for_a_level_run_and_for_a_fight():
    runner, _, _, _ = scripted([hop(5020.0), at()], leashed=True)
    perform(runner)
    assert runner.attack_mode is True
    runner, _, _, _ = scripted([hop(5020.0, BOSS), at(BOSS)])
    perform(runner)
    assert runner.attack_mode is True


def test_on_arrival_attack_mode_stays_off_when_the_player_turned_it_off_or_the_loop_runs():
    runner, _, _, _ = scripted([hop(5020.0, BOSS), at(BOSS)])
    runner.attack_declined = True
    perform(runner)
    assert runner.attack_mode is False
    runner, _, _, _ = scripted([hop(5020.0, BOSS), at(BOSS)])
    runner.loop.start()
    perform(runner)
    assert runner.attack_mode is False


def test_the_players_hand_stops_the_jump_and_turns_nothing_on(caplog):
    caplog.set_level(logging.INFO)
    runner, hunter, play, _ = scripted([])
    hunter.looks = [hop(5020.0, BOSS, then=lambda: setattr(play.keys, 'held', True)), hop(5040.0, BOSS), at(BOSS)]
    with pytest.raises(Hand, match='a key was pressed'):
        perform(runner)
    assert len(hunter.looks) == 2
    assert runner.attack_mode is False  # a fight's goal, but the hand had it: nothing is turned on
    assert any("jump: the boss: 1 hops in 0.5 s, the player's hand: a key was pressed" in m for m in caplog.messages)


def test_a_mouse_button_stops_the_jump():
    runner, hunter, play, _ = scripted([])

    def down() -> tuple[int, int, int]:
        return (*play.keys.at, 1 << 8)  # XQueryPointer's mask: the left button down

    hunter.looks = [hop(5020.0, then=lambda: setattr(play.keys, 'pointer_state', down)), hop(5040.0), at()]
    with pytest.raises(Hand, match='a mouse button was pressed'):
        perform(runner)
    assert len(hunter.looks) == 2


def test_after_a_death_nothing_more_is_done_and_the_loop_stops():
    runner, hunter, play, _ = scripted([])

    def dies() -> None:
        play.world = replace(play.world, player=replace(character_of(play.world), mode=0))

    hunter.looks = [hop(5020.0, BOSS, then=dies), hop(5040.0, BOSS), at(BOSS)]
    runner.attack_mode = True
    runner.loop.start()
    with pytest.raises(Dead):
        perform(runner)
    assert len(hunter.looks) == 2  # nothing pressed after it
    assert runner.attack_mode is False
    assert runner.loop.on is False
    assert hunter.ended == ['the character died']


def test_a_press_during_the_jump_gives_it_fresh_seconds(monkeypatch):
    monkeypatch.setattr(jump_module, 'JUMP_SECONDS', 1.2)
    looks = [hop(5000.0 + 20 * n) for n in range(1, 8)]
    runner, hunter, _, said = scripted(list(looks))
    perform(runner)
    assert said[-1].endswith('the next takes a press')
    assert len(hunter.asked) == 3  # 0.5 s each: 1.5 s past 1.2

    runner, hunter, _, said = scripted(list(looks))
    hunter.looks[1] = hop(5040.0, then=lambda: runner.jumping and runner.jumping.extend())
    perform(runner)
    assert len(hunter.asked) == 5  # 1.0 s after the press at 1.0: 2.5 s past 2.2


def test_a_press_during_a_jump_extends_it_and_queues_no_other_step():
    runs, going, go_on = [], threading.Event(), threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        runner.jumping = Jump()
        going.set()
        assert go_on.wait(5)
        presses.append(runner.jumping.presses)

    presses: list[int] = []
    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, execute=execute)
    runner.valuable_left = lambda: None
    assert runner.request(10.0, 10.1, TELEPORT)
    assert going.wait(5)
    assert runner.request(10.3, 10.4, TELEPORT)
    assert runner.queue.first() is None
    go_on.set()
    joined(runner)
    assert runs == [TELEPORT]
    assert presses == [1]
    runner.close()


def test_a_teleport_press_during_attack_mode_pauses_it_for_the_jump():
    runs, ended = [], threading.Event()

    def execute(cancelled, routine):
        runs.append(routine)
        if routine == 'hunt any':
            if len(runs) > 1:
                ended.set()
            assert cancelled.wait(5)
            raise jump_module.Cancelled

    runner = MacroRunner(None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, execute=execute, fallback=BUILD)
    runner.valuable_left = lambda: None
    runner.hunter = hunts.hunter(hunts.game())  # the pursuit on: the press was posted to the mode before the jump
    assert runner.pursuit
    assert runner.request(10.0, 10.1, 'hunt any')
    assert runner.request(10.3, 10.4, TELEPORT)
    assert ended.wait(5)
    assert runs == ['hunt any', TELEPORT, 'hunt any']
    runner.close()


@pytest.mark.parametrize(
    ('act', 'goal', 'on', 'why'),
    [
        (Move(Step((1.0, 0.0)), MARK), MARK, True, ''),
        (Move(Step((1.0, 0.0)), MARK, 'safe approach'), MARK, True, ''),
        (Move(Step((1.0, 0.0)), MARK, f'the door: {PASSAGE}'), MARK, True, ''),
        (Move(Step((1.0, 0.0)), MARK, 'firing spot'), MARK, False, 'safety: firing spot'),
        (Operate(MARK), MARK, False, 'arrived: the mark (stand)'),
        (NoWay('no way toward the mark: walls'), MARK, False, 'no way toward the mark: walls'),
    ],
)
def test_what_one_look_means_for_the_jump(act, goal, on, why):
    found = leap_of(Judged(act, goal, None))
    assert (found.on, found.why) == (on, why)
    assert found.goal == goal.label
