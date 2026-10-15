"""The Lower Kurast loop (routes/lower-kurast-loop-plan.md phase 4): the leg from where the character is, and a
game from Pandemonium Fortress to the lobby over the scripted game."""

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import (
    CHESTS,
    LEAVE,
    NEXT_GAME,
    PICK_UP,
    PORTAL,
    TO_THE_CHESTS,
    TO_THE_FORTRESS,
    Loop,
    next_leg,
)
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.world import Thing, World
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
    with pytest.raises(Abort, match='the character is dead'):
        next_leg(at(LOWER_KURAST, mode=0), lk, loop)


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
