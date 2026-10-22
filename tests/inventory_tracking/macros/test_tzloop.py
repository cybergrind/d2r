"""The terror zone kinds of the KP_6 loop (macros/tzloop.py) over the scripted game: each leg is the agenda's goal,
made through `Loop.leg`. The routines a leg calls (the waypoint, Town Portal, back through it, the prebuff) have their
own tests; here they are recorded and move the character, so the order of the goals is what is checked. Offline: no
proof of the game's own behaviour (macros/goals-plan.md §9)."""

import time
from dataclasses import replace

import pytest

from inventory_tracking.macros import loop as loop_module, tzloop, tzroutine
from inventory_tracking.macros.actuator import Abort, Cause
from inventory_tracking.macros.agenda import (
    KILL,
    LEAVE_GAME,
    ON_THE_WAY,
    Leader,
    LevelView,
    Objective,
    game_end,
    town_of,
)
from inventory_tracking.macros.loop import (
    LEAVE,
    TOWN,
    TZ,
    TZ_BACK,
    TZ_CLEAR,
    TZ_LEVEL,
    TZ_LOOT,
    TZ_NEXT_LEVEL,
    TZ_OUT,
    TZ_PICKUP,
    TZ_PORTAL,
    TZ_SHARD,
    TZ_WAYPOINT,
    LegHands,
    Loop,
    loop_kinds,
)
from inventory_tracking.macros.route import PERFORMED
from inventory_tracking.macros.teleport import Untook
from inventory_tracking.macros.town import Exit
from inventory_tracking.macros.tzroutine import Itinerary
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.tracker import ZoneTracker
from tests.inventory_tracking.macros.fakes import KEYS, Game, player, world


GAME = 'cyber32'
CATACOMBS = frozenset((32, 33, 34, 35, 36, 37))
ROGUE_ENCAMPMENT, FORTRESS = 1, 103


def keys(_world, skills=None):
    return {skill: {**KEYS, 220: 'x'}[skill] for skill in skills or ()}


def at(area: int):
    return world(area, player=player(area))


class Book(ZoneTracker):
    """The terror tracker as the game's boss book (macros/bossledger.py: its file-backed records, none kept here), its
    kills the game's (`Script.killed`)."""

    def __init__(self, killed: set[str]) -> None:
        super().__init__()
        self.game_killed = killed

    def killed(self) -> frozenset[str]:
        return frozenset(self.game_killed)


class Script:
    """A terror zone game: the fakes' game read, the leg routines recorded and moving the character."""

    def __init__(self, area: int, monkeypatch: pytest.MonkeyPatch, zone: frozenset[int] = CATACOMBS):
        self.play = Game(at(area))
        self.killed: set[str] = set()
        self.book = Book(self.killed)
        self.progress = Progress(ROUTES, PERFORMED, self.book.killed, wanted=lambda a: a in zone)
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
        # Zone navigation (macros/zonenav.py): the levels whose map a run never reads, the doors no click takes
        self.unmapped: set[int] = set()
        self.stuck: set[int] = set()
        # The levels whose way in is an object no click takes yet (teleport.py `Untook`: the Throne's portal before
        # Baal left): the ways made before it takes, None never
        self.untook: dict[int, int | None] = {}
        self.untook_why = 'no click took {}'  # its words, the mark's label put in
        # The levels whose next run ends at a child's door before its rooms ("Enter when passing"): left unexplored
        self.cut_short: set[int] = set()
        # The levels whose next run ends at its route's door and stands there, a warp's press the leg's (live: "at
        # Forgotten Reliquary: going through takes a press", 14:10:58 on 2026-10-21): mapped, not explored, no move
        self.at_door: set[int] = set()
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
        area = self.area
        self.runs.append(area)
        self.on_run(area)
        if area in self.at_door:
            self.at_door.discard(area)
            self.loop.agenda.mapped.add(area)
        elif area in self.cut_short:
            # The run took its route's way on (a door beside it) before its rooms: over in the next level
            self.cut_short.discard(area)
            self.loop.agenda.mapped.add(area)
            step = self.progress.step(area)
            assert step is not None
            assert step.stage.to
            self.go('door', step.stage.to)
        elif area not in self.unmapped:
            # runner.py `_zone_seen`: the run's tour found no room left, the level's map read
            self.loop.agenda.mapped.add(area)
            self.loop.agenda.explored.add(area)
        self.loop.agenda.ran(area)

    def take_one(self) -> bool:
        return self.picks.pop(0) if self.picks else False

    def door(self) -> None:
        step = self.progress.step(self.area)
        assert step is not None
        assert step.stage.to
        if step.stage.to in self.stuck:
            raise Abort(f'no click took {step.stage.mark}', cause='door')
        if step.stage.to in self.untook:
            left = self.untook[step.stage.to]
            if left is None or left > 0:
                self.untook[step.stage.to] = None if left is None else left - 1
                self.calls.append(('untook', step.stage.to))
                raise Untook(self.untook_why.format(step.stage.mark))
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
            walk_out=lambda to: self.go('walk out', to),
            inventory_key=lambda: 'i',
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
    legs = [game.leg() for _ in range(24) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [
        TZ_WAYPOINT,
        *[TZ_LEVEL, TZ_NEXT_LEVEL] * 2,  # Catacombs 2-3 (from the Catacombs 2 waypoint): each run, then the way on
        TZ_LEVEL,  # Level 4: the unique, then her fight (the route's goal)
        TZ_LOOT,
        # Then the levels before her from the Inner Cloister's waypoint (tzroutine.py SKIPPED_TRIPS, 2026-10-22: Bone
        # Ash in the Cathedral)
        TZ_PORTAL,
        TZ_WAYPOINT,
        *[TZ_LEVEL, TZ_NEXT_LEVEL] * 2,
        TZ_LEVEL,
        LEAVE,  # no goals left: Save and Exit, the next game
    ]
    assert game.runs == [35, 36, 37, 32, 33, 34]
    assert [kind for area, kind in targets if area == 35] == [KILL, None]  # the champion, then the way on
    assert [kind for area, kind in targets if area == 37] == [KILL, None]  # the unique, then Andariel
    assert all(kind is None for area, kind in targets if area not in (35, 37))
    assert ('waypoint', 35) in game.calls
    assert ('prebuff',) not in game.calls
    assert 'Save and Exit' in game.play.said
    assert game.loop.games == 1


KURAST_DOCKS, TRAVINCAL = 75, 83


def test_an_act_3_terror_zone_game_ends_in_the_fortress_by_lower_kurasts_way(monkeypatch):
    # The player, 2026-10-19: "if we're doing save/exit in any act3 zone in loop, we must use the same routins as LK
    # (teleport home -> pandemonium fortress -> save/exit)": the next game starts by the Fortress's waypoint
    game = Script(KURAST_DOCKS, monkeypatch, zone=frozenset((TRAVINCAL,)))
    game.on_run = lambda area: game.killed.add('Ismail Vilehand')
    legs = [game.leg() for _ in range(8) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [TZ_WAYPOINT, TZ_LEVEL, TZ_LOOT, TZ_PORTAL, TZ_WAYPOINT, LEAVE]
    assert [call for call in game.calls if call[0] != 'prebuff'] == [
        ('waypoint', TRAVINCAL),
        ('portal', KURAST_DOCKS),  # Town Portal home, as Lower Kurast's `PORTAL` leg
        ('waypoint', FORTRESS),  # its `TO_THE_FORTRESS`
    ]
    assert game.loop.done == GAME
    assert game.loop.games == 1
    assert game.play.said.count('Save and Exit') == 1


def test_a_visit_due_at_an_act_3_games_end_is_made_in_the_fortress_and_ends_with_save_and_exit(monkeypatch):
    game = Script(KURAST_DOCKS, monkeypatch, zone=frozenset((TRAVINCAL,)))
    game.on_run = lambda area: game.killed.add('Ismail Vilehand')
    exits: list[Exit] = []
    assert [game.leg() for _ in range(4)] == [TZ_WAYPOINT, TZ_LEVEL, TZ_LOOT, TZ_PORTAL]
    game.loop.visiting = GAME  # a visit cut short: due again (`Loop.visit_due`)
    legs = [game.leg(visit=exits.append) for _ in range(3)]

    assert legs == [TZ_WAYPOINT, TOWN, LEAVE]
    assert exits == [Exit.LEAVE]  # no walk to the waypoint before Save and Exit (loop.py `exit_of`)
    assert game.loop.games == 1


def test_an_act_3_games_end_never_takes_the_portal_with_a_valuable_on_the_ground(monkeypatch):
    game = Script(TRAVINCAL, monkeypatch, zone=frozenset((TRAVINCAL,)))
    game.sightings[80] = 'Ber Rune at (1, 2)'  # on another level: no pickup goal here
    goal = game_end(TRAVINCAL)
    with pytest.raises(Abort, match='Ber Rune') as stop:
        tzloop.perform(game.loop, game.play.run(), keys, game.progress, goal, game.hands())
    assert stop.value.cause == 'room'
    assert game.calls == []


DURANCE, RIVER = frozenset((100, 101, 102)), frozenset((106, 107))


def walked_hands(game: Script) -> LegHands:
    """The leg hands with the runner's way on (running/legs.py `_way_on`): at a door's stage through it, else the
    level run to it."""
    from inventory_tracking.routes.model import ENTER

    def way_on() -> None:
        step = game.progress.step(game.area)
        if step is not None and step.stage.kind == ENTER and step.stage.to:
            game.door()
        else:
            game.level_run()

    return replace(game.hands(), way_on=way_on)


def test_a_durance_game_crosses_travincal_and_ends_by_the_red_portal_in_the_fortress(monkeypatch):
    # rca/2026-10-19/tz-coverage-findings.md F3: "next level" on Travincal with the Council's loot left, 30 times, then
    # an Abort; F4: the Red portal to the Fortress with Durance 3 unfinished, and the trip made again. The player,
    # 2026-10-19 ~21:56: "it should run within terror zones": Travincal is crossed, the Council not fought
    from inventory_tracking.routes.model import USE

    game = Script(KURAST_DOCKS, monkeypatch, zone=DURANCE)

    def run_of(area: int) -> None:
        step = game.progress.step(area)
        if area == 102 and step is not None and step.stage.kind == USE:
            game.go('red portal', step.stage.to)  # the route's way out: the run uses the portal
        elif area == 102:
            game.progress.stood(102, 'Red portal')
            game.killed.add('Mephisto')

    game.on_run = run_of
    hands = walked_hands(game)
    legs = [game.loop.leg(game.play.run(), keys, game.progress, hands) for _ in range(14) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [
        TZ_WAYPOINT,
        *[TZ_NEXT_LEVEL, TZ_LEVEL] * 3,  # Travincal crossed by its door (no Council), then Durance 1-3, each its run
        TZ_LOOT,  # Mephisto's
        TZ_LEVEL,  # the Red portal: the excursion's end, no Town Portal
        LEAVE,  # in the Fortress: no excursion left, Save and Exit there
    ]
    assert [call for call in game.calls if call[0] != 'prebuff'] == [
        ('waypoint', TRAVINCAL),
        ('door', 100),
        ('door', 101),
        ('door', 102),
        ('red portal', FORTRESS),
    ]
    assert game.runs == [100, 101, 102, 102]  # no run on Travincal: no Council, no loot of a level not terrorized
    assert game.loop.games == 1
    assert game.play.said.count('Save and Exit') == 1


def test_mephisto_dead_and_looted_the_game_ends_through_the_red_portal_with_save_and_exit_in_the_fortress(monkeypatch):
    # The player, 2026-10-19 ~22:11: "when we have killed mephisto -- we must go through red portal and do save/exit
    # only when we're in fortress" (game 32 was left in Durance 3)
    from inventory_tracking.routes.model import USE

    game = Script(102, monkeypatch, zone=DURANCE)
    game.killed.add('Mephisto')
    game.progress.stood(102, 'Red portal')
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    game.loop.agenda.ran(102)  # its fight's run
    game.picks = [True]  # a drop of his first

    def run_of(area: int) -> None:
        step = game.progress.step(area)
        if step is not None and step.stage.kind == USE:
            game.go('red portal', step.stage.to)

    game.on_run = run_of
    legs = [game.leg() for _ in range(6) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [TZ_LOOT, TZ_LOOT, TZ_LEVEL, LEAVE]  # the loot first, then the Red portal, then Save and Exit
    assert [call for call in game.calls if call[0] != 'prebuff'] == [('red portal', FORTRESS)]  # left from there
    assert game.play.said.count('Save and Exit') == 1


def test_a_red_portal_not_taken_is_followed_by_the_town_portal_home_and_the_fortress(monkeypatch):
    game = Script(102, monkeypatch, zone=DURANCE)
    game.killed.add('Mephisto')
    game.progress.stood(102, 'Red portal')
    game.progress.looted(102)
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    game.loop.agenda.ran(102)
    legs = [game.leg() for _ in range(6) if game.play.world.in_game]  # the run never takes the portal
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [TZ_LEVEL, TZ_PORTAL, TZ_WAYPOINT, LEAVE]
    assert [call for call in game.calls if call[0] != 'prebuff'] == [('portal', KURAST_DOCKS), ('waypoint', FORTRESS)]


def test_the_act_3_games_end_is_the_red_portal_from_durance_3_with_mephisto_dead_else_the_town_portal():
    from inventory_tracking.macros.agenda import LEVEL, PORTAL_TO_TOWN, Agenda

    mephisto = frozenset(('Mephisto',))
    end = game_end(102, mephisto)
    assert (end.kind, end.area, end.to, end.ends) == (LEVEL, 102, FORTRESS, True)
    assert end.label == 'the Red portal to The Pandemonium Fortress: the game ends there'
    assert game_end(102).kind == PORTAL_TO_TOWN  # alive, or not known
    assert game_end(101, mephisto).kind == PORTAL_TO_TOWN  # any other act 3 level
    assert game_end(107, mephisto).kind == LEAVE_GAME  # act 4: Save and Exit where it is
    agenda = Agenda()
    agenda.begin('g')
    assert agenda.next(None, area=102, dead=mephisto) == end
    agenda.failed(end)
    agenda.failed(end)
    agenda.failed(end)  # its leg stopped TRIES times: the Town Portal home
    assert agenda.next(None, area=102, dead=mephisto).kind == PORTAL_TO_TOWN


def test_the_river_of_flames_run_never_walks_into_the_chaos_sanctuary_off_its_excursion(monkeypatch, caplog):
    # F5: the River's script ends by an open passage into the Chaos Sanctuary; the run walked it and explored the
    # non-terror sanctuary, seals and Diablo too. The trip's script is held to the trip: the level's run ends in it
    game = Script(FORTRESS, monkeypatch, zone=RIVER)
    stages: dict[int, str | None] = {}

    def run_of(area: int) -> None:
        step = game.progress.step(area)
        stages[area] = step.stage.text() if step is not None else None

    game.on_run = run_of
    hands = walked_hands(game)
    with caplog.at_level('INFO'):
        legs = [game.loop.leg(game.play.run(), keys, game.progress, hands) for _ in range(8) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [TZ_WAYPOINT, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_LEVEL, LEAVE]
    assert stages == {106: 'enter River of Flame', 107: None}  # no route stage left on the River: no way on
    assert [call for call in game.calls if call[0] != 'prebuff'] == [('waypoint', 106), ('door', 107)]
    assert 'Macro: tz: River of Flame: enter Chaos Sanctum not taken: off the terror zone' in caplog.text
    step = game.progress.step(108)
    assert step is None  # had the run got there all the same: no seal, no Diablo


def test_the_chaos_sanctuary_zones_trip_keeps_the_rivers_way_into_it(monkeypatch):
    from inventory_tracking.macros.tzroutine import itinerary

    plan = itinerary(frozenset((108,)))
    assert plan is not None
    game = Script(107, monkeypatch, zone=frozenset((108,)))
    tzloop.select(game.progress, GAME, 107, plan.excursions[0], plan)
    step = game.progress.step(107)
    assert step is not None
    assert (step.stage.text(), step.stage.to) == ('enter Chaos Sanctum', 108)


def test_a_zone_with_no_excursion_waits_for_the_next_zone_instead_of_making_games(monkeypatch):
    # F1: Moo Moo Farm's only way in is the red portal the player opens with Wirt's Leg: each game was left at once, a
    # game a minute for the hour. The player, 2026-10-19: "we need to make sure that we don't stuck or die". Stopped,
    # the loop stood until someone looked (03:30:20 on 2026-10-20): the next zone is waited for instead
    import time

    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=frozenset((39,)))
    with pytest.raises(Abort, match='the terror zone Act1-MooMooFarm is not playable: no excursion') as stop:
        game.leg()
    assert stop.value.cause == 'zone'
    assert game.loop.cooling > time.monotonic() + tzloop.ZONE_SETTLE - 1
    assert game.calls == []
    assert 'Save and Exit' not in game.play.said
    # In a field level (the zone changed under the game) no goals end the game first
    field = Script(3, monkeypatch, zone=frozenset((39,)))
    assert field.leg() == LEAVE


def test_a_trip_from_the_town_it_stands_in_is_walked_out_of_and_prebuffed_where_its_town_allows(monkeypatch):
    # rca/2026-10-19/town-exit-findings.md. The Rogue Encampment: the prebuff at the field's edge (its start NPCs fail
    # it in town); the Fortress: in town, before the walk
    moor = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=frozenset((2, 8)))
    moor.loop.prebuffed = None
    assert moor.leg() == TZ_OUT
    assert moor.calls == [('walk out', 2), ('prebuff',)]
    assert moor.leg() == TZ_LEVEL  # Blood Moor's run, as any trip's first level
    assert moor.runs == [2]
    steppes = Script(FORTRESS, monkeypatch, zone=frozenset((104, 105)))
    steppes.loop.prebuffed = None
    assert steppes.leg() == TZ_OUT
    assert steppes.calls == [('prebuff',), ('walk out', 104)]
    # From another act's town the town's waypoint first, then the walk
    waste = Script(FORTRESS, monkeypatch, zone=frozenset((41, 55, 59)))
    assert waste.leg() == TZ_WAYPOINT
    assert waste.leg() == TZ_OUT
    assert waste.calls == [('waypoint', 40), ('walk out', 41)]


def test_an_idle_stop_ends_the_loop_with_its_cause_on_the_hud():
    from tests.inventory_tracking.macros.test_runner import make

    shown: list = []
    runner = make(lambda cancelled, routine: None, shown)
    runner.loop.on, runner.loop.kind = True, TZ
    runner._loop_stopped(Abort('the terror zone Act1-BloodMoor is not playable: no excursion (...)', cause='idle'))
    assert not runner.loop.on
    assert any('Loop stopped: the terror zone Act1-BloodMoor is not playable' in line for lines in shown
               for line in (lines if isinstance(lines, list) else [lines]))  # fmt: skip
    runner.close()


def test_games_in_a_row_with_no_level_run_stop_the_loop_and_a_level_run_counts_afresh(monkeypatch):
    # A greyed waypoint row (waypoint.py: "not got yet?") left every game with no level run, the recovery making the
    # next: IDLE_GAMES of them, then the loop stops
    game = Script(ROGUE_ENCAMPMENT, monkeypatch)

    def greyed(run, to, marks=None):
        raise Abort('its row greyed: not got yet?')

    monkeypatch.setattr(tzloop, 'travel', greyed)
    for number in range(tzloop.IDLE_GAMES):
        game.play.world = replace(at(ROGUE_ENCAMPMENT), game_name=f'cyber{number}')
        with pytest.raises(Abort, match='greyed'):
            game.leg()
    game.play.world = replace(at(ROGUE_ENCAMPMENT), game_name='cyber9')
    with pytest.raises(Abort, match=f'{tzloop.IDLE_GAMES} games in a row with no level run') as stop:
        game.leg()
    assert stop.value.cause == 'idle'
    worked = Script(35, monkeypatch)
    worked.loop.idle = tzloop.IDLE_GAMES - 1  # its game is the IDLE_GAMES-th: played
    assert worked.leg() == TZ_LEVEL
    assert worked.loop.idle == 0
    # A game whose level run carried on across a way out (River of Flame into the Chaos Sanctuary, no LEVEL leg) is
    # played too (08:38:04 on 2026-10-20: two Diablo games then a stop)
    crossed = Script(ROGUE_ENCAMPMENT, monkeypatch)
    crossed.loop.idle = tzloop.IDLE_GAMES
    crossed.loop.agenda.begin('cyber1')
    crossed.loop.agenda.ran(108)
    crossed.play.world = replace(at(ROGUE_ENCAMPMENT), game_name='cyber2')
    crossed.leg()  # no idle stop
    assert crossed.loop.idle == 1


def test_a_recovery_in_act_3_leaves_the_game_where_it_stands(monkeypatch):
    game = Script(TRAVINCAL, monkeypatch, zone=frozenset((TRAVINCAL,)))
    game.loop.abandon = True
    assert game.leg() == LEAVE
    assert game.calls == []  # no portal, no waypoint: the quickest way out
    assert 'Save and Exit' in game.play.said


def test_the_lower_kurast_kinds_game_still_ends_in_the_fortress_by_its_own_legs(monkeypatch):
    from inventory_tracking.macros.loop import LK, TO_THE_FORTRESS, next_leg

    loop = Loop(on=True, kind=LK, chosen=True)
    assert next_leg(at(KURAST_DOCKS), None, loop) == TO_THE_FORTRESS


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
    # The route over, nothing seen: the level left, by the Town Portal for the levels before her (SKIPPED_TRIPS)
    assert game.leg() == TZ_PORTAL


def test_the_leave_leg_itself_refuses_a_game_with_a_valuable_on_another_level(monkeypatch):
    game = Script(37, monkeypatch)
    game.sightings[36] = 'Ber Rune at (1, 2)'
    goal = Objective(LEAVE_GAME, 'no goals left', 60)
    with pytest.raises(Abort, match='Ber Rune') as stop:
        tzloop.perform(game.loop, game.play.run(), keys, game.progress, goal, game.hands())
    assert stop.value.cause == 'room'  # the room rules, then the stop for the player (runner.py `_loop_stopped`)
    assert 'Save and Exit' not in game.play.said


def test_a_valuable_left_on_the_level_before_an_open_passage_is_fetched_there_then_the_game_ends(monkeypatch):
    # 00:05:52 on 2026-10-20: Izual dead, the Plains of Despair looted, a Grand Charm left in the Outer Steppes; the
    # pickup leg's trip back crosses the open passage (running/valuables.py `cross`), here the scripted hand's move
    game = Script(105, monkeypatch, zone=frozenset((104, 105)))
    game.killed.add('Izual')
    game.progress.looted(105)
    game.sightings[104] = 'Grand Charm at (5477, 5092)'

    def take_one() -> bool:
        if 104 not in game.sightings:
            return False
        if game.area == 105:
            game.go('across', 104)  # the trip back: through the passage, within a click of the charm
        else:
            del game.sightings[104]  # picked up from there
        return True

    game.take_one = take_one
    game.door = lambda: game.go('door', 105)  # the Steppes' way on: the passage again
    legs = [game.leg() for _ in range(8) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]
    # The Plains' run (its first in this agenda), the pickup before leaving (across), the charm still on the ground in
    # the Steppes, their run, the way on back into the Plains, the agenda's own end with nothing left
    assert legs == [TZ_LEVEL, TZ_PICKUP, TZ_PICKUP, TZ_LEVEL, TZ_NEXT_LEVEL, LEAVE]
    assert game.calls == [('across', 104), ('door', 105)]
    assert 'Save and Exit' in game.play.said
    assert not game.sightings


def test_a_game_with_no_zone_read_is_a_stop_and_a_dead_character_stops_the_loop(monkeypatch):
    from inventory_tracking.macros.loop import Dead

    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=frozenset())
    with pytest.raises(Abort, match='no terror zone is read'):
        game.leg()
    # The zone turned under a game with a valuable on the ground (Set Occult Codex by Andariel, 08:30:01 on
    # 2026-10-20): picked up first, no stop
    turned = Script(37, monkeypatch, zone=frozenset())
    turned.sightings[37] = 'Set Occult Codex at (22548, 9559)'

    def take_one() -> bool:
        turned.sightings.clear()
        return True

    turned.take_one = take_one
    assert turned.leg() == TZ_PICKUP
    with pytest.raises(Abort, match='no terror zone is read'):
        turned.leg()  # then the game is left
    dead = Script(35, monkeypatch)
    dead.play.world = replace(at(35), player=player(35, mode=0))
    with pytest.raises(Dead):
        dead.leg()


def test_the_terror_zone_kinds_are_offered_only_once_promoted(monkeypatch):
    from inventory_tracking.macros import actloop

    monkeypatch.setattr(actloop, 'ENABLED', False)
    monkeypatch.setattr(tzloop, 'ENABLED', False)
    assert set(loop_kinds()) == {'lk', 'andariel'}
    monkeypatch.setattr(tzloop, 'ENABLED', True)
    assert set(loop_kinds()) == {'lk', 'andariel', 'tz', 'tzclear'}
    assert (TZ.metric, TZ_CLEAR.name) == ('experience and elite kills an hour', 'Full clear TZ')
    assert TZ.game_seconds is not None
    assert TZ.game_seconds > 240.0


def test_a_runner_restarted_with_a_terror_zone_kind_keeps_its_own_while_it_is_off(monkeypatch):
    from tests.inventory_tracking.macros.test_runner import make

    monkeypatch.setattr(tzloop, 'ENABLED', False)
    made = make(lambda cancelled, routine: None, [])
    made.resume({'loop': False, 'loop_kind': 'tz'})
    assert made.loop.kind.key == 'andariel'  # the service's own first kind
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
    from inventory_tracking.game.records import Thing
    from inventory_tracking.levels.model import SUPER_CHEST, Ground
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


def test_a_super_chest_far_off_is_opened_before_the_level_is_left_and_no_detour_with_the_level_spots_off(monkeypatch):
    # The player, 2026-10-20: "we always should try to open such chests whenever we encountered them"
    # (macros/superchests.py LEVEL_SPOTS); before, one past CHEST_NEAR was no detour the metric paid for
    from inventory_tracking.game.records import Thing
    from inventory_tracking.levels.model import SUPER_CHEST, Ground
    from inventory_tracking.macros import superchests
    from inventory_tracking.macros.agenda import CHEST_NEAR
    from inventory_tracking.macros.goals import PLACE_NEAR, Goal
    from inventory_tracking.macros.travel import PRESSED
    from inventory_tracking.routes.model import ENTER, USE

    monkeypatch.setattr(superchests, 'BOOK', superchests.Book())
    play, hunt, run = agenda_hunt(ON_THE_WAY)
    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Andariel')
    play.thing = Thing(70, SUPER_CHEST, 0, 5000.0 + CHEST_NEAR + 5.0, 5000.0, True)
    goal = hunt.cleared(run, play.world, [], Ground(()), door)
    assert goal is not None
    assert (goal.do, goal.unit) == (USE, 70)
    monkeypatch.setattr(superchests, 'LEVEL_SPOTS', False)
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


LEAVING = Objective(LEAVE_GAME, 'no goals left', 60)


def landing_drop(game: Script, after: float):
    """A pickup that finds the boss's drop only once it has landed, `after` s on the game's clock: (take_one, takes),
    each take noted with what was said by then."""
    start = game.play.clock.now
    takes: list[list[str]] = []

    def take_one() -> bool:
        if game.play.clock.now - start >= after and not takes:
            takes.append(list(game.play.said))
            return True
        return False

    return take_one, takes


def test_a_boss_killed_just_before_the_games_end_has_its_drop_picked_up_before_save_and_exit(monkeypatch):
    # Game 30, 21:55:05.9-06.7 (rca/2026-10-19/game30-run-findings.md S1): Diablo killed, the game left 0.8 s later
    # with his drop still landing and the remembered sightings empty. The drop shows in the ground's next read
    game = Script(37, monkeypatch)
    monkeypatch.setattr(loop_module, 'KILLED_AT', {'Andariel': time.monotonic() - 0.8})
    take_one, takes = landing_drop(game, 1.0)  # lands 1.8 s after the kill
    hands = replace(game.hands(), take_one=take_one, left=lambda: None)

    tzloop.perform(game.loop, game.play.run(), keys, game.progress, LEAVING, hands)

    assert len(takes) == 1
    assert 'Save and Exit' not in takes[0]  # picked up first
    assert 'Save and Exit' in game.play.said
    assert game.play.clock.now >= 1.0  # the drops' landing waited for (DROPS_AFTER_KILL from the kill)


def test_the_games_end_reads_the_ground_fresh_and_keeps_the_game_for_a_drop_the_sightings_missed(monkeypatch):
    game = Script(37, monkeypatch)
    monkeypatch.setattr(loop_module, 'KILLED_AT', {})
    hands = replace(game.hands(), left=lambda: 'Ber Rune at (5003, 5001)')  # no room, say: the pickup took nothing
    with pytest.raises(Abort, match='Ber Rune') as stop:
        tzloop.perform(game.loop, game.play.run(), keys, game.progress, LEAVING, hands)
    assert stop.value.cause == 'room'
    assert 'Save and Exit' not in game.play.said
    # Unread, the game's sightings decide (as before the fresh read)
    hands = replace(game.hands(), left=lambda: loop_module.UNREAD)
    tzloop.perform(game.loop, game.play.run(), keys, game.progress, LEAVING, hands)
    assert 'Save and Exit' in game.play.said


def test_the_games_end_by_its_portal_waits_for_a_bosss_drops_and_picks_them_up_first(monkeypatch):
    game = Script(KURAST_DOCKS, monkeypatch, zone=frozenset((TRAVINCAL,)))
    game.play.world = at(TRAVINCAL)
    monkeypatch.setattr(loop_module, 'KILLED_AT', {'Ismail Vilehand': time.monotonic() - 0.5})
    take_one, takes = landing_drop(game, 1.2)
    hands = replace(game.hands(), take_one=take_one, left=lambda: None)
    portal = Objective(tzloop.PORTAL_TO_TOWN, 'home', 60, ends=True)

    tzloop.perform(game.loop, game.play.run(), keys, game.progress, portal, hands)

    assert len(takes) == 1
    assert game.calls[-1] == ('portal', KURAST_DOCKS)  # then Town Portal home


def test_a_kill_the_service_missed_waits_drops_land_from_the_first_leg_that_read_it(monkeypatch):
    # A route's super unique KILLED_AT does not track: DROPS_LAND from the first leg's reading of the boss dead
    monkeypatch.setattr(loop_module, 'KILLED_AT', {})
    loop = Loop()
    loop.note_slain(GAME, frozenset({'Coldcrow'}), 10.0)
    loop.note_slain(GAME, frozenset({'Coldcrow'}), 10.5)  # the first reading kept
    assert loop.landing(10.5) == pytest.approx(loop_module.DROPS_LAND - 0.5)
    assert loop.landing(10.0 + loop_module.DROPS_LAND) == 0.0
    loop.note_slain('another game', frozenset(), 11.0)
    assert loop.landing(11.0) == 0.0  # a new game forgets the last one's
    # A kill the service saw goes by its own clock, not the leg's
    monkeypatch.setattr(loop_module, 'KILLED_AT', {'Coldcrow': time.monotonic() - 1.0})
    loop.note_slain('another game', frozenset({'Coldcrow'}), 12.0)
    assert loop.landing(12.0) == pytest.approx(loop_module.DROPS_AFTER_KILL - 1.0, abs=0.05)


def test_a_dead_character_presses_nothing_at_the_games_end(monkeypatch):
    from inventory_tracking.macros.loop import Dead

    game = Script(37, monkeypatch)
    game.play.world = replace(at(37), player=player(37, mode=0))
    picks: list[bool] = []
    hands = replace(game.hands(), take_one=lambda: picks.append(True) or True, left=lambda: None)
    with pytest.raises(Dead):
        tzloop.perform(game.loop, game.play.run(), keys, game.progress, LEAVING, hands)
    assert picks == []
    assert 'Save and Exit' not in game.play.said


SPIDER_FOREST = 76


def held(game: Script):
    assert game.play.pack is not None
    return game.play.pack


def gheeds_game(monkeypatch, area: int = SPIDER_FOREST):
    """A terror zone game in Spider Forest with the player's Gheed's Fortune carried; the stash's park and choice
    recorded (their own tests: test_charms.py, test_loop.py `gheeds_play`)."""
    from inventory_tracking.game.records import Carried, Pack
    from inventory_tracking.macros.charms import GHEEDS_FORTUNE, UNIQUE, Parked, grand_charm

    game = Script(area, monkeypatch, zone=frozenset((SPIDER_FOREST, 84, 85)))  # Act3-SpiderForest
    theirs = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    new = Carried(7, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, identified=False)
    game.play.pack = Pack((theirs,), ('.' * 10,) * 4)
    stash: list[str] = []

    def park(run, ours, item_stats, shown):
        stash.append('park')
        assert game.area == FORTRESS
        game.play.pack = replace(held(game), items=())
        return Parked(ours.unit_id, 2, (ours.txt, ours.x, ours.y), 25)

    def choose(run, parked, rival, item_stats, shown, others=()):
        stash.append(f'choose {rival.unit_id if rival is not None else None}, others {[i.unit_id for i in others]}')
        assert game.area == FORTRESS
        return theirs

    def take_one() -> bool:
        if game.area == SPIDER_FOREST and new not in held(game).items:
            game.play.pack = replace(held(game), items=(*held(game).items, new))
            return True
        return False

    monkeypatch.setattr(loop_module, 'park', park)
    monkeypatch.setattr(loop_module, 'choose', choose)
    monkeypatch.setattr(loop_module, 'to_town', game.to_town)
    game.take_one = take_one
    return game, stash


def test_a_refused_gheeds_on_a_terror_zone_kind_is_the_swap_package_then_the_level_goes_on(monkeypatch, caplog):
    # 23:05:42 on 2026-10-19: a Herald's unique Grand Charm in Spider Forest refused for the player's Gheed's Fortune
    # fell to the room rules (the cube), then stopped the loop by it; Andariel's swap, as the agenda's package
    from inventory_tracking.macros.loop import GHEED_CHOOSE, GHEED_PICK, GHEED_STASH, SWAP_BACK, SWAP_OUT

    game, stash = gheeds_game(monkeypatch)
    forgot: list[bool] = []
    game.loop.forget = lambda: forgot.append(True)
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    assert game.leg() == TZ_LEVEL  # the first look tells the player's items (`own`); the run meets the charm
    tzloop.gheeds_swap(game.loop, GAME, SPIDER_FOREST)
    game.calls.clear()

    def identify(items) -> None:  # Cain: another unique Grand Charm, no Gheed's
        game.play.pack = replace(held(game), items=tuple(
            replace(i, identified=True, unique=360) for i in held(game).items
        ))  # fmt: skip

    caplog.set_level('INFO')
    hands = replace(game.hands(), identify=identify)
    legs = [game.loop.leg(game.play.run(), keys, game.progress, hands) for _ in range(12)]

    assert legs == [
        SWAP_OUT,  # Town Portal to Kurast Docks
        TZ_WAYPOINT,  # the Fortress
        GHEED_STASH,
        TZ_WAYPOINT,  # back to the portal's town
        TZ_BACK,
        GHEED_PICK,  # the new one picked up
        SWAP_BACK,  # Town Portal home again
        TZ_WAYPOINT,
        GHEED_CHOOSE,  # Cain, then the choice
        TZ_WAYPOINT,
        TZ_BACK,
        TZ_NEXT_LEVEL,  # the package done: the agenda's own (its level run made before the refusal: the way on)
    ]
    assert [call for call in game.calls if call[0] != 'prebuff'][:-1] == [  # the last: the way on's door
        ('portal', KURAST_DOCKS),
        ('waypoint', FORTRESS),
        ('waypoint', KURAST_DOCKS),
        ('through', SPIDER_FOREST),
        ('portal', KURAST_DOCKS),
        ('waypoint', FORTRESS),
        ('waypoint', KURAST_DOCKS),
        ('through', SPIDER_FOREST),
    ]
    # Not a Gheed's after identifying: no rival, the player's back, the new charm kept (made way for, charms.py)
    assert stash == ['park', 'choose None, others [7]']
    assert forgot == [True]  # the level run tries the charm again
    assert (game.loop.parked, game.loop.gheed, game.loop.agenda.stack) == (None, None, [])
    assert 'the new unique Grand Charm identified at Cain' in caplog.text
    assert "the new Gheed's Fortune picked up (unit 7" in caplog.text


def test_a_refused_charm_on_a_terror_zone_kind_pushes_the_swap_before_any_room_rule_once():
    from inventory_tracking.macros.agenda import SWAP_AWAY
    from tests.inventory_tracking.macros.test_runner import gheeds_runner, refused_charm

    runner = gheeds_runner()
    loop = runner.loop
    loop.kind, runner.area_seen = TZ, SPIDER_FOREST
    runner._loop_stopped(refused_charm())
    assert loop.on
    assert not loop.make_room
    assert not loop.trip_due
    assert not loop.drop_room
    assert not loop.swap_due
    assert loop.agenda.stack[-1].kind == SWAP_AWAY
    pushed = list(loop.agenda.stack)
    runner._loop_stopped(refused_charm())  # again before its first leg: the package goes on, not pushed twice
    assert runner._carry_one(refused_charm())
    assert loop.agenda.stack == pushed
    assert loop.on
    runner.close()


def test_the_players_gheeds_parked_at_a_games_end_is_fetched_first(monkeypatch):
    # A recovery gives the game up mid-swap: Town Portal home, the Fortress, the choice, then Save and Exit; a new game
    # (or a restart: runner.py `resume`) fetches it from its town first
    from inventory_tracking.macros.charms import Parked
    from inventory_tracking.macros.loop import GHEED_CHOOSE, SWAP_BACK

    game, stash = gheeds_game(monkeypatch)
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    game.leg()
    game.play.pack = replace(held(game), items=())
    game.loop.parked, game.loop.gheed, game.loop.abandon = Parked(1, 2, (620, 0, 0), 25), 'pick', True
    legs = [game.leg() for _ in range(4)]
    assert legs == [SWAP_BACK, TZ_WAYPOINT, GHEED_CHOOSE, LEAVE]
    assert stash == ['choose None, others []']
    assert game.loop.parked is None

    game, stash = gheeds_game(monkeypatch, area=KURAST_DOCKS)
    game.play.pack = replace(held(game), items=())
    game.loop.parked = Parked(1, 2, (620, 0, 0), 25)
    assert [game.leg() for _ in range(2)] == [TZ_WAYPOINT, GHEED_CHOOSE]
    assert game.calls[0] == ('waypoint', FORTRESS)
    assert stash == ['choose None, others []']
    assert game.loop.parked is None
    assert game.leg() == TZ_WAYPOINT  # the agenda's own: to the zone


def test_the_new_charm_refused_again_with_the_players_parked_goes_to_town_for_theirs(monkeypatch, caplog):
    from inventory_tracking.macros.loop import CHOOSE, GHEED_PICK, SWAP_BACK
    from tests.inventory_tracking.macros.test_runner import refused_charm

    game, _ = gheeds_game(monkeypatch)
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    game.leg()
    tzloop.gheeds_swap(game.loop, GAME, SPIDER_FOREST)

    def refused() -> bool:
        raise refused_charm()

    game.take_one = refused
    caplog.set_level('INFO')
    legs = [game.leg() for _ in range(7)]
    assert legs[5:] == [GHEED_PICK, SWAP_BACK]
    assert game.loop.gheed == CHOOSE
    assert "is still not taken with the player's Gheed's Fortune on shared page 2: to town for theirs" in caplog.text


def test_the_next_zone_is_waited_for_to_just_after_the_half_hour():
    turn = 1_760_000_400.0  # a half hour of the wall clock
    assert turn % tzloop.ZONE_TURN == 0
    assert tzloop.zone_wait(turn + 10) == tzloop.ZONE_TURN - 10 + tzloop.ZONE_SETTLE
    assert tzloop.zone_wait(turn + tzloop.ZONE_TURN - 1) == 1 + tzloop.ZONE_SETTLE


def test_an_elite_outside_this_levels_rooms_is_no_agenda_target():
    # 08:43:48 on 2026-10-20: just across into the Chaos Sanctuary, a River of Flame elite still in the client's units
    # was the agenda's kill target; the Teleport toward it took the run back into the River and the Diablo game was
    # lost (rca/2026-10-20/crossing-teleport-back-findings.md F1)
    from inventory_tracking.levels.route import room_at
    from inventory_tracking.native.layout import TILE_UNITS
    from tests.inventory_tracking.macros.test_hunt import CHAMPION, ROOMS, foe

    play, hunt, run = agenda_hunt(ON_THE_WAY)
    me = play.world.player
    assert me is not None
    here = (me.x, me.y)  # in ROOMS[0], whose west edge is 20 units off
    inside = foe(31, me.x + 30.0, me.y, CHAMPION)  # in ROOMS[1]
    across = foe(32, me.x - 30.0, me.y, CHAMPION)  # past ROOMS[0]'s west edge: the level before's
    assert room_at(ROOMS, (inside.x / TILE_UNITS, inside.y / TILE_UNITS)) is not None
    assert room_at(ROOMS, (across.x / TILE_UNITS, across.y / TILE_UNITS)) is None
    assert hunt.agenda_target(run, play.world, [across], here, frozenset(), ROOMS, None) is None
    assert hunt.agenda_target(run, play.world, [across], here, frozenset(), (), None) is None  # no map read: none
    target = hunt.agenda_target(run, play.world, [inside, across], here, frozenset(), ROOMS, None)
    assert target is not None
    assert target.unit == 31


def test_the_players_own_input_is_no_failure_of_the_leg(monkeypatch):
    # 09:54:25-09:54:28 on 2026-10-20: three mouse moves of the player in a second each stopped the town visit, the
    # agenda dropped it (TRIES) and made a Save and Exit under the player's hand
    from inventory_tracking.macros.actuator import Hand
    from inventory_tracking.macros.agenda import TRIES

    game = Script(37, monkeypatch)
    agenda = game.loop.agenda
    agenda.begin('g')

    def moved(*_args, **_kwargs):
        raise Hand('the mouse was moved')

    monkeypatch.setattr(game.loop, 'leave', moved)
    for _ in range(TRIES + 1):
        with pytest.raises(Hand):
            tzloop.perform(game.loop, game.play.run(), keys, game.progress, LEAVING, game.hands())
    assert not agenda.failures[LEAVING.key]
    assert LEAVING.key not in agenda.dropped

    def stopped(*_args, **_kwargs):
        raise Abort('not in the lobby')

    monkeypatch.setattr(game.loop, 'leave', stopped)
    with pytest.raises(Abort):
        tzloop.perform(game.loop, game.play.run(), keys, game.progress, LEAVING, game.hands())
    assert agenda.failures[LEAVING.key] == 1  # any other stop still counts


CANYON, LUT_GHOLEIN = 46, 40
TOMBS = (66, 67, 68, 69, 70, 71, 72)
TAL_RASHAS = frozenset((CANYON, *TOMBS, 73))
NEAREST = (69, 66, 72, 67, 71, 68, 70)  # the order the tour's entrances come nearest in, in this game


def tomb_tour(game: Script, order: tuple[int, ...] = NEAREST, noted: bool = True):
    """The way on of the Canyon's game: from the Canyon the press through the nearest entrance not yet entered, noted
    gone through as macros/route.py `note_toured` does (`noted`); from a tomb its way back to the Canyon.

    Each tomb entered is read without the Orifice (levels/handlers/tal_rasha.py DURIEL, on since 2026-10-21: the
    card goal's `absent` on arrival, the client holding every room of the level from its entry), so its route's
    Orifice `use` is done and its way on is its way back; the lair's own games: tests/.../acts/test_act2_duriel.py."""

    def door() -> None:
        if game.area != CANYON:
            game.go('back', CANYON)
            return
        used = {place for _, _, place in game.progress.facts.used}
        tomb = next(level for level in order if (float(level), 0.0) not in used)
        if noted:
            game.progress.used(CANYON, 'Tomb', (float(tomb), 0.0), ())
        game.go('tomb', tomb)
        game.progress.absent(tomb, 'Orifice')

    return door


def test_a_canyon_game_clears_the_canyon_then_each_tomb_once_by_the_nearest_entrance_and_ends_in_the_last(
    monkeypatch, caplog
):
    # 14:02:17 on 2026-10-20: the Canyon's run over at a tomb's entrance, no goals left, Save and Exit. The player,
    # 2026-10-20 ~14:03: "we need to utilize smaller tombs too - it gives a great ext/hour rate"
    caplog.set_level('INFO')
    # The tour's mechanics: no tomb here holds the Orifice (`tomb_tour`), so Duriel is out of reach and the boss
    # ledger's game end stops the loop for the player (tzloop.py BOSS_STAYS: `test_a_tomb_tour_with_no_orifice_...`)
    monkeypatch.setattr(tzloop, 'BOSS_STAYS', False)
    game = Script(LUT_GHOLEIN, monkeypatch, zone=TAL_RASHAS)
    game.door = tomb_tour(game)
    legs = [game.leg() for _ in range(40) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [
        TZ_WAYPOINT,
        TZ_LEVEL,  # the Canyon first
        TZ_NEXT_LEVEL,  # through the nearest entrance
        *[TZ_LEVEL, TZ_NEXT_LEVEL, TZ_NEXT_LEVEL] * 6,  # a tomb's run, its way back, the next entrance
        TZ_LEVEL,  # the last tomb's run
        LEAVE,  # no way back: Save and Exit from there
    ]
    assert game.runs == [CANYON, *NEAREST]  # each tomb once
    assert [area for what, area in game.calls if what == 'tomb'] == list(NEAREST)
    assert game.loop.agenda.finished == set(TOMBS)
    assert 'Save and Exit' in game.play.said
    said = [record.getMessage() for record in caplog.records]
    assert "Macro: tz: tour: Tal Rasha's Tomb 4 done, back in Canyon of the Magi: 1 of 7 done" in said
    assert any("next level: the Tal Rasha's Tomb 1 run (toured level 2 of 7)" in line for line in said)
    assert not any('entered again' in line for line in said)


def test_a_room_trip_from_a_tomb_comes_back_through_the_portal_and_the_tour_goes_on(monkeypatch):
    # The tour's mechanics: no tomb here holds the Orifice (`tomb_tour`), so Duriel is out of reach and the boss
    # ledger's game end stops the loop for the player (tzloop.py BOSS_STAYS: `test_a_tomb_tour_with_no_orifice_...`)
    monkeypatch.setattr(tzloop, 'BOSS_STAYS', False)
    game = Script(LUT_GHOLEIN, monkeypatch, zone=TAL_RASHAS)
    game.door = tomb_tour(game)
    exits: list[Exit] = []

    def run_of(area: int) -> None:
        if area == NEAREST[1] and not exits:
            tzloop.trip(game.loop, GAME, area)  # no room for a valuable in the second tomb

    game.on_run = run_of
    legs = [game.leg(visit=exits.append) for _ in range(50) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    trip = legs.index(TZ_PORTAL)
    assert legs[trip : trip + 6] == [TZ_PORTAL, TZ_WAYPOINT, TOWN, TZ_WAYPOINT, TZ_BACK, TZ_NEXT_LEVEL]
    assert ('through', NEAREST[1]) in game.calls  # back into that tomb, its way back next
    assert game.runs == [CANYON, *NEAREST]  # no tomb from scratch, none twice
    assert exits == [Exit.PORTAL]


def test_back_by_the_waypoint_mid_tour_the_tombs_entered_are_done_and_the_rest_follow(monkeypatch):
    # A trip to town that comes back by the Canyon's waypoint, not the portal: the tomb half done counts done (no level
    # twice in a game), the tour goes on with those not entered
    # The tour's mechanics: no tomb here holds the Orifice (`tomb_tour`), so Duriel is out of reach and the boss
    # ledger's game end stops the loop for the player (tzloop.py BOSS_STAYS: `test_a_tomb_tour_with_no_orifice_...`)
    monkeypatch.setattr(tzloop, 'BOSS_STAYS', False)
    game = Script(LUT_GHOLEIN, monkeypatch, zone=TAL_RASHAS)
    game.door = tomb_tour(game)
    legs = []
    while game.area != NEAREST[2]:
        legs.append(game.leg())
    game.go('portal', LUT_GHOLEIN)  # out of the third tomb before its run
    legs += [game.leg() for _ in range(30) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert game.runs == [CANYON, *NEAREST[:2], *NEAREST[3:]]
    assert [area for what, area in game.calls if what == 'tomb'] == list(NEAREST)  # each entrance once
    assert legs.count(TZ_WAYPOINT) == 2  # the zone's, then the Canyon's again
    assert game.loop.agenda.finished == set(TOMBS)


def test_a_tomb_entered_again_ends_the_game_and_no_tomb_is_run_twice(monkeypatch, caplog):
    # The entrance not noted gone through (route.py `note_toured`): the tour still leads to it
    caplog.set_level('INFO')
    # The tour's mechanics: no tomb here holds the Orifice (`tomb_tour`), so Duriel is out of reach and the boss
    # ledger's game end stops the loop for the player (tzloop.py BOSS_STAYS: `test_a_tomb_tour_with_no_orifice_...`)
    monkeypatch.setattr(tzloop, 'BOSS_STAYS', False)
    game = Script(LUT_GHOLEIN, monkeypatch, zone=TAL_RASHAS)
    game.door = tomb_tour(game, noted=False)
    legs = [game.leg() for _ in range(20) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    assert legs == [TZ_WAYPOINT, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_NEXT_LEVEL, LEAVE]
    assert game.runs == [CANYON, NEAREST[0]]
    assert any("Tal Rasha's Tomb 4 entered again" in record.getMessage() for record in caplog.records)


def until_stopped(game: Script, legs: list[str], count: int, after=None) -> Abort:
    """The game's legs into `legs` (`after()` after each) until one stops it; the stop."""
    for _ in range(count):
        try:
            legs.append(game.leg())
        except Abort as stop:
            return stop
        if after is not None:
            after()
    raise AssertionError(f'no stop in {count} legs: {legs}')


def test_a_tomb_tour_with_no_orifice_found_stops_the_loop_for_the_player_naming_duriel(monkeypatch):
    # The player, 2026-10-22: "we should always kill act bosses": a Tal Rasha's game never ends with Duriel alive; with
    # no way into his Lair found, the loop stops where it is (cause 'idle': stops.py STOP, no Save and Exit)
    game = Script(LUT_GHOLEIN, monkeypatch, zone=TAL_RASHAS)
    game.door = tomb_tour(game)
    legs: list[str] = []
    stopped = until_stopped(game, legs, 40)
    assert str(stopped) == "no goals left, but Duriel (Duriel's Lair) alive: the loop stops here for the player"
    assert stopped.cause == 'idle'
    assert LEAVE not in legs
    assert 'Save and Exit' not in game.play.said
    assert game.runs == [CANYON, *NEAREST]  # every tomb toured first
    game.killed.add('Duriel')  # once he is dead, the game ends as before
    assert game.leg() == LEAVE


def test_the_canyons_tour_takes_fewer_ways_on_than_the_loops_repeat_guard():
    from inventory_tracking.macros.loop import REPEATS

    # Per tomb: the Canyon's run to its entrance, the press through, its way back; the Catacombs' and the others' 30
    assert REPEATS[TZ_NEXT_LEVEL] >= 30 + 3 * len(TOMBS)


ACT4 = frozenset((104, 105, 106, 107, 108))


def test_tz_with_a_hand_used_shard_plays_the_act_and_the_rotation_instead_of_stopping(monkeypatch):
    # The player, 2026-10-20 ~19:00: "for TZ/TZ+ modes we want to know how to handle whole terrorized act (when we
    # terrorized it manually with stone)". Before: no single zone matched and the loop stopped, "no terror zone is
    # read in this game" (rca/2026-10-20/act-terrorize-findings.md §4)
    game = Script(FORTRESS, monkeypatch, zone=ACT4 | CATACOMBS)
    assert game.leg() == TZ_WAYPOINT
    assert game.calls == [('waypoint', 107)]  # the act's boss first: Diablo's trip from the River of Flame
    plan = game.loop.agenda.plan
    assert isinstance(plan, Itinerary)
    assert plan.zone == 'Act4-Manual + Act1-Catacombs'
    assert game.leg() == TZ_LEVEL
    assert game.runs == [107]


def test_a_terrorized_act_4_game_is_diablo_from_the_river_then_its_rest_the_city_the_steppes_and_the_plains(
    monkeypatch, caplog
):
    # The player, 2026-10-20 ~21:27: "we must go river of flame -> CS -> kill diablo -> do rest of flame river -> city
    # of damned/planes of despair and etc" (game 21, 21:22:11: the City's waypoint first, City and River before him)
    tzroutine.itinerary.cache_clear()  # its plan line is said as it is made: not by another test before it
    game = Script(FORTRESS, monkeypatch, zone=ACT4)
    policies: list[tuple[int, str]] = []

    def run_of(area: int) -> None:
        plan = game.loop.agenda.plan
        assert isinstance(plan, Itinerary)
        from inventory_tracking.macros.tzroutine import policy_of

        policies.append((area, policy_of(area, plan.excursion_of(area, game.loop.agenda.finished))))
        if area == 108:
            # The seals' bosses, then Diablo (the game's boss ledger holds all four: routes/catalog/act4.py)
            game.killed.update(('Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls', 'Diablo'))
            game.progress.looted(108)
        if area == 105:
            game.killed.add('Izual')
            game.progress.looted(105)

    game.on_run = run_of
    hands = walked_hands(game)
    with caplog.at_level('INFO'):
        legs = [
            game.loop.leg(game.play.run(), keys, game.progress, hands) for _ in range(30) if game.play.world.in_game
        ]
    legs = legs[: legs.index(LEAVE) + 1]

    moves = [call for call in game.calls if call[0] != 'prebuff']
    assert moves == [
        ('waypoint', 107),
        ('door', 108),  # straight through the River to the Sanctuary
        ('portal', FORTRESS),  # Diablo dead: home for the next trip
        ('waypoint', 107),  # the River's rest
        ('portal', FORTRESS),
        ('waypoint', 106),  # the City of the Damned
        ('portal', FORTRESS),
        ('walk out', 104),  # the Steppes, then the Plains and Izual
        ('door', 105),
    ]
    assert game.runs.index(107, 1) > game.runs.index(108)  # the River's own run after Diablo's
    assert list(dict.fromkeys(game.runs)) == [107, 108, 106, 104, 105]
    assert policies[0] == (107, ON_THE_WAY)  # crossed to him: the leaders near only
    assert (107, 'tz+') in policies[2:]  # its own run after Diablo: TZ+
    assert legs[-1] == LEAVE
    assert 'Macro: tz: River of Flame was crossed to the boss: its own run now (1 run(s) on the way)' in caplog.text
    assert 'Diablo from 107: [107, 108], [107] crossed to the boss, worked after it' in caplog.text


def test_tz_while_an_act_is_read_group_by_group_plays_what_is_read(monkeypatch):
    game = Script(FORTRESS, monkeypatch, zone=frozenset((104, 105, 106, 107)))
    assert game.leg() == TZ_OUT  # the Steppes (the Izual trip) walked out of the Fortress
    plan = game.loop.agenda.plan
    assert isinstance(plan, Itinerary)
    assert plan.zone == 'Act4_OuterSteppes + Act4-RiverOfFlame'


# -- the shard act kind (macros/actloop.py; the player, 2026-10-20 ~19:25: "yes, let's do act 4 mode")
# -------------------------

DEEP = 677


def act4_game(monkeypatch, area: int = FORTRESS, deep: int = 97, outcome: str = 'used', zone=CATACOMBS) -> Script:
    """An act4 game: the tracker reads `zone` (the rotation; the client's list never names the shard's act here, the
    open check 4), the stash `deep` Deep shards; `outcome` what the shard's clicks make ('used', 'failed', 'stops')."""
    from inventory_tracking.macros import actloop, terrorize
    from inventory_tracking.macros.loop import ACT4

    game = Script(area, monkeypatch, zone=zone)
    game.keys_given = []  # pyrefly: ignore[missing-attribute] the fake's record of the inventory keys
    game.loop.kind = ACT4
    game.play.stash_pages = [('.' * 10,) * 10]
    game.play.stacks = {DEEP: deep}
    monkeypatch.setattr(terrorize, 'CLICKS', True)

    def used(run, key, act, terrorized):
        game.calls.append(('terrorize', act))
        game.keys_given.append(key)  # pyrefly: ignore[missing-attribute]
        if outcome == 'stops':
            raise Abort('no stash in sight')
        if outcome == 'failed':
            return None
        game.play.stacks[DEEP] -= 1
        return terrorize.Used(DEEP, act, deep, deep - 1, gone=True, listed=False)

    monkeypatch.setattr(actloop, 'terrorize', used)
    return game


def test_an_act4_game_uses_the_deep_shard_first_then_diablo_first_whatever_the_list_reads(monkeypatch, caplog):
    game = act4_game(monkeypatch)
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_SHARD
        assert game.calls == [('terrorize', 4)]
        assert game.loop.agenda.acts == (4,)
        assert game.leg() == TZ_WAYPOINT  # the act planned with the rotation, the act and its boss first
    assert game.calls[-1] == ('waypoint', 107)
    plan = game.loop.agenda.plan
    assert isinstance(plan, Itinerary)
    assert plan.zone == 'Act4-Manual + Act1-Catacombs'
    assert 'Macro: act: act 4 terrorized by a Deep Worldstone Shard' in caplog.text
    assert game.leg() == TZ_LEVEL  # the River of Flame's run: no shard again in the game
    assert [call for call in game.calls if call[0] == 'terrorize'] == [('terrorize', 4)]


def test_the_shard_step_gets_the_characters_inventory_key(monkeypatch):
    # 21:42:42 and 21:42:54 on 2026-10-20: "no inventory key read" left the first two act4 games at once (the player:
    # "something is wrong, we have restarted game twice ... with no obvious reasons")
    game = act4_game(monkeypatch)
    assert game.leg() == TZ_SHARD
    assert game.keys_given == ['i']  # pyrefly: ignore[missing-attribute]


def test_an_act4_game_with_no_deep_shard_at_90_plays_tz_plus_on_the_rotation(monkeypatch, caplog):
    game = act4_game(monkeypatch, deep=89)
    with caplog.at_level('INFO'):
        assert game.leg() == TZ_SHARD
        assert game.leg() == TZ_WAYPOINT
    assert game.calls[-1] == ('waypoint', 35)  # the rotation's Catacombs: never a stop
    assert all(call[0] != 'terrorize' for call in game.calls)
    assert 'Macro: act: no shard for act 4 at 90 or more' in caplog.text


def test_a_shard_that_does_not_take_twice_is_given_up_and_the_rotation_played(monkeypatch, caplog):
    from inventory_tracking.macros import actloop

    game = act4_game(monkeypatch, outcome='failed')
    assert game.leg() == TZ_SHARD
    assert game.loop.agenda.shard == actloop.FAILED
    assert game.leg() == TZ_WAYPOINT  # this game: the rotation
    assert game.calls[-1] == ('waypoint', 35)
    # The next game's shard stops its leg (no stash in sight): the second failure in a row
    stopped = act4_game(monkeypatch, outcome='stops')
    stopped.loop.agenda.shard_failures = game.loop.agenda.shard_failures
    with pytest.raises(Abort, match='no stash in sight'):
        stopped.leg()
    assert stopped.loop.agenda.shard_failures == actloop.SHARD_FAILURES
    with caplog.at_level('INFO'):
        stopped.loop.agenda.game = None  # a new game begun (the fake's keeps its name)
        assert stopped.leg() == TZ_WAYPOINT
    assert 'the shard did not take 2 games in a row' in caplog.text


def test_the_shard_waits_for_a_visit_due_and_goes_to_the_fortress_from_another_town(monkeypatch):
    game = act4_game(monkeypatch, area=ROGUE_ENCAMPMENT)
    assert game.leg() == TZ_WAYPOINT
    assert game.calls == [('waypoint', FORTRESS)]
    assert game.leg() == TZ_SHARD
    # The visit due: first (it makes the room the shard needs), then the shard
    due = act4_game(monkeypatch)
    due.loop.visiting = GAME
    exits: list[Exit] = []

    def visit(exit: Exit) -> None:
        exits.append(exit)
        due.loop.visited = GAME

    assert due.leg(visit=visit) == TOWN
    assert due.leg() == TZ_SHARD
    joined = act4_game(monkeypatch, area=107)  # a game joined in a field level (a restart): the zones read
    monkeypatch.setattr(tzloop, 'BOSS_STAYS', False)  # its first leg's end, not the bosses left (BOSS_STAYS)
    joined.leg()
    assert all(call[0] != 'terrorize' for call in joined.calls)


def test_no_shard_for_the_tz_kinds(monkeypatch):
    game = Script(FORTRESS, monkeypatch)
    assert game.leg() == TZ_WAYPOINT
    assert game.loop.agenda.shard is None


def test_the_act4_kind_is_offered_only_once_enabled_and_the_picker_entry_goes_by_itself(monkeypatch):
    from inventory_tracking.macros import actloop
    from inventory_tracking.macros.loop import ACT4, coming_kinds

    assert actloop.ENABLED is True  # on since the player's in-game test, 2026-10-20 ~21:18
    monkeypatch.setattr(actloop, 'ENABLED', False)
    assert 'act4' not in loop_kinds()
    assert 'ACT4' in [coming.word for coming in coming_kinds()]  # the placeholder "Shard: Act 4"
    monkeypatch.setattr(actloop, 'ENABLED', True)
    assert loop_kinds()['act4'] is ACT4
    assert 'ACT4' not in [coming.word for coming in coming_kinds()]
    assert (ACT4.name, ACT4.word, ACT4.game_seconds, ACT4.metric) == (
        'Shard: Act 4',
        'ACT4',
        2700.0,
        'elite and Herald kills an hour',
    )
    assert ACT4.agenda
    assert ACT4.packaged
    assert ACT4.swaps_gheeds
    assert not ACT4.full_clear
    monkeypatch.setattr(tzloop, 'ENABLED', False)
    assert 'act4' not in loop_kinds()


STEPPES = frozenset((104, 105))


@pytest.mark.parametrize('carried', [False, True])
def test_the_izual_trip_works_the_plains_under_tz_plus_and_fights_izual_before_its_loot(monkeypatch, carried):
    # Game 21 (21:33:35-21:38:12 on 2026-10-20): the Steppes' run carried across the open passage into the Plains
    # (21:35:26), worked them 136 s (159 kills), killed Izual (21:37:20) and a Herald, then the loot and the portal. The
    # Plains' own line, "+0 in 5s", was the loot leg's: the run's experience is booked to the level it began in
    from inventory_tracking.macros.agenda import PLUS
    from inventory_tracking.macros.tzroutine import policy_of
    from inventory_tracking.routes.model import FIGHT

    game = Script(FORTRESS, monkeypatch, zone=STEPPES)
    seen: list[tuple[int, str, str | None]] = []

    def run_of(area: int) -> None:
        plan = game.loop.agenda.plan
        assert isinstance(plan, Itinerary)
        if carried and area == 104:
            game.go('passage', 105)  # the run goes on across the way out (pursuit.py `carried`)
            area = 105
        step = game.progress.step(area)
        policy = policy_of(area, plan.excursion_of(area, game.loop.agenda.finished))
        seen.append((area, policy, step.stage.kind if step is not None else None))
        if area == 105:
            game.killed.add('Izual')

    game.on_run = run_of
    hands = walked_hands(game)
    legs = [game.loop.leg(game.play.run(), keys, game.progress, hands) for _ in range(12) if game.play.world.in_game]
    legs = legs[: legs.index(LEAVE) + 1]

    plains = [entry for entry in seen if entry[0] == 105]
    assert plains[0] == (105, PLUS, FIGHT)  # the Plains worked TZ+, Izual still to fight
    assert 'Izual' in game.killed
    assert legs.index(TZ_LOOT) > legs.index(TZ_LEVEL)  # his loot only after the run that fought him
    assert legs[-1] == LEAVE
    if not carried:
        assert legs[:4] == [TZ_OUT, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_LEVEL]
        assert [call for call in game.calls if call[0] != 'prebuff'][:2] == [('walk out', 104), ('door', 105)]


# The Burial Grounds zone (rca/2026-10-21/crypt-door-findings.md §6): two trips from Cold Plains' waypoint, the Crypt
# [3, 17, 18] then the Mausoleum [3, 17, 19]. 08:01-08:07 on 2026-10-21, four games: "no click took Crypt" left each
# game; the Mausoleum's trip was never tried
BURIAL_GROUNDS = frozenset((17, 18, 19))


def door_game(monkeypatch, refused: tuple[int, ...] = (18,), cause: Cause | None = 'door') -> tuple[Script, LegHands]:
    """A Burial Grounds game whose doors into `refused` take no click (teleport.py `walk_into`'s stop, `cause`)."""
    from inventory_tracking.routes.model import ENTER

    game = Script(ROGUE_ENCAMPMENT, monkeypatch, zone=BURIAL_GROUNDS)
    game.on_run = lambda area: game.killed.add('Blood Raven') if area == 17 else None  # the Mausoleum's script's

    def way_on() -> None:
        step = game.progress.step(game.area)
        if step is None or step.stage.kind != ENTER or not step.stage.to:
            game.level_run()
        elif step.stage.to in refused:
            raise Abort(f'no click took {"Crypt" if step.stage.to == 18 else "Mausoleum"}', cause=cause)
        else:
            game.door()

    return game, replace(game.hands(), way_on=way_on)


def door_legs(game: Script, hands: LegHands, count: int = 14, stops: list[str] | None = None) -> list[str]:
    """The game's legs; a stop for the player (cause 'idle': tzloop.py BOSS_STAYS) into `stops` when given."""
    legs = []
    for _ in range(count):
        if not game.play.world.in_game:
            break
        try:
            legs.append(game.loop.leg(game.play.run(), keys, game.progress, hands))
        except Abort as stop:
            if stops is None or stop.cause != 'idle':
                raise
            stops.append(str(stop))
            break
    return legs


BONEBREAKER_LEFT = 'no goals left, but Bonebreaker (Crypt) alive: the loop stops here for the player'


def test_a_door_no_click_takes_skips_its_trip_and_the_zone_goes_on(monkeypatch, caplog):
    game, hands = door_game(monkeypatch)
    stops: list[str] = []
    with caplog.at_level('INFO'):
        legs = door_legs(game, hands, stops=stops)
    assert legs[:6] == [
        TZ_WAYPOINT,
        TZ_NEXT_LEVEL,  # into the Burial Grounds
        TZ_LEVEL,  # its run (Blood Raven killed on the way)
        TZ_NEXT_LEVEL,  # the Crypt's door: no click takes it, the trip skipped, the game not left
        TZ_LOOT,  # the Mausoleum's trip from where the character stands: Blood Raven's loot
        TZ_NEXT_LEVEL,  # into the Mausoleum
    ]
    assert 18 in game.loop.agenda.finished  # the Crypt's trip over
    assert [call for call in game.calls if call[0] == 'door'] == [('door', 17), ('door', 19)]
    # The game's end with the Crypt's Bonebreaker alive: the loop stops for the player (tzloop.py BOSS_STAYS), never
    # a Save and Exit
    assert stops == [BONEBREAKER_LEFT]
    assert LEAVE not in legs
    assert set(game.runs) == {17, 19}  # the Mausoleum worked before the game's end
    assert 'Macro: loop: no click took Crypt: the trip to Crypt is skipped, the game is not left' in caplog.text


def test_the_last_trips_door_failing_ends_the_game_by_the_agenda(monkeypatch, caplog):
    game, hands = door_game(monkeypatch, refused=(18, 19))
    stops: list[str] = []
    with caplog.at_level('INFO'):
        legs = door_legs(game, hands, stops=stops)
    assert legs == [TZ_WAYPOINT, TZ_NEXT_LEVEL, TZ_LEVEL, TZ_NEXT_LEVEL, TZ_LOOT, TZ_NEXT_LEVEL]
    # no trip left after the Mausoleum's door: the game's end, as the agenda makes it, Bonebreaker alive: the loop stops
    assert stops == [BONEBREAKER_LEFT]
    assert {18, 19} <= game.loop.agenda.finished
    assert 19 not in game.runs
    assert 'no click took Mausoleum: the trip to Mausoleum is skipped' in caplog.text


def test_another_stop_on_the_way_on_still_leaves_the_game(monkeypatch):
    game, hands = door_game(monkeypatch, cause=None)
    with pytest.raises(Abort, match='no click took Crypt'):
        door_legs(game, hands)
    assert 18 not in game.loop.agenda.finished  # the runner's recovery leaves the game (stops.py RECOVER)


def test_a_door_no_click_takes_with_the_switch_off_still_leaves_the_game(monkeypatch):
    monkeypatch.setattr(tzloop, 'SKIP_DOOR', False)
    game, hands = door_game(monkeypatch)
    with pytest.raises(Abort, match='no click took Crypt') as stopped:
        door_legs(game, hands)
    assert stopped.value.cause == 'door'
    assert 18 not in game.loop.agenda.finished


# tzloop.py PORTAL_FIGHT_FIRST (rca/2026-10-22/portal-cast-findings.md): the Sling's Town Portal was cast with 5
# hostiles within 30 (09:30:05 on 2026-10-22) and with Fetishes striking at 3 units (22:26:32 on 2026-10-21); a block
# dropped it
FETISH = 142  # monstats fetish2


def fetish_near(game: Script) -> None:
    from inventory_tracking.game.records import Monster

    here = game.play.world.player
    assert here is not None
    foe = Monster(77, FETISH, 4, here.x + 3.0, here.y, life=128, max_life=128)
    game.play.world = replace(game.play.world, monsters=(foe,))


def portal_trip(monkeypatch, *, turned: bool = False) -> tuple[Script, list[str]]:
    from dataclasses import replace as changed

    monkeypatch.setattr(tzloop, '_portal_fights', {})
    game = Script(36, monkeypatch)
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    tzloop.trip(game.loop, GAME, 36)
    fetish_near(game)
    fought: list[str] = []

    def fight() -> None:
        fought.append('plain')
        game.level_run()

    def fight_back() -> None:
        fought.append('back')
        game.level_run()

    hands = changed(
        game.hands(),
        fight=fight,
        fight_back=fight_back,
        terrorized=lambda area: area in game.zone and not (turned and area == 36),  # its zone turned: 36 off it
    )
    game.hands = lambda visit=None: hands  # every leg the same hands
    return game, fought


def portals_cast(game: Script) -> list[tuple]:
    return [call for call in game.calls if call[0] == 'portal']


def test_a_town_portal_with_a_hostile_near_fights_first_then_is_cast(monkeypatch):
    game, fought = portal_trip(monkeypatch)
    # The second fight kills it: the read shows none near after it
    game.on_run = lambda area: game.go('stay', area) if len(game.runs) == 2 else None

    legs = [game.leg() for _ in range(3)]

    assert legs == [TZ_PORTAL, TZ_PORTAL, TZ_PORTAL]
    assert fought == ['back', 'back']  # the run against an attacker, twice
    assert game.runs == [36, 36]
    assert portals_cast(game) == [('portal', ROGUE_ENCAMPMENT)]  # cast once none is near


def test_a_hostile_that_stays_near_is_fought_portal_fights_times_then_the_portal_is_cast(monkeypatch):
    game, fought = portal_trip(monkeypatch)

    legs = [game.leg() for _ in range(tzloop.PORTAL_FIGHTS + 1)]

    assert legs == [TZ_PORTAL] * (tzloop.PORTAL_FIGHTS + 1)
    assert len(fought) == tzloop.PORTAL_FIGHTS
    assert portals_cast(game) == [('portal', ROGUE_ENCAMPMENT)]  # the bound: cast all the same


def test_on_a_level_no_longer_terrorized_the_plain_run_fights_before_the_portal(monkeypatch):
    # 09:30:05 on 2026-10-22: the zone turned mid-fight; the agenda's run ends at once there (choice.py ZONE_LEFT)
    from dataclasses import replace as changed

    game, fought = portal_trip(monkeypatch)
    hands = changed(game.hands(), terrorized=lambda area: False)  # The Worldstone Keep Level 3 at 09:30:05
    goal = game.loop.agenda.stack[-1]

    assert tzloop.portal_fight(game.play.run(), hands, GAME, goal)
    assert fought == ['plain']  # past nothing: what is near is fought
    game.play.world = at(36)  # fought: none near
    assert not tzloop.portal_fight(game.play.run(), hands, GAME, goal)
    assert fought == ['plain']


def test_with_the_switch_off_the_portal_is_cast_with_a_hostile_near(monkeypatch):
    game, fought = portal_trip(monkeypatch)
    monkeypatch.setattr(tzloop, 'PORTAL_FIGHT_FIRST', False)

    assert game.leg() == TZ_PORTAL
    assert fought == []
    assert portals_cast(game) == [('portal', ROGUE_ENCAMPMENT)]


# --- the game's bosses (macros/bossledger.py; tzloop.py BOSS_STAYS, BOSS_ZONES; 2026-10-22) ---


def test_a_level_only_crossed_is_no_bosss_but_an_act_bosss_level_always_is():
    # The player, 2026-10-22: "we should always kill act bosses, no need to kill hepasto if it is just travel through":
    # the Chaos Sanctuary alone terrorized (10-20 08:32-08:51), the River of Flame crossed to it
    sanctuary = tzroutine.itinerary(frozenset((108,)))
    assert sanctuary is not None
    assert tzloop.boss_scope(sanctuary) == frozenset((108,))
    worldstone = tzroutine.itinerary(frozenset((128, 129, 130, 131, 132)))
    assert worldstone is not None
    assert {131, 132} <= tzloop.boss_scope(worldstone)


def test_the_way_to_act_3s_last_town_is_not_taken_with_a_council_member_alive(monkeypatch, caplog):
    # Maffer Dragonhand left in Durance 3 in 11 games, the game ended through the Red portal after Mephisto
    # (rca/2026-10-22/boss-audit-findings.md §4 cause 4): the game's end (agenda.py `game_end`) asks the ledger
    from inventory_tracking.levels.model import Room

    game = Script(102, monkeypatch, zone=DURANCE)
    game.killed.add('Mephisto')
    game.progress.stood(102, 'Red portal')
    game.progress.looted(102)
    game.loop.agenda.begin(game.loop.observe(game.play.world))
    game.loop.agenda.ran(102)
    legs: list[str] = []

    def council() -> None:
        # The run read Durance 3's rooms: the Council's piece (macros/bossledger.py `rooms`); two of them killed
        game.loop.agenda.bosses.rooms(102, [Room(796, 100, 100, 24, 24, variant=0, block=(100, 100, 24, 24))])
        game.killed.update(('Bremm Sparkfist', 'Wyand Voidbringer'))

    with caplog.at_level('INFO'):
        stopped = until_stopped(game, legs, 6, council)
    assert stopped.cause == 'idle'
    assert str(stopped) == (
        'Town Portal home: the game ends in The Pandemonium Fortress, but Maffer Dragonhand (Durance of Hate Level 3) '
        'alive: the loop stops here for the player'
    )
    assert [call for call in game.calls if call[0] != 'prebuff'] == []  # stopped in Durance 3
    assert 'Save and Exit' not in game.play.said


def test_a_door_to_a_boss_alive_is_tried_its_tries_then_the_loop_stops_for_the_player(monkeypatch, caplog):
    # SKIP_DOOR blocked a door at once (Bonebreaker's Crypt, 10-21 07:56-08:06); with its boss alive it is tried
    # USE_TRIES times, the game kept, then the loop stops naming him (`boss_stays`), the game never left
    from inventory_tracking.macros import zonenav

    monkeypatch.setattr(zonenav, 'ROTATION', True)
    game, hands = door_game(monkeypatch)
    stops: list[str] = []
    with caplog.at_level('INFO'):
        legs = door_legs(game, hands, count=30, stops=stops)
    assert stops == ['Crypt: no click took its door (no click took Crypt): Bonebreaker (Crypt) alive: the loop stops '
                     'here for the player']  # fmt: skip
    assert caplog.text.count('a boss alive there: the game is not left') == tzloop.USE_TRIES - 1
    assert LEAVE not in legs
    assert 18 not in game.loop.agenda.blocked
