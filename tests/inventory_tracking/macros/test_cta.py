"""Call to Arms kept on the character (macros/cta.py): Battle Command and Battle Orders out of town, from the weapon set
that gives them, the set found in hand back after."""

from dataclasses import replace

from inventory_tracking.builds.characters import HEART_OF_THE_OAK
from inventory_tracking.game.memory import CTA_CODE
from inventory_tracking.game.records import Monster, gives_orders
from inventory_tracking.macros import cta
from inventory_tracking.macros.buffs import STATE_RETRY, Buffs
from inventory_tracking.macros.build import BuffFacts, Casting
from inventory_tracking.macros.cta import (
    ARRIVAL_LEFT,
    BATTLE_COMMAND,
    BATTLE_ORDERS,
    FIGHT_LEFT,
    FIGHT_WAIT,
    ORDERS_LASTS,
    QUIET_LEFT,
    ROWS,
    SWAP_AFTER_CAST,
    call_to_arms,
    cast_in_hand,
    orders_shown,
    worn_and_in_front,
)
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


def test_swaps_that_never_show_the_call_to_arms_are_tried_again_soon_and_the_set_found_in_hand_is_back():
    # The Call to Arms is worn (the row runs only then): the swaps were dropped, as under the player's teleports by
    # hand (18:45 on 2026-10-19), not a missing weapon: asked again in DROPPED_WAIT, not MISSING_WAIT
    from inventory_tracking.macros.buffs import STATE_RETRY
    from inventory_tracking.macros.cta import DROPPED_WAIT

    play = Game(world(LOWER_KURAST, slots=CTA_SLOTS))
    play.staff = None
    play.sets = [PREBUFF_SET, OTHER_SET]
    run, tried = cast_in(play)
    assert not tried.cast
    assert tried.at is not None
    assert run.clock() < tried.at + STATE_RETRY <= run.clock() + DROPPED_WAIT
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


def test_at_the_arrival_nothing_is_cast_with_battle_orders_shown_fresh_in_a_town_or_no_call_to_arms_in_hand():
    for shown, area, sets in (
        (True, LOWER_KURAST, [PREBUFF_SET, CTA_SET]),
        (False, PANDEMONIUM_FORTRESS, [PREBUFF_SET, CTA_SET]),
        (False, LOWER_KURAST, [PREBUFF_SET, OTHER_SET]),
    ):
        play = Game(world(area, slots=CTA_SLOTS, player=player(area, battle_orders=shown)))
        play.staff = None
        play.sets = [sets[1], sets[0]]  # the other set in hand, as after the check's swap
        run = play.run()
        run.lasting = {BATTLE_ORDERS: run.clock() - 10.0}  # cast 10 s ago: ORDERS_LASTS - 10 left
        assert not cast_in_hand(run, keys)
        assert not {'F7', 'F8'} & set(play.pressed())


# -- Battle Orders cast again before it ends (cta.py RENEW_ORDERS, 2026-10-22) ------------------------------------
# It ran out at 23:35:32.66 on 2026-10-21 in the Disused Fane fight that killed the character, 180.6 s after its cast
# at 23:32:32.08 by the service before a restart at 23:35:00: max life 2943 -> 1896 with 57% left, the death 1.3 s
# later (rca/2026-10-21/battle-orders-findings.md). The player: "we must have top priority to no die ourselves".

SHOWN = world(LOWER_KURAST, slots=CTA_SLOTS, player=player(LOWER_KURAST, battle_orders=True))
GONE = replace(SHOWN, player=player(LOWER_KURAST, battle_orders=False))
NEAR = Monster(7, 19, 1, 5008.0, 5000.0, life=100, max_life=128)  # 8 from the character: a fight
FAR = Monster(8, 19, 1, 5040.0, 5000.0, life=100, max_life=128)  # 40 away: the quiet still


def asked(out=SHOWN, foes=(), *, hurt=False, ahead=0.0, took=None, now=1000.0, buffs=None):
    """The facts a row is asked with; `buffs`: its executor's records (`Buffs.facts`)."""
    return BuffFacts(
        out,
        now,
        tuple(foes),
        cast_at=buffs.cast_at if buffs is not None else {},
        focused=lambda: True,
        cta=True,
        ahead=ahead,
        took=buffs.took if buffs is not None else {} if took is None else took,
        hurt=lambda: hurt,
    )


def test_battle_orders_shown_is_renewed_in_the_quiet_under_quiet_left_or_with_its_cast_not_known():
    renew = cta.renew_orders
    assert renew(asked(), None) is not None  # a restart: the age of the one shown is not known
    assert renew(asked(foes=[FAR]), None) is not None  # nobody within QUIET_UNITS
    assert renew(asked(), ORDERS_LASTS - 100.0) is None
    assert renew(asked(), QUIET_LEFT + 1.0) is None
    assert renew(asked(), QUIET_LEFT - 1.0) is not None
    assert renew(asked(), -5.0) is not None  # shown past ORDERS_LASTS: a longer one, cast again
    assert renew(asked(ahead=QUIET_LEFT + 30.0), QUIET_LEFT + 20.0) is not None  # a boss fight ahead (hunt `ahead`)
    # Not shown: the state rule casts it, as before; in town nothing is cast
    assert renew(asked(GONE), 5.0) is None
    assert renew(asked(replace(SHOWN, player=player(PANDEMONIUM_FORTRESS, battle_orders=True))), 5.0) is None


def test_in_a_fight_battle_orders_is_renewed_only_near_its_end_and_with_the_character_not_hurt(monkeypatch):
    monkeypatch.setattr(cta, 'REBUFF', False)  # the rule before the rebuff (test_rebuff.py has REBUFF's)
    renew = cta.renew_orders
    assert renew(asked(foes=[NEAR]), None) is None  # not known: only in the quiet
    assert renew(asked(foes=[NEAR]), FIGHT_LEFT + 5.0) is None
    assert renew(asked(foes=[NEAR]), FIGHT_LEFT - 1.0) is not None
    assert renew(asked(foes=[NEAR], hurt=True), FIGHT_LEFT - 1.0) is None  # hurt within HURT_SECONDS
    unknown = replace(asked(foes=[NEAR]), hurt=None)
    assert renew(unknown, FIGHT_LEFT - 1.0) is None


def test_with_the_switch_off_battle_orders_is_cast_only_once_gone(monkeypatch):
    monkeypatch.setattr(cta, 'RENEW_ORDERS', False)
    assert cta.renew_orders(asked(), None) is None
    assert cta.renew_orders(asked(), 1.0) is None
    assert cta.renew_orders(asked(foes=[NEAR]), 1.0) is None
    [row] = ROWS
    play = Game(SHOWN)
    run = play.run()
    buffs = Buffs(BUILD)
    buffs.took[BATTLE_ORDERS] = run.clock() - ORDERS_LASTS + 5.0
    assert buffs.due(run, row, asked(buffs=buffs)) is None


def test_the_executor_casts_a_shown_battle_orders_again_near_its_end_its_tries_state_retry_apart(monkeypatch):
    monkeypatch.setattr(cta, 'REBUFF', False)  # a hostile 8 away: the rebuff retreats first (test_rebuff.py)
    [row] = ROWS
    play = Game(SHOWN)
    play.clock.now = 1000.0
    run = play.run()
    buffs = Buffs(BUILD)
    quiet = asked(buffs=buffs)
    assert buffs.due(run, row, quiet) is not None  # its cast not known (the service just restarted)
    buffs.took[BATTLE_ORDERS] = 1000.0 - 100.0  # 80 s left
    assert buffs.due(run, row, quiet) is None
    buffs.took[BATTLE_ORDERS] = 1000.0 - ORDERS_LASTS + 20.0  # 20 s left
    due = buffs.due(run, row, quiet)
    assert due is not None
    assert due.facts.lapsing
    buffs.remember(row, 999.0)  # a try 1 s ago (Tried.again: the swaps did not take)
    assert buffs.due(run, row, quiet) is None
    buffs.remember(row, 1000.0 - STATE_RETRY - 0.5)
    assert buffs.due(run, row, quiet) is not None
    # The hunt's look between moves out of the quiet asks only the lapsing rows (hunt.py `upkeep`, `renewing`)
    fight = asked(foes=[NEAR], buffs=buffs)
    assert buffs.first(run, 'upkeep', fight, renewing=True) is None  # 20 s left: not yet in a fight
    buffs.took[BATTLE_ORDERS] = 1000.0 - ORDERS_LASTS + 5.0  # 5 s left
    found = buffs.first(run, 'upkeep', fight, renewing=True)
    assert found is not None
    assert found.row is row
    assert buffs.first(run, 'upkeep', replace(fight, hurt=lambda: True), renewing=True) is None


def call_in(play: Game, *, own_teleport: bool | None):
    run = play.run()
    run.own_teleport = (lambda: own_teleport) if own_teleport is not None else None
    [row] = ROWS
    return run, call_to_arms(Casting(run, row, Buffs(BUILD), run.world(), key_names=keys))


def test_a_renewal_in_a_fight_swaps_only_with_teleport_the_characters_own():
    # The swap must not take Teleport away in a fight (a staff's charges hang on its set): Enigma's is the character's
    # own ("Teleport is the character's own: in every move", 23:35:08 on 2026-10-21)
    for own, cast in ((None, False), (False, False), (True, True)):
        play = Game(replace(SHOWN, monsters=(NEAR,)))
        play.staff = None
        play.sets = [PREBUFF_SET, CTA_SET]
        run, tried = call_in(play, own_teleport=own)
        assert tried.cast is cast
        assert ('F8' in play.pressed()) is cast
        if not cast:
            assert tried.at is not None
            assert run.clock() < tried.at + STATE_RETRY <= run.clock() + FIGHT_WAIT + 0.01
        assert play.sets[0] == PREBUFF_SET
    # In the quiet, or with Battle Orders gone (the cast as before), the swap is made whatever gives Teleport
    for out in (SHOWN, replace(GONE, monsters=(NEAR,))):
        play = Game(out)
        play.staff = None
        play.sets = [PREBUFF_SET, CTA_SET]
        _, tried = call_in(play, own_teleport=None)
        assert tried.cast


def test_at_the_arrival_battle_orders_shown_is_cast_again_under_arrival_left_or_not_known_and_counted():
    for lasting, cast in (
        ({BATTLE_ORDERS: -ORDERS_LASTS + ARRIVAL_LEFT - 10.0}, True),  # 50 s left
        ({BATTLE_ORDERS: -ORDERS_LASTS + ARRIVAL_LEFT + 10.0}, False),  # 70 s left
        ({}, True),  # not known: a restart
        (None, True),
    ):
        play = Game(SHOWN)
        play.staff = None
        play.sets = [CTA_SET, PREBUFF_SET]  # the other set in hand, as after the check's swap
        run = play.run()
        run.lasting = lasting
        assert cast_in_hand(run, keys) is cast
        assert ('F8' in play.pressed()) is cast
        if cast and lasting is not None:
            assert lasting[BATTLE_ORDERS] >= 0.0  # the cast counted: its age for the renewal
    # Gone: cast and counted
    play = Game(GONE)
    play.staff = None
    play.sets = [CTA_SET, PREBUFF_SET]
    run = play.run()
    run.lasting = counted = {}
    assert cast_in_hand(run, keys)
    assert cta.orders_left(run) == ORDERS_LASTS - (run.clock() - counted[BATTLE_ORDERS])


def test_at_the_arrival_with_the_switch_off_battle_orders_shown_is_not_cast(monkeypatch):
    monkeypatch.setattr(cta, 'RENEW_ORDERS', False)
    play = Game(SHOWN)
    play.staff = None
    play.sets = [CTA_SET, PREBUFF_SET]
    run = play.run()
    assert not cast_in_hand(run, keys)
    assert 'F8' not in play.pressed()
