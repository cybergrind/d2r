"""The fight-efficiency switches of 2026-10-23 (rca/2026-10-23/fight-efficiency-findings.md): the dance budget keyed
on the fight's unit (judging.py DANCE_BY_UNIT), no walk back into a pack the hop just left while it comes on
(HELD_OFF), the strike kept while it still kills (YIELD_KEEPS_KILLING), and a drop's guard fight that is at the drop
and makes progress (choice.py GUARD_AT_DROP, GUARD_STALL)."""

import math
from typing import TYPE_CHECKING, cast

import pytest

from inventory_tracking.combat.harm import Harm
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.goals import PICK_UP, Goal
from inventory_tracking.macros.hunting import choice, judging
from inventory_tracking.macros.hunting.base import Judged
from inventory_tracking.macros.pursuit import FULL, Candidate, Facts, Hold, Move, NoWay, Pursuit
from inventory_tracking.macros.travel import PRESSED, Step
from inventory_tracking.routes.model import FIGHT
from tests.inventory_tracking.macros.test_hunt import foe, game, hunter


if TYPE_CHECKING:
    from inventory_tracking.macros.engine import Run


HERE = (5000.0, 5000.0)


def harm(worst: float = 0.0) -> Harm:
    return Harm(mean=worst, worst=worst, losses=(worst,))


def facts(*candidates: Candidate, now: float = 10.0) -> Facts:
    return Facts(now, None, False, True, True, lambda: NoWay('none'), 101, candidates=candidates, priced=True,
                 budget=1000.0, life=2943.0)  # fmt: skip


def mover(spot, reason: str = '', *, retreat: bool = False, dodge: bool = False) -> Candidate:
    goal = Goal('full clear: the elite 14 (3339623512)', (5030.0, 5000.0), FIGHT, 22.0, PRESSED, unit=3339623512)
    return Candidate(Move(Step(spot), goal, reason, dodge=dodge), 0.5, harm(), retreat, 0.5, True)


def holding(worst: float = 0.0) -> Candidate:
    return Candidate(Hold(), 1.0, harm(worst), False, 0.0, True)


# --- DANCE_BY_UNIT: take 20261023T113952Z-57, 14:40:07-48: two labels on one Herald, the place moving ---


def dance_goal(label: str, place) -> Goal:
    return Goal(label, place, FIGHT, 22.0, PRESSED, unit=1877455282, clearing=True)


def retreat_of(goal: Goal) -> Move:
    return Move(Step((4990.0, 5000.0)), goal, 'retreating: every progress act is vetoed (kept at range)')


@pytest.mark.parametrize(('switch', 'fires'), [(True, True), (False, False)])
def test_the_dance_clock_runs_across_the_labels_and_places_of_one_fight(monkeypatch, switch, fires):
    monkeypatch.setattr(judging, 'DANCE_BY_UNIT', switch)
    herald = foe(1877455282, 5025.0, 5000.0, life=120, max_life=128)
    play = game(herald)
    hunted = hunter(play)
    labels = ('Amethyst, on the way: the fight first (1 in the way)', 'full clear: the elite 101 (1877455282)')
    said = None
    for look in range(14):
        goal = dance_goal(labels[look % 2], (5025.0 + look * 0.7, 5000.0))
        said = judging.danced(hunted, play.world, goal, retreat_of(goal), 1.0 + 0.45 * look) or said
    assert (said is not None) is fires


# --- HELD_OFF: take 20261023T123721Z-106, 15:39:59.55 hop, 59.99 "safe approach" 3 units back in, 01.06 hop again ---

MEMBER = 2135887389


def held(monkeypatch, member_at, *, switch=True, now=10.0):
    monkeypatch.setattr(judging, 'HELD_OFF', switch)
    member = foe(MEMBER, *member_at, txt_id=140, life=127, max_life=128)
    play = game(member)
    hunted = hunter(play)
    hunted.held_off = judging.HeldOff(now - 0.6, 101, {MEMBER: (5017.0, 5000.0)})
    return play, hunted, member


def test_a_safe_approach_toward_a_pack_that_comes_on_is_not_made(monkeypatch, caplog):
    play, hunted, member = held(monkeypatch, (5014.0, 5000.0))  # 3 units nearer than at the hop's look
    approach = mover((5004.0, 5000.0), judging.SAFE_APPROACH)
    away = mover((4985.0, 5000.0), 'retreating within strike reach', retreat=True)
    found = facts(approach, holding(), away)
    with caplog.at_level('INFO'):
        kept, waits = judging.hold_off(hunted, play.world, [member], found, False, 10.0)
    assert kept.candidates == (found.candidates[1], away)
    assert waits is None
    assert '(HELD_OFF)' in caplog.text


def test_with_only_the_approach_priced_the_look_waits_for_the_pack(monkeypatch):
    play, hunted, member = held(monkeypatch, (5014.0, 5000.0))
    kept, waits = judging.hold_off(hunted, play.world, [member], facts(mover((5004.0, 5000.0))), False, 10.0)
    assert kept.candidates == ()
    assert waits is not None
    assert waits.startswith(judging.HELD_OFF_SAID)


@pytest.mark.parametrize(
    ('member_at', 'advanced', 'now', 'switch'),
    [
        ((5017.0, 5000.0), False, 10.0, True),  # it stands: gone to as before
        ((5014.0, 5000.0), True, 10.0, True),  # a fresh advance press goes
        ((5014.0, 5000.0), False, 13.0, True),  # past HELD_OFF_SECONDS
        ((5014.0, 5000.0), False, 10.0, False),  # the switch off
    ],
)
def test_the_hold_ends_when_the_pack_stands_or_the_press_goes(monkeypatch, member_at, advanced, now, switch):
    play, hunted, member = held(monkeypatch, member_at, switch=switch, now=10.0)
    found = facts(mover((5004.0, 5000.0), judging.SAFE_APPROACH))
    kept, waits = judging.hold_off(hunted, play.world, [member], found, advanced, now)
    assert kept is found
    assert waits is None


def test_a_member_dead_or_out_of_the_read_ends_the_hold(monkeypatch):
    play, hunted, _member = held(monkeypatch, (5014.0, 5000.0))
    found = facts(mover((5004.0, 5000.0)))
    kept, _ = judging.hold_off(hunted, play.world, [], found, False, 10.0)
    assert kept is found
    assert hunted.held_off is None


def test_a_move_away_or_a_dodge_stays_and_a_firing_spot_into_the_pack_goes(monkeypatch):
    play, hunted, member = held(monkeypatch, (5014.0, 5000.0))
    side = mover((5000.0, 5012.0))  # no nearer the member than here
    dodge = mover((5006.0, 5000.0), 'stepping out of a charge', dodge=True)
    firing = mover((5005.0, 5000.0), 'firing spot')
    kept, _ = judging.hold_off(hunted, play.world, [member], facts(side, dodge, firing), False, 10.0)
    assert [c.act for c in kept.candidates] == [side.act, dodge.act]


def test_the_keep_range_hop_holds_off_what_it_leaves(monkeypatch):
    monkeypatch.setattr(judging, 'HELD_OFF', True)
    near, far = foe(51, 5016.0, 5000.0), foe(52, 5040.0, 5000.0)
    play = game(near, far)
    hunted = hunter(play)
    reason = 'pack: keeping range: mana burn: 1 of the pack on the character within 18'
    hop = mover((4985.0, 5000.0), reason, dodge=True)
    judging.note_hold_off(hunted, play.world, [near, far], hop.act, 5.0)
    assert hunted.held_off is not None
    assert set(hunted.held_off.seen) == {51}
    monkeypatch.setattr(judging, 'HELD_OFF', False)
    hunted.held_off = None
    judging.note_hold_off(hunted, play.world, [near, far], hop.act, 5.0)
    assert hunted.held_off is None


# --- YIELD_KEEPS_KILLING: 16:41:07.3, "1 casts seen in 0.2s; Yielded" for "a group of 7" 51 away, 2 of 40 in reach ---


def asked(monkeypatch, *, reason='', kill_ago=0.5, worst=0.0, tier=0, switch=True, rush=False, goal_do=FIGHT):
    monkeypatch.setattr(judging, 'YIELD_KEEPS_KILLING', switch)
    monkeypatch.setattr(judging, 'HELD_STRIKES_ON', False)
    monkeypatch.setattr(judging, 'PACK_FIGHT_FIRST', False)
    judging.KEEPS_SAID.clear()
    member = foe(61, 5012.0, 5000.0, txt_id=96, tier=tier, life=100, max_life=128)
    play = game(member)
    hunted = hunter(play)
    monkeypatch.setattr(type(hunted), 'pursuing', property(lambda _self: True))
    run = play.run()
    goal = Goal('full clear: a group of 7', (5051.0, 5000.0), goal_do, 22.0, PRESSED, clearing=True)
    posted = Pursuit('pickup', 1.0, advance=False, leash=FULL, rush=rush)
    found = Judged(Move(Step((5030.0, 5000.0)), goal, reason), goal, goal.place, posted, False)
    monkeypatch.setattr(hunted, 'judge', lambda *_a, **_k: found)
    monkeypatch.setattr(hunted, 'pursuit', posted)
    hunted.judged = (1.0, -10.0, False)
    hunted.look_facts = facts(holding(worst), Candidate(found.act, 0.3, harm(), False, 0.3, True))
    now = run.clock()
    world = play.world
    hunted.killing = (now - kill_ago, frozenset(), {61: 100})  # the look before saw the same life
    return hunted, run, world, member


def test_the_fight_that_still_kills_keeps_its_strikes_from_the_goals_move(monkeypatch, caplog):
    hunted, run, world, member = asked(monkeypatch)
    with caplog.at_level('INFO'):
        assert not hunted.key_asks(run, world, [member], Ground(()))
    assert '(YIELD_KEEPS)' in caplog.text


@pytest.mark.parametrize(
    'changes',
    [
        {'kill_ago': 3.0},  # no kill or damage for 3 s
        {'worst': 5000.0},  # the hold over the life budget: the move goes
        {'reason': 'firing spot'},  # the safety's better place still goes
        {'reason': 'pack: keeping range: 1 of the pack on the character within 10'},
        {'rush': True},  # the KP_6 loop's rushed run
        {'goal_do': PICK_UP},  # a pickup on the way is the goal's own move too: the strikes stay
        {'switch': False},
    ],
)
def test_the_move_still_goes(monkeypatch, changes):
    hunted, run, world, member = asked(monkeypatch, **changes)
    expected = changes.get('goal_do') == PICK_UP
    assert hunted.key_asks(run, world, [member], Ground(())) is not expected


def test_a_herald_pack_in_reach_keeps_the_strikes_with_no_kill_yet(monkeypatch):
    hunted, run, world, member = asked(monkeypatch, kill_ago=4.0, tier=5)
    assert not hunted.key_asks(run, world, [member], Ground(()))


def test_damage_in_reach_is_the_fights_progress_and_a_raised_ones_is_not(monkeypatch):
    monkeypatch.setattr(judging, 'YIELD_KEEPS_KILLING', True)
    hit = foe(71, 5010.0, 5000.0, life=90, max_life=128)
    play = game(hit)
    hunted = hunter(play)
    hunted.killing = (-math.inf, frozenset(), {71: 100})
    assert judging.fight_kills(hunted, play.world, HERE, 7.0) == 7.0
    hunted.killing = (-math.inf, frozenset(), {71: 100})
    hunted.slain = (101, frozenset({71}))  # seen dead before on the level: raised
    assert judging.fight_kills(hunted, play.world, HERE, 7.0) == -math.inf
    far = foe(72, 5060.0, 5000.0, life=10, max_life=128)
    play = game(far)
    hunted = hunter(play)
    hunted.killing = (-math.inf, frozenset(), {72: 100})
    assert judging.fight_kills(hunted, play.world, HERE, 7.0) == -math.inf  # out of the strike's reach


# --- GUARD_AT_DROP / GUARD_STALL: 16:11:13-39, take 20261023T130907Z-67, the Topaz 0.7 off, the Herald 80 off ---

TOPAZ = Goal('Flawless Topaz, on the way', (22767.0, 6626.0), PICK_UP, 4.0, PRESSED, unit=3001)


@pytest.mark.parametrize(
    ('guard_at', 'here', 'guards'),
    [
        ((22722.4, 6693.4), (22767.5, 6626.5), False),  # the Herald 80 off both
        ((22770.0, 6630.0), (22767.5, 6626.5), True),  # by the drop
        ((22790.0, 6650.0), (22781.5, 6643.5), True),  # by the character (the agenda's rule)
    ],
)
def test_the_drops_guard_is_one_at_the_drop_or_the_character(guard_at, here, guards):
    assert choice.at_the_drop(foe(81, *guard_at), TOPAZ, here) is guards


def topaz_run(monkeypatch, guard_at, *, at_drop=True, stall=False):
    monkeypatch.setattr(choice, 'GUARD_AT_DROP', at_drop)
    monkeypatch.setattr(choice, 'GUARD_STALL', stall)
    choice.GUARD_SAID.clear()
    from inventory_tracking.macros.agenda import KILL, Objective

    guard = foe(81, *guard_at, life=100, max_life=128)
    play = game(guard)
    play.world = replace_player(play.world, (22767.5, 6626.5))
    hunted = hunter(play)
    monkeypatch.setattr(
        hunted, 'agenda_target', lambda *_a, **_k: Objective(KILL, 'the elite 103', 0, 101, guard_at, 81)
    )
    return play, hunted, guard


def replace_player(world, at):
    from dataclasses import replace

    assert world.player is not None
    return replace(world, player=replace(world.player, x=at[0], y=at[1]))


@pytest.mark.parametrize(('guard_at', 'switch', 'fight'), [
    ((22722.4, 6693.4), True, False),
    ((22722.4, 6693.4), False, True),
    ((22770.0, 6630.0), True, True),
])  # fmt: skip
def test_a_far_kill_target_is_no_guard_of_the_drop(monkeypatch, guard_at, switch, fight):
    play, hunted, guard = topaz_run(monkeypatch, guard_at, at_drop=switch)
    found = choice.agenda_cleared(hunted, play.run(), play.world, [guard], Ground(()), TOPAZ)
    assert found is not None
    assert (found.do == FIGHT) is fight


def test_a_guard_fight_with_no_progress_frees_the_drop(monkeypatch, caplog):
    play, hunted, _guard = topaz_run(monkeypatch, (22770.0, 6630.0), stall=True)
    here = (22767.5, 6626.5)
    with caplog.at_level('INFO'):
        stalled = [choice.guard_stalled(hunted, play.world, TOPAZ, here, 1.0 + 0.5 * k) for k in range(12)]
    assert stalled.index(True) == 10  # 5 s after the watch began
    assert all(stalled[10:])
    assert '(GUARD_STALL)' in caplog.text


def test_damage_to_the_guard_keeps_the_fight_first(monkeypatch):
    play, hunted, guard = topaz_run(monkeypatch, (22770.0, 6630.0), stall=True)
    here = (22767.5, 6626.5)
    from dataclasses import replace

    for k in range(12):
        life = 100 - 5 * k
        play.world = replace(play.world, monsters=(replace(guard, life=life),))
        assert not choice.guard_stalled(hunted, play.world, TOPAZ, here, 1.0 + 0.5 * k)


def test_the_stall_switch_off_never_frees(monkeypatch):
    play, hunted, _guard = topaz_run(monkeypatch, (22770.0, 6630.0), stall=False)
    assert not any(choice.guard_stalled(hunted, play.world, TOPAZ, (22767.5, 6626.5), 1.0 + k) for k in range(12))


# --- REFUSED_PASS: canyon-death-1452 with READ_THROWS (the death agent's trace): land by the elite, 1-2 casts,
# "retreating: no progress act fits the life budget", back to the same elite, 37 hops ---

SLINGER = 3167950388
CANYON = (12652.0, 5328.0)


def refused_run(monkeypatch, *, switch=True):
    monkeypatch.setattr(judging, 'REFUSED_PASS', switch)
    elite = foe(SLINGER, *CANYON, txt_id=376, life=120, max_life=128)
    play = game(elite)
    return play, hunter(play)


def slinger_goal(label='full clear: the elite 376 (3167950388): clearing the way (15 near)', place=CANYON) -> Goal:
    return Goal(label, place, FIGHT, 22.0, PRESSED, unit=SLINGER, clearing=True)


def refusal(goal: Goal) -> Move:
    return Move(Step((12630.0, 5345.0)), goal, 'retreating: no progress act fits the life budget')


def approach(goal: Goal) -> Move:
    return Move(Step((12645.0, 5335.0)), goal, '')


def refusals(hunted, world, times, *, start=1.0, gap=2.5):
    said = None
    for n in range(times):
        goal = slinger_goal(place=(CANYON[0] + n, CANYON[1]))
        judging.refused(hunted, world, goal, approach(goal), start + gap * n - 1.0)  # the approach between: no reset
        said = judging.refused(hunted, world, goal, refusal(goal), start + gap * n)
    return said


@pytest.mark.parametrize(('switch', 'fires'), [(True, True), (False, False)])
def test_four_retreats_from_one_fight_with_no_kill_give_it_up(monkeypatch, switch, fires):
    play, hunted = refused_run(monkeypatch, switch=switch)
    assert refusals(hunted, play.world, judging.REFUSED_TIMES - 1) is None
    goal = slinger_goal()
    said = judging.refused(hunted, play.world, goal, refusal(goal), 8.5)
    assert (said is not None) is fires
    if said is not None:
        assert '(REFUSED_PASS)' in said


def test_a_kill_at_the_fight_counts_the_retreats_again(monkeypatch):
    from dataclasses import replace

    play, hunted = refused_run(monkeypatch)
    refusals(hunted, play.world, judging.REFUSED_TIMES - 1)
    dead = replace(foe(12345, CANYON[0] + 5.0, CANYON[1], txt_id=376), mode=0)
    world = replace(play.world, monsters=(*play.world.monsters, dead))
    goal = slinger_goal()
    assert judging.refused(hunted, world, goal, refusal(goal), 9.0) is None
    assert hunted.refusals is not None
    assert hunted.refusals[1] == 1


def test_retreats_far_apart_in_time_or_place_are_no_count(monkeypatch):
    play, hunted = refused_run(monkeypatch)
    refusals(hunted, play.world, judging.REFUSED_TIMES - 1)
    goal = slinger_goal()
    assert judging.refused(hunted, play.world, goal, refusal(goal), 30.0) is None  # past REFUSED_LAPSE
    refusals(hunted, play.world, judging.REFUSED_TIMES - 1, start=40.0)
    far = slinger_goal(place=(CANYON[0] + 80.0, CANYON[1]))
    assert judging.refused(hunted, play.world, far, refusal(far), 49.0) is None


def test_a_kept_goal_or_a_dodge_is_no_refusal(monkeypatch):
    play, hunted = refused_run(monkeypatch)
    drop = Goal('Flawless Ruby', CANYON, PICK_UP, 2.0, PRESSED, unit=99)
    for n in range(6):
        assert judging.refused(hunted, play.world, drop, refusal(drop), 1.0 + n) is None
    goal = slinger_goal()
    dodge = Move(Step((12630.0, 5345.0)), goal, 'retreating: stepping out', dodge=True)
    for n in range(6):
        assert judging.refused(hunted, play.world, goal, dodge, 10.0 + n) is None


def test_the_refused_fight_is_passed_and_the_tour_keeps_off_it(monkeypatch, caplog):
    play, hunted = refused_run(monkeypatch)
    refusals(hunted, play.world, judging.REFUSED_TIMES - 1)
    goal = slinger_goal()
    caplog.set_level('INFO')
    run = cast('Run', None)  # read only on the KP_6 loop's rushed run
    assert judging.no_progress(hunted, run, play.world, goal, refusal(goal), 9.0, None)
    assert '(REFUSED_PASS)' in caplog.text
    assert hunted.passed  # the goal and the hostiles round it
    assert choice.refused_near(hunted, (CANYON[0] + 20.0, CANYON[1]), 10.0)
    assert not choice.refused_near(hunted, (CANYON[0] + 60.0, CANYON[1]), 10.0)
    assert not choice.refused_near(hunted, (CANYON[0] + 20.0, CANYON[1]), 9.0 + choice.PASS_SECONDS + 1.0)


# --- SLOW_FIGHT: take 20261023T154020Z-94, Ruined Temple 18:40:56-18:41:41: a tier 5 Herald pack of Wailing Beasts,
# immune to magic, the Herald 127 -> 119/128 in 45 s of "held until it dies" ---

HERALD = 3249094580


def beasts(herald_life: int, member_life: int, *, away: float = 15.0):
    return (
        foe(HERALD, HERE[0] + away, HERE[1], txt_id=27, life=herald_life, max_life=128),
        *(foe(1142590459 + n, HERE[0] + away + n, HERE[1] + 2.0, txt_id=27, life=member_life, max_life=128)
          for n in range(6)),
    )  # fmt: skip


def temple_goal(away: float = 15.0) -> Goal:
    return Goal('full clear: the elite 27 (3249094580): clearing the way (10 near)', (HERE[0] + away, HERE[1]), FIGHT,
                22.0, PRESSED, unit=HERALD, clearing=True)  # fmt: skip


def slow_looks(monkeypatch, lives, *, switch=True, away=15.0):
    """`lives`: (herald, member) at each look, one a second; the last look's verdict."""
    from dataclasses import replace

    monkeypatch.setattr(judging, 'SLOW_FIGHT', switch)
    play = game(*beasts(*lives[0], away=away))
    hunted = hunter(play)
    said = None
    for n, (herald_life, member_life) in enumerate(lives):
        world = replace(play.world, monsters=beasts(herald_life, member_life, away=away))
        said = judging.slow_fight(hunted, world, temple_goal(away), float(n))
    return said, hunted


@pytest.mark.parametrize(('switch', 'fires'), [(True, True), (False, False)])
def test_a_fight_that_takes_almost_nothing_off_is_given_up(monkeypatch, switch, fires):
    lives = [(127 - n // 3, 120 - n // 2) for n in range(12)]  # 4 + 6 x 5 of life in 11 s: 750 left, ~270 s more
    said, _ = slow_looks(monkeypatch, lives, switch=switch)
    assert (said is not None) is fires
    if said is not None:
        assert '(SLOW_FIGHT)' in said


def test_a_fight_that_kills_at_a_pace_goes_on(monkeypatch):
    lives = [(max(1, 127 - 11 * n), max(1, 120 - 11 * n)) for n in range(12)]
    said, _ = slow_looks(monkeypatch, lives)
    assert said is None


def test_the_clock_starts_only_in_the_strikes_reach(monkeypatch):
    lives = [(127, 120)] * 12
    said, hunted = slow_looks(monkeypatch, lives, away=40.0)
    assert said is None
    assert hunted.slow is None


def test_a_given_up_leader_keeps_no_fight(monkeypatch):
    monkeypatch.setattr(judging, 'SLOW_FIGHT', True)
    play = game(*beasts(119, 100))
    hunted = hunter(play)
    goal = temple_goal()
    move = Move(Step((5100.0, 5000.0)), goal, '')
    monkeypatch.setattr(hunted.attack, 'holding', lambda: HERALD, raising=False)
    assert judging.held_strikes_on(hunted, play.world, list(play.world.monsters), Ground(()), move, 10.0)
    hunted.passed[HERALD] = 40.0
    assert not judging.held_strikes_on(hunted, play.world, list(play.world.monsters), Ground(()), move, 10.0)
