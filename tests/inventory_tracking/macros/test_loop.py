"""The Lower Kurast loop (routes/lower-kurast-loop-plan.md phase 4): the leg from where the character is, and a
game from Pandemonium Fortress to the lobby over the scripted game."""

from contextlib import suppress
from pathlib import Path

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import (
    CHESTS,
    GAME_SECONDS,
    IDENTIFY,
    LEAVE,
    NEXT_GAME,
    PICK_UP,
    PORTAL,
    REPAIR,
    SHOP,
    STASH,
    STILL_SECONDS,
    TO_THE_CHESTS,
    TO_THE_FORTRESS,
    TRADE_ROOM,
    Dead,
    Loop,
    next_leg,
)
from inventory_tracking.macros.route import PERFORMED
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
    # Phase 9: the loop's items into the cube between games (macros/cube.py); the player's own stay
    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.world import Carried, Pack

    play = Game(at(PANDEMONIUM_FORTRESS))
    play.pack = Pack((Carried(1, CUBE_CLASS, 0, 0, (2, 2)),), ('...',) * 4)
    loop, stashed = Loop(on=True), []
    loop.done = GAME  # the chests done: the game is left

    def stash(own, keep=frozenset(), force=False):
        stashed.append(own)
        return 0

    assert loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False, stash) == LEAVE
    assert stashed == [frozenset({(CUBE_CLASS, 0, 0)})]
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


def test_the_staff_under_20_percent_of_its_charges_is_repaired_before_the_chests(monkeypatch):
    # The player, 2026-10-17: "we can start thinking on repairing teleport charges ... to travel more efficiently"
    from inventory_tracking.macros.loop import REPAIR
    from inventory_tracking.macros.repair import wants
    from inventory_tracking.macros.world import Teleport

    monkeypatch.setattr('inventory_tracking.macros.repair.STASH_TOUCHED', Path('/nonexistent/touched'))
    assert wants(Teleport(3, 20, False))  # under 20% (repair.py REPAIR_BELOW: the sessions top it up meanwhile)
    assert not wants(Teleport(4, 20, False))
    assert not wants(None)
    monkeypatch.setattr('inventory_tracking.macros.repair.ENABLED', False)
    assert not wants(Teleport(0, 69, False))  # off
    loop, lk = Loop(), progress_in(LOWER_KURAST)
    loop.repair = True
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == REPAIR
    loop.short = True
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == SHOP  # the shop first: a key or a scroll short


def test_the_trade_waits_for_the_room_to_run_low_then_identifies_stashes_and_sells_in_one_session():
    # The player, 2026-10-17: "we need to perform mass identify at decard cain -> stash good -> sell junk -> return to
    # loop"; "probably we need to trade not by 2 junk items, but by remaining free slots"
    from inventory_tracking.macros.cube import CUBE_CLASS
    from inventory_tracking.macros.world import Carried, Pack

    cube = Carried(1, CUBE_CLASS, 0, 0, (2, 2))
    charms = Carried(2, 999, 0, 2, (10, 2))  # the player's own items: two rows of the inventory
    full = ('###',) * 4  # the cube full
    unknown = [Carried(10 + n, 41, 2 + n, 0, (1, 3), quality=4, identified=False) for n in range(4)]
    play = Game(at(PANDEMONIUM_FORTRESS))
    loop, stashed, asked = Loop(on=True), [], []
    loop.done = GAME  # the chests done, back in the fortress
    loop.own = frozenset({(CUBE_CLASS, 0, 0), (999, 0, 2)})  # the player's, read at the loop's start
    play.pack = Pack((cube, charms, *unknown[:3]), ('...',) * 4, in_cube=(unknown[3],), cube_items=frozenset({13}))
    lk = progress_in(PANDEMONIUM_FORTRESS)
    junked: set[int] = set()

    def stash(own, keep=frozenset(), force=False):
        stashed.append((keep, force))
        return 0

    def identify(items):
        asked.append(sorted(i.unit_id for i in items))
        assert play.pack is not None
        known = tuple(Carried(i.unit_id, i.txt, i.x, i.y, i.size, i.quality) for i in (*play.pack.items[2:],))
        cubed = tuple(Carried(i.unit_id, i.txt, i.x, i.y, i.size, i.quality) for i in play.pack.in_cube)
        play.pack = Pack((cube, charms, *known), full, in_cube=cubed, cube_items=frozenset({13}))
        junked.update({10, 12, 13})  # the appraisal: three junk, one keeper (11)

    def judge(items):
        return [i for i in items if i.unit_id in junked]

    def leg():
        return loop.leg(play.run(), keys, lk, lambda: None, lambda: False, stash, identify, judge)

    assert leg() == LEAVE  # 7 + 12 cells free in the inventory and the cube: no trade yet (`shopped`: no Jamella here)
    play.pack = Pack((cube, charms, *unknown[:3]), full, in_cube=(unknown[3],), cube_items=frozenset({13}))
    play.world = at(PANDEMONIUM_FORTRESS)  # the next game's end, the same game's name in the fakes
    loop.made.clear()
    loop.shopped = None
    stashed.clear()
    assert leg() == IDENTIFY  # 7 cells free (the cube full): the whole session, the cube's item among them
    assert asked == [[10, 11, 12, 13]]
    assert [i.unit_id for i in loop.junk] == [10, 12, 13]  # in the inventory and in the cube
    assert stashed == [(frozenset({10, 12, 13}), True)]  # at once, beside Cain: the keeper in, the junk stays
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == SHOP  # then Jamella in the same session, the room or not
    loop.shopped = GAME
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == STASH  # the cube not empty yet: the stash again
    loop.cubed = False  # sold and stashed: the cube empty
    assert next_leg(at(PANDEMONIUM_FORTRESS), lk, loop) == LEAVE  # once a game


def test_the_session_waits_for_the_room_to_run_low_and_is_made_once_a_game():
    loop = Loop(on=True)
    loop.unknown, loop.free = (carried_of(),), 20
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == TO_THE_CHESTS
    loop.free, loop.carrying = 6, True  # under TRADE_ROOM with the loop's items carried: the session now
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == IDENTIFY
    loop.identified = GAME  # tried in this game: not again
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
    assert loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False) == IDENTIFY


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
        return loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False), loop

    made, loop = leg(('###', '###', '##.', '##.'))
    assert made == IDENTIFY
    assert loop.free is not None
    assert loop.free < TRADE_ROOM
    # The same inventory with a column of three free in the cube: room as before, no session
    made, loop = leg(('##.', '##.', '##.', '###'))
    assert made != IDENTIFY
    assert loop.free is not None
    assert loop.free >= TRADE_ROOM


def test_a_session_at_a_games_end_repairs_before_the_game_is_left():
    # The player, 2026-10-17: "we must go to LK with all refilled and empty cube and free inventory slots"
    loop = Loop(on=True)
    loop.done = loop.identified = GAME
    loop.shopped = GAME  # sold
    loop.repair = True  # a charge missing, the carried gold enough
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == REPAIR
    loop.repair = False
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == LEAVE
    loop.identified = None  # no session this game: the repair waits for the next game's start
    loop.repair = True
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == LEAVE


def test_a_worn_item_low_on_durability_sends_the_loop_to_halbu_with_the_staffs_charges_full(monkeypatch):
    # 22:37 on 2026-10-17: Enigma's Teleport is the character's own, the staff's charges stay full, and their repairs
    # had been what mended the gear; Enigma read 33 of 60
    from inventory_tracking.macros.repair import WEAR_BELOW, WEAR_CARRIED, worn_out
    from inventory_tracking.macros.world import Loot, Wear

    monkeypatch.setattr('inventory_tracking.macros.repair.STASH_TOUCHED', Path('/nonexistent/touched'))
    assert worn_out(Wear(373, 23, 60))  # under 40%
    assert not worn_out(Wear(373, 33, 60))
    assert not worn_out(None)
    assert WEAR_BELOW == 0.4
    visits = []
    monkeypatch.setattr('inventory_tracking.macros.loop.repair', lambda run, fix=True: visits.append(fix) or True)
    monkeypatch.setattr('inventory_tracking.macros.loop.back', lambda run: None)
    monkeypatch.setattr('inventory_tracking.macros.loop.unknown', lambda: False)  # his line learned
    worn: list[str] = []

    def repairs(wear: Wear | None, coins: int) -> bool:
        play, loop = Game(at(PANDEMONIUM_FORTRESS)), Loop(on=True)
        play.staff = None  # Teleport of the character's own: no staff read
        play.loot = Loot(stats=((14, coins),))
        run = play.run()
        run.wear = lambda: wear
        loop.done = loop.identified = loop.shopped = GAME  # a session at the game's end: Halbu, else the game left
        leg = loop.leg(run, keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False)
        worn.append(loop.wear)
        return leg == REPAIR

    assert repairs(Wear(373, 20, 60), WEAR_CARRIED)
    assert worn == ['20/60 (class 373)']
    assert not repairs(Wear(373, 20, 60), WEAR_CARRIED - 1)  # the cost can only be read: the stash kept out of reach
    assert not repairs(Wear(373, 33, 60), 900_000)
    assert visits == [True]


def test_a_session_goes_to_the_stash_again_when_the_cube_still_holds_items_after_the_sales():
    # 13:15:47 on 2026-10-17: three of the cube's keepers did not come out, the inventory full of the junk still to
    # sell; the contract wants an empty cube
    loop = Loop(on=True)
    loop.identified = loop.shopped = GAME
    loop.cubed = True
    loop.repair = True  # Halbu first: he stands by Jamella, the stash by the waypoint (16:54 on 2026-10-17)
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == REPAIR
    loop.repair = False
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == STASH
    loop.restashed = GAME  # once a game
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == TO_THE_CHESTS


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


def test_near_the_gold_cap_a_session_repairs_before_it_sells():
    # 15:33:27 on 2026-10-17: no sale at 908,518 of 940,000 carried, then the repair spent 39,237: the sales' room
    loop = Loop(on=True)
    loop.identified = GAME
    loop.junk = (Carried(9, 418, 0, 0, (2, 2), 4, identified=True),)
    loop.repair = loop.capped = True
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == REPAIR
    loop.capped = False  # room for the sales: they come first, the repair after them
    assert next_leg(at(PANDEMONIUM_FORTRESS), progress_in(PANDEMONIUM_FORTRESS), loop) == SHOP


def test_a_session_tops_the_staff_up_only_until_it_is_done():
    # 15:48:43 on 2026-10-17: a session done at the game's start sent the loop to Halbu at its end for 5 charges
    from inventory_tracking.macros.loop import tops_up
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
    assert next_leg(fortress, lk, loop) == IDENTIFY
    loop.short, loop.repair = False, True  # the staff low
    assert next_leg(fortress, lk, loop) == IDENTIFY
    loop.carrying = False  # nothing to trade: the errand alone
    assert next_leg(fortress, lk, loop) == REPAIR


def test_gold_near_its_cap_is_deposited_down_to_room_for_the_sales():
    # The player, 2026-10-17: "probably we need to move extra gold to our cube [stash]"
    from inventory_tracking.macros.loop import deposit_to

    assert deposit_to(924_000, 940_000) == 690_000
    assert deposit_to(800_000, 940_000) is None  # room for two sales and more: none
    assert deposit_to(None, 940_000) is None
    assert deposit_to(924_000, None) is None  # the level unread: the cap unknown


def test_after_halbu_the_loop_goes_to_jamella_when_she_is_next_not_to_the_waypoint():
    # The player, 2026-10-17: "we repaired staff -> walked to wp -> walked to jamella"
    loop = Loop(on=True)
    loop.identified = GAME
    loop.junk = (Carried(9, 418, 0, 0, (2, 2), 4, identified=True),)
    assert loop.shop_next(GAME)
    loop.shopped = GAME  # sold already: the waypoint next
    assert not loop.shop_next(GAME)
    loop.shopped, loop.junk, loop.identified = None, (), None
    assert not loop.shop_next(GAME)  # no session, nothing short
    loop.short = True
    assert loop.shop_next(GAME)


def test_after_halbu_at_a_games_end_the_game_is_left_from_beside_him():
    # 18:04:54 on 2026-10-17: 8.6 s walked back to the waypoint, then Save and Exit; a new game starts by it anyway
    loop = Loop(on=True)
    assert loop.walks_back(GAME)  # the chests still to come: the waypoint next
    loop.done = GAME
    assert not loop.walks_back(GAME)  # the game is left next
    loop.cubed = True  # the cube's keepers for the stash again, by the waypoint
    assert loop.walks_back(GAME)
    loop.restashed = GAME
    assert not loop.walks_back(GAME)


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
        return loop.leg(play.run(), keys, progress_in(PANDEMONIUM_FORTRESS), lambda: None, lambda: False)

    assert leg(()) != IDENTIFY  # only the gems, less than a transmute's: a session would take nothing away
    assert leg((Carried(20, 135, 0, 3, (1, 2), quality=4, identified=False),)) == IDENTIFY  # a dagger to identify
    # A transmute's worth (three into a perfect one, cube.py `transmute`): the session cubes them, and the stash takes
    # the perfect gem (21 items, no session from 09:43 to 10:22 on 2026-10-18)
    assert leg((), gems) == IDENTIFY


def test_a_full_stacks_flawless_gems_past_a_transmutes_worth_are_sold():
    # 09:22-09:45 on 2026-10-18: all seven flawless stacks full, 19 gems kept filled the cube, no transmute had room,
    # a trade session every game, then the loop stood by a Flawless Sapphire with no room (the player: "sell surplus to
    # Jamella", a few of each kind kept for the next transmute)
    from inventory_tracking.macros.cube import perfect_of
    from inventory_tracking.macros.loop import GEMS_KEPT, surplus

    ruby, sapphire, skull, potion = 595, 585, 615, 610
    gems = [Carried(n, ruby, n, 0, (1, 1)) for n in range(5)]
    gems += [Carried(10 + n, sapphire, n, 1, (1, 1)) for n in range(2)]
    gems += [Carried(20 + n, skull, n, 2, (1, 1)) for n in range(2)]
    other = Carried(30, potion, 0, 3, (1, 1))
    perfect = {perfect_of(txt) for txt in (ruby, sapphire, skull)}
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
    from inventory_tracking.macros.loop import ANDARIEL, IDENTIFY, TO_THE_CATACOMBS

    loop = Loop(kind=ANDARIEL, free=TRADE_ROOM - 1, carrying=True)
    found = progress_in(ROGUE_ENCAMPMENT)

    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == TO_THE_FORTRESS
    assert next_leg(at(PANDEMONIUM_FORTRESS), found, loop) == IDENTIFY
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
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP  # once a game: no second trip
    loop.trip_due = True
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP


def test_an_unidentified_item_or_a_rune_moved_by_hand_is_still_the_loops():
    # 10:28 on 2026-10-18: after the player sorted items by hand, Antlers, a Ring, runes and a Topaz read as theirs
    loop = Loop()
    charm, antlers, rune = (620, 0, 0), (420, 3, 0), (630, 4, 2)
    loop.sort(frozenset({charm, antlers, rune}), None, loose=frozenset({antlers, rune}))
    assert loop.own == frozenset({charm})
    assert loop.mine == frozenset({antlers, rune})


def test_a_refused_unique_grand_charm_puts_the_players_gheeds_away_and_brings_it_back_before_the_game_is_left():
    from inventory_tracking.macros.loop import ANDARIEL, SWAP_BACK, SWAP_OUT

    found = Progress(ROUTES, PERFORMED, lambda: frozenset({'Andariel'}))
    found.note(GAME, CATACOMBS_4)
    loop = Loop(kind=ANDARIEL, swap_due=True)

    assert next_leg(at(CATACOMBS_4), found, loop) == SWAP_OUT
    loop.swap_due, loop.swap = False, GAME
    loop.parked = Carried(1, 620, 2, 0, (1, 3), quality=7, unique=359)  # (the leg's own: theirs on the stash page)
    assert next_leg(at(CATACOMBS_4), found, loop) == PICK_UP  # the new one, and the rest
    found.looted(CATACOMBS_4)
    assert next_leg(at(CATACOMBS_4), found, loop) == SWAP_BACK  # never Save and Exit with theirs in the stash
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == SWAP_BACK
    loop.parked, loop.done = None, GAME
    assert next_leg(at(ROGUE_ENCAMPMENT), found, loop) == LEAVE


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
