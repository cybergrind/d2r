"""Town Portal out of a level (routes/lower-kurast-loop-plan.md phase 3): the tome's key, the portal beside the
character once it is open, the click, the town."""

import math

import pytest

from inventory_tracking.game.records import Pack, Thing
from inventory_tracking.levels.model import TOWN_PORTAL
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.portal import FROM_SLING, FROM_TOME, TOME, portal_source, to_town
from inventory_tracking.macros.skills import SLING_TOWN_PORTAL
from tests.inventory_tracking.macros.fakes import KEYS, PREBUFF_SET, SLOTS, Game, world


LOWER_KURAST, KURAST_DOCKS = 79, 75


def keys(_world, skills):
    return {skill: {**KEYS, TOME: 'x'}[skill] for skill in skills}


def lower_kurast() -> Game:
    play = Game(world(LOWER_KURAST))
    play.next_area = KURAST_DOCKS
    return play


def test_the_tome_is_cast_and_its_portal_taken_once_open():
    play = lower_kurast()
    play.portal_opens = 0.6

    to_town(play.run(), keys)

    assert play.pressed() == ['x', 'c', 'c']  # the tome; the arrival's check: a swap that takes, and back
    assert play.sets[0] == PREBUFF_SET  # the set held before (a game left with the staff in hand loses its key)
    assert play.character.area == KURAST_DOCKS
    clicks = [event for event in play.keys.events if event[0] == 'click']
    assert len(clicks) == 1  # not at the portal while it opened
    assert play.clock.now >= 0.6
    assert play.said[-4:] == ['Through the portal to town, 4 away', 'town: there', 'Swap Weapons', 'Swap Weapons']


def test_a_portal_that_was_open_before_the_cast_is_not_the_new_one():
    play = lower_kurast()
    play.thing = Thing(9, TOWN_PORTAL, 2, 5030.0, 5000.0)  # the portal of an earlier trip, open
    play.portal_opens = None  # the tome casts nothing

    with pytest.raises(Abort, match='no Town Portal opened'):
        to_town(play.run(), keys)
    assert play.character.area == LOWER_KURAST
    assert [event for event in play.keys.events if event[0] == 'click'] == []


def test_with_no_portal_after_the_cast_it_is_cast_once_more_then_stops_saying_so():
    play = lower_kurast()
    play.portal_opens = None

    with pytest.raises(Abort, match=r'no Town Portal opened .* is the tome empty\?'):
        to_town(play.run(), keys)
    assert play.pressed() == ['x', 'x']  # portal.py CAST_FREE: once more before the stop


def _blocks(play: Game, seconds: float, mode: int = 9) -> list[float]:
    """The character blocks (mode 9) for `seconds`, and the game drops a Town Portal key pressed in a block or a hit
    (09:30:05 on 2026-10-22: the Sling's 411 on the right button for one frame, no cast). The clock times of the
    presses the game took."""
    from dataclasses import replace

    from tests.inventory_tracking.macros.fakes import character_of

    def mode_now(value: int) -> None:
        play.world = replace(play.world, player=replace(character_of(play.world), mode=value))

    mode_now(mode)
    play.later(seconds, lambda: mode_now(1))
    act, taken = play.act, []

    def dropping(event) -> None:
        if event[0] == 'key' and event[1] == 'x':
            if character_of(play.world).mode in (4, 9):
                return
            taken.append(play.clock.now)
        act(event)

    play.act = dropping
    return taken


@pytest.mark.parametrize('mode', [9, 4])
def test_a_cast_in_a_block_or_a_hit_waits_for_its_end(mode):
    # 09:30:05 on 2026-10-22: the Sling's key went in during a block (mode 9) and the game dropped it
    play = lower_kurast()
    play.portal_opens = 0.6
    taken = _blocks(play, 0.4, mode)

    to_town(play.run(), keys)

    assert play.pressed()[0] == 'x'
    assert play.pressed().count('x') == 1  # one key, after the block
    assert len(taken) == 1
    assert taken[0] >= 0.4
    assert play.character.area == KURAST_DOCKS


def test_a_cast_cut_short_is_made_once_more_and_its_portal_taken():
    # 22:26:32 on 2026-10-21: the Sling's cast was cut by a block 0.04 s in; no portal, the game left 2.5 s later
    from inventory_tracking.macros.portal import RECAST_AFTER

    play = lower_kurast()
    play.portal_opens = 0.6
    act, presses = play.act, []

    def first_cut(event) -> None:
        if event[0] == 'key' and event[1] == 'x':
            presses.append(play.clock.now)
            if len(presses) == 1:
                return  # the cast cut short: no portal
        act(event)

    play.act = first_cut

    to_town(play.run(), keys)

    assert len(presses) == 2
    assert presses[1] - presses[0] >= RECAST_AFTER
    assert play.character.area == KURAST_DOCKS


def test_with_the_switch_off_a_key_in_a_block_is_pressed_at_once_and_the_game_left(monkeypatch):
    import inventory_tracking.macros.portal as portal_module

    monkeypatch.setattr(portal_module, 'CAST_FREE', False)
    play = lower_kurast()
    play.portal_opens = 0.6
    taken = _blocks(play, 0.4)

    with pytest.raises(Abort, match='no Town Portal opened'):
        to_town(play.run(), keys)
    assert play.pressed() == ['x']
    assert taken == []


def test_in_town_nothing_is_cast():
    play = Game(world(KURAST_DOCKS))

    with pytest.raises(Abort, match='in town already'):
        to_town(play.run(), keys)
    assert play.keys.events == []


def test_after_the_portal_the_leg_waits_for_the_town_to_come_up():
    # rca/2026-10-16/loop-first-game-findings.md §2: the waypoint's aims were tried 0.002 s after the portal's arrival
    play = lower_kurast()
    play.arrival_load = 1.2

    to_town(play.run(), keys)

    assert play.arrived_at is not None
    assert play.clock.now >= play.arrived_at + 1.2


def test_with_no_load_shown_the_leg_is_over_once_a_swap_takes_and_waits_the_settle_at_most():
    # The eight trips of 2026-10-16 19:55-20:04 showed no load by the view byte; game 1 took no input for 4.5 s
    from inventory_tracking.macros.routines import ARRIVAL_SETTLE

    play = lower_kurast()  # the view byte never shows a load
    play.arrival_deaf = 2.0

    to_town(play.run(), keys)

    assert play.arrived_at is not None
    assert play.arrived_at + 2.0 <= play.clock.now < play.arrived_at + ARRIVAL_SETTLE
    assert play.sets[0] == PREBUFF_SET

    deaf = lower_kurast()
    deaf.arrival_deaf = 60.0  # no input taken at all: the settle, and nothing more

    to_town(deaf.run(), keys)

    assert deaf.arrived_at is not None
    assert deaf.clock.now >= deaf.arrived_at + ARRIVAL_SETTLE


def test_what_lands_while_the_portal_opens_is_picked_up_before_it_is_gone_through():
    # 03:04:16-17 on 2026-10-18: a chest's Chipped Ruby landed 0.8 s after its click, while the portal opened, and the
    # character went through without it
    play = lower_kurast()
    play.portal_opens = 0.6
    asked: list[tuple[float, int]] = []

    def first() -> bool:
        clicks = sum(event[0] == 'click' for event in play.keys.events)
        asked.append((play.clock.now, clicks))
        return len(asked) < 2  # one drop picked up, then nothing more

    to_town(play.run(), keys, first)

    assert len(asked) == 2
    assert all(now >= 0.6 and clicks == 0 for now, clicks in asked)  # the portal open, not yet clicked
    assert play.character.area == KURAST_DOCKS


@pytest.mark.parametrize('walk_back', [True, False])
def test_a_pickup_that_takes_the_character_off_the_portal_walks_back_to_it(monkeypatch, walk_back):
    # 02:30:33 on 2026-10-21: a pickup at the open portal went 47 units off it, every aim at the portal was off the
    # screen and the game was left with a Magic Kriss on the ground (portal.py WALK_BACK)
    from dataclasses import replace

    import inventory_tracking.macros.portal as portal_module
    from tests.inventory_tracking.macros.fakes import character_of

    monkeypatch.setattr(portal_module, 'WALK_BACK', walk_back)
    play = lower_kurast()
    play.portal_opens = 0.6
    asked: list[int] = []

    def first() -> bool:
        asked.append(1)
        if len(asked) == 1:  # the drop 45 units off: the character is there after it
            me = character_of(play.world)
            play.world = replace(play.world, player=replace(me, x=me.x + 45.0))
            return True
        return False

    if not walk_back:
        with pytest.raises(Abort, match='town is not under the pointer at any aim'):
            to_town(play.run(), keys, first)
        return
    to_town(play.run(), keys, first)

    assert play.character.area == KURAST_DOCKS
    assert play.walks  # walked back on the ground before the click on the portal


def test_a_portal_whose_middle_is_covered_is_taken_by_its_top():
    # 05:25:08 on 2026-10-18: a Doom Ape killed on the portal lay under the three aims down its middle, and the game was
    # left for it (teleport.py PORTAL_AIMS)
    play = lower_kurast()
    play.portal_opens = 0.6
    play.thing_above = 110  # only the portal's top is under the pointer: its middle shows the body

    to_town(play.run(), keys)

    assert play.character.area == KURAST_DOCKS


# The Sling (uniqueitems.txt, a Ring: `oskill` "Townportal O Skill", skills.txt 411) in place of the tome: the player,
# 2026-10-18, "when we have sling ring equipped - we don't need to run any logic in regard of town portal"
SLING_SLOTS = tuple(SLING_TOWN_PORTAL if skill == TOME else skill for skill in SLOTS)  # bound where the tome was: `x`


def sling_keys(world, skills):
    found = {**KEYS, **{s: 'x' for s in (TOME, SLING_TOWN_PORTAL) if s in world.slots}}
    missing = [s for s in skills if s not in found]
    if missing:
        raise Abort(f'skill {missing[0]} is not on a skill key')
    return {skill: found[skill] for skill in skills}


def test_the_source_is_the_slings_when_it_is_worn_and_the_tomes_otherwise_unread_too():
    play = Game(world(LOWER_KURAST))
    assert portal_source(play.run()) == FROM_TOME  # unread
    play.worn = frozenset({54})  # Enigma's Teleport alone
    assert portal_source(play.run()) == FROM_TOME
    play.worn = frozenset({54, SLING_TOWN_PORTAL})
    assert portal_source(play.run()) == FROM_SLING
    assert FROM_SLING.count(Pack(portals=0)) is None  # no tome carried: nothing to count
    assert FROM_TOME.count(Pack(portals=0)) == 0
    assert FROM_SLING.said(Pack(portals=0)) == 'portals from the Sling'
    assert FROM_TOME.said(Pack(portals=7)) == '7 portals'


def test_with_the_sling_worn_its_town_portal_is_cast_and_the_portal_taken():
    play = Game(world(LOWER_KURAST, slots=SLING_SLOTS))
    play.next_area = KURAST_DOCKS
    play.worn = frozenset({SLING_TOWN_PORTAL})
    play.portal_opens = 0.6
    run = play.run()

    to_town(run, sling_keys)

    assert play.pressed()[0] == 'x'
    assert run.keys[SLING_TOWN_PORTAL] == 'x'
    assert 'Town Portal (Sling)' in play.said
    assert play.character.area == KURAST_DOCKS


def test_with_the_sling_worn_and_its_skill_on_no_key_nothing_is_cast_and_the_tome_is_not_tried():
    play = lower_kurast()  # the tome's 220 on `x`, the Sling's 411 on no key
    play.worn = frozenset({SLING_TOWN_PORTAL})

    with pytest.raises(Abort, match=f'skill {SLING_TOWN_PORTAL} is not on a skill key'):
        to_town(play.run(), sling_keys)
    assert play.pressed() == []


def test_a_sling_cast_with_no_portal_does_not_ask_about_the_tome():
    play = Game(world(LOWER_KURAST, slots=SLING_SLOTS))
    play.worn = frozenset({SLING_TOWN_PORTAL})
    play.portal_opens = None

    with pytest.raises(Abort, match=r'no Town Portal opened 2.5s after the cast from the Sling$'):
        to_town(play.run(), sling_keys)


def test_a_walk_to_the_portal_that_goes_through_it_is_the_arrival_not_a_failure(monkeypatch):
    # 2026-10-21 00:55:22: the walk toward the portal took it; the step then clicked for the town's portal from the
    # City of the Damned, read "not under the pointer at any aim", and the recovery left a Double Bow on the ground
    from inventory_tracking.macros import portal as portal_module, shop

    play = Game(world(KURAST_DOCKS))

    def walked_through(run, place, bounds, label):
        play.arrive(LOWER_KURAST)
        return run.world()

    monkeypatch.setattr(shop, 'walk_until', walked_through)
    monkeypatch.setattr(portal_module, 'portals', lambda run: [])
    used = []
    monkeypatch.setattr(portal_module, 'use_thing', lambda *a, **k: used.append(a))

    portal_module.through_portal(play.run(), near=(5048.0, 5049.0))

    assert used == []  # no click for the town's portal from the level
    assert play.character.area == LOWER_KURAST


def test_with_the_switch_off_a_walk_through_the_portal_still_clicks_as_before(monkeypatch):
    from inventory_tracking.macros import portal as portal_module, shop

    monkeypatch.setattr(portal_module, 'THROUGH_ON_THE_WAY', False)
    play = Game(world(KURAST_DOCKS))

    def walked_through(run, place, bounds, label):
        play.arrive(LOWER_KURAST)
        return run.world()

    monkeypatch.setattr(shop, 'walk_until', walked_through)
    monkeypatch.setattr(portal_module, 'portals', lambda run: [])
    with pytest.raises(Abort, match='no Town Portal in sight'):
        portal_module.through_portal(play.run(), near=(5048.0, 5049.0))


@pytest.mark.parametrize('on', [True, False])
def test_a_key_a_block_drops_after_it_is_cast_again_once_the_character_is_free(monkeypatch, on):
    # 2026-10-23: 63 pauses by the portal under blows; a key dropped by a block waited RECAST_AFTER (1.6 s) for its
    # recast (rca/2026-10-23/pause-findings.md)
    from dataclasses import replace

    import inventory_tracking.macros.portal as portal_module
    from tests.inventory_tracking.macros.fakes import character_of

    monkeypatch.setattr(portal_module, 'DROP_RECAST', on)
    play = lower_kurast()
    play.portal_opens = 0.6
    act, presses = play.act, []

    def dropped(event) -> None:
        if event[0] == 'key' and event[1] == 'x':
            presses.append(play.clock.now)
            if len(presses) == 1:  # a block begins with the key and drops it, over 0.2 s later
                play.world = replace(play.world, player=replace(character_of(play.world), mode=9))
                play.later(
                    0.2,
                    lambda: setattr(
                        play, 'world', replace(play.world, player=replace(character_of(play.world), mode=1))
                    ),
                )
                return
        act(event)

    play.act = dropped
    to_town(play.run(), keys)

    assert len(presses) == 2
    assert (presses[1] - presses[0] < 0.5) if on else (presses[1] - presses[0] >= portal_module.RECAST_AFTER)
    assert play.character.area == KURAST_DOCKS


ROGUE_ENCAMPMENT = 1


def _walled_town(monkeypatch, walled: bool):
    """17:39:42-17:40:54 on 2026-10-23: the character in the Rogue Encampment 20 units from its portal, a low stone wall
    between; clicks on the portal never moved it. The walks and clicks recorded; `walk_until` with `until` puts the
    character by the portal."""
    from dataclasses import replace

    from inventory_tracking.macros import portal as portal_module, shop
    from inventory_tracking.macros.teleport import Untook
    from tests.inventory_tracking.macros.fakes import character_of

    play = Game(world(ROGUE_ENCAMPMENT))
    me = play.character
    gate = Thing(9, TOWN_PORTAL, 2, me.x - 4.0, me.y + 20.0)
    walks, clicks = [], []

    def walk_until(run, place, bounds, label, *, until=None, **_):
        walks.append(until is not None)
        if until is not None:
            play.world = replace(play.world, player=replace(character_of(play.world), x=gate.x, y=gate.y - 3.0))
        return run.world()

    def use_thing(run, mark, here, thing, aspect):
        clicks.append((here.x, here.y))
        if math.dist((here.x, here.y), (thing.x, thing.y)) > portal_module.NEAR:
            raise Untook('no click took the level')
        play.arrive(LOWER_KURAST)

    monkeypatch.setattr(shop, 'walk_until', walk_until)
    monkeypatch.setattr(portal_module, 'portals', lambda run: [gate])
    monkeypatch.setattr(portal_module, 'use_thing', use_thing)
    monkeypatch.setattr(portal_module, '_walled', lambda run, here, portal: walled)
    return play, walks, clicks


def test_with_a_wall_on_the_line_the_character_walks_up_to_the_portal_before_the_click(monkeypatch):
    from inventory_tracking.macros import portal as portal_module

    play, walks, clicks = _walled_town(monkeypatch, walled=True)
    portal_module.through_portal(play.run())
    assert walks == [False, True]  # until drawn, then up to it
    assert len(clicks) == 1
    assert play.character.area == LOWER_KURAST


def test_portal_clicks_that_move_nothing_are_followed_by_the_walk_up_and_one_more_try(monkeypatch):
    from inventory_tracking.macros import portal as portal_module

    play, walks, clicks = _walled_town(monkeypatch, walled=False)  # the ground did not show the wall
    portal_module.through_portal(play.run())
    assert walks == [False, True]
    assert len(clicks) == 2
    assert play.character.area == LOWER_KURAST


def test_with_the_switch_off_the_portal_is_clicked_from_afar_as_before(monkeypatch):
    from inventory_tracking.macros import portal as portal_module
    from inventory_tracking.macros.teleport import Untook

    monkeypatch.setattr(portal_module, 'WALK_ROUND', False)
    play, walks, clicks = _walled_town(monkeypatch, walled=True)
    with pytest.raises(Untook):
        portal_module.through_portal(play.run())
    assert walks == [False]
    assert len(clicks) == 1
