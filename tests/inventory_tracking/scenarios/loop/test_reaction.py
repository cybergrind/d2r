"""How soon attack mode strikes: situations on the scripted game, timed on its clock.

The clock only moves when the macro sleeps, so each bound here is on the pauses the loop makes
between seeing and striking: the idle nap, the pointer's steps and the pause after them, a key hold,
a mark cast first. A bound is in game ticks (TICK, 40 ms): the game takes input no finer than that.
The measured numbers in the reasons are this file's own, on the fakes' clock; the ones from play are
in evidence.py (letters a to g).
"""

import pytest

from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.levels.model import Walkable, pack_cells
from inventory_tracking.macros.hunt import TOUGH_POINTS
from tests.inventory_tracking.scenarios.loop.helpers import (
    CHAMPION,
    NO_MARK_SLOTS,
    TICK,
    appear,
    attack_mode,
    foe,
    game,
    hunter,
    vanish,
)


@pytest.fixture
def marks_all(monkeypatch):
    """Death Mark on whatever is strongest, as before 2026-10-11: these tests are about the mark's timing."""
    from inventory_tracking.macros import hunt as hunt_module

    monkeypatch.setattr(hunt_module, 'MARK_CASTS', 0)


CAST = 0.36  # the fakes' cast: 0.3 s of animation and the free frame before the next (0.36 s in the takes too)


def wall_at_5005() -> Walkable:
    """The character's room with a wall one sub-tile thick at world x = 5005, on the walk and the flight layer."""
    rows = ['.' * 25 + '#' + '.' * 14] * 40
    cells = pack_cells(''.join('0' if cell == '#' else '1' for row in rows for cell in row))
    return Walkable(996, 996, 8, 8, cells, flight=cells)


@pytest.mark.xfail(
    strict=True,
    reason='the idle loop looks every POLL (0.1 s) and the aim is 3 pointer steps and a pause: 0.10 to 0.20 s here '
    'by the phase of the nap; in the takes 165 ms at the median, 455 ms at p90 (evidence a, n=29)',
)
def test_a_monster_walking_into_reach_is_struck_within_three_ticks():
    waited = []
    for arrives in (1.0, 1.013, 1.031, 1.052, 1.077, 1.094):  # every phase of the idle nap
        play = game(slots=NO_MARK_SLOTS)
        attack_mode(play, hunter(play), until=3.0, events=[(arrives, appear(play, foe(10, 5008.0, 5000.0)))])
        waited.append(play.strike_presses()[0] - arrives)
    assert max(waited) <= 3 * TICK


@pytest.mark.parametrize('flags', [0, CHAMPION], ids=['a monster: Death Mark', 'an elite: the sigil and Death Mark'])
def test_the_first_strike_does_not_wait_for_the_mark_or_the_sigil(flags, marks_all):
    play = game(foe(10, 5008.0, 5000.0, flags))
    play.toughness[10] = 1000
    attack_mode(play, hunter(play), until=3.0)
    assert play.marks == [10]  # still cast, in the fight
    assert play.strike_presses()[0] <= 4 * TICK


def test_with_nothing_else_to_cast_the_first_strike_is_held_within_three_ticks_of_the_mode_coming_on():
    # The floor today: one look, one aim (0.096 s here; 207 ms in the logs, with the reads and the decision).
    play = game(foe(10, 5008.0, 5000.0), slots=NO_MARK_SLOTS)
    attack_mode(play, hunter(play), until=2.0)
    assert play.strike_presses()[0] <= 3 * TICK


def test_the_lined_monster_dying_moves_the_pointer_to_the_next_line_within_a_tick():
    # Two monsters on different bearings: no line takes both. The first dies at its third strike.
    play = game(foe(10, 5008.0, 5000.0), foe(11, 5000.0, 5009.0), slots=NO_MARK_SLOTS)
    play.toughness[10], play.toughness[11] = 3, 1000
    attack_mode(play, hunter(play), until=3.0)
    killed = max(at for at, unit in play.struck_at if unit == 10)
    aiming = [at for at, _ in play.moved_at if killed <= at < killed + CAST]
    assert aiming  # the pointer was put on the next line
    assert max(aiming) - killed <= TICK
    following = [(at, unit) for at, unit in play.struck_at if at > killed]
    assert following[0][1] == 11  # the very next cast goes to the monster left
    assert following[0][0] - killed <= CAST  # and no cast is lost for the aim


@pytest.mark.xfail(
    strict=True,
    reason='a monster out of reach for 0.2 s ends the fight: the input is let go, the mode naps, aims and presses '
    'again, 0.1 s late here; in the logs 43 of 358 fights that ended "Nothing left in reach" struck again within '
    '1 s, 539 ms after the end line at the median (evidence d)',
)
def test_a_monster_out_of_reach_for_a_moment_does_not_end_the_hold():
    monster = foe(10, 5008.0, 5000.0)
    play = game(monster, slots=NO_MARK_SLOTS)
    play.toughness[10] = 1000
    attack_mode(play, hunter(play), until=4.0, events=[(2.0, vanish(play, 10)), (2.2, appear(play, monster))])
    assert len(play.strike_presses()) == 1  # one hold through the gap
    before = max(at for at, _ in play.struck_at if at < 2.0)
    after = min(at for at, _ in play.struck_at if at > 2.2)
    assert after - before <= CAST + TICK  # the cast after the gap comes at the game's own rate


def test_a_reachable_monster_is_struck_at_once_while_an_elite_stands_behind_a_wall():
    play = game(foe(10, 5010.0, 5000.0, CHAMPION), foe(11, 5000.0, 5012.0), slots=NO_MARK_SLOTS)
    play.toughness[11] = 3
    attack_mode(play, hunter(play, ground=(wall_at_5005(),)), until=3.0)
    assert play.strike_presses()[0] <= 3 * TICK
    assert [unit for _, unit in play.struck_at] == [11, 11, 11]
    assert play.sigils == []  # nothing is cast at the elite it cannot reach


@pytest.mark.xfail(
    strict=True,
    reason="with the walled-off elite on the reachable monster's bearing the line is named after the elite, and the "
    'sigil is cast under it behind the wall before the first strike: 0.47 s here against 0.10 s',
)
def test_no_sigil_is_cast_under_an_elite_behind_a_wall_on_the_way_to_a_strike():
    play = game(foe(10, 5010.0, 5000.0, CHAMPION), foe(11, 5003.5, 5000.0), slots=NO_MARK_SLOTS)
    play.toughness[11] = 3
    attack_mode(play, hunter(play, ground=(wall_at_5005(),)), until=3.0)
    assert [unit for _, unit in play.struck_at] == [11, 11, 11]
    assert play.sigils == []
    assert play.strike_presses()[0] <= 3 * TICK


@pytest.mark.xfail(
    strict=True,
    reason='the stop for the main weapons leaves the strike input up 0.69 s here: the wait for a free character, the '
    'swap, a pause after a swap already seen in hand, a new aim; 850 ms at the median in the logs, 50 stops in 567 '
    'fights (evidence g)',
)
def test_the_swap_to_the_main_weapons_keeps_the_strike_up_half_a_second_at_most():
    count = int(TOUGH_POINTS / points_of(19, 101)) + 1  # a pack worth the swap
    pack = [foe(100 + index, 5004.0 + index % 8, 4996.0 + index // 8) for index in range(count)]
    play = game(*pack, slots=NO_MARK_SLOTS)
    for monster in pack:
        play.toughness[monster.unit_id] = 1000
    play.sets.reverse()  # the staff's set in hand, as after a hop
    attack_mode(play, hunter(play), until=4.0)
    assert play.pressed().count('c') == 1
    released, pressed = play.strike_releases()[0], play.strike_presses()[1]
    assert pressed - released <= 0.5
