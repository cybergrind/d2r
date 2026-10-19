"""The terror zone kinds of the KP_6 loop (macros/tzloop.py) over the scripted game: each leg is the agenda's goal,
made through `Loop.leg`. The routines a leg calls (the waypoint, Town Portal, back through it, the prebuff) have their
own tests; here they are recorded and move the character, so the order of the goals is what is checked. Offline: no
proof of the game's own behaviour (macros/goals-plan.md §9)."""

from dataclasses import replace

import pytest

from inventory_tracking.macros import loop as loop_module, tzloop
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.agenda import KILL, LEAVE_GAME, ON_THE_WAY, Leader, LevelView, Objective, town_of
from inventory_tracking.macros.loop import (
    LEAVE,
    TOWN,
    TZ,
    TZ_BACK,
    TZ_CLEAR,
    TZ_LEVEL,
    TZ_LOOT,
    TZ_NEXT_LEVEL,
    TZ_PICKUP,
    TZ_PORTAL,
    TZ_WAYPOINT,
    LegHands,
    Loop,
    loop_kinds,
)
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.town import Exit
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.fakes import KEYS, Game, player, world


GAME = 'cyber32'
CATACOMBS = frozenset((32, 33, 34, 35, 36, 37))
ROGUE_ENCAMPMENT, FORTRESS = 1, 103


def keys(_world, skills=None):
    return {skill: {**KEYS, 220: 'x'}[skill] for skill in skills or ()}


def at(area: int):
    return world(area, player=player(area))


class Script:
    """A terror zone game: the fakes' game read, the leg routines recorded and moving the character."""

    def __init__(self, area: int, monkeypatch: pytest.MonkeyPatch, zone: frozenset[int] = CATACOMBS):
        self.play = Game(at(area))
        self.killed: set[str] = set()
        self.progress = Progress(ROUTES, PERFORMED, lambda: frozenset(self.killed), wanted=lambda a: a in zone)
        self.progress.note(GAME, area)
        self.zone = zone
        self.calls: list[tuple] = []
        self.sightings: dict[int, str] = {}
        self.picks: list[bool] = []
        self.portal_from: int | None = None
        self.loop = Loop(on=True, kind=TZ, chosen=True, prebuffed=GAME)
        self.loop.start()
        self.runs: list[int] = []
        self.on_run = lambda area: None
        monkeypatch.setattr(tzloop, 'travel', lambda run, to, marks=None: self.go('waypoint', to))
        monkeypatch.setattr(tzloop, 'to_town', self.to_town)
        monkeypatch.setattr(loop_module, 'through_portal', lambda run, near=None: self.go('through', self.portal_from))
        monkeypatch.setattr(loop_module, 'prebuff', lambda run, **_: self.calls.append(('prebuff',)))
        monkeypatch.setattr(tzloop, 'gold', lambda run: None)

    @property
    def area(self) -> int:
        here = self.play.world.player
        assert here is not None
        return here.area

    def go(self, what: str, area: int | None) -> None:
        assert area is not None
        self.calls.append((what, area))
        self.play.world = at(area)
        self.progress.note(GAME, area)

    def to_town(self, run, key_names, first=None) -> None:
        self.portal_from = self.area
        self.go('portal', town_of(self.area))

    def level_run(self) -> None:
        # The runner's: the level run posted and over by itself (runner.py `_run_over`: `Agenda.ran`)
        self.runs.append(self.area)
        self.on_run(self.area)
        self.loop.agenda.ran(self.area)

    def take_one(self) -> bool:
        return self.picks.pop(0) if self.picks else False

    def door(self) -> None:
        step = self.progress.step(self.area)
        assert step is not None
        assert step.stage.to
        self.go('door', step.stage.to)

    def sighted(self, area: int | None) -> str | None:
        found = [label for where, label in self.sightings.items() if area is None or where == area]
        return found[0] if found else None

    def hands(self, visit=None) -> LegHands:
        return LegHands(
            self.level_run,
            self.take_one,
            visit=visit,
            way_on=self.door,
            sighted=self.sighted,
            terrorized=lambda area: area in self.zone,
        )

    def leg(self, visit=None) -> str:
        return self.loop.leg(self.play.run(), keys, self.progress, self.hands(visit))


def test_a_catacombs_terror_zone_game_kills_the_elites_on_the_way_then_andariel_and_is_left(monkeypatch):
    # The player, 2026-10-19: "what will catacombs TZLeveling looks like: we're finding each elite on the way to
    # Andariel, kill her and start a new game"
    game = Script(ROGUE_ENCAMPMENT, monkeypatch)
    targets: list[tuple[int, str | None]] = []
    here = (5000.0, 5000.0)

    def run_of(area: int) -> None:
        # What the level run asks the agenda at its looks (hunting/choice.py `agenda_target`): a champion in the read on
        # Level 2, on Level 4 a unique by Andariel; once dead, nothing of the agenda's: the route's own goal (her fight)
        agenda = game.loop.agenda
        seen = {35: Leader(7, (5060.0, 5000.0), 'a champion'), 37: Leader(8, (5020.0, 5000.0), 'a unique')}
        if area in seen:
            first = agenda.in_level(LevelView(area, here, (seen[area],), policy=ON_THE_WAY))
            targets.append((area, first.kind if first is not None else None))
        last = agenda.in_level(LevelView(area, here, (), policy=ON_THE_WAY))
        targets.append((area, last.kind if last is not None else None))
        if area == 37:
            game.killed.add('Andariel')

    game.on_run = run_of
    legs = [game.leg() for _ in range(16) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [
        TZ_WAYPOINT,
        *[TZ_LEVEL, TZ_NEXT_LEVEL] * 5,  # Inner Cloister, Cathedral, Catacombs 1-3: each run, then the way on
        TZ_LEVEL,  # Level 4: the unique, then her fight (the route's goal)
        TZ_LOOT,
        LEAVE,  # no goals left: Save and Exit, the next game
    ]
    assert game.runs == [32, 33, 34, 35, 36, 37]
    assert [kind for area, kind in targets if area == 35] == [KILL, None]  # the champion, then the way on
    assert [kind for area, kind in targets if area == 37] == [KILL, None]  # the unique, then Andariel
    assert all(kind is None for area, kind in targets if area not in (35, 37))
    assert ('waypoint', 32) in game.calls
    assert ('prebuff',) not in game.calls
    assert 'Save and Exit' in game.play.said
    assert game.loop.games == 1


def test_the_room_package_goes_to_town_and_back_through_the_portal_then_the_level_goes_on(monkeypatch):
    game = Script(36, monkeypatch)
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    tzloop.trip(game.loop, GAME, 36)
    exits: list[Exit] = []
    legs = [game.leg(visit=exits.append) for _ in range(6)]

    assert legs == [TZ_PORTAL, TZ_WAYPOINT, TOWN, TZ_WAYPOINT, TZ_BACK, TZ_LEVEL]
    assert [call for call in game.calls if call[0] != 'prebuff'] == [
        ('portal', ROGUE_ENCAMPMENT),
        ('waypoint', FORTRESS),
        ('waypoint', ROGUE_ENCAMPMENT),
        ('through', 36),
    ]
    assert exits == [Exit.PORTAL]
    assert (game.loop.trips, game.loop.returned) == (1, GAME)
    assert game.loop.agenda.stack == []


def test_a_level_whose_goals_run_out_is_left_and_never_with_a_valuable_on_the_ground(monkeypatch):
    game = Script(37, monkeypatch)
    game.killed.add('Andariel')
    game.progress.looted(37)
    game.sightings[37] = 'Ist Rune at (100, 200)'

    with pytest.raises(Abort, match='no pickup and no trip back took it'):
        game.leg()  # a valuable seen on this level first, before the metric's run; the pickup's failure is a stop
    game.picks = [True]
    assert game.leg() == TZ_PICKUP
    del game.sightings[37]  # off the ground
    assert game.leg() == TZ_LEVEL  # its first run (the leaders), whatever the route says
    assert game.leg() == LEAVE  # the route over, nothing seen: no goals
    assert 'Save and Exit' in game.play.said


def test_the_leave_leg_itself_refuses_a_game_with_a_valuable_on_another_level(monkeypatch):
    game = Script(37, monkeypatch)
    game.sightings[36] = 'Ber Rune at (1, 2)'
    goal = Objective(LEAVE_GAME, 'no goals left', 60)
    with pytest.raises(Abort, match='Ber Rune') as stop:
        tzloop.perform(game.loop, game.play.run(), keys, game.progress, goal, game.hands())
    assert stop.value.cause == 'room'  # the room rules, then the stop for the player (runner.py `_loop_stopped`)
    assert 'Save and Exit' not in game.play.said


def test_a_game_with_no_zone_read_is_a_stop_and_a_dead_character_stops_the_loop(monkeypatch):
    from inventory_tracking.macros.loop import Dead

    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=frozenset())
    with pytest.raises(Abort, match='no terror zone is read'):
        game.leg()
    dead = Script(35, monkeypatch)
    dead.play.world = replace(at(35), player=player(35, mode=0))
    with pytest.raises(Dead):
        dead.leg()


def test_the_terror_zone_kinds_are_offered_only_once_promoted(monkeypatch):
    monkeypatch.setattr(tzloop, 'ENABLED', False)
    assert set(loop_kinds()) == {'lk', 'andariel'}
    monkeypatch.setattr(tzloop, 'ENABLED', True)
    assert set(loop_kinds()) == {'lk', 'andariel', 'tz', 'tzclear'}
    assert (TZ.metric, TZ_CLEAR.name) == ('elite kills an hour', 'Full clear TZ')
    assert TZ.game_seconds is not None
    assert TZ.game_seconds > 240.0


def test_a_runner_restarted_with_a_terror_zone_kind_keeps_its_own_while_it_is_off(monkeypatch):
    from tests.inventory_tracking.macros.test_runner import make

    monkeypatch.setattr(tzloop, 'ENABLED', False)
    made = make(lambda cancelled, routine: None, [])
    made.resume({'loop': False, 'loop_kind': 'tz'})
    assert made.loop.kind.key == 'lk'
    made.close()


# -- the level run with the agenda (hunting/choice.py `agenda_cleared`, `agenda_target`) and its mode
# -------------------------


def agenda_hunt(policy: str):
    from inventory_tracking.macros.agenda import Agenda
    from inventory_tracking.macros.pursuit import FULL, Pursuit
    from inventory_tracking.macros.runmode import AGENDA, Mode
    from tests.inventory_tracking.macros.test_hunt import game as hunt_game, hunter

    play = hunt_game(area=35)
    hunt = hunter(play)
    run = play.run()
    hunt.agenda, hunt.agenda_policy = Agenda(), lambda area: policy
    hunt.agenda.begin('g')
    hunt.pursuit = Pursuit('pickup', 10.0, advance=False, leash=FULL, looped=True, agenda=True)
    hunt.mode = Mode(True, AGENDA, agenda=True)
    return play, hunt, run


def test_the_agenda_runs_target_is_the_leader_before_the_routes_door_and_white_monsters_are_left():
    from inventory_tracking.levels.model import Ground
    from inventory_tracking.macros.goals import PLACE_NEAR, Goal
    from inventory_tracking.macros.travel import PRESSED
    from inventory_tracking.routes.model import ENTER, FIGHT
    from tests.inventory_tracking.macros.test_hunt import CHAMPION, foe

    play, hunt, run = agenda_hunt(ON_THE_WAY)
    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Andariel')
    champion, white = foe(31, 5060.0, 5000.0, flags=CHAMPION), foe(32, 5010.0, 5000.0)
    goal = hunt.cleared(run, play.world, [white, champion], Ground(()), door)
    assert goal is not None
    assert (goal.do, goal.unit, goal.route) == (FIGHT, 31, 'Andariel')  # TZ leveling: only elites/champions
    assert hunt.cleared(run, play.world, [white], Ground(()), door) == door  # none left: the route's way on


def test_a_full_clear_tz_run_goes_for_every_hostile():
    from inventory_tracking.levels.model import Ground
    from inventory_tracking.macros.agenda import FULL_CLEAR
    from tests.inventory_tracking.macros.test_hunt import foe

    play, hunt, run = agenda_hunt(FULL_CLEAR)
    white = foe(32, 5010.0, 5000.0)
    goal = hunt.cleared(run, play.world, [white], Ground(()), None)
    assert goal is not None
    assert goal.unit == 32


def test_a_side_drop_with_a_hostile_by_it_is_that_fight_first_then_the_drop():
    from inventory_tracking.levels.model import Ground
    from inventory_tracking.macros.goals import PICK_REACH, PICK_UP, Goal
    from inventory_tracking.macros.travel import PRESSED
    from inventory_tracking.routes.model import FIGHT
    from tests.inventory_tracking.macros.test_hunt import foe

    play, hunt, run = agenda_hunt(ON_THE_WAY)
    rune = Goal('Ist Rune, on the way', (5040.0, 5000.0), PICK_UP, PICK_REACH, PRESSED, unit=900)
    guard = foe(33, 5045.0, 5002.0)  # a plain one by the rune: the fight first
    first = hunt.cleared(run, play.world, [guard], Ground(()), rune)
    assert first is not None
    assert (first.do, first.unit) == (FIGHT, 33)
    # the run's own work, on a level with no route too: no `run_level` end (09:01:51 on 2026-10-19, Great Marsh)
    assert first.clearing
    assert not first.route
    assert hunt.cleared(run, play.world, [], Ground(()), rune) == rune


def test_a_kp6_loops_run_is_no_full_clear_on_a_terror_zone_and_the_agenda_run_is_its_own_mode():
    # The player, 2026-10-19 ~02:12: "andy loop shouldn't focus on full clearing level"
    from inventory_tracking.macros.hunt import Bearings
    from inventory_tracking.macros.pursuit import FULL, Pursuit
    from inventory_tracking.macros.runmode import AGENDA, TERROR, Mode, badge
    from tests.inventory_tracking.macros.test_hunt import game as hunt_game, hunter

    play = hunt_game(area=37)
    hunt = hunter(play)
    hunt.bearings = Bearings(Progress(ROUTES, PERFORMED, wanted=lambda area: True))
    run = play.run()
    fight = Pursuit('pickup', 10.0, advance=False, leash=FULL, rush=False, looped=True)
    assert hunt.run_mode(run, 37, fight) == Mode(False)
    pressed = Pursuit('pickup', 10.0, advance=False, leash=FULL)
    assert hunt.run_mode(run, 37, pressed) == Mode(True, TERROR)  # KP_1 by hand: the terror zone's full clear
    tz = Pursuit('pickup', 10.0, advance=False, leash=FULL, looped=True, agenda=True)
    assert hunt.run_mode(run, 37, tz) == Mode(True, AGENDA, agenda=True)
    assert badge(hunt.mode) == 'TZ LOOP'


def test_a_valuable_with_no_room_on_a_terror_zone_kind_pushes_the_room_package_after_the_cube():
    from inventory_tracking.macros.agenda import PORTAL_TO_TOWN
    from tests.inventory_tracking.macros.test_runner import make

    runner = make(lambda cancelled, routine: None, [])
    loop = runner.loop
    loop.on, loop.kind, loop.seen, loop.carrying = True, TZ, (GAME, 0.0), True
    runner.area_seen = 36
    runner.valuable_left = lambda: 'Ist Rune'
    stop = Abort('inventory full: Ist Rune here — make room', cause='room')
    runner._loop_stopped(stop)
    assert (loop.make_room, loop.agenda.stack) == (True, [])  # the cube first
    runner._loop_stopped(stop)
    assert loop.on
    assert loop.agenda.stack[-1].kind == PORTAL_TO_TOWN  # the package: Town Portal first
    assert (loop.trip, loop.trips) == (GAME, 1)
    assert not loop.drop_room
    runner.close()


def test_a_super_chest_in_sight_is_opened_on_the_way_after_the_leaders_and_never_again(caplog):
    # 2026-10-19, the player: "also in marsh (and I think in other places) - we don't open intermediate goals, like
    # superchests. probably we should add superchests to intemediate goals and open them along the way"
    from inventory_tracking.levels.model import SUPER_CHEST, Ground
    from inventory_tracking.macros.game.records import Thing
    from inventory_tracking.macros.goals import PLACE_NEAR, USE_NEAR, Goal
    from inventory_tracking.macros.hunting.base import SUPER_TRIES
    from inventory_tracking.macros.teleport import marked_thing
    from inventory_tracking.macros.travel import PRESSED
    from inventory_tracking.routes.model import ENTER, FIGHT, USE
    from tests.inventory_tracking.macros.test_hunt import CHAMPION, foe

    play, hunt, run = agenda_hunt(ON_THE_WAY)
    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Andariel')
    play.thing = Thing(70, SUPER_CHEST, 0, 5040.0, 5000.0, True)
    champion = foe(31, 5080.0, 5000.0, flags=CHAMPION)
    first = hunt.cleared(run, play.world, [champion], Ground(()), door)
    assert first is not None
    assert (first.do, first.unit) == (FIGHT, 31)  # the leader in sight first: the metric
    with caplog.at_level('INFO'):
        chest = hunt.cleared(run, play.world, [], Ground(()), door)
    assert chest is not None
    assert (chest.do, chest.unit, chest.near, chest.route) == (USE, 70, USE_NEAR, 'Andariel')
    assert chest.mark is not None
    assert chest.mark.use == SUPER_CHEST
    assert marked_thing(run, chest.mark) == play.thing  # what `operate` opens (the full clear's chest routine)
    assert 'Macro: agenda: target Super chest (open, tier 5' in caplog.text
    # A level with no route (Great Marsh): the chest is the run's own work, no `run_level` end ("no route stage")
    marsh = hunt.cleared(run, play.world, [], Ground(()), None)
    assert marsh is not None
    assert (marsh.do, marsh.clearing, marsh.route) == (USE, True, '')
    # Opened: the route's door again, and never the chest again in this game
    play.thing = replace(play.thing, mode=2, selectable=False)
    assert hunt.cleared(run, play.world, [], Ground(()), door) == door
    play.thing = replace(play.thing, mode=0, selectable=True)
    assert hunt.cleared(run, play.world, [], Ground(()), door) == door
    # One tried out (SUPER_TRIES opens that did not take) is left too
    play.thing = Thing(71, SUPER_CHEST, 0, 5030.0, 5000.0, True)
    hunt.shack_tries[71] = SUPER_TRIES
    assert hunt.cleared(run, play.world, [], Ground(()), door) == door


def test_a_super_chest_far_off_is_no_detour_for_the_agenda_run():
    from inventory_tracking.levels.model import SUPER_CHEST, Ground
    from inventory_tracking.macros.agenda import CHEST_NEAR
    from inventory_tracking.macros.game.records import Thing
    from inventory_tracking.macros.goals import PLACE_NEAR, Goal
    from inventory_tracking.macros.travel import PRESSED
    from inventory_tracking.routes.model import ENTER

    play, hunt, run = agenda_hunt(ON_THE_WAY)
    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Andariel')
    play.thing = Thing(70, SUPER_CHEST, 0, 5000.0 + CHEST_NEAR + 5.0, 5000.0, True)
    assert hunt.cleared(run, play.world, [], Ground(()), door) == door


def test_a_level_whose_route_goal_has_no_way_is_explored_instead_of_stood_on(monkeypatch):
    # 09:46:02-43 on 2026-10-19, Frozen River: no way over the rooms known to Frozenstein's mark, 40 s idle and the game
    # left; the player: "we stuck and exit without visiting next location and probably without full exploration"
    play, hunt, run = agenda_hunt(ON_THE_WAY)
    monkeypatch.setattr(hunt, 'next_room', lambda *_args: ((5100.0, 5000.0), 'an unexplored room 3', 0))
    target = hunt.agenda_target(run, play.world, [], (5000.0, 5000.0), frozenset(), (), None)
    assert target is None  # on the way: the route's own goal
    hunt.wayless.add((play.world.game_name, 35))
    target = hunt.agenda_target(run, play.world, [], (5000.0, 5000.0), frozenset(), (), None)
    assert target is not None
    assert target.label == 'an unexplored room 3'
