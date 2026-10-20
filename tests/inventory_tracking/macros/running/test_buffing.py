"""The attack mode key's active modes and buff mode (macros/running/buffing.py; the player, 2026-10-19: "KP_3 - toggle
attack mode, let's add double tap to cycle different active modes (ATTACK, BUFF - where buff - we keep desired buffs
active)")."""

import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.builds.warlock.skills import HEX_PURGE
from inventory_tracking.game.memory import CTA_CODE
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.actuator import Cancelled
from inventory_tracking.macros.buffmode import REST
from inventory_tracking.macros.build import Buff, Casting, Tried
from inventory_tracking.macros.cta import BATTLE_COMMAND, BATTLE_ORDERS
from inventory_tracking.macros.routines import Dead, swap_until
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.running.base import ATTACK, BUFF
from tests.inventory_tracking.macros.fakes import BUILD, KEYS, OTHER_SET, PREBUFF_SET, SLOTS, Game, player, world


LOWER_KURAST = 79
SAVED_GAMES = Path('/nonexistent/Saved Games')


CTA_KEYS = {**KEYS, BATTLE_COMMAND: 'F7', BATTLE_ORDERS: 'F8'}


def keys(_world, skills=None):
    return {skill: CTA_KEYS[skill] for skill in skills or ()}


# --- the presses ------------------------------------------------------------------------------------------------------


def make() -> tuple[MacroRunner, list[str], list[list[str]]]:
    """A runner whose modes' runs only wait to be cancelled and whose steps end at once, with the routines started
    and the cards shown."""
    runs: list[str] = []
    shown: list[list[str]] = []

    def execute(cancelled: threading.Event, routine: str) -> None:
        runs.append(routine)
        if routine in (ATTACK, BUFF, 'loop'):
            assert cancelled.wait(5)
            raise Cancelled

    runner = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=SAVED_GAMES, display=shown.append, execute=execute
    )
    runner.valuable_left = lambda: None
    return runner, runs, shown


def settled(runner: MacroRunner, test, seconds: float = 3.0) -> None:
    """Wait for the presses' window to close and `test()` to hold."""
    if runner.mode_timer is not None:
        runner.mode_timer.join(seconds)
    ends = time.monotonic() + seconds
    while not test():
        assert time.monotonic() < ends, 'not settled'
        time.sleep(0.01)


def working(runner: MacroRunner, routine: str | None):
    return lambda: (runner.routine if runner.working else None) == routine


def said(shown: list[list[str]]) -> list[str]:
    return [line for card in shown for line in card]


def test_one_press_toggles_attack_mode_at_once_as_before():
    runner, runs, _ = make()
    assert runner.request(10.0, 10.0, ATTACK)
    assert runner.attack_mode  # at once: no wait for the window
    settled(runner, working(runner, ATTACK))
    assert runner.run_badge == 'ATT PICK:GOOD'
    assert runner.request(11.0, 11.0, ATTACK)
    assert not runner.attack_mode
    settled(runner, working(runner, None))
    assert runs == [ATTACK]
    runner.close()


def test_a_double_press_with_no_mode_on_picks_buff_mode_and_starts_nothing():
    runner, runs, shown = make()
    assert runner.request(10.0, 10.0, ATTACK)
    assert runner.request(10.2, 10.2, ATTACK)
    settled(runner, lambda: runner.active == BUFF and not runner.working)
    assert not runner.attack_mode
    assert not runner.buff_mode
    assert 'Macro: Active mode: BUFF' in said(shown)  # said as `Pickup: GOOD`
    assert runner.run_badge == 'PICK:GOOD'
    # Then one press turns buff mode on, and the HUD says so
    assert runner.request(12.0, 12.0, ATTACK)
    settled(runner, working(runner, BUFF))
    assert runner.buff_mode
    assert runner.run_badge == 'BUFF PICK:GOOD'
    assert runner.request(13.0, 13.0, ATTACK)
    settled(runner, working(runner, None))
    assert not runner.buff_mode
    assert runs[-1] == BUFF
    runner.close()


def test_a_double_press_switches_a_running_mode_in_place():
    runner, runs, shown = make()
    assert runner.request(10.0, 10.0, ATTACK)
    settled(runner, working(runner, ATTACK))
    assert runner.request(11.0, 11.0, ATTACK)
    assert runner.request(11.25, 11.25, ATTACK)
    settled(runner, working(runner, BUFF))
    assert runner.buff_mode
    assert not runner.attack_mode
    assert runner.attack_declined  # the player chose no fight: a teleport press's fight leaves attack mode off
    assert 'Macro: Active mode: BUFF' in said(shown)
    # And back: buff mode to attack mode, in place
    assert runner.request(12.0, 12.0, ATTACK)
    assert runner.request(12.2, 12.2, ATTACK)
    settled(runner, working(runner, ATTACK))
    assert runner.attack_mode
    assert not runner.buff_mode
    assert runner.active == ATTACK
    assert runs == [ATTACK, BUFF, ATTACK]
    runner.close()


def test_a_mashed_key_switches_no_mode():
    runner, _, shown = make()
    for at in (10.0, 10.1, 10.2):
        assert runner.request(at, at, ATTACK)
    settled(runner, lambda: not runner.mode_taps)
    assert runner.active == ATTACK
    assert any('pressed 3 times together: no mode switched' in line for line in said(shown))
    runner.close()


def test_buff_mode_pauses_for_a_step_and_resumes_after_it():
    runner, runs, _ = make()
    runner.active = BUFF
    assert runner.request(10.0, 10.0, ATTACK)
    settled(runner, working(runner, BUFF))
    assert runner.request(11.0, 11.0, 'teleport')
    settled(runner, lambda: runs[-1] == BUFF and len(runs) == 3)
    assert runs == [BUFF, 'teleport', BUFF]
    runner.close()


def test_buff_mode_yields_to_the_loop():
    runner, _runs, _ = make()
    runner.active = BUFF
    assert runner.request(10.0, 10.0, ATTACK)
    settled(runner, working(runner, BUFF))
    with runner.lock:
        runner._toggle_loop()
    settled(runner, working(runner, 'loop'))
    assert runner.buff_mode  # wanted again once the loop is off
    assert runner.run_badge is not None
    assert runner.run_badge.startswith(runner.loop.kind.word)
    runner.close()


# --- the routine ------------------------------------------------------------------------------------------------------


def buffing(play: Game, until: float) -> tuple[MacroRunner, list[float]]:
    """Buff mode on `play` until the clock passes `until` (cancelled then); the casts of Hex: Purge."""
    runner, _, _ = make()
    run = play.run()
    play.arrivals.append((until, run.cancelled.set))
    with pytest.raises(Cancelled):
        runner._keep_buffs(run, keys)
    return runner, play.purges


def out_of_town(**changes) -> Game:
    return Game(world(LOWER_KURAST, player=player(LOWER_KURAST, hex_purge=False, **changes)))


def test_buff_mode_casts_a_buff_whose_state_is_off():
    play = out_of_town()
    _, purges = buffing(play, 3.0)
    assert len(purges) == 1  # cast once: the state shows it after
    assert 'Buff mode on' in play.said
    assert not play.walks
    assert not play.strikes


def test_buff_mode_casts_again_when_the_buff_runs_out():
    play = out_of_town()

    def lapsed():
        play.world = replace(play.world, player=replace(play.character, hex_purge=False))

    play.arrivals.append((5.0, lapsed))
    _, purges = buffing(play, 10.0)
    assert len(purges) == 2
    assert purges[1] >= 5.0


def test_buff_mode_renews_a_self_ending_buff_before_it_ends():
    # A row that lasts 60 s (buffs.py `lapsing`): cast again within RENEW_AHEAD of its end, not before
    row = Buff(HEX_PURGE, 'upkeep', lambda facts: facts.lapsing, lasts=60.0)
    play = out_of_town()
    play.build = replace(BUILD, buffs=(row,))
    runner, _, _ = make()
    runner.lasting[HEX_PURGE] = 0.0  # cast at the clock's start
    run = play.run()
    run.lasting = runner.lasting
    play.arrivals.append((50.0, run.cancelled.set))
    with pytest.raises(Cancelled):
        runner._keep_buffs(run, keys)
    assert len(play.purges) == 1
    assert 60.0 - 15.0 <= play.purges[0] < 60.0  # RENEW_AHEAD before its end


def test_the_players_hand_wins():
    play = out_of_town()
    play.keys.held = True  # the player holds a key all along
    _, purges = buffing(play, 3.0)
    assert purges == []


def test_a_cast_waits_for_the_hand_to_rest():
    play = out_of_town()
    for at in (0.0, 0.5, 1.0, 1.5, 2.0):
        play.arrivals.append((at, lambda at=at: setattr(play.keys, 'at', (2000 + int(100 * at), 700))))
    _, purges = buffing(play, 6.0)
    assert len(purges) == 1
    assert purges[0] >= 2.0 + REST  # the last move of the mouse, then the rest


@pytest.mark.parametrize(('area', 'panels'), [(109, ()), (LOWER_KURAST, ('inventory',))])
def test_no_cast_in_town_or_with_a_panel_open(area, panels):
    play = Game(world(area, open_panels=panels, player=player(area, hex_purge=False)))
    _, purges = buffing(play, 3.0)
    assert purges == []


def test_after_a_death_nothing_is_pressed():
    play = out_of_town(mode=0)  # DEAD
    runner, _, _ = make()
    run = play.run()
    with pytest.raises(Dead):
        runner._keep_buffs(run, keys)
    assert play.pressed() == []


def call_to_arms_game(*monsters: Monster) -> tuple[Game, MacroRunner, list[str]]:
    """Buff mode for 8 s with a Call to Arms worn and Battle Orders off; the keys pressed."""
    slots = (*SLOTS[:13], BATTLE_COMMAND, BATTLE_ORDERS, *SLOTS[15:])
    here = player(LOWER_KURAST, battle_orders=False)
    play = Game(world(LOWER_KURAST, slots=slots, player=here, monsters=monsters))
    play.staff = None
    play.sets = [PREBUFF_SET, (CTA_CODE, 'uit')]
    react = play.keys.on_event

    def shown(event) -> None:
        react(event)
        if event == ('key', 'F8'):  # Battle Orders shows on the character after its cast
            play.world = replace(play.world, player=replace(play.character, battle_orders=True))

    play.keys.on_event = shown
    runner, _, _ = make()
    run = play.run()
    run.cta = lambda: True
    play.arrivals.append((8.0, run.cancelled.set))
    with pytest.raises(Cancelled):
        runner._keep_buffs(run, keys)
    return play, runner, play.pressed()


def test_battle_orders_from_the_call_to_arms_with_no_hostile_near_and_the_set_back_after():
    play, _, pressed = call_to_arms_game()
    assert [key for key in pressed if key in ('c', 'F7', 'F8')] == ['c', 'F7', 'F8', 'c']
    assert play.sets[0] == PREBUFF_SET


def test_no_weapon_swap_with_a_hostile_near():
    play, _, pressed = call_to_arms_game(Monster(9, 100, 1, 5010.0, 5000.0))
    assert 'c' not in pressed
    assert play.sets[0] == PREBUFF_SET


def test_a_set_a_cast_left_in_hand_is_swapped_back():
    # A row cast with a set of its own that leaves it in hand (as Consume's renewal leaves the prebuff set)
    def swapper(cast: Casting) -> Tried:
        hands = cast.run.hands
        assert hands is not None
        swap_until(cast.run, lambda: hands() == OTHER_SET)
        return Tried(cast.run.clock(), cast=True)

    row = Buff(HEX_PURGE, 'upkeep', lambda facts: facts.since(HEX_PURGE) > 100, needs='prebuff', caster='swap')
    play = out_of_town()
    play.build = replace(BUILD, buffs=(row,), casters={'swap': swapper})
    buffing(play, 3.0)
    assert play.pressed().count('c') == 2
    assert play.sets[0] == PREBUFF_SET
