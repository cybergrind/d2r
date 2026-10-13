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

from inventory_tracking.macros.build import NoWay
from inventory_tracking.macros.goals import FIGHT, PICK_REACH, PICK_UP, STAND_NEAR, WAIT, goal_of, in_the_way
from inventory_tracking.macros.hunt import BLOCK_SECONDS
from inventory_tracking.macros.pickup import PICK_UNITS, approach
from inventory_tracking.macros.pursuit import FULL, Hold, Move, Operate, Pursuit, decide
from inventory_tracking.macros.supply import Potions, detour, worth
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.macros.world import HEALING, REJUVENATION, VALUABLE, Drop, Loot, Monster, Teleport
from tests.inventory_tracking.macros.test_hunt import game, hunter, keys
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


def running(play, *, loot: Loot):
    """A hunter on a level run on test_hunt's level with the pursuit loop on; `loot` is what the game shows."""
    play.loot = loot
    hunt = hunter(play)
    hunt.build = replace(hunt.build, settings=hunt.build.settings.model_copy(update={'pursuit': True}))
    hunt.post(Pursuit('pickup', 0.0, advance=False, leash=FULL, area=AREA))
    return hunt


def look(hunt, play, run, foes=()):
    """The goal of the run's look now (hunt.py `goal`), with `foes` standing in the world."""
    play.world = replace(play.world, monsters=tuple(foes))
    hunt.pursued = hunt.goal(run, play.world, list(foes), False)  # as `judge` keeps it
    return hunt.pursued


# -- a valuable with no room for it: the run stands by it ----------------------------------------------------


def test_a_valuable_with_no_room_is_a_goal_to_stand_by_and_say() -> None:
    goal = goal_of((5000.0, 5000.0), spend=PRESSED, reach=20.0, stay=THUL)
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
    goal = goal_of((5000.0, 5000.0), spend=PRESSED, reach=20.0, side=POTION)
    far = Monster(950, 362, 1, 5040.0, 5040.0, 0xFFFFFFFF)
    assert set(in_the_way(goal, [*GUARDS, far], (5000.0, 5000.0))) == set(GUARDS)
    rune = goal_of((5000.0, 5000.0), spend=PRESSED, reach=20.0, side=THUL)
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
    level = hunter(play).known_level(play.world.player)
    with caplog.at_level(logging.INFO):
        approach(run, amn, level, keys)
    here = play.world.player
    assert play.warps or play.walks
    assert ((here.x - amn.x) ** 2 + (here.y - amn.y) ** 2) ** 0.5 <= PICK_UNITS
