"""The act scripts' test harness (macros/acts/; routes/act-terrorize-plan.md §11): an act's itinerary, and a shard act
game walked leg by leg over test_tzloop.py's scripted game, its waypoints, level runs, boss kills and the shard step
recorded in order. Offline: the order of the goals is what is checked, not the game's own behaviour.

    plan = plan_of(monkeypatch, 4, rotation=CATACOMBS)       # the act's script forced ready
    assert trips_of(plan)[0] == ('Diablo', 107, (107, 108))
    walk = ActGame(4, monkeypatch).play()
    assert walk.stopped is None
    assert walk.shard == [4]
    assert walk.waypoints[:3] == [107, 107, 106]
    assert walk.kills[-1] == 'Izual'
"""

from dataclasses import dataclass, replace

import pytest

from inventory_tracking.macros import actloop, acts, terrorize, tzroutine, zonenav
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import ACT_KINDS, LEAVE
from inventory_tracking.macros.tzroutine import Itinerary, itinerary, trips_said
from inventory_tracking.routes.model import ENTER, FIGHT, LOOT, STAND, USE
from inventory_tracking.routes.tz_groups import manual_zone
from inventory_tracking.routes.zone_graph import WALK as WALK_WAY, way
from inventory_tracking.terror.elites import table
from tests.inventory_tracking.macros.test_tzloop import CATACOMBS, FORTRESS, Script, keys


# The act's shard class (terrorize.py SHARDS, inverted)
SHARD_OF = {act: shard for shard, act in terrorize.SHARDS.items()}
# The rotation read with the act by default: a zone of another act (the union's trips come after the act's)
STEPPES = frozenset((104, 105))
ROTATION = {1: STEPPES, 2: CATACOMBS, 3: CATACOMBS, 4: CATACOMBS, 5: CATACOMBS}
# Stage kinds a level run does by itself in the walk (a fight's boss killed, an object used, a stand made, the loot)
WORK = (FIGHT, USE, STAND, LOOT)


def force_ready(monkeypatch: pytest.MonkeyPatch, act: int) -> None:
    """Act `act`'s script played as if ready (its own test runs before `ready=True`), the itinerary cache cleared."""
    script = acts.script_of(act)
    assert script is not None, f'no script for act {act}'
    monkeypatch.setitem(acts.SCRIPTS, act, replace(script, ready=True))
    tzroutine.itinerary.cache_clear()


def plan_of(monkeypatch: pytest.MonkeyPatch, act: int, rotation: frozenset[int] = frozenset()) -> Itinerary:
    """The itinerary of act `act` terrorized (its core read) with `rotation` read too, by the act's script."""
    force_ready(monkeypatch, act)
    zone = manual_zone(act)
    assert zone is not None
    plan = itinerary(zone.core | rotation)
    assert plan is not None
    return plan


def trips_of(plan: Itinerary) -> list[tuple[str, int, tuple[int, ...]]]:
    """(route, waypoint, levels) of each excursion, in order."""
    return [(trip.route, trip.waypoint, trip.areas) for trip in plan.excursions]


def line_of(plan: Itinerary) -> str:
    """The excursions as the plan's log line says them (`Macro: tz: zone <name>: <this>; skipped ...`)."""
    return trips_said(plan.excursions)


@dataclass
class Walk:
    """A walked game: the legs made, the moves (waypoint, door, portal, walk out: (what, level)), the level runs in
    order, the bosses killed in order, the acts terrorized by the shard step; `stopped` the Abort that stopped the
    walk (None: the game was left, or the legs ran out) and `where` the level it stopped on."""

    legs: list[str]
    moves: list[tuple[str, int]]
    runs: list[int]
    kills: list[str]
    shard: list[int]
    stopped: str | None = None
    where: int | None = None

    @property
    def waypoints(self) -> list[int]:
        return [area for what, area in self.moves if what == 'waypoint']

    @property
    def levels(self) -> list[int]:
        """The levels run, each at its first run."""
        return list(dict.fromkeys(self.runs))


# The order the Canyon of the Magi's tomb entrances come nearest in (a tour's marks, routes/model.py `tour`): which
# mark leads into which tomb is not known to the route
NEAREST_TOMBS = (69, 66, 72, 67, 71, 68, 70)
# The true tomb, the one Tal Rasha's tomb whose rooms hold the Orifice (levels/handlers/tal_rasha.py `orifice`): by
# default the third nearest, as test_act2_duriel.py's fixture. Every other tomb is read without it on arrival (the card
# goal's `absent`: the client holds every room of the level from its entry), so its Orifice `use` into Duriel's Lair
# is done there (routes/progress.py `done`); in the true tomb that `use` is its way on, through the portal
TOMBS = frozenset(range(66, 73))
TRUE_TOMB = 72
ORIFICE = 'Orifice'


class ZoneWalk:
    """A terror zone game of loop kind `kind` (TZ+ by default) from `area` (the Fortress by default), the tracker
    reading `zone`. A level run does its level's route stages by itself (`WORK`: the fights won, objects used, stands
    made, loot taken) up to a way on; `on_run(area)` may do more. A tour's way on goes through the nearest of its marks
    not yet gone through into a level not entered (`tour_order`), noted as macros/route.py `note_toured` does. A Tal
    Rasha's tomb but `true_tomb` (None: none) is read without the Orifice (`TRUE_TOMB`)."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        zone: frozenset[int],
        kind=None,
        area: int = FORTRESS,
        tour_order: tuple[int, ...] = NEAREST_TOMBS,
        true_tomb: int | None = TRUE_TOMB,
    ):
        self.game = Script(area, monkeypatch, zone=zone)
        self.true_tomb = true_tomb
        if kind is not None:
            self.game.loop.kind = kind
        self.kills: list[str] = []
        self.shard: list[int] = []
        self.on_run = lambda area: None
        self.tour_order = tour_order
        self.made: list[str] = []
        self.game.on_run = self._work

    def _read(self, area: int) -> None:
        """The level's rooms read on arrival: a tomb but the true one holds no Orifice (`TRUE_TOMB`)."""
        if area in TOMBS and area != self.true_tomb:
            self.game.progress.absent(area, ORIFICE)

    def _work(self, area: int) -> None:
        self._read(area)
        progress = self.game.progress
        fought = False
        for _ in range(20):
            step = progress.step(area)
            if step is not None and step.stage.kind == USE and step.stage.mark == ORIFICE and step.stage.to:
                # The true tomb's run ends through the Orifice's portal (its `use` the run's goal, the portal a
                # `leaves` object: macros/teleport.py DURIEL_PORTAL), as the Stony Field's run through the Cairn Stones
                self.game.go('portal', step.stage.to)
                break
            if step is None or step.stage.kind not in WORK or step.stage.to:
                break
            stage = step.stage
            if stage.kind == FIGHT:
                self.game.killed.add(stage.boss)
                fought = True
                if stage.boss:
                    self.kills.append(stage.boss)
            elif stage.kind == USE:
                progress.facts = replace(progress.facts, finished=progress.facts.finished | {(area, stage.mark)})
            elif stage.kind == STAND:
                progress.stood(area, stage.mark)
            else:
                progress.looted(area)
        if fought:
            # The bosses a script brings to the level die in its fights too (terror/data/elites.json `scripted`: the
            # Throne's waves with Lister, as live since 10-21 16:23), so the game's boss ledger (macros/bossledger.py)
            # holds none of them alive after them
            self.game.killed.update(table().scripted.get(area, ()))
        self.on_run(area)

    def way_on(self) -> None:
        """The runner's way on (running/legs.py `_way_on`): at a stage into a level (a door, a portal used: the
        Cairn Stones' into Tristram) through it; at a tour's, through its nearest mark not yet gone through
        (`tour_order`); else the level run to it."""
        game = self.game
        self._read(game.area)
        step = game.progress.step(game.area)
        if step is not None and step.stage.kind == ENTER and step.stage.tours:
            area, mark = game.area, step.stage.mark
            used = {place for level, label, place in game.progress.facts.used if (level, label) == (area, mark)}
            order = [*self.tour_order, *step.stage.tours]
            level = next(each for each in order if each in step.stage.tours and (float(each), 0.0) not in used)
            game.progress.used(area, mark, (float(level), 0.0), ())
            game.go('door', level)
        elif step is not None and step.stage.kind in (ENTER, USE) and step.stage.to:
            game.door()
        else:
            game.level_run()

    def play(self, legs: int = 300, visit=None, until=None) -> Walk:
        """The game's legs until it is left (LEAVE), a leg stops it (`Walk.stopped`, `Walk.where`), `until(game)`
        holds after a leg (the test's moment: a restart), or `legs` are made; `visit` the town visit's hand (a room
        package's). The walk's lists are the game's whole so far."""
        hands = replace(self.game.hands(visit), way_on=self.way_on)
        made = self.made
        stopped = where = None
        for _ in range(legs):
            if not self.game.play.world.in_game or (until is not None and made and until(self.game)):
                break
            try:
                made.append(self.game.loop.leg(self.game.play.run(), keys, self.game.progress, hands))
            except Abort as error:
                stopped, where = str(error), self.game.area
                break
            if made[-1] == LEAVE:
                break
        moves = [(call[0], call[1]) for call in self.game.calls if call[0] != 'prebuff']
        return Walk(list(made), moves, list(self.game.runs), list(self.kills), list(self.shard), stopped, where)


class ActGame(ZoneWalk):
    """A game of act `act`'s kind (loop.py ACT_KINDS) from `area` (the Fortress by default): the tracker reads
    `rotation` (the client's list never names the act: it is planned from the shard's use, as live), the stash holds
    `shards` of the act's shard, and the shard's clicks take (`outcome` 'used'), or not ('failed'); `true_tomb` as
    ZoneWalk's."""

    def __init__(
        self,
        act: int,
        monkeypatch: pytest.MonkeyPatch,
        rotation: frozenset[int] | None = None,
        area: int = FORTRESS,
        shards: int = 97,
        outcome: str = 'used',
        true_tomb: int | None = TRUE_TOMB,
    ):
        force_ready(monkeypatch, act)
        self.act = act
        zone = ROTATION[act] if rotation is None else rotation
        super().__init__(monkeypatch, zone, ACT_KINDS[f'act{act}'], area, true_tomb=true_tomb)
        shard = SHARD_OF[act]
        self.game.play.stash_pages = [('.' * 10,) * 10]
        self.game.play.stacks = {shard: shards}
        monkeypatch.setattr(terrorize, 'CLICKS', True)

        def used(run, key, act, terrorized):
            self.shard.append(act)
            if outcome != 'used':
                return None
            self.game.play.stacks[shard] -= 1
            # The act's levels read terrorized from here, as live (349 "is worked tz+" runs on 2026-10-23..24, the
            # client's list naming the shard acts at 11:00:04 on 2026-10-24): a level read not terrorized is the zone
            # left (hunting/choice.py ZONE_LEFT, tzloop.py MANUAL_TURNED), its run going to nothing
            terror = manual_zone(act)
            if terror is not None:
                self.game.zone = self.game.zone | frozenset(terror.areas)
                self.game.progress.wanted = lambda level: level in self.game.zone
            return terrorize.Used(shard, act, shards, shards - 1, gone=True, listed=False)

        monkeypatch.setattr(actloop, 'terrorize', used)


def crossing[Walked: ZoneWalk](walk: Walked) -> Walked:
    """`walk` with its open passages (routes/zone_graph.py WALK: Upper Kurast - Kurast Causeway, River of Flame -
    Chaos Sanctuary) crossed as the live run crosses them (pursuit.py `to_the_door`): walked through when the run's
    `allowed` levels (running/legs.py `_trip_levels`: zonenav.py `allowed`) hold the level across, else the run ends
    "leads off the trip" where it stands, no level changed (13:48:00 on 2026-10-21, "TZ next level again and again")."""
    doors = walk.way_on

    def way_on() -> None:
        game = walk.game
        here = game.area
        step = game.progress.step(here)
        to = step.stage.to if step is not None and step.stage.kind == ENTER else 0
        if to and way(here, to).kind == WALK_WAY:
            plan = game.loop.agenda.plan
            levels = zonenav.allowed(zonenav.graph_of(plan), here) if zonenav.on(plan) else None
            if levels is not None and to not in levels:
                return  # "<level> leads off the trip: going through takes a press": the run over, no move
            game.go('walk', to)
            return
        doors()

    walk.way_on = way_on
    return walk
