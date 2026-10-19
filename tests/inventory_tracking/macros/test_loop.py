"""The Lower Kurast loop (routes/lower-kurast-loop-plan.md phase 4): the leg from where the character is, and a
game from Pandemonium Fortress to the lobby over the scripted game."""

from contextlib import suppress
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import (
    CHESTS,
    GAME_SECONDS,
    LEAVE,
    NEXT_GAME,
    PICK_UP,
    PORTAL,
    STILL_SECONDS,
    TO_THE_CHESTS,
    TO_THE_FORTRESS,
    TOWN,
    TRADE_ROOM,
    Dead,
    Loop,
    next_leg,
)
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.town import Exit
from inventory_tracking.macros.world import Carried, Thing, World
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.fakes import KEYS, Game, player, world


KURAST_DOCKS, LOWER_KURAST, PANDEMONIUM_FORTRESS = 75, 79, 103
GAME = 'cyber32'  # the fakes' game
WAYPOINT_ACT3, WAYPOINT_ACT4 = 237, 398  # objects.txt WaypointAct3, WaypointAct4Town


def progress_in(area: int) -> Progress:
    found = Progress(ROUTES, PERFORMED)
    found.note(GAME, area)
    return found


def at(area: int, **changes) -> World:
    return world(area, player=player(area, **changes))


def test_the_leg_is_read_from_where_the_character_is():
    loop, lk = Loop(), progress_in(LOWER_KURAST)

    assert next_leg(World(False, (), GAME, ()), lk, loop) == NEXT_GAME
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == TO_THE_CHESTS
    assert next_leg(at(LOWER_KURAST), lk, loop) == CHESTS
    lk.absent(LOWER_KURAST, 'Super chests')  # (or each of them used)
    assert next_leg(at(LOWER_KURAST), lk, loop) == PICK_UP
    lk.looted(LOWER_KURAST)
    assert next_leg(at(LOWER_KURAST), lk, loop) == PORTAL
    assert next_leg(at(KURAST_DOCKS), lk, loop) == TO_THE_FORTRESS
    loop.done = GAME
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == LEAVE
    loop.done = 'cyber31'  # the game before's: this one is fresh
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == TO_THE_CHESTS


def test_the_loop_stops_where_it_has_no_leg_and_with_the_character_dead():
    loop, lk = Loop(), progress_in(LOWER_KURAST)

    with pytest.raises(Abort, match='nothing to do in'):
        next_leg(at(1), lk, loop)
    with pytest.raises(Dead, match='the character is dead'):
        next_leg(at(LOWER_KURAST, mode=0), lk, loop)


def test_a_recovery_leaves_the_game_from_wherever_the_character_is_and_not_after_death():
    # The player, 2026-10-17: "we should try to not stuck in some weird situation without being able to fix it from
    # agent"
    loop, lk = Loop(), progress_in(LOWER_KURAST)
    loop.start()

    assert loop.recover(Abort('the waypoint did not open'), 100.0)
    for area in (LOWER_KURAST, KURAST_DOCKS, PANDEMONIUM_FORTRESS, 1):
        assert next_leg(at(area), lk, loop) == LEAVE
    assert next_leg(World(False, (), GAME, ()), lk, loop) == NEXT_GAME
    with pytest.raises(Dead):
        next_leg(at(LOWER_KURAST, mode=0), lk, loop)
    assert not loop.recover(Dead('the character is dead'), 101.0)


def test_a_game_the_loop_stays_in_too_long_is_overdue_once():
    loop = Loop()
    loop.start()

    assert not loop.overdue(GAME, 0.0)
    assert not loop.overdue(GAME, GAME_SECONDS)
    assert loop.overdue(GAME, GAME_SECONDS + 1)
    assert loop.recover(Abort('over'), GAME_SECONDS + 1)
    assert not loop.overdue(GAME, GAME_SECONDS + 2)  # being left already
    assert not loop.overdue(None, GAME_SECONDS + 3)  # the lobby: a fresh count


def test_each_trip_for_room_gives_the_game_more_seconds():
    from inventory_tracking.macros.loop import TRIP_SECONDS

    loop = Loop(trip=GAME, trips=2)
    loop.start()
    assert not loop.overdue(GAME, 0.0)
    assert not loop.overdue(GAME, GAME_SECONDS + 2 * TRIP_SECONDS)
    assert loop.overdue(GAME, GAME_SECONDS + 2 * TRIP_SECONDS + 1)


def keys(_world, skills=None):
    return {skill: {**KEYS, 220: 'x'}[skill] for skill in skills or ()}


def test_a_game_goes_from_the_fortress_through_the_chests_and_the_portal_back_to_the_lobby():
    play = Game(at(PANDEMONIUM_FORTRESS, x=5048.0, y=5044.0))  # where every game of 2026-10-15 began
    play.thing, play.thing_above = Thing(6, WAYPOINT_ACT4, 2, 5044.0, 5019.0), 0.0
    play.next_area = KURAST_DOCKS  # where the portal leads
    progress = progress_in(PANDEMONIUM_FORTRESS)
    loop = Loop(on=True, prebuffed=GAME)  # prebuffed by hand: the prebuff has its own tests
    runs, picks = [], [True, False]

    def level_run() -> None:  # the KP_1 run, the runner's: here the chests are opened at once
        runs.append(1)
        progress.absent(LOWER_KURAST, 'Super chests')

    def pick_up() -> bool:
        return picks.pop(0) if picks else False

    legs = []
    for _ in range(9):
        here = play.world.player
        if here is not None:
            progress.note(GAME, here.area)
        if here is not None and here.area == KURAST_DOCKS and play.thing is not None and play.thing.txt_id != 237:
            # The portal leaves the character 20 units south of the waypoint (the player's nine trips); the fake's
            # portal changes only the level, so the waypoint is put that far from where the character stands.
            play.thing = Thing(5, WAYPOINT_ACT3, 2, here.x + 1.0, here.y - 19.0)
        legs.append(loop.leg(play.run(), keys, progress, level_run, pick_up))
        if not play.world.in_game:
            break

    assert legs == [TO_THE_CHESTS, CHESTS, PICK_UP, PICK_UP, PORTAL, TO_THE_FORTRESS, LEAVE]
    assert runs == [1]
    assert loop.games == 1
    assert 'Save and Exit' in play.said


def test_with_the_sling_worn_and_no_tome_a_game_casts_its_town_portal_and_never_goes_for_scrolls(caplog):
    # The player, 2026-10-18: "sling provides town teleport skill, that frees two slots in inventory (we can replace
    # tome of town portals) ... when we have sling ring equipped - we don't need to run any logic in regard of town
    # portal (do not track, do not buy)". The tome taken out: its charges read 0 (world.py `carried_items`)
    from dataclasses import replace

    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.skills import SLING_TOWN_PORTAL
    from inventory_tracking.macros.world import Pack
    from tests.inventory_tracking.macros.fakes import SLOTS

    slots = tuple(SLING_TOWN_PORTAL if skill == 220 else skill for skill in SLOTS)  # bound where the tome was: `x`
    play = Game(replace(at(PANDEMONIUM_FORTRESS, x=5048.0, y=5044.0), slots=slots))
    play.thing, play.thing_above = Thing(6, WAYPOINT_ACT4, 2, 5044.0, 5019.0), 0.0
    play.next_area = KURAST_DOCKS
    play.pack = Pack((Carried(1, CUBE_CLASS, 0, 0, (2, 2)),), ('...',) * 4, keys=12, portals=0)
    play.worn = frozenset({54, SLING_TOWN_PORTAL})
    progress = progress_in(PANDEMONIUM_FORTRESS)
    loop = Loop(on=True, prebuffed=GAME)
    loop.start()

    def sling_keys(_world, skills=None):
        return {skill: {**KEYS, SLING_TOWN_PORTAL: 'x'}[skill] for skill in skills or ()}

    def level_run() -> None:
        progress.absent(LOWER_KURAST, 'Super chests')

    legs = []
    with caplog.at_level('INFO'):
        for _ in range(6):
            here = play.world.player
            if here is not None:
                progress.note(GAME, here.area)
            if here is not None and here.area == KURAST_DOCKS:
                break
            legs.append(loop.leg(play.run(), sling_keys, progress, level_run, lambda: False))

    assert legs == [TO_THE_CHESTS, CHESTS, PICK_UP, PORTAL]  # not to Jamella for scrolls first (`TOWN`)
    assert not loop.short
    assert play.character.area == KURAST_DOCKS
    assert 'Town Portal (Sling)' in play.said
    # Said once, at the first leg: the live game's confirmation (macros/sling-plan.md)
    assert caplog.text.count('Macro: loop: Town Portal from the Sling: skill 411 in slot 5; worn skills [54, 411]') == 1


def test_without_the_sling_the_tome_is_counted_and_the_session_report_says_which(caplog):
    from inventory_tracking.macros.portal import FROM_SLING
    from inventory_tracking.macros.town import Needs, contract
    from inventory_tracking.macros.world import Pack

    pack = Pack(keys=12, portals=0)
    play = Game(at(PANDEMONIUM_FORTRESS))
    play.pack = pack
    loop = Loop(on=True, prebuffed=GAME)
    loop.start()
    with caplog.at_level('INFO'), suppress(Abort):  # her visit, which the fake has no town visit for
        loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False)
    assert loop.short  # no tome and no Sling: short, as before
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == TOWN
    assert 'Macro: loop: Town Portal from the tome: skill 220 in slot 5; worn skills unread' in caplog.text

    tome = contract(pack, frozenset(), Needs())
    assert (tome.keys, tome.portals) == (12, '0')
    assert 'portals 0' in tome.misses
    sling = contract(pack, frozenset(), Needs(portals=FROM_SLING))  # the visit's report: the Sling's, never short
    assert sling.portals == 'from the Sling'
    assert not [miss for miss in sling.misses if 'portals' in miss]


def test_a_leg_made_again_and_again_with_nothing_coming_of_it_stops_the_loop():
    play = Game(at(LOWER_KURAST))
    progress, loop = progress_in(LOWER_KURAST), Loop(on=True)

    for _ in range(3):
        assert loop.leg(play.run(), keys, progress, lambda: None, lambda: False) == CHESTS
    with pytest.raises(Abort, match='the chests again and again in cyber32'):
        loop.leg(play.run(), keys, progress, lambda: None, lambda: False)


def test_each_game_left_has_its_own_count_of_the_next_game_leg():
    # 20:55:43 and 21:05:53 on 2026-10-16: "next game again and again in the lobby", each the third game after KP_6:
    # the lobby's leg was counted for the whole loop, not for each game left
    loop = Loop(on=True)
    for name in ('cyber18', 'cyber19', 'cyber20', 'cyber21'):
        loop.count(World(False, (), name, ()), NEXT_GAME)
    lobby = World(False, (), 'cyber21', ())  # the same game left again: the next one was not made
    loop.count(lobby, NEXT_GAME)
    with pytest.raises(Abort, match='next game again and again in the lobby after cyber21'):
        loop.count(lobby, NEXT_GAME)


def test_a_leg_over_its_count_is_counted_afresh_after_its_stop():
    # 18:55:34 on 2026-10-18: the player's mouse in the lobby twice, then each recovery's next game stopped at once:
    # 4 recoveries in 20 ms, the loop held 30 s
    loop = Loop(on=True)
    lobby = World(False, (), 'cyberr34', ())
    loop.count(lobby, NEXT_GAME)
    loop.count(lobby, NEXT_GAME)
    with pytest.raises(Abort, match='next game again and again'):
        loop.count(lobby, NEXT_GAME)
    loop.count(lobby, NEXT_GAME)  # the recovery's try: a leg of its own, not stopped at once
    loop.count(lobby, NEXT_GAME)
    with pytest.raises(Abort, match='next game again and again'):
        loop.count(lobby, NEXT_GAME)


def test_a_game_name_come_round_again_starts_its_own_count():
    # 09:19:49 on 2026-10-18: the second cyber81 of a session (cyber99 -> cyber1) began with the first one's count,
    # and its first next game stopped the loop
    loop = Loop(on=True)
    first = World(False, (), 'cyber81', ())
    loop.count(first, NEXT_GAME)
    loop.count(first, NEXT_GAME)
    for name in ('cyber82', 'cyber99', 'cyber1', 'cyber80'):
        loop.count(World(False, (), name, ()), NEXT_GAME)
    loop.count(first, NEXT_GAME)
    loop.count(first, NEXT_GAME)


def test_the_inventory_kept_at_the_loops_start_is_what_the_cube_leaves_before_the_game_is_left():
    # Phase 9: the player's own items are what the loop's first look finds carried; with nothing of the loop's and the
    # room fine, the game's end is no visit
    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.world import Carried, Pack

    play = Game(at(PANDEMONIUM_FORTRESS))
    play.pack = Pack((Carried(1, CUBE_CLASS, 0, 0, (2, 2)),), ('...',) * 4)
    loop, visits = Loop(on=True), []
    loop.done = GAME  # the chests done: the game is left

    made = loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False, visits.append)
    assert made == LEAVE
    assert visits == []
    assert loop.own == frozenset({(CUBE_CLASS, 0, 0)})
    assert 'Save and Exit' in play.said


def test_a_character_standing_still_too_long_is_said_once_and_moving_counts_afresh():
    # 01:15:03 on 2026-10-17: the level run stood by a Flawless Diamond with the inventory full until the player came
    # ("we stuck, but didn't detect it in time")
    loop = Loop()
    loop.start()

    assert not loop.still((5384.3, 2614.3), 0.0)
    assert not loop.still((5385.0, 2614.0), STILL_SECONDS)  # within STILL_UNITS: the same stand
    assert loop.still((5384.3, 2614.3), STILL_SECONDS + 1)
    assert not loop.still((5384.3, 2614.3), STILL_SECONDS + 2)  # said once
    assert not loop.still((5400.0, 2614.0), 2 * STILL_SECONDS + 5)  # moved: afresh
    assert not loop.still(None, 10 * STILL_SECONDS)


def test_a_new_game_and_the_recovery_pause_count_no_stand():
    """09:22:44-09:23:50 on 2026-10-19: the stand of the game before and the 30 s pause counted on into the next game,
    left 5 s in, 5 recoveries in a row."""
    loop = Loop()
    assert not loop.still((5384.3, 2614.3), 0.0, 'g1')
    assert not loop.still((5384.3, 2614.3), STILL_SECONDS + 1, 'g2')  # the same spot, a new game: afresh
    assert loop.still((5384.3, 2614.3), 2 * STILL_SECONDS + 2, 'g2')
    loop.cooling = 4 * STILL_SECONDS
    assert not loop.still((5384.3, 2614.3), 3.5 * STILL_SECONDS, 'g2')  # pausing: no stand
    assert not loop.still((5384.3, 2614.3), 4 * STILL_SECONDS + 1, 'g2')  # counted from the pause's end
    assert loop.still((5384.3, 2614.3), 5 * STILL_SECONDS + 2, 'g2')


def test_the_staff_under_20_percent_of_its_charges_is_repaired_before_the_chests(monkeypatch):
    # The player, 2026-10-17: "we can start thinking on repairing teleport charges ... to travel more efficiently"
    from inventory_tracking.macros.repair import wants
    from inventory_tracking.macros.world import Teleport

    monkeypatch.setattr('inventory_tracking.macros.repair.STASH_TOUCHED', Path('/nonexistent/touched'))
    assert wants(Teleport(3, 20, False))  # under 20% (repair.py REPAIR_BELOW: the visits top it up meanwhile)
    assert not wants(Teleport(4, 20, False))
    assert not wants(None)
    monkeypatch.setattr('inventory_tracking.macros.repair.STASH_TOUCHED', Path(__file__))
    assert not wants(Teleport(0, 69, False))  # off: a repair once touched the stash's gold
    loop, lk = Loop(), progress_in(LOWER_KURAST)
    loop.repair = True
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == TOWN  # the visit: Halbu in it (macros/visit.py)
    loop.repair, loop.short = False, True
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == TOWN  # a key or a scroll short: Jamella in it
    loop.done = GAME  # at a game's end a refill or a repair waits for the next game's start
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == LEAVE


def test_the_trade_waits_for_the_room_to_run_low_then_identifies_stashes_and_sells_in_one_session():
    # The player, 2026-10-17: "we need to perform mass identify at decard cain -> stash good -> sell junk -> return to
    # loop"; "probably we need to trade not by 2 junk items, but by remaining free slots"; 2026-10-18 12:55: one visit
    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.world import Carried, Pack

    cube = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
    charms = Carried(2, 999, 0, 2, (10, 2))  # the player's own items: two rows of the inventory
    full = ('###',) * 4  # the cube full
    unknown = [Carried(10 + n, 41, 2 + n, 0, (1, 3), quality=4, identified=False) for n in range(4)]
    play = Game(at(PANDEMONIUM_FORTRESS))
    loop, visits = Loop(on=True), []
    loop.done = GAME  # the chests done, back in the fortress
    loop.own = frozenset({(CUBE_CLASS, 0, 0), (999, 0, 2)})  # the player's, read at the loop's start
    play.pack = Pack((cube, charms, *unknown[:3]), ('...',) * 4, in_cube=(unknown[3],), cube_items=frozenset({13}))
    lk = progress_in(PANDEMONIUM_FORTRESS)

    def visit(exit: Exit):
        visits.append(exit)
        play.pack = Pack((cube, charms), ('...',) * 4)  # identified, stashed, sold: the contract kept

    def leg():
        return loop.leg(play.run(), keys, lk, lambda: None, lambda: False, visit)

    assert leg() == LEAVE  # 7 + 12 cells free in the inventory and the cube: no trade yet
    assert visits == []
    play.pack = Pack((cube, charms, *unknown[:3]), full, in_cube=(unknown[3],), cube_items=frozenset({13}))
    play.world = at(PANDEMONIUM_FORTRESS)  # the next game's end, the same game's name in the fakes
    loop.made.clear()
    assert leg() == TOWN  # 7 cells free (the cube full): the whole visit, the cube's item among them
    assert visits == [Exit.LEAVE]  # at a game's end: no walk back to the waypoint, the game is left from it
    assert (loop.visiting, loop.visited) == (GAME, GAME)
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == LEAVE  # once a game


def test_the_session_waits_for_the_room_to_run_low_and_is_made_once_a_game():
    loop = Loop(on=True)
    loop.free = 20
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == TO_THE_CHESTS
    loop.free, loop.carrying = 6, True  # under TRADE_ROOM with the loop's items carried: the visit now
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == TOWN
    loop.visited = GAME  # made in this game: not again
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == TO_THE_CHESTS


def carried_of():
    from inventory_tracking.macros.world import Carried

    return Carried(11, 41, 4, 0, (1, 3), quality=4, identified=False)


def test_a_cube_whose_room_no_item_of_the_loop_fits_is_no_room():
    # 12:44-12:45 on 2026-10-17: the cube's 9 free cells in pieces ('.#./.#./.#./...'), two items out, the inventory
    # full, no session: a Rage Mask left on the ground
    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.world import Carried, Pack

    cube = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
    charms = Carried(2, 999, 0, 2, (10, 2))  # the player's own: two rows
    belts = Carried(3, 998, 4, 0, (6, 2))  # and more: 2 inventory cells left
    helm = Carried(11, 405, 2, 0, (2, 2), quality=4, identified=False)  # the loop's: a 2 x 2 fits nowhere in the cube
    play = Game(at(PANDEMONIUM_FORTRESS))
    play.pack = Pack((cube, charms, belts, helm), ('.#.', '.#.', '.#.', '...'))
    loop = Loop(on=True)
    loop.own = frozenset({(CUBE_CLASS, 0, 0), (999, 0, 2), (998, 4, 0)})
    loop.done = GAME
    town = loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False, lambda exit: None)
    assert town == TOWN


def test_cells_free_with_no_block_a_grand_charm_fits_are_no_room():
    # 21:00:03 on 2026-10-17: free cells left in pieces, the cube's last two ('##.' twice), no session before the game;
    # a Grand Charm (1 x 3) found no room and the loop stopped with it on the ground
    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.world import Carried, Pack

    cube = Carried(1, CUBE_CLASS, 0, 2, (2, 2))
    dagger = Carried(20, 135, 0, 0, (1, 2), quality=4, identified=False)  # the loop's, to identify
    # The player's own across the middle rows of columns 2-9: 18 cells free, no three in a column
    own = tuple(Carried(2 + x, 999 - x, x, 1, (1, 2)) for x in range(2, 10))

    def leg(cube_rows: tuple[str, ...]) -> tuple[str, Loop]:
        play = Game(at(PANDEMONIUM_FORTRESS))
        play.pack = Pack((cube, dagger, *own), cube_rows)
        loop = Loop(on=True)
        loop.own = frozenset({(CUBE_CLASS, 0, 2), *((item.txt, item.x, item.y) for item in own)})
        loop.done = GAME
        made = loop.leg(
            play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False, lambda e: None
        )
        return made, loop

    made, loop = leg(('###', '###', '##.', '##.'))
    assert made == TOWN
    assert loop.free is not None
    assert loop.free < TRADE_ROOM
    # The same inventory with a column of three free in the cube: room as before, no session
    made, loop = leg(('##.', '##.', '##.', '###'))
    assert made != TOWN
    assert loop.free is not None
    assert loop.free >= TRADE_ROOM


def test_a_visit_cut_by_the_players_hand_is_made_again_and_only_once_done():
    # The player's hand mid-visit (runner.py `_loop_stopped`: the leg is made again): the room may read fine by then
    # (the stash stop done), the visit is made again all the same and does what is left (macros/visit.py)
    loop = Loop(on=True)
    loop.free, loop.done = 30, GAME  # the room fine at a game's end: no visit of its own
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == LEAVE
    loop.visiting = GAME  # begun, then cut
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == TOWN
    loop.visited = GAME
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == LEAVE
    loop.repair = True  # no visit at a game's end for a repair alone: the next game's start
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == LEAVE


def test_a_worn_item_low_on_durability_sends_the_loop_to_halbu_with_the_staffs_charges_full(monkeypatch):
    # 22:37 on 2026-10-17: Enigma's Teleport is the character's own, the staff's charges stay full, and their repairs
    # had been what mended the gear; Enigma read 33 of 60
    from inventory_tracking.macros.repair import WEAR_BELOW, WEAR_CARRIED, due, worn_out
    from inventory_tracking.macros.world import Loot, Wear

    monkeypatch.setattr('inventory_tracking.macros.repair.STASH_TOUCHED', Path('/nonexistent/touched'))
    monkeypatch.setattr('inventory_tracking.macros.repair.unknown', lambda: False)  # his line learned
    assert worn_out(Wear(373, 23, 60))  # under 40%
    assert not worn_out(Wear(373, 33, 60))
    assert not worn_out(None)
    assert WEAR_BELOW == 0.4
    assert due(None, Wear(373, 20, 60), WEAR_CARRIED)
    assert not due(None, Wear(373, 20, 60), WEAR_CARRIED - 1)  # the cost can only be read: the stash out of reach
    assert not due(None, Wear(373, 33, 60), 900_000)
    assert not due(None, Wear(373, 20, 60), WEAR_CARRIED, waited=False)  # a visit that raised nothing: not yet
    worn: list[str] = []

    def repairs(wear: Wear | None, coins: int) -> bool:
        play, loop, visits = Game(at(PANDEMONIUM_FORTRESS)), Loop(on=True, prebuffed=GAME), []
        play.staff = None  # Teleport of the character's own: no staff read
        play.loot = Loot(stats=((14, coins),))
        run = play.run()
        run.wear = lambda: wear
        with suppress(Abort):  # (the fakes' waypoint to the chests: the leg is what counts)
            loop.leg(run, keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False, visits.append)
        worn.append(loop.wear)
        return visits == [Exit.WAYPOINT]

    assert repairs(Wear(373, 20, 60), WEAR_CARRIED)
    assert worn == ['20/60 (class 373)']
    assert not repairs(Wear(373, 20, 60), WEAR_CARRIED - 1)
    assert not repairs(Wear(373, 33, 60), 900_000)


def test_a_visit_ends_by_the_waypoint_by_the_portal_or_where_the_game_is_left():
    loop = Loop(on=True)
    assert loop.exit_of(GAME) == Exit.WAYPOINT  # a game's start: the chests next, by the waypoint
    loop.trip = GAME
    assert loop.exit_of(GAME) == Exit.PORTAL  # a trip for room: back through the portal (by the Rogue Encampment)
    loop.returned = GAME
    assert loop.exit_of(GAME) == Exit.WAYPOINT
    loop.done = GAME
    assert loop.exit_of(GAME) == Exit.LEAVE  # the game is left from where the visit ends: no walk back


def test_teleport_is_taken_while_the_gold_carried_is_high_and_left_when_it_runs_low():
    # The player, 15:24 on 2026-10-17: "if we make enough gold - we can use teleport staff more often to speed up
    # things"; Teleport spends ~11,900 gold a cycle, the sales bring about half that
    from inventory_tracking.macros.loop import teleports

    cap = 900_000
    assert teleports(320_000, cap, False)  # 35% of the cap: Teleport
    assert teleports(200_000, cap, True)  # still over 15%: on
    assert not teleports(200_000, cap, False)  # nor turned on there
    assert not teleports(130_000, cap, True)  # under 15%: Blade Warp alone
    assert teleports(None, cap, True)  # unread: as it was
    assert not teleports(None, cap, False)
    assert teleports(700_000, None, False)  # the level unread: the cap at level 99


def test_the_loops_teleport_intent_hops_and_the_plain_one_does_not():
    from inventory_tracking.macros.travel import LOOPED, LOOPED_TELEPORT

    assert LOOPED.hop_from == float('inf')
    assert LOOPED_TELEPORT.hop_from == 0.0
    assert LOOPED_TELEPORT.reserve == LOOPED.reserve  # the last charges kept as before


def test_a_session_tops_the_staff_up_only_until_it_is_done():
    # 15:48:43 on 2026-10-17: a session done at the game's start sent the loop to Halbu at its end for 5 charges
    from inventory_tracking.macros.town import tops_up
    from inventory_tracking.macros.world import Teleport

    staff = Teleport(64, 69, False)
    assert tops_up(staff, in_session=True, reported=False)
    assert not tops_up(staff, in_session=True, reported=True)
    assert not tops_up(staff, in_session=False, reported=False)
    assert not tops_up(Teleport(69, 69, False), in_session=True, reported=False)


def test_any_errand_to_a_vendor_is_the_whole_session():
    # The player, 15:52 on 2026-10-17: "when we get to maintenance (refilling, trading, repairing) - it is better to
    # identify everything, stash good, sell junk, refill, optionally repair"
    loop = Loop(on=True)
    loop.carrying, loop.free = True, 20  # room enough: no trade of its own
    fortress, lk = at(PANDEMONIUM_FORTRESS), progress_in(LOWER_KURAST)
    assert next_leg(fortress, lk, loop) == TO_THE_CHESTS
    loop.short = True  # keys or scrolls short
    assert next_leg(fortress, lk, loop) == TOWN
    loop.short, loop.repair = False, True  # the staff low
    assert next_leg(fortress, lk, loop) == TOWN
    loop.carrying = False  # nothing to trade: the visit all the same, Halbu alone in it (macros/visit.py)
    assert next_leg(fortress, lk, loop) == TOWN


def test_gold_near_its_cap_is_deposited_down_to_room_for_the_sales():
    # The player, 2026-10-17: "probably we need to move extra gold to our cube [stash]"
    from inventory_tracking.macros.town import deposit_to

    assert deposit_to(924_000, 940_000) == 690_000
    assert deposit_to(924_000, 940_000, 600_000) == 720_000  # never below the expected repair and a share over it
    assert deposit_to(800_000, 940_000) is None  # room for two sales and more: none
    assert deposit_to(None, 940_000) is None
    assert deposit_to(924_000, None) is None  # the level unread: the cap unknown


def test_after_a_start_teleport_is_on_over_the_lower_mark():
    # 16:40-16:50 on 2026-10-17: each restart began with Teleport off; at 527,000-588,000 carried (under 60% of the
    # cap) 12 of 24 stays were made without it
    from inventory_tracking.macros.loop import teleports

    assert teleports(550_000, 940_000, None)
    assert not teleports(100_000, 940_000, None)
    assert teleports(None, 940_000, None) is None  # unread: still undecided


def test_a_cube_holding_only_a_full_gem_stacks_gems_sends_the_loop_to_no_session():
    # 07:05-07:07 on 2026-10-18: ten flawless gems of full stacks (kept, neither stashed nor sold) filled the cube, the
    # room read low every game, and a session every game left it as low
    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.world import Carried, Pack

    flawless = 595  # Flawless Ruby (items metadata)
    cube = Carried(1, CUBE_CLASS, 0, 2, (2, 2))
    own = tuple(Carried(2 + x, 999 - x, x, 0, (1, 2)) for x in range(2, 10))  # the player's: few cells left
    gems = tuple(Carried(30 + n, flawless, n % 3, n // 3, (1, 1)) for n in range(10))

    def leg(extra: tuple[Carried, ...], cubed: tuple[Carried, ...] = gems[:2]) -> str:
        play = Game(at(PANDEMONIUM_FORTRESS))
        play.pack = Pack((cube, *own, *extra), ('###', '###', '###', '#..'), in_cube=cubed)
        loop = Loop(on=True)
        loop.own = frozenset({(CUBE_CLASS, 0, 2), *((item.txt, item.x, item.y) for item in own)})
        loop.full = {flawless}
        loop.done = GAME
        return loop.leg(
            play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False, lambda e: None
        )

    assert leg(()) != TOWN  # only the gems, less than a transmute's: a session would take nothing away
    assert leg((Carried(20, 135, 0, 3, (1, 2), quality=4, identified=False),)) == TOWN  # a dagger to identify
    # A transmute's worth (three into a perfect one, cube.py `transmute`): the session cubes them, and the stash takes
    # the perfect gem (21 items, no session from 09:43 to 10:22 on 2026-10-18)
    assert leg((), gems) == TOWN


def test_a_full_stacks_flawless_gems_past_a_transmutes_worth_are_sold():
    # 09:22-09:45 on 2026-10-18: all seven flawless stacks full, 19 gems kept filled the cube, no transmute had room,
    # a trade session every game, then the loop stood by a Flawless Sapphire with no room (the player: "sell surplus to
    # Jamella", a few of each kind kept for the next transmute)
    from inventory_tracking.macros.cube import perfect_of
    from inventory_tracking.macros.town import GEMS_KEPT, surplus

    ruby, sapphire, skull, potion = 595, 585, 615, 610
    gems = [Carried(n, ruby, n, 0, (1, 1)) for n in range(5)]
    gems += [Carried(10 + n, sapphire, n, 1, (1, 1)) for n in range(2)]
    gems += [Carried(20 + n, skull, n, 2, (1, 1)) for n in range(2)]
    other = Carried(30, potion, 0, 3, (1, 1))
    perfect = {made for txt in (ruby, sapphire, skull) if (made := perfect_of(txt)) is not None}
    full = frozenset({ruby, sapphire, skull, *perfect})

    # the player, 09:51: "we don't need to do gem sale until we have 99 pgems of type": the perfect stacks not full
    assert surplus([*gems, other], frozenset({ruby, sapphire, skull})) == ()

    sold = surplus([*gems, other], full)

    assert other not in sold
    kept = [g for g in gems if g not in sold]
    assert len(kept) == GEMS_KEPT
    assert sum(g.txt == ruby for g in kept) == 3  # the most of a kind: a transmute's worth kept
    assert {g.txt for g in sold} <= {ruby, sapphire, skull}
    assert surplus(gems[:3], full) == ()  # one transmute's worth: nothing sold
    assert surplus(gems, frozenset()) == ()  # no stack full: nothing sold


ROGUE_ENCAMPMENT, CATACOMBS_2, CATACOMBS_3, CATACOMBS_4 = 1, 35, 36, 37


def test_an_andariel_game_goes_down_the_catacombs_fights_her_loots_and_is_left_on_her_level():
    from inventory_tracking.macros.loop import ANDARIEL, DOWN, FIGHT_ANDARIEL, TO_THE_CATACOMBS

    killed: set[str] = set()
    found = Progress(ROUTES, PERFORMED, lambda: frozenset(killed))
    found.note(GAME, ROGUE_ENCAMPMENT)
    loop = Loop(kind=ANDARIEL)

    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_CATACOMBS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_THE_CATACOMBS  # a game begun there (LK's town)
    assert next_leg(at(CATACOMBS_2), found, loop) == DOWN
    assert next_leg(at(CATACOMBS_3), found, loop) == DOWN
    assert next_leg(at(CATACOMBS_4), found, loop) == FIGHT_ANDARIEL
    killed.add('Andariel')
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP
    found.looted(CATACOMBS_4)
    assert next_leg(at(CATACOMBS_4), found, loop) == LEAVE
    with pytest.raises(Abort, match='nothing to do in'):
        next_leg(at(LOWER_KURAST), found, loop)


def test_an_andariel_game_begun_in_the_rogue_encampment_trades_in_the_fortress():
    """The player, 2026-10-18: "inventory management and trading - same as LK": the session is the Fortress's."""
    from inventory_tracking.macros.loop import ANDARIEL, TO_THE_CATACOMBS

    loop = Loop(kind=ANDARIEL, free=TRADE_ROOM - 1, carrying=True)
    found = progress_in(ROGUE_ENCAMPMENT)

    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TOWN
    loop.carrying = False  # only what no session takes away (a full gem stack's gems): no trip for it
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_CATACOMBS
    loop.short = True  # keys or scrolls short: Jamella
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS


def test_the_loop_runs_the_kind_of_where_it_is_started_unless_chosen_by_hand():
    from inventory_tracking.macros.loop import ANDARIEL, LK, kind_of

    assert kind_of(ROGUE_ENCAMPMENT) == ANDARIEL
    assert kind_of(CATACOMBS_3) == ANDARIEL
    assert kind_of(KURAST_DOCKS) == LK
    assert kind_of(LOWER_KURAST) == LK
    assert kind_of(PANDEMONIUM_FORTRESS) is None  # both kinds' town: the kind chosen

    play = Game(at(ROGUE_ENCAMPMENT))
    loop = Loop(prebuffed=GAME)
    loop.start()
    with suppress(Abort):  # (the fakes' waypoint: the leg is what counts)
        loop.leg(play.run(), keys, progress_in(ROGUE_ENCAMPMENT), lambda: None, lambda: False)
    assert loop.kind == ANDARIEL
    hand = Loop(chosen=True)
    hand.start()
    with pytest.raises(Abort, match='nothing to do in'):
        hand.leg(play.run(), keys, progress_in(ROGUE_ENCAMPMENT), lambda: None, lambda: False)
    assert hand.kind == LK


def test_a_valuable_with_no_room_on_andariels_level_is_a_trip_to_the_fortress_and_back_through_the_portal():
    # 10:22:20 on 2026-10-18: a Flawless Topaz and an Amulet on Catacombs Level 4, the inventory full, the loop stopped
    from inventory_tracking.macros.loop import ANDARIEL, THROUGH_PORTAL, TO_THE_ENCAMPMENT, TRIP

    killed = {'Andariel'}
    found = Progress(ROUTES, PERFORMED, lambda: frozenset(killed))
    found.note(GAME, CATACOMBS_4)
    loop = Loop(kind=ANDARIEL, trip_due=True)

    assert next_leg(at(CATACOMBS_4), found, loop) == TRIP
    loop.trip_due, loop.trip = False, GAME  # (the leg's own)
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS
    loop.fortressed = GAME
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_THE_ENCAMPMENT  # the session over (none due here)
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == THROUGH_PORTAL
    loop.returned = GAME
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP
    loop.trip_due = True  # another, the runner's rules allowing it (`Loop.may_trip`): several a game
    assert next_leg(at(CATACOMBS_4), found, loop) == TRIP
    loop.trips, loop.returned = 3, None  # the bound's last on its way: none from the level meanwhile
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_THE_ENCAMPMENT


def trip_legs(loop: Loop, found: Progress, area: int) -> str:
    """The leg the loop makes where `area` is (the fakes' portal and waypoint: the leg's state is what counts)."""
    play = Game(at(area))
    leg = next_leg(at(area), found, loop)
    with suppress(Abort):
        loop.leg(play.run(), keys, found, lambda: None, lambda: False, visit=lambda exit: None)
    return leg


def test_a_game_makes_several_trips_for_room_while_each_makes_room_up_to_trips_a_game():
    # The player, 2026-10-18 16:50: "one game can do several trips to the town"; a trip that cannot help is not made
    # again and again (TRIPS_A_GAME, and none after one that made no room)
    from inventory_tracking.macros import loop as loop_module
    from inventory_tracking.macros.loop import ANDARIEL, THROUGH_PORTAL, TO_THE_ENCAMPMENT, TRIP, TRIPS_A_GAME

    found = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    found.note(GAME, CATACOMBS_4)
    forgot: list[bool] = []
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, prebuffed=GAME, carrying=True, room_tried=GAME)
    loop.start()
    loop.forget = lambda: forgot.append(True)
    for made in range(1, TRIPS_A_GAME + 1):
        assert loop.may_trip(GAME)
        loop.trip_due, loop.free = True, 2
        assert trip_legs(loop, found, CATACOMBS_4) == TRIP
        assert (loop.trip, loop.trips, loop.trip_free) == (GAME, made, 2)
        assert not loop.may_trip(GAME)  # on its way
        assert trip_legs(loop, found, ROGUE_ENCAMPMENT) == TO_THE_FORTRESS
        assert trip_legs(loop, found, PANDEMONIUM_FORTRESS) == TOWN  # a whole visit of its own, each trip
        assert loop.visited == GAME
        assert trip_legs(loop, found, PANDEMONIUM_FORTRESS) == TO_THE_ENCAMPMENT
        loop.free = 14  # the visit's room, as the next look reads it
        loop_module.SHUNNED[3821340916] = 1e9
        assert trip_legs(loop, found, ROGUE_ENCAMPMENT) == THROUGH_PORTAL
        assert (loop.returned, loop.trip_gained) == (GAME, 12)
        assert loop.room_tried is None  # the cube emptied by the visit: room made in it again before another trip
        assert not loop_module.SHUNNED  # the level's ground tried again with the room the trip made
        assert len(forgot) == made
        loop.room_tried = GAME
    assert not loop.may_trip(GAME)  # TRIPS_A_GAME made
    loop.trip_due = True
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP
    loop.trips, loop.trip_gained = 1, 0  # one trip that made no room: another cannot help
    assert not loop.may_trip(GAME)
    loop.trip = 'cyberr59'  # the game before's trips: this game has made none
    assert loop.may_trip(GAME)
    assert loop.trips_in(GAME) == 0


def test_a_game_with_its_own_visit_every_trips_visit_and_a_cut_one_is_not_given_up():
    # REPEATS: the start's visit, TRIPS_A_GAME trips' visits and one cut by the player's hand; the trips' and the
    # Gheed's swap's ways to the Fortress and back
    from inventory_tracking.macros.loop import THROUGH_PORTAL, TO_THE_ENCAMPMENT, TRIP, TRIPS_A_GAME

    loop = Loop()
    legs = {
        TOWN: 1 + TRIPS_A_GAME + 1,
        TRIP: TRIPS_A_GAME,
        TO_THE_FORTRESS: 1 + TRIPS_A_GAME + 2,
        TO_THE_ENCAMPMENT: TRIPS_A_GAME + 2,
        THROUGH_PORTAL: TRIPS_A_GAME + 2,
    }
    for leg, times in legs.items():
        for _ in range(times):
            loop.count(at(PANDEMONIUM_FORTRESS), leg)
    with pytest.raises(Abort, match='again and again'):  # one more visit than those
        loop.count(at(PANDEMONIUM_FORTRESS), TOWN)


def test_a_full_stash_after_a_town_visit_stops_the_leg_with_its_names():
    # The player, 2026-10-18 16:50: "if stash is full - we need to stop loop": the visit's contract names the keepers
    # no page takes (town.py `Contract.stash_full`); the leg stops after the visit's own end, the visit done
    from types import SimpleNamespace

    found = progress_in(PANDEMONIUM_FORTRESS)
    loop = Loop(on=True, chosen=True, prebuffed=GAME, free=TRADE_ROOM - 1, carrying=True)
    loop.start()
    contracts = [SimpleNamespace(stash_full=('Ber Rune', 'Battle Boots')), SimpleNamespace(stash_full=()), object()]

    def visit(exit: Exit) -> object:
        return contracts.pop(0)

    play = Game(at(PANDEMONIUM_FORTRESS))
    with pytest.raises(Abort, match=r'^the stash is full: Ber Rune, Battle Boots$') as stop:
        loop.leg(play.run(), keys, found, lambda: None, lambda: False, visit=visit)
    assert stop.value.cause == 'stash'
    assert loop.visited == GAME
    for _ in range(2):  # a stash with room, and a contract from before the field
        loop.visited = None
        with suppress(Abort):
            assert loop.leg(Game(at(PANDEMONIUM_FORTRESS)).run(), keys, found, lambda: None, lambda: False,
                            visit=visit) == TOWN  # fmt: skip
        assert loop.visited == GAME


def test_an_unidentified_item_or_a_rune_moved_by_hand_is_still_the_loops():
    # 10:28 on 2026-10-18: after the player sorted items by hand, Antlers, a Ring, runes and a Topaz read as theirs
    loop = Loop()
    charm, antlers, rune = (620, 0, 0), (420, 3, 0), (630, 4, 2)
    loop.sort(frozenset({charm, antlers, rune}), None, loose=frozenset({antlers, rune}))
    assert loop.own == frozenset({charm})
    assert loop.mine == frozenset({antlers, rune})


def test_the_gheeds_swap_goes_to_the_shared_stash_back_for_the_new_one_and_to_town_again_to_choose():
    # The player, 2026-10-18 13:39: "go to town; put our own gheed into SHARED tab; go back and pick new one; go to
    # town, identify; check what is better (magic find roll); keep in own inventory better one"
    from inventory_tracking.macros.charms import Parked
    from inventory_tracking.macros.loop import (
        ANDARIEL,
        CHOOSE,
        GHEED_CHOOSE,
        GHEED_STASH,
        OUT,
        PICK,
        RETURN,
        SWAP_BACK,
        SWAP_OUT,
        THROUGH_PORTAL,
        TO_THE_ENCAMPMENT,
    )

    found = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    found.note(GAME, CATACOMBS_4)
    loop = Loop(kind=ANDARIEL, swap_due=True)

    assert next_leg(at(CATACOMBS_4), found, loop) == SWAP_OUT
    loop.swap_due, loop.swap, loop.gheed = False, GAME, OUT  # (the leg's own: to town by the portal)
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == GHEED_STASH
    loop.parked, loop.gheed = Parked(1, 2, (620, 0, 0), 31), PICK  # (the leg's own: on shared page 2)
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_THE_ENCAMPMENT
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == THROUGH_PORTAL
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP  # the new one, and the rest
    loop.fresh = True  # the new one carried
    assert next_leg(at(CATACOMBS_4), found, loop) == SWAP_BACK
    loop.gheed = CHOOSE  # (the leg's own: to town by the portal)
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == GHEED_CHOOSE
    loop.parked, loop.gheed, loop.fresh = None, RETURN, False  # (the leg's own: the better one carried)
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TO_THE_ENCAMPMENT
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == THROUGH_PORTAL
    loop.gheed = None
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP
    found.looted(CATACOMBS_4)
    assert next_leg(at(CATACOMBS_4), found, loop) == LEAVE


def test_the_players_gheeds_is_never_left_in_the_stash_at_a_games_end():
    from inventory_tracking.macros.charms import Parked
    from inventory_tracking.macros.loop import ANDARIEL, GHEED_CHOOSE, PICK, SWAP_BACK

    found = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    found.note(GAME, CATACOMBS_4)
    found.looted(CATACOMBS_4)
    loop = Loop(kind=ANDARIEL, swap=GAME, parked=Parked(1, 2, (620, 0, 0), 31), gheed=PICK)
    assert next_leg(at(CATACOMBS_4), found, loop) == SWAP_BACK  # the level done, no new one: theirs fetched
    loop.abandon = True  # a game given up: the way back is tried first
    assert next_leg(at(CATACOMBS_4), found, loop) == SWAP_BACK
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == GHEED_CHOOSE
    loop.made[GAME, GHEED_CHOOSE] = 2  # tried REPEAT times: the game is left, the next game's town fetches it
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == LEAVE
    loop.abandon, loop.gheed = False, None  # (a new game)
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == GHEED_CHOOSE


def gheeds_play(new: Carried | None = None):
    from inventory_tracking.macros.charms import GHEEDS_FORTUNE, UNIQUE, grand_charm
    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.world import BANK, Pack

    cube = Carried(2, CUBE_CLASS, 1, 0, (2, 2))
    theirs = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    play = Game(at(PANDEMONIUM_FORTRESS, x=5048.0, y=5044.0))
    play.thing = Thing(9, BANK, 0, 5038.0, 5040.0)
    play.pack = Pack((theirs, cube, *((new,) if new is not None else ())), ('...',) * 4)
    play.stash_pages = [('.' * 10,) * 10] * 6
    return play, theirs, cube


def test_the_fortress_legs_park_the_players_gheeds_then_keep_the_better_one(caplog):
    from inventory_tracking.macros.charms import GHEEDS_FORTUNE, MAGIC_FIND, UNIQUE, grand_charm
    from inventory_tracking.macros.loop import ANDARIEL, GHEED_CHOOSE, GHEED_STASH, OUT, PICK, RETURN

    play, theirs, cube = gheeds_play()
    progress = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    progress.note(GAME, PANDEMONIUM_FORTRESS)
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, swap=GAME, swap_level=CATACOMBS_4, gheed=OUT)
    loop.own = frozenset({(theirs.txt, 0, 0), (cube.txt, 1, 0)})
    loop.swap_units = frozenset({1, 2})
    stats = {1: {MAGIC_FIND: 25}, 7: {MAGIC_FIND: 38}}

    def leg() -> str:
        return loop.leg(play.run(), keys, progress, lambda: None, lambda: False, item_stats=stats.get)

    assert leg() == GHEED_STASH
    assert loop.parked is not None
    assert loop.parked.page == 3
    assert loop.gheed == PICK
    assert [i.unit_id for i in carried(play).items] == [2]
    assert play.page_items == {3: [1]}

    # Back with the new one, unidentified, picked up at (9, 0); Cain identifies it
    new = Carried(7, grand_charm(), 9, 0, (1, 3), quality=UNIQUE, identified=False)
    play.pack = replace(carried(play), items=(cube, new))
    loop.gheed = 'choose'

    def identify(items) -> None:
        known = {i.unit_id for i in items}
        play.pack = replace(carried(play), items=tuple(
            replace(i, identified=True, unique=GHEEDS_FORTUNE) if i.unit_id in known else i for i in carried(play).items
        ))  # fmt: skip

    caplog.set_level('INFO')
    assert loop.leg(play.run(), keys, progress, lambda: None, lambda: False, identify=identify,
                    item_stats=stats.get, left=lambda: None) == GHEED_CHOOSE  # fmt: skip
    assert loop.parked is None
    assert loop.gheed == RETURN
    assert sorted((i.unit_id, i.x, i.y) for i in carried(play).items) == [(2, 1, 0), (7, 0, 0)]  # the new one kept
    assert (grand_charm(), 0, 0) in loop.own
    assert "the new Gheed's Fortune is better: magic find 38% against the player's 25%" in caplog.text


def test_a_full_material_stack_is_not_picked_up_as_a_full_rune_stack_but_a_gem_or_a_potion_is():
    # The player, 10:37 on 2026-10-18: "essensies are stacking to 99, when we have full stash cell - just stop picking
    # it up, there is no use for it"
    from inventory_tracking.items.metadata import metadata

    def class_of(name: str) -> int:
        [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
        return found

    essence, shard, rune = class_of('Twisted Essence of Suffering'), class_of('Western Worldstone Shard'), 629
    gem, rejuvenation = class_of('Flawless Ruby'), class_of('Full Rejuvenation Potion')
    loop = Loop(full={essence, shard, rune, gem, rejuvenation})
    assert loop.sold_full == frozenset({essence, shard, rune})


def test_a_prebuff_the_rogue_encampments_townsfolk_spoil_is_made_again_on_the_catacombs_and_the_game_kept(
    monkeypatch,
):
    # The player, 10:58 on 2026-10-18: Consume's speed is the town's too; 10:20:17: three tries among the townsfolk
    # and the game left
    from inventory_tracking.macros import loop as looping

    def spoilt(run, fresh=None):
        raise Abort('Consume: not seen in 2.5s, 3 times over')

    monkeypatch.setattr(looping, 'character_keys', lambda run, key_names: {})
    monkeypatch.setattr(looping, 'prebuff', spoilt)
    loop = Loop(kind=looping.ANDARIEL)
    play = Game(World(False, (), GAME, ()))

    def made(run, name):
        play.world = at(ROGUE_ENCAMPMENT)

    monkeypatch.setattr(looping, 'create_next_game', made)
    assert loop.leg(play.run(), keys, progress_in(ROGUE_ENCAMPMENT), lambda: None, lambda: False) == NEXT_GAME
    assert loop.prebuffed is None  # cast on Catacombs Level 2 (`DOWN`)

    play.world = World(False, (), GAME, ())
    monkeypatch.setattr(looping, 'create_next_game', lambda run, name: setattr(play, 'world', at(PANDEMONIUM_FORTRESS)))
    with pytest.raises(Abort, match='Consume'):  # elsewhere the game is left as before
        loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False)


def test_andariels_level_is_not_left_with_nothing_picked_up_before_her_drops_land():
    # 11:52:14 on 2026-10-18: Save and Exit 0.6 s after her kill; her drops land through her death animation, the last
    # 1.7 s after the kill was said (macros/loop.py `DROPS_LAND`)
    from inventory_tracking.macros.loop import ANDARIEL, DROPS_LAND

    killed = {'Andariel'}
    found = Progress(ROUTES, PERFORMED, lambda: frozenset(killed))
    found.note(GAME, CATACOMBS_4)
    play = Game(at(CATACOMBS_4))
    run = play.run()
    loop = Loop(kind=ANDARIEL, prebuffed=GAME, chosen=True)
    loop.start()
    loop.fought = ('an earlier game', run.clock() - 60.0)  # her fight was posted long before, in this game too
    begun = run.clock()

    assert loop.leg(run, keys, found, lambda: None, lambda: False) == PICK_UP
    assert run.clock() - begun >= DROPS_LAND - 0.01  # waited from the first loot leg, not the fight's post
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP  # the ground looked at again
    assert loop.leg(run, keys, found, lambda: None, lambda: False) == PICK_UP
    assert next_leg(at(CATACOMBS_4), found, loop) == LEAVE  # landed, nothing: left


def test_a_fight_long_over_leaves_her_level_with_no_wait():
    from inventory_tracking.macros.loop import ANDARIEL, DROPS_LAND

    found = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    found.note(GAME, CATACOMBS_4)
    play = Game(at(CATACOMBS_4))
    run = play.run()
    loop = Loop(kind=ANDARIEL, prebuffed=GAME, chosen=True)
    loop.start()
    loop.fought = (GAME, run.clock() - DROPS_LAND)
    begun = run.clock()

    assert loop.leg(run, keys, found, lambda: None, lambda: False) == PICK_UP
    assert run.clock() - begun < 0.5
    assert next_leg(at(CATACOMBS_4), found, loop) == LEAVE


def test_a_trip_for_room_makes_its_own_session_after_one_the_game_began_with():
    # 11:56:48 on 2026-10-18: the game's trade session in the Fortress first; the trip for room then went back through
    # the portal 3 s later with no session, still no room for a Unique Brandistock, and the loop stopped
    from inventory_tracking.macros.loop import ANDARIEL

    found = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    found.note(GAME, CATACOMBS_4)
    play = Game(at(CATACOMBS_4))
    loop = Loop(kind=ANDARIEL, prebuffed=GAME, chosen=True, trip_due=True, fortressed=GAME, visited=GAME)
    loop.start()
    with suppress(Abort):  # (the fakes' portal: the leg's state is what counts)
        loop.leg(play.run(), keys, found, lambda: None, lambda: False)
    assert loop.trip == GAME
    assert loop.visited is None  # the game's own visit is not the trip's
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS


def test_a_trip_for_room_is_a_whole_session_whatever_the_cells_count():
    # 12:36 on 2026-10-18: 9 cells free (TRADE_ROOM 8), so the trip's Fortress had nothing to do, and the Unique
    # Brandistock (2 x 4) still found no room
    from inventory_tracking.macros.loop import ANDARIEL

    found = progress_in(PANDEMONIUM_FORTRESS)
    loop = Loop(kind=ANDARIEL, free=TRADE_ROOM + 1, carrying=True, trip=GAME, visiting=GAME, visited=GAME)
    loop.visiting = loop.visited = None  # (the TRIP leg's own: a visit of its own)
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == TOWN
    assert loop.exit_of(GAME) == Exit.PORTAL


def test_an_andariel_visit_to_jamella_buys_one_key_stack():
    # The player, 2026-10-18: "probably we don't need 2x sets of keys for non LK loop; LK loop needs 2x12 keys"
    from inventory_tracking.macros.loop import ANDARIEL, LK
    from inventory_tracking.macros.portal import FROM_SLING
    from inventory_tracking.macros.shop import KEY, buys
    from inventory_tracking.macros.world import Pack

    def wants(keys: int, most: int) -> bool:
        key = next(b for b in buys(FROM_SLING, most) if b.txt == KEY)
        return key.room(Pack(keys=keys))

    assert wants(12, LK.keys)
    assert not wants(12, ANDARIEL.keys)
    assert wants(11, ANDARIEL.keys)


def test_her_drops_are_waited_for_from_her_kill_not_from_the_loot_leg(monkeypatch):
    # 13:21 on 2026-10-18: timed from the first loot leg, every game waited 2 s, her pack's fight long after her death
    # included; from the kill the service saw (terror/bosses.py KILLED_AT) a long fight waits nothing
    import time

    from inventory_tracking.macros.loop import ANDARIEL, DROPS_AFTER_KILL
    from inventory_tracking.terror import bosses

    found = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    found.note(GAME, CATACOMBS_4)
    play = Game(at(CATACOMBS_4))
    run = play.run()
    waits = []
    monkeypatch.setattr(run.pace, 'sleep', waits.append)
    loop = Loop(kind=ANDARIEL, prebuffed=GAME, chosen=True)
    loop.start()

    monkeypatch.setitem(bosses.KILLED_AT, 'Andariel', time.monotonic() - 10.0)  # her pack fought 10 s on
    assert loop.leg(run, keys, found, lambda: None, lambda: False) == PICK_UP
    assert not [w for w in waits if w > 0.2]
    assert next_leg(at(CATACOMBS_4), found, loop) == LEAVE

    found = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    found.note(GAME, CATACOMBS_4)
    monkeypatch.setitem(bosses.KILLED_AT, 'Andariel', time.monotonic() - 0.5)  # just died
    loop.leg(run, keys, found, lambda: None, lambda: False)
    assert any(DROPS_AFTER_KILL - 0.6 < w <= DROPS_AFTER_KILL - 0.5 for w in waits)


def carried(play: Game):
    assert play.pack is not None
    return play.pack


def test_the_gheed_stash_leg_forgets_the_level_runs_give_up_of_the_refused_charm():
    # 13:57:40.710 on 2026-10-18: the player's onto shared page 1 and only the pickup step's SHUNNED cleared; back at
    # 13:57:50 the level run never tried the new one (the same unit, given up), and stood 45 s by it
    from inventory_tracking.macros import loop as loop_module
    from inventory_tracking.macros.loop import ANDARIEL, GHEED_STASH, OUT, PICK

    play, theirs, cube = gheeds_play()
    progress = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    progress.note(GAME, PANDEMONIUM_FORTRESS)
    forgot: list[bool] = []
    loop = Loop(on=True, kind=ANDARIEL, chosen=True, swap=GAME, swap_level=CATACOMBS_4, gheed=OUT)
    loop.own = frozenset({(theirs.txt, 0, 0), (cube.txt, 1, 0)})
    loop.forget = lambda: forgot.append(True)
    loop_module.SHUNNED[3821340916] = 1e9  # the pickup step's own (loop.py holds it by its import)
    assert loop.leg(play.run(), keys, progress, lambda: None, lambda: False) == GHEED_STASH
    assert loop.gheed == PICK
    assert forgot == [True]
    assert not loop_module.SHUNNED


def test_a_game_is_its_name_and_the_players_unit_and_a_change_is_logged(caplog):
    # rca/2026-10-18/arch-loop-orchestration.md Option B, step 1: names come round again (the second cyber81 of a
    # session, 09:19:49 on 2026-10-18), the player's unit id is a new one in a new game; nothing reads it yet
    from inventory_tracking.macros.loop import GameId

    loop = Loop()
    caplog.set_level('INFO')
    first = world(LOWER_KURAST, game_name='cyber81', player=player(LOWER_KURAST, unit_id=7))
    assert loop.observe(first) == GameId('cyber81', 7)
    assert loop.observe(replace(first, player=player(PANDEMONIUM_FORTRESS, unit_id=7))) == GameId('cyber81', 7)
    assert loop.observe(World(False, (), 'cyber81', ())) == GameId('cyber81', 7)  # the lobby keeps the last
    assert loop.observe(replace(first, player=None)) == GameId('cyber81', 7)  # a game still loading too
    assert loop.observe(replace(first, player=player(LOWER_KURAST, unit_id=9))) == GameId('cyber81', 9)
    assert loop.game_id == ('cyber81', 9)  # the key `Sightings` keeps (world.py `Loot.game`)
    changes = [line for line in caplog.text.splitlines() if 'Macro: loop: game changed' in line]
    assert len(changes) == 2
    assert changes[0].endswith('Macro: loop: game changed: cyber81 (player unit 7), was none')
    assert changes[1].endswith('game changed: cyber81 (player unit 9), was cyber81 (player unit 7)')


def test_a_leg_observes_the_game_it_is_made_in(caplog):
    loop, lk = Loop(on=True, prebuffed=GAME), progress_in(LOWER_KURAST)
    loop.start()
    play = Game(at(LOWER_KURAST))
    caplog.set_level('INFO')
    with suppress(Abort):
        loop.leg(play.run(), lambda _world, skills=None: KEYS, lk, lambda: None, lambda: False)
    assert loop.game_id == (GAME, 1)
    assert caplog.text.count('Macro: loop: game changed') == 1


CRYSTALLINE_PASSAGE = 113


def test_a_character_hit_standing_outside_a_fight_is_beset_once():
    # 09:36:54-09:37:02 on 2026-10-19 at the Frozen River door (rca/2026-10-19/near-death-findings.md): standing, life
    # 3119 -> 2986 -> 2789 -> 2592 -> 2334 in hits of 130-260 (the player: "we stood still while under attack and
    # almost died")
    from inventory_tracking.macros.loop import BESET_SECONDS

    loop, door = Loop(), (10212.5, 5359.5)
    loop.start()
    assert not loop.beset(door, (3119, 3134), 0.0, GAME, CRYSTALLINE_PASSAGE)
    assert not loop.beset(door, (2986, 3134), 1.0, GAME, CRYSTALLINE_PASSAGE)  # 4 %: one small hit
    assert loop.beset(door, (2789, 3134), 3.0, GAME, CRYSTALLINE_PASSAGE)  # 11 % in 3 s
    assert not loop.beset(door, (2592, 3134), 4.0, GAME, CRYSTALLINE_PASSAGE)  # said once: counted afresh
    assert loop.beset(door, (2334, 3134), 6.0, GAME, CRYSTALLINE_PASSAGE)
    # A loss spread over more than BESET_SECONDS, a loss while moving, in a town or a new game: no stand under attack
    assert not loop.beset(door, (3000, 3134), 10.0, GAME, CRYSTALLINE_PASSAGE)
    assert not loop.beset(door, (2900, 3134), 10.0 + BESET_SECONDS + 0.5, GAME, CRYSTALLINE_PASSAGE)
    assert not loop.beset((10230.0, 5359.5), (2700, 3134), 16.0, GAME, CRYSTALLINE_PASSAGE)
    assert not loop.beset(door, (3134, 3134), 20.0, GAME, PANDEMONIUM_FORTRESS)
    assert not loop.beset(door, (2700, 3134), 21.0, GAME, PANDEMONIUM_FORTRESS)
    assert not loop.beset(door, (3134, 3134), 30.0, GAME, CRYSTALLINE_PASSAGE)
    assert not loop.beset(door, (2700, 3134), 31.0, 'cyber33', CRYSTALLINE_PASSAGE)
    assert not loop.beset(None, (2700, 3134), 32.0, GAME, CRYSTALLINE_PASSAGE)  # unread
    assert not loop.beset(door, None, 33.0, GAME, CRYSTALLINE_PASSAGE)
    # Being left already: no second recovery
    loop.abandon = True
    assert not loop.beset(door, (3134, 3134), 40.0, GAME, CRYSTALLINE_PASSAGE)
    assert not loop.beset(door, (2700, 3134), 41.0, GAME, CRYSTALLINE_PASSAGE)


def recovered_past_the_limit(loop: Loop) -> None:
    """Recoveries one after another, past RECOVERIES: the next leg is to wait RECOVERY_PAUSE (`cooling`)."""
    import time

    from inventory_tracking.macros.loop import RECOVERIES

    now = time.monotonic()
    for at in range(RECOVERIES + 1):
        assert loop.recover(Abort('TZ next level again and again in cyber32: nothing came of it'), now + at * 0.01)
    assert loop.cooling > now


def test_the_pause_after_recoveries_is_not_stood_in_a_battle_level_the_game_is_left_first(caplog):
    # 09:36:41-09:37:11 on 2026-10-19: the pause stood 30 s at the Frozen River door, three hostiles hit the character
    # from 3119 to 2334 life until the player struck them; then Save and Exit (rca/2026-10-19/near-death-findings.md)
    from inventory_tracking.macros.loop import RECOVERY_PAUSE

    play = Game(at(LOWER_KURAST))
    loop = Loop(on=True)
    loop.start()
    recovered_past_the_limit(loop)
    with caplog.at_level('INFO'):
        assert loop.leg(play.run(), keys, progress_in(LOWER_KURAST), lambda: None, lambda: False) == LEAVE
    assert play.clock.now < RECOVERY_PAUSE / 2  # not stood: Save and Exit at once
    assert 'Save and Exit' in play.said
    assert 'the pause after recoveries (30 s) is not stood in level 79: the game is left first' in caplog.text


def test_the_pause_after_recoveries_is_waited_in_a_town():
    from inventory_tracking.macros.loop import RECOVERY_PAUSE

    play = Game(at(PANDEMONIUM_FORTRESS))
    loop = Loop(on=True, prebuffed=GAME)
    loop.start()
    recovered_past_the_limit(loop)
    assert loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False) == LEAVE
    assert play.clock.now >= RECOVERY_PAUSE - 1  # the town: the pause kept, as before
