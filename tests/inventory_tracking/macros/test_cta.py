"""Call to Arms kept on the character (macros/cta.py): Battle Command and Battle Orders out of town, from the weapon set
that gives them, the set found in hand back after."""

from dataclasses import replace

from inventory_tracking.builds.characters import HEART_OF_THE_OAK
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Casting
from inventory_tracking.macros.cta import (
    BATTLE_COMMAND,
    BATTLE_ORDERS,
    ROWS,
    SWAP_AFTER_CAST,
    call_to_arms,
    cast_in_hand,
    orders_shown,
    worn_and_in_front,
)
from inventory_tracking.macros.world import CTA_CODE, gives_orders
from tests.inventory_tracking.macros.fakes import BUILD, KEYS, OTHER_SET, PREBUFF_SET, SLOTS, Game, player, world


LOWER_KURAST, PANDEMONIUM_FORTRESS = 79, 103
CTA_SLOTS = (*SLOTS[:13], BATTLE_COMMAND, BATTLE_ORDERS, *SLOTS[15:])
CTA_KEYS = {**KEYS, BATTLE_COMMAND: 'F7', BATTLE_ORDERS: 'F8'}
CTA_SET = (CTA_CODE, 'uit')  # Call to Arms and the second Spirit (22:58 on 2026-10-17)


def keys(_world, skills=None):
    return {skill: CTA_KEYS[skill] for skill in skills or ()}


def test_a_weapon_that_gives_battle_orders_is_the_call_to_arms():
    # The live capture of 22:58 on 2026-10-17: the Flail on the swap holds (97, 146, 3), (97, 149, 4), (97, 155, 4)
    cta = [{'id': 97, 'layer': 146, 'raw': 3}, {'id': 97, 'layer': 149, 'raw': 4}, {'id': 97, 'layer': 155, 'raw': 4}]
    assert gives_orders(cta)
    assert not gives_orders([{'id': 97, 'layer': 54, 'raw': 1}])  # Enigma's Teleport
    assert not gives_orders([{'id': 127, 'layer': 0, 'raw': 3}])  # Heart of the Oak's +3 to all skills
    # The main set is told by the Heart of the Oak's Flail: Spirit is in both sets, the Call to Arms is not `fla`
    assert HEART_OF_THE_OAK & set(PREBUFF_SET)
    assert not HEART_OF_THE_OAK & set(CTA_SET)


def test_battle_orders_is_kept_up_out_of_town_only_and_only_with_a_call_to_arms_worn():
    # skills.txt: Battle Orders and Battle Command have no `InTown` (the player, 2026-10-17: "probably cta cannot be
    # used in town")
    out = world(LOWER_KURAST, slots=CTA_SLOTS, player=player(LOWER_KURAST, battle_orders=False))
    assert orders_shown(out) is False
    assert orders_shown(replace(out, player=player(LOWER_KURAST, battle_orders=True))) is True
    assert orders_shown(replace(out, player=player(PANDEMONIUM_FORTRESS, battle_orders=False))) is None
    # The main set's keys do not hold it (the player, 23:40: "swap weapon and there are 7 and 8 bound to skills")
    assert orders_shown(replace(out, slots=SLOTS)) is False
    assert worn_and_in_front(BuffFacts(out, 0.0, focused=lambda: True, cta=True))
    assert not worn_and_in_front(BuffFacts(out, 0.0, focused=lambda: True, cta=False))  # none worn: no swap tried
    assert not worn_and_in_front(BuffFacts(out, 0.0, focused=lambda: True))  # not known
    assert not worn_and_in_front(BuffFacts(out, 0.0, focused=lambda: False, cta=True))  # the game behind
    [row] = ROWS
    assert row.phase == 'upkeep'
    assert row.caster == 'cta'
    assert row in BUILD.buffs
    assert 'cta' in BUILD.casters


def cast_in(play: Game):
    run = play.run()
    [row] = ROWS
    return run, call_to_arms(Casting(run, row, Buffs(BUILD), run.world(), key_names=keys))


def test_the_call_to_arms_is_swapped_in_for_battle_command_then_battle_orders_and_swapped_out():
    play = Game(world(LOWER_KURAST, slots=CTA_SLOTS))
    play.staff = None
    play.sets = [PREBUFF_SET, CTA_SET]
    _, tried = cast_in(play)
    assert tried.cast
    assert tried.at is not None
    assert [key for key in play.pressed() if key in ('c', 'F7', 'F8')] == ['c', 'F7', 'F8', 'c']
    assert play.sets[0] == PREBUFF_SET  # the main set back in hand


def test_no_call_to_arms_in_the_other_set_is_said_asked_again_later_and_the_set_found_in_hand_is_back():
    play = Game(world(LOWER_KURAST, slots=CTA_SLOTS))
    play.staff = None
    play.sets = [PREBUFF_SET, OTHER_SET]
    run, tried = cast_in(play)
    assert not tried.cast
    assert tried.at is not None
    assert tried.at > run.clock()  # not asked again for a while (MISSING_WAIT)
    assert 'F8' not in play.pressed()
    assert play.sets[0] == PREBUFF_SET


def test_the_arrivals_input_check_casts_them_with_the_call_to_arms_its_swap_put_in_hand():
    # 01:15:46-52 on 2026-10-18: the check's swap pair, then the caster's own pair for the cast (1.5 s)
    from inventory_tracking.macros.routines import took_input
    from inventory_tracking.macros.skills import SWAP_WEAPONS

    play = Game(world(LOWER_KURAST, slots=CTA_SLOTS, player=player(LOWER_KURAST, battle_orders=False)))
    play.staff = None
    play.sets = [PREBUFF_SET, CTA_SET]
    run = play.run()
    run.keys.update(keys(run.world(), (SWAP_WEAPONS,)))
    run.arrival_swap = lambda: cast_in_hand(run, keys)
    timed, heard = [], play.keys.on_event

    def timing(event):
        if event[0] == 'key':
            timed.append((event[1], play.clock.now))
        heard(event)

    play.keys.on_event = timing
    assert took_input(run, 'Lower Kurast', run.clock())
    assert [key for key in play.pressed() if key in ('c', 'F7', 'F8')] == ['c', 'F7', 'F8', 'c']
    assert play.sets[0] == PREBUFF_SET
    # The swap back SWAP_AFTER_CAST after Battle Orders' key: one 0.4 s after it was refused (01:41-01:58)
    orders = next(at for key, at in timed if key == 'F8')
    back = [at for key, at in timed if key == 'c' and at > orders]
    assert back[0] - orders >= SWAP_AFTER_CAST


def test_at_the_arrival_nothing_is_cast_with_battle_orders_shown_in_a_town_or_no_call_to_arms_in_hand():
    for shown, area, sets in (
        (True, LOWER_KURAST, [PREBUFF_SET, CTA_SET]),
        (False, PANDEMONIUM_FORTRESS, [PREBUFF_SET, CTA_SET]),
        (False, LOWER_KURAST, [PREBUFF_SET, OTHER_SET]),
    ):
        play = Game(world(area, slots=CTA_SLOTS, player=player(area, battle_orders=shown)))
        play.staff = None
        play.sets = [sets[1], sets[0]]  # the other set in hand, as after the check's swap
        assert not cast_in_hand(play.run(), keys)
        assert not {'F7', 'F8'} & set(play.pressed())
