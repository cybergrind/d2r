"""What a level run does about drops it cannot take as they lie: a valuable the inventory has no room for, and the
potions of the level (rca/2026-10-13/run-2110-findings.md §2.3, potions-findings.md steps 2-4).

Recorded moments, moved to test_hunt's level (the character at (5000, 5000)) with their distances kept:

- **M2a, 21:13:51.7** (take 20261013T181240Z-108): the inventory 40/40 after a pair of gloves; a Thul Rune and a
  Ring dropped by the Vizier 15 units off; the run walked on past them saying nothing, and the player went back by
  hand. M2c, 21:15:17.7: a Grand Charm (1x3) beside a Jewel with four free cells in two 2-tall columns: the run
  took the Jewel and left the charm.
- **M4, 21:50:53.9** (take 20261013T184953Z-108): a super healing potion 6 away with three of the Infector's
  monsters within 3 of it, the belt short (1, 5): refused silently ("not a potion with hostiles near it"), and the
  run warped on toward Vizier seal 1. CS 1, 21:44:33 and 21:44:55: the same.
- **M2, 21:50:21-25**: no healing potion on the belt, a super healing potion 3.6 away (step 1, the emptied
  columns, made the belt want it: here through the run's own goal).
"""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.builds import pursuing
from inventory_tracking.levels.model import Ground, Walkable, pack_cells
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.build import NoWay
from inventory_tracking.macros.goals import FIGHT, PICK_REACH, PICK_UP, STAND_NEAR, WAIT, Goal, goal_of, in_the_way
from inventory_tracking.macros.hunt import BLOCK_SECONDS, GATHER_TRIES
from inventory_tracking.macros.pickup import PICK_UNITS, approach, pick_up
from inventory_tracking.macros.pursuit import FULL, Hold, Move, Operate, Pursuit, decide
from inventory_tracking.macros.supply import Potions, detour, worth
from inventory_tracking.macros.travel import PRESSED, clear_line, open_reaches, walk_reaches
from inventory_tracking.macros.world import HEALING, REJUVENATION, VALUABLE, Drop, Loot, Monster, PutDown, Teleport
from tests.inventory_tracking.macros.test_hunt import game, hunter, keys, me
from tests.inventory_tracking.macros.test_level_run import STEP, facts as level_facts, unasked


AREA = 101
HP, JUV = 606, 531
FULL_INVENTORY = ('#' * 10,) * 4
TWO_TALL = ('##.#.#####', '##.#.#####', '##########', '##########')  # M2c: four cells in two 2-tall columns
THUL = Drop(71, 5015.0, 5000.0, 'Thul Rune', VALUABLE, prized=False)
RING = Drop(72, 5018.0, 5004.0, 'Ring', VALUABLE, prized=False)
GRAND = Drop(73, 5012.0, 4996.0, 'Grand Charm', VALUABLE, (1, 3))
JEWEL = Drop(74, 5011.0, 4995.0, 'Jewel', VALUABLE, prized=False)
KRISS = Drop(75, 5008.0, 5000.0, 'Magic Kriss', VALUABLE, (1, 3), prized=False)
# M4: the belt with three healing potions and seven rejuvenations (short (1, 5)) and with none (H0 R6)
M4_BELT = (JUV, JUV, HP, HP, JUV, JUV, HP, None, JUV, JUV, None, None, JUV, None, None, None)
DRY = (JUV, JUV, None, None) * 3 + (None,) * 4
POTION = Drop(1684803542, 4998.0, 5006.0, 'a super healing potion', HEALING)
GUARDS = tuple(
    Monster(900 + i, 362, 1, x, y, 0xFFFFFFFF)
    for i, (x, y) in enumerate(((4999.0, 5008.5), (4996.0, 5007.0), (5001.0, 5009.0)))
)


def goal_here(**given) -> Goal:
    """The goal of a character at (5000, 5000), which the test expects there to be."""
    goal = goal_of((5000.0, 5000.0), spend=PRESSED, reach=20.0, **given)
    assert goal is not None
    return goal


def running(play, *, loot: Loot, ground=()):
    """A hunter on a level run on test_hunt's level with the pursuit loop on; `loot` is what the game shows."""
    play.loot = loot
    hunt = hunter(play, ground=ground)
    hunt.build = replace(hunt.build, settings=hunt.build.settings.model_copy(update={'pursuit': True}))
    hunt.post(Pursuit('pickup', 0.0, advance=False, leash=FULL, area=AREA))
    return hunt


def look(hunt, play, run, foes=()):
    """The goal of the run's look now (hunt.py `goal`), with `foes` standing in the world."""
    play.world = replace(play.world, monsters=tuple(foes))
    hunt.pursued = hunt.goal(run, play.world, list(foes), False, hunt.pursuit)  # as `judge` keeps it
    return hunt.pursued


# -- a valuable with no room for it: the run stands by it ----------------------------------------------------


def test_a_valuable_with_no_room_is_a_goal_to_stand_by_and_say() -> None:
    goal = goal_here(stay=THUL)
    assert (goal.do, goal.unit, goal.near, goal.place) == (WAIT, 71, STAND_NEAR, (THUL.x, THUL.y))
    assert decide(level_facts(goal), Pursuit('pickup', 0.0, advance=False, leash=FULL)) == Move(STEP, goal)
    there = decide(level_facts(goal, there=True, way=unasked), Pursuit('pickup', 0.0, advance=False, leash=FULL))
    assert isinstance(there, NoWay)
    assert there.arrived
    assert there.reason == 'inventory full: Thul Rune here — make room'
    # what comes is fought while it waits
    held = decide(level_facts(goal, there=True, in_reach=True, way=unasked), Pursuit('pickup', 0.0, leash=FULL))
    assert held == Hold(goal)


def test_with_the_inventory_full_the_run_stands_by_the_thul_rune_until_there_is_room_then_takes_it(caplog) -> None:
    """M2a: as it ran the run went on past the Thul Rune and the Ring, saying nothing."""
    play = game()
    hunt = running(play, loot=Loot((THUL, RING), room=FULL_INVENTORY, cube=('...', '...', '#..', '###')))
    run = play.run()
    warned: list[str | None] = []
    run.warn = warned.append
    with caplog.at_level(logging.INFO):
        goal = look(hunt, play, run)
    assert (goal.do, goal.unit) == (WAIT, THUL.unit_id)
    assert warned == ['Inventory full: Thul Rune here — make room (the cube has room for it)']
    assert 'the run stands by it (the cube has room for it)' in caplog.text
    assert look(hunt, play, run).do == WAIT
    assert len(warned) == 1  # said once while it lasts
    # The player makes room: the rune is a drop to take, and the warning is taken back
    play.loot = replace(play.loot, room=('#########.', *FULL_INVENTORY[1:]))
    taken = look(hunt, play, run)
    assert (taken.do, taken.unit, taken.near) == (PICK_UP, THUL.unit_id, PICK_REACH)
    assert warned[-1] is None


def test_the_grand_charm_with_no_three_tall_room_is_stood_by_after_the_jewel_beside_it_is_taken() -> None:
    """M2c: four free cells in two 2-tall columns: the Jewel fits, the Grand Charm (1x3) does not."""
    play = game()
    hunt = running(play, loot=Loot((GRAND, JEWEL), room=TWO_TALL))
    run = play.run()
    assert look(hunt, play, run).unit == JEWEL.unit_id  # what fits is taken first
    play.loot = replace(play.loot, drops=(GRAND,))
    assert (look(hunt, play, run).do, look(hunt, play, run).unit) == (WAIT, GRAND.unit_id)


def test_gear_shown_by_the_filter_only_is_not_stood_by_and_a_press_goes_on_without_the_valuable() -> None:
    play = game()
    hunt = running(play, loot=Loot((KRISS,), room=FULL_INVENTORY, shown=frozenset({KRISS.unit_id})))
    run = play.run()
    assert look(hunt, play, run) is None  # the player, 2026-10-12: "allow moving when the item isn't very valuable"
    play.loot = Loot((THUL, RING), room=FULL_INVENTORY)
    assert look(hunt, play, run).unit == THUL.unit_id
    hunt.post(Pursuit('pickup', 1.0, advance=False, leash=FULL))  # the player goes on: KP_1 again
    assert look(hunt, play, run).unit == RING.unit_id  # the rune is let go; the ring is the next one
    hunt.post(Pursuit('teleport', 2.0))
    assert look(hunt, play, run) is None


# -- a drop the sweep has given up: no hold by it ----------------------------------------------------------------


CHARM = Drop(36472766, 4986.0, 5010.0, 'Large Charm', VALUABLE, (1, 2))  # 17 away, as at 00:26:30 (run-0025 §1)


def sweeping(play, ground=()):
    """A hunter whose sweep is on, with the pickup step's own hand-over stubbed: what it would stop for."""
    hunt = hunter(play, ground=ground)
    run = play.run()
    hunt.sweep.start(run.clock())
    stopped: list[bool] = []
    hunt.pick = lambda: stopped.append(True)
    return hunt, run, stopped


def test_the_sweep_does_not_stay_by_a_drop_whose_tries_are_spent_and_says_why_it_left_it(caplog) -> None:
    """River of Flame, 00:26:49.75-53.4 on 2026-10-14 (run-0025-findings.md §2.3): the level run's two tries at the
    Large Charm had expired mid-walk ("priced act expired"), and the sweep then stood 3.9 s by it, "no better place"
    twelve times with six hostiles near, saying "no click took it"; the player took it by hand."""
    play = game()
    play.loot = Loot((CHARM,), room=('..........',) * 4)
    hunt, run, stopped = sweeping(play, (LAVA,))  # across the lava: no clear line, no one more try (`again`)
    hunt.gathered[CHARM.unit_id] = GATHER_TRIES
    hunt.tried[CHARM.unit_id] = 'priced act expired: look again before continuing'
    with caplog.at_level(logging.INFO):
        hunt.gather(run, (5000.0, 5000.0))
    assert not stopped
    assert hunt.held is None
    assert not hunt.leaves((5000.0, 4950.0), run.clock())  # the sweep's steps are its own again
    assert 'no click took it' not in caplog.text
    assert 'the sweep leaves Large Charm' in caplog.text
    assert 'priced act expired' in caplog.text  # the true reason, said


def test_the_sweep_still_stays_by_a_valuable_it_leaves_for_later_and_says_the_hostiles_are_why(caplog) -> None:
    """The Ral Rune at 00:27:14.6 (run-0025 §2.3): left for later for a hostile within 12, and said as "no click
    took it" though no click had been made."""
    play = game()
    ral = Drop(55, 5020.0, 5000.0, 'Ral Rune', VALUABLE)
    play.loot = Loot((ral,), room=('..........',) * 4)
    hunt, run, stopped = sweeping(play)
    guard = Monster(901, 362, 1, 5025.0, 5000.0, 0xFFFFFFFF)
    with caplog.at_level(logging.INFO):
        hunt.gather(run, (5000.0, 5000.0), [guard])
    assert not stopped
    assert hunt.held == ral
    assert 'no click took it' not in caplog.text
    assert 'Staying by Ral Rune: 1 hostiles within 12 of it or the character' in play.said


# -- near enough to click: by a walk, not by a straight line -------------------------------------------------------

# Test_hunt's room (world 4980-5020 both ways) with a strip of lava three units wide at x 4991-4993 from its top edge
# down to y 5016: the character at (5000, 5000) and the charm at (4986, 5010) are 17 apart in a straight line and
# about 30 by the walk round the strip's end (the River of Flame, 00:26:36: 17 straight, 43 by walking).
LAVA_ROWS = ''.join(('1' * 11 + '000' + '1' * 26) if row < 37 else '1' * 40 for row in range(40))
LAVA = Walkable(996, 996, 8, 8, pack_cells(LAVA_ROWS), pack_cells(LAVA_ROWS))
FREE = ('..........',) * 4


def on_a_run(play, ground=()):
    hunt = hunter(play, ground=ground)
    hunt.build = pursuing(hunt.build)
    hunt.post(Pursuit('pickup', 0.0, advance=False, leash=FULL, area=AREA))
    return hunt


def test_a_drop_near_in_a_straight_line_and_far_by_walking_is_gone_to_first_not_clicked_from_here() -> None:
    """River of Flame, 00:26:36-39.5 on 2026-10-14 (run-0025-findings.md §2.2): the charm was 17 away (within
    PICK_REACH 20) across lava, the hands clicked from where the character stood, the client walked the detour and
    the 1.5 s the act was priced for ran out twice, mid-walk; the charm was given up and the player took it."""
    play = game()
    play.loot = Loot((CHARM,), room=FREE)
    hunt = on_a_run(play, (LAVA,))
    found = hunt.judge(play.run(), play.world, [], Ground((LAVA,)), in_reach=False)
    assert found.goal is not None
    assert (found.goal.do, found.goal.unit) == (PICK_UP, CHARM.unit_id)
    assert isinstance(found.act, Move)  # the navigator's move, with the movement in hand
    # The same drop with nothing between: clicked from here, as before
    play = game()
    play.loot = Loot((CHARM,), room=FREE)
    found = on_a_run(play).judge(play.run(), play.world, [], Ground(()), in_reach=False)
    assert isinstance(found.act, Operate)


def test_the_hands_do_not_click_a_drop_across_ground_no_walk_crosses_in_reach() -> None:
    """The same in the pickup's own approach (pickup.py `approach`): a drop within PICK_UNITS is clicked from where
    the character stands only with a walk to it; across the lava it is hopped toward first."""
    play = game()
    play.loot = Loot((CHARM,), room=FREE)
    run = play.run()
    level = hunter(play, ground=(LAVA,)).known_level(me(play.world))
    approach(run, CHARM, level, keys)
    here = (me(play.world).x, me(play.world).y)
    assert here != (5000.0, 5000.0)  # it went first
    assert walk_reaches(Ground((LAVA,)), (), here, (CHARM.x, CHARM.y), PICK_UNITS)


def test_the_hands_take_the_drop_the_goal_names_not_the_one_they_would_choose() -> None:
    """The Magic Dusk Shroud at 00:01:36 on 2026-10-14 (run-0025 §2.2): the run's goal was "5037 gold, on the way"
    and the hands clicked the Shroud, which `pickup.choose` puts first (valuables first): the act priced was not the
    one made."""
    play = game()
    ring = Drop(81, 5005.0, 5000.0, 'Ring', VALUABLE, prized=False)
    play.loot = Loot((ring, CHARM), room=FREE)
    hunt = on_a_run(play)
    run = play.run()
    goal = goal_here(side=CHARM)
    hunt.operate(run, play.world, goal, keys)
    assert play.picked[:1] == ['Large Charm']


# -- what the player put down: not the run's ------------------------------------------------------------------


def test_a_valuable_the_player_put_down_is_neither_gone_for_nor_stood_by_nor_warned_about() -> None:
    """The Superior Crystal Sword after Diablo, 00:30:57.9 on 2026-10-14 (run-0025-findings.md §3): put down by the
    player 71 units back, named by the loot step and warned about ("Inventory full: Superior Crystal Sword left on
    the ground"); with room for it the step would have gone back for it. The runner's loot passes through the
    game's `PutDown` (runner.py), as here."""
    play = game()
    sword = Drop(490846825, 5010.0, 5000.0, 'Superior Crystal Sword', VALUABLE, (2, 3), prized=True)
    put_down = PutDown()
    put_down.see(Loot((), game=('cyber32', 1), carried=frozenset({sword.unit_id})))
    hunt = running(play, loot=Loot((sword,), room=FULL_INVENTORY, game=('cyber32', 1)))
    run = play.run()
    run.loot = lambda: put_down.see(play.loot)
    warned: list[str | None] = []
    run.warn = warned.append
    assert look(hunt, play, run) is None  # no wait by it for room
    play.loot = replace(play.loot, room=FREE)
    assert look(hunt, play, run) is None  # nor a drop to go for once there is room
    assert not pick_up(run, None, keys, lambda: None)  # the pickup step has nothing to pick up
    assert not any(text for text in warned)
    assert play.picked == []


# -- potions: guards first, said, remembered, worth a detour --------------------------------------------------


def test_a_wanted_potions_guards_are_the_fight_first_and_the_pickup_never_begins_among_them(caplog) -> None:
    """M4: as it ran the potion 6 away was refused with no line and the run warped on toward the seal."""
    play = game()
    hunt = running(play, loot=Loot((POTION,), M4_BELT, 1815, 1818))
    run = play.run()
    with caplog.at_level(logging.INFO):
        goal = look(hunt, play, run, GUARDS)
        again = look(hunt, play, run, GUARDS)
    assert goal.do == FIGHT
    assert goal.unit in {m.unit_id for m in GUARDS}
    assert goal.label == 'a super healing potion, on the way: the fight first (3 in the way)'
    assert again.label == goal.label
    # the fight first is the run's own side goal: held and gone to, the run not ended for want of a route stage
    assert decide(level_facts(goal, in_reach=True, way=unasked, area=AREA), hunt.pursuit) == Hold(goal)
    assert decide(level_facts(goal, area=AREA), hunt.pursuit) == Move(STEP, goal)
    assert caplog.text.count('are the fight first') == 1  # said once a potion
    # the guards dead: the potion is the goal, and taken
    taken = look(hunt, play, run)
    assert (taken.do, taken.unit, taken.guarded) == (PICK_UP, POTION.unit_id, True)
    assert decide(level_facts(taken, there=True, way=unasked, area=AREA), hunt.pursuit) == Operate(taken)


def test_a_potion_held_by_its_guards_longer_than_the_block_is_left_and_that_is_said(caplog) -> None:
    play = game()
    hunt = running(play, loot=Loot((POTION,), M4_BELT, 1815, 1818))
    run = play.run()
    look(hunt, play, run, GUARDS)
    play.clock.now += BLOCK_SECONDS + 0.1
    with caplog.at_level(logging.INFO):
        assert look(hunt, play, run, GUARDS) is None
    assert f'left: guarded {BLOCK_SECONDS:.0f} s' in caplog.text


def test_the_guards_of_a_potion_are_those_near_it_or_the_character() -> None:
    goal = goal_here(side=POTION)
    far = Monster(950, 362, 1, 5040.0, 5040.0, 0xFFFFFFFF)
    assert set(in_the_way(goal, [*GUARDS, far], (5000.0, 5000.0))) == set(GUARDS)
    rune = goal_here(side=THUL)
    assert not rune.guarded
    assert in_the_way(rune, GUARDS, (5000.0, 5000.0)) == []  # a valuable is gone for all the same


def test_with_no_healing_potion_on_the_belt_the_run_takes_the_one_at_its_feet_before_the_route() -> None:
    """M2, 21:50:22.3: H0 R6, a super healing potion 3.6 away; as it ran the run warped on to Vizier seal 1."""
    play = game()
    near = Drop(1051927826, 5002.2, 4997.1, 'a super healing potion', HEALING)
    hunt = running(play, loot=Loot((near,), DRY, 1807, 1818))
    goal = look(hunt, play, play.run())
    assert (goal.do, goal.unit) == (PICK_UP, near.unit_id)


def test_a_healing_potion_is_worth_a_detour_only_below_the_reserve_rising_as_the_belt_empties() -> None:
    assert worth(2, 2, 4.0) == 0.0  # at the reserve: the pickup key's own rule only (U8)
    assert worth(1, 2, 4.0) == 4.0
    assert worth(0, 2, 4.0) == 8.0
    assert worth(0, 3, 4.0) == 12.0  # no rejuvenation on the belt: one more kept
    assert detour(2.0, 1.5) == 5.5


def test_a_remembered_healing_potion_beyond_the_pickups_reach_is_gone_for_when_worth_its_detour(caplog) -> None:
    """With no healing potion on the belt (reserve 2 at 1818 life: worth 8 s), a potion seen 40 away is the side
    goal when the way there and back by the movement in hand fits, and left, said, when it does not."""
    play = game()
    far = Drop(77, 5040.0, 5000.0, 'a super healing potion', HEALING)
    loot = Loot((far,), DRY, 1807, 1818)
    hunt = running(play, loot=loot)
    run = play.run()
    hunt.potions.see(loot, AREA, (5000.0, 5000.0), 0.0, -1.0)
    hunt.travel.eta = lambda *args, **kwargs: 2.0  # 2 s there: 5.5 s with the way back and the pickup
    goal = look(hunt, play, run)
    assert (goal.do, goal.unit, goal.near) == (PICK_UP, 77, PICK_REACH)
    hunt.fetching = (-1e9, None)
    hunt.travel.eta = lambda *args, **kwargs: 4.0  # 9.5 s: more than the 8 s it is worth
    with caplog.at_level(logging.INFO):
        assert look(hunt, play, run) is None
    assert 'not worth its detour: 9.5 s against 8 s (belt healing 0)' in caplog.text
    # with the belt at its reserve it is worth no detour: never asked
    hunt.fetching = (-1e9, None)
    play.loot = replace(loot, belt=(JUV, JUV, HP, HP) + (JUV, JUV, None, None) * 2 + (None,) * 4)
    hunt.travel.eta = lambda *args, **kwargs: pytest.fail('the navigator was asked')
    assert look(hunt, play, run) is None


# -- the level's potions and the empty belt --------------------------------------------------------------------


def test_a_potion_is_remembered_after_it_leaves_the_look_and_forgotten_once_seen_gone() -> None:
    potions = Potions()
    hp = Drop(1, 5030.0, 5000.0, 'a super healing potion', HEALING)
    juv = Drop(2, 5000.0, 5060.0, 'a full rejuvenation potion', REJUVENATION)
    potions.see(Loot((hp, juv), DRY, 1000, 1000), AREA, (5000.0, 5000.0), 0.0, -1.0)
    potions.see(Loot((), DRY, 1000, 1000), AREA, (4900.0, 5000.0), 1.0, -1.0)  # walked off: out of the look
    assert {p.unit for p in potions.lying(HEALING, (0.0, 0.0))} == {1}
    potions.see(Loot((), DRY, 1000, 1000), AREA, (5025.0, 5000.0), 2.0, -1.0)  # back by it: it is not there
    assert potions.lying(HEALING, (0.0, 0.0)) == []
    assert potions.fates[1] == 'gone'
    potions.see(Loot((), DRY, 1000, 1000), AREA + 1, (0.0, 0.0), 3.0, -1.0)  # another level: all forgotten
    assert potions.lying(REJUVENATION, (0.0, 0.0)) == []


def test_the_last_healing_potion_gone_is_a_warning_with_who_took_them_and_the_levels_potions() -> None:
    """ "something is wrong if we're empty" (the player, 2026-10-13); 21:50:13.8 as it ran: three of the last four
    healing potions went to the mercenary by the healer within 6 s, and two were left on the ground."""
    potions = Potions()
    two = (JUV, JUV, HP, HP) + (JUV, JUV, None, None) * 2 + (None,) * 4
    one = (JUV, JUV, HP, None) + (JUV, JUV, None, None) * 2 + (None,) * 4
    left = Drop(5, 5003.0, 5004.0, 'a super healing potion', HEALING)
    assert potions.see(Loot((left,), two, 1500, 1818), AREA, (5000.0, 5000.0), 10.0, -1.0) is None
    potions.refuse(5, 'guarded: its guards are the fight first')
    assert potions.see(Loot((left,), one, 1500, 1818), AREA, (5000.0, 5000.0), 12.0, 11.8) is None  # the macro's key
    said = potions.see(Loot((left,), DRY, 1500, 1818), AREA, (5000.0, 5000.0), 14.0, 11.8)
    assert said is not None
    assert said.startswith('no healing potion on the belt 4 s into the level (rejuvenations 6, life 1500/1818)')
    assert 'the last gone, newest first: not the macro (the healer or a hand) 0.0 s ago, the macro 2.0 s ago' in said
    assert 'healing potions seen on the level: 1: 1 still on the ground, the nearest 5 away' in said
    assert potions.see(Loot((left,), DRY, 1500, 1818), AREA, (5000.0, 5000.0), 15.0, 11.8) is None  # once


# -- the pickup's approach with the staff empty ------------------------------------------------------------------


def test_with_the_staff_empty_a_drop_beyond_a_click_is_approached_by_the_movement_in_hand(caplog) -> None:
    """21:13:29: "No use of Amn Rune, on the way: the Teleport staff has no charges left", twice, 24 away."""
    play = game()
    play.staff = Teleport(0, 69, True)
    amn = Drop(80, 5028.0, 4990.0, 'Amn Rune', VALUABLE, prized=False)
    play.loot = Loot((amn,))
    run = play.run()
    level = hunter(play).known_level(me(play.world))
    with caplog.at_level(logging.INFO):
        approach(run, amn, level, keys)
    here = me(play.world)
    assert play.warps or play.walks
    assert ((here.x - amn.x) ** 2 + (here.y - amn.y) ** 2) ** 0.5 <= PICK_UNITS


# -- a click from afar only on a clear line; a given-up drop tried once more from one ----------------------------

# The ground round the Flawless Emerald of 15:18:31-37 on 2026-10-14 (Chaos Sanctuary take 20261014T121630Z-108,
# rca/2026-10-14/run-1214-findings.md §3.2; scripts/emerald_ground.py), world (7790-7830, 5150-5190) moved onto
# test_hunt's room (4980-5020 both ways): '.' walkable, '#' not, one char a unit. The gem at (7814, 5173); four clicks
# from (7799.9, 5161.3), 18.3 away and 19.4 by the walk round the wall's corner, and the character never moved;
# given up; at (7810.5, 5168.5), 5.7 from it on a clear line, the run went on to De Seis.
EMERALD_ROWS = (
    *('.' * 32 + '#' * 8,) * 10,
    *('.' * 34 + '#' * 6,) * 2,
    '..........##......................######',
    *('############......................######',) * 2,
    *('###############...................######',) * 2,
    '################..................######',
    '#################.................######',
    '##################................######',
    '#################................#######',
    *('################.................#######',) * 9,
    '##################................######',
    '#############..###................######',
    '#############.....................######',
    *('###########.......................######',) * 2,
    '############......................######',
    *('..........##......................######',) * 2,
    *('..................................######',) * 2,
)
EMERALD_BITS = ''.join(row.replace('.', '1').replace('#', '0') for row in EMERALD_ROWS)
CORNER = Walkable(996, 996, 8, 8, pack_cells(EMERALD_BITS), pack_cells(EMERALD_BITS))
CLICKED_FROM = (7799.9 - 2810, 5161.3 - 170)  # where the four clicks were made
PASSED_AT = (7810.5 - 2810, 5168.5 - 170)  # where the run passed it 2 s later
GEM = Drop(2327255744, 7814.0 - 2810, 5173.0 - 170, 'Flawless Emerald', VALUABLE, prized=False)


def standing(play, here):
    play.world = replace(play.world, player=replace(me(play.world), x=here[0], y=here[1]))


def test_the_emerald_round_the_wall_corner_is_not_near_enough_to_click_and_from_where_the_run_passed_it_is() -> None:
    assert len(EMERALD_ROWS) == 40
    assert {len(row) for row in EMERALD_ROWS} == {40}
    ground = Ground((CORNER,))
    gem = (GEM.x, GEM.y)
    assert not clear_line(ground, (), CLICKED_FROM, gem)
    assert not walk_reaches(ground, (), CLICKED_FROM, gem, PICK_UNITS)  # 18.3 straight, 19.4 round: no click
    assert clear_line(ground, (), PASSED_AT, gem)
    assert walk_reaches(ground, (), PASSED_AT, gem, PICK_UNITS)
    assert walk_reaches(Ground(()), (), CLICKED_FROM, gem, PICK_UNITS)  # open ground: the distance alone


def test_on_a_run_the_emerald_round_the_corner_is_gone_to_first_and_said(caplog) -> None:
    play = game()
    play.loot = Loot((GEM,), room=FREE)
    standing(play, CLICKED_FROM)
    hunt = on_a_run(play, (CORNER,))
    with caplog.at_level(logging.INFO):
        found = hunt.judge(play.run(), play.world, [], Ground((CORNER,)), in_reach=False)
        hunt.judge(play.run(), play.world, [], Ground((CORNER,)), in_reach=False)
    assert found.goal is not None
    assert (found.goal.do, found.goal.unit) == (PICK_UP, GEM.unit_id)
    assert isinstance(found.act, Move)  # the navigator's move first, not four clicks the client does not walk
    assert caplog.text.count('Macro: pickup: Flawless Emerald, on the way: 18 away with no clear line from') == 1
    standing(play, PASSED_AT)
    assert isinstance(hunt.judge(play.run(), play.world, [], Ground((CORNER,)), in_reach=False).act, Operate)


def test_the_pickups_own_approach_goes_round_the_corner_before_it_clicks(caplog) -> None:
    play = game()
    play.loot = Loot((GEM,), room=FREE)
    standing(play, CLICKED_FROM)
    run = play.run()
    level = hunter(play, ground=(CORNER,)).known_level(me(play.world))
    with caplog.at_level(logging.INFO):
        approach(run, GEM, level, keys)
    player = me(play.world)
    assert player is not None
    here = (player.x, player.y)
    assert here != CLICKED_FROM
    assert walk_reaches(Ground((CORNER,)), (), here, (GEM.x, GEM.y), PICK_UNITS)
    assert 'Macro: pickup: Flawless Emerald: 18 away with no clear line' in caplog.text


def test_the_given_up_emerald_is_tried_once_more_from_a_clear_line_and_no_more(caplog) -> None:
    play = game()
    standing(play, CLICKED_FROM)
    hunt = running(play, loot=Loot((GEM,), room=FREE), ground=(CORNER,))
    run = play.run()
    hunt.gathered[GEM.unit_id] = GATHER_TRIES
    hunt.tried[GEM.unit_id] = 'priced act expired: look again before continuing'
    with caplog.at_level(logging.INFO):
        assert look(hunt, play, run) is None  # from where the clicks were made: still given up
        assert 'one more try' not in caplog.text
        standing(play, PASSED_AT)
        goal = look(hunt, play, run)
    assert (goal.do, goal.unit) == (PICK_UP, GEM.unit_id)
    assert (
        'Macro: pickup: one more try at Flawless Emerald at (5004, 5003), 6 away on a clear line now '
        '(given up after 2 tries (the last: priced act expired' in caplog.text
    )
    assert 'One more try at Flawless Emerald' in play.said
    hunt.gathered[GEM.unit_id] = GATHER_TRIES  # the one more try took nothing either
    with caplog.at_level(logging.INFO):
        assert look(hunt, play, run) is None
    assert caplog.text.count('one more try') == 1
    assert caplog.text.count('the level run leaves Flawless Emerald') == 2  # said again after the one more try


def test_a_given_up_drop_the_player_put_down_is_not_tried_again() -> None:
    play = game()
    standing(play, PASSED_AT)
    put_down = PutDown()
    put_down.see(Loot((), game=('cyber32', 1), carried=frozenset({GEM.unit_id})))
    hunt = running(play, loot=Loot((GEM,), room=FREE, game=('cyber32', 1)), ground=(CORNER,))
    run = play.run()
    run.loot = lambda: put_down.see(play.loot)
    hunt.gathered[GEM.unit_id] = GATHER_TRIES
    assert look(hunt, play, run) is None
    assert GEM.unit_id not in hunt.retried


# -- a unique or set item the filter shows, with no room: stood by (the player, 2026-10-14) -----------------------

# run-1214-findings.md §3.1: "Inventory full: Unique Plate Mail left on the ground" at 15:19:21.99 and "Magic Bone
# Knife" at 15:19:49.74; the run went on from both, and the player made room and fetched each by hand.
PLATE = Drop(301, 5010.0, 5004.0, 'Unique Plate Mail', VALUABLE, (2, 3), prized=True)  # world.py `NAMED`
KNIFE = Drop(302, 5006.0, 4998.0, 'Magic Bone Knife', VALUABLE, (1, 2), prized=False)


def test_with_the_inventory_full_the_run_stands_by_a_unique_the_filter_shows_and_not_by_a_magic_one() -> None:
    play = game()
    hunt = running(play, loot=Loot((PLATE, KNIFE), room=FULL_INVENTORY, shown=frozenset({KNIFE.unit_id})))
    run = play.run()
    warned: list[str | None] = []
    run.warn = warned.append
    goal = look(hunt, play, run)
    assert (goal.do, goal.unit) == (WAIT, PLATE.unit_id)
    assert warned == ['Inventory full: Unique Plate Mail here — make room']
    play.loot = replace(play.loot, drops=(KNIFE,))  # the knife alone: the run goes on, as ruled 2026-10-12
    assert look(hunt, play, run) is None


def test_the_pickup_press_stops_for_a_unique_the_filter_shows_and_goes_on_from_a_magic_one() -> None:
    play = game()
    play.loot = Loot((PLATE, KNIFE), room=FULL_INVENTORY, shown=frozenset({KNIFE.unit_id}))
    with pytest.raises(Abort, match='inventory full: no room for Unique Plate Mail'):
        pick_up(play.run(), None, keys, lambda: None)
    play.loot = Loot((KNIFE,), room=FULL_INVENTORY, shown=frozenset({KNIFE.unit_id}))
    assert not pick_up(play.run(), None, keys, lambda: None)


# -- a belt low on potions restocks in the quiet (the player, 2026-10-14; run-1932-findings.md issue 2) ------------

# 22:55:31.8, Icy Cellar: 2 healing potions of 8, all 8 rejuvenations, nothing within 30; a full rejuvenation 7 away
# (the belt has no room for it), super healing potions 13 and 16 away; the run warped on toward Snapchip 84 away.
LOW_BELT = (JUV, JUV, HP, HP, JUV, JUV, None, None) + (JUV, JUV, None, None) * 2
NAMED = ('cber5', 7)
HEAL_13 = Drop(801, 5013.0, 5000.0, 'a super healing potion', HEALING)
HEAL_16 = Drop(802, 5000.0, 5016.0, 'a super healing potion', HEALING)
JUV_7 = Drop(803, 4993.0, 5000.0, 'a full rejuvenation potion', REJUVENATION)
SAPPHIRE = Drop(804, 5043.0, 5000.0, 'Flawless Sapphire', VALUABLE, prized=False)


def test_a_low_belt_wants_healing_under_half_its_columns_and_rejuvenations_under_the_reserve() -> None:
    from inventory_tracking.macros.supply import low

    assert low(Loot(belt=LOW_BELT, life=1278, max_life=1818, game=NAMED)) == (HEALING,)
    full = (JUV, JUV, HP, HP) * 4
    assert low(Loot(belt=full, life=1818, max_life=1818, game=NAMED)) == ()
    half = (JUV, JUV, HP, HP) * 2 + (JUV, JUV, None, None) * 2  # 4 of 8: half, not under it
    assert low(Loot(belt=half, life=1818, max_life=1818, game=NAMED)) == ()
    dry = (JUV, None, HP, HP) + (None, None, HP, HP) * 3  # one rejuvenation of 8: under the reserve of 2
    assert low(Loot(belt=dry, life=1818, max_life=1818, game=NAMED)) == (REJUVENATION,)
    assert low(Loot(belt=LOW_BELT, life=1278, max_life=1818)) == ()  # a belt of no game: unread


def test_in_the_quiet_attack_mode_takes_the_potions_lying_near_before_its_standing_goal(caplog) -> None:
    """22:55:31.8: the standing goal (Snapchip, by its mark) went first; now the healing potion 13 away does."""
    play = game()
    play.loot = Loot((HEAL_13, HEAL_16, JUV_7), LOW_BELT, 1278, 1818, game=NAMED)
    hunt = hunter(play)
    hunt.build = replace(hunt.build, settings=hunt.build.settings.model_copy(update={'pursuit': True}))
    run = play.run()
    with caplog.at_level(logging.INFO):
        goal = hunt.goal(run, play.world, [], False, None)
    assert goal is not None
    assert (goal.do, goal.unit) == (PICK_UP, HEAL_13.unit_id)  # the nearest of the kind the belt is low on
    assert 'restock: a super healing potion at (5013, 5000), 13 away, before the goal' in caplog.text
    # a hostile within 30: no restock, the fight and the goal first
    near = Monster(1, 19, 1, 5025.0, 5000.0, 0xFFFFFFFF)
    play.world = replace(play.world, monsters=(near,))
    goal = hunt.goal(run, play.world, [near], False, None)
    assert goal is None or goal.do != PICK_UP
    # a stocked belt: no restock
    play.world = replace(play.world, monsters=())
    play.loot = replace(play.loot, belt=(JUV, JUV, HP, HP) * 4)
    goal = hunt.goal(run, play.world, [], False, None)
    assert goal is None or goal.do != PICK_UP


def test_attack_mode_goes_to_its_restock_and_picks_it_up() -> None:
    goal = goal_here(side=HEAL_13)
    assert decide(level_facts(goal), None) == Move(STEP, goal)  # no level run, no press: attack mode's own
    assert decide(level_facts(goal, there=True, way=unasked), None) == Operate(goal)


def test_a_valuable_not_on_the_way_hides_no_potion_nearer() -> None:
    """22:56:06.4: KP_1's run chose a Flawless Sapphire 43 away, `side_drop` returned None, and a super healing potion
    8 away was left with the belt 6 short."""
    play = game()
    potion = Drop(805, 5008.0, 5000.0, 'a super healing potion', HEALING)
    hunt = running(play, loot=Loot((SAPPHIRE, potion), LOW_BELT, 1748, 1818, game=NAMED))
    goal = look(hunt, play, play.run())
    assert goal is not None
    assert (goal.do, goal.unit) == (PICK_UP, potion.unit_id)


def test_the_life_budget_scales_with_the_potions_the_belt_can_give_back() -> None:
    """22:55:09 (8 of 8) and 22:55:38 (2 of 8): the budget was 636.3 both times at full life. The player, 2026-10-15:
    the whole budget down to 4 healing potions, never under about half of it (the curve once gave none at 2 of 8)."""
    from inventory_tracking.combat.harm import SafetySettings, budget, stock_share
    from inventory_tracking.combat.survival import CALM
    from inventory_tracking.macros.supply import spendable

    settings = SafetySettings()
    whole = budget(1818, 1818, CALM, settings)  # the belt not counted

    def belt_of(healing: int) -> tuple:
        return (HP,) * healing + (JUV,) * 4 + (None,) * (12 - healing)  # the rejuvenation reserve stocked

    def allowance(belt, life=1818, **changes) -> float:
        loot = Loot(belt=belt, life=life, max_life=1818, game=NAMED)
        points = spendable(loot, settings.healing_points, settings.floor)
        return budget(life, 1818, CALM, settings, spendable=points, **changes)

    assert whole == pytest.approx(636.3)
    assert allowance((JUV, JUV, HP, HP) * 4) == pytest.approx(whole)  # a stocked belt: as before
    by_stock = [allowance(belt_of(healing)) for healing in range(9)]
    assert by_stock[4:] == pytest.approx([whole] * 5)  # 4 of 8 and more: the whole budget
    assert by_stock[3] == pytest.approx(0.75 * whole)  # one beyond the 2 kept for under the floor
    assert by_stock[:3] == pytest.approx([0.5 * whole] * 3)  # the kept ones alone, or none: half, never nothing
    assert by_stock == sorted(by_stock)  # never less budget for more potions
    assert allowance(LOW_BELT) == pytest.approx(0.5 * whole)  # 22:55:38's belt
    # Below full life the share is of what is above the floor: half of it still, not the floor raised to nothing.
    assert allowance(belt_of(2), life=1300) == pytest.approx(0.5 * budget(1300, 1818, CALM, settings))
    assert allowance(LOW_BELT, insisting=3.0) > allowance(LOW_BELT)  # an insisted goal still lowers the floor
    unread = Loot(belt=LOW_BELT, life=1818, max_life=1818)
    assert spendable(unread, settings.healing_points, settings.floor) is None
    assert stock_share(settings, None) == 1.0


# A shack's wall: '#' a column 34 units long, the way round it under its end (one char a unit, from (4980, 4980))
SHACK_ROWS = (*('....................#...................',) * 34, *('.' * 40,) * 6)
SHACK = Walkable(996, 996, 8, 8, *(pack_cells(''.join(r.replace('.', '1').replace('#', '0') for r in SHACK_ROWS)),) * 2)


def test_a_chest_is_opened_from_afar_only_where_the_walk_to_it_is_not_round_a_wall() -> None:
    # 19:54:36 on 2026-10-17: a shack's chest clicked from 12 away outside its wall; the open's 1.5 s ran out and the
    # leg lost 7-8 s. Of 933 opens 17:43-20:08 the walk round 1.5 times the line parts the 896 opened from the 34 not
    ground = Ground((SHACK,))
    outside, chest = (4980.0 + 14, 4980.0 + 10), (4980.0 + 25, 4980.0 + 10)
    assert not open_reaches(ground, (), outside, chest, 12.0)  # 11 straight, ~50 round the wall's end
    assert open_reaches(ground, (), (4980.0 + 22, 4980.0 + 10), chest, 12.0)  # its own side: a clear line
    assert open_reaches(Ground(()), (), outside, chest, 12.0)  # open ground: the distance alone
    assert not open_reaches(Ground(()), (), (4980.0 + 10, 4980.0 + 10), chest, 12.0)  # 15 away: further than reach
    # 18:38:34: a corner clipped, the walk round 1.12 times the line: opened at once (the emerald's corner here)
    corner = Ground((CORNER,))
    assert not clear_line(corner, (), CLICKED_FROM, (GEM.x, GEM.y))
    assert open_reaches(corner, (), CLICKED_FROM, (GEM.x, GEM.y), 20.0)  # 18.3 straight, 19.4 round
