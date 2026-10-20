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

from inventory_tracking.macros import actloop, acts, terrorize, tzroutine
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.loop import ACT_KINDS, LEAVE
from inventory_tracking.macros.tzroutine import Itinerary, itinerary, trips_said
from inventory_tracking.routes.model import ENTER, FIGHT, LOOT, STAND, USE
from inventory_tracking.routes.tz_groups import manual_zone
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


class ActGame:
    """A game of act `act`'s kind (loop.py ACT_KINDS) from `area` (the Fortress by default): the tracker reads
    `rotation` (the client's list never names the act: it is planned from the shard's use, as live), the stash holds
    `shards` of the act's shard, and the shard's clicks take (`outcome` 'used'), or not ('failed'). A level run does
    its level's route stages by itself (`WORK`: the fights won, objects used, stands made, loot taken) up to a way on;
    `on_run(area)` may do more."""

    def __init__(
        self,
        act: int,
        monkeypatch: pytest.MonkeyPatch,
        rotation: frozenset[int] | None = None,
        area: int = FORTRESS,
        shards: int = 97,
        outcome: str = 'used',
    ):
        force_ready(monkeypatch, act)
        self.act = act
        self.game = Script(area, monkeypatch, zone=ROTATION[act] if rotation is None else rotation)
        self.game.loop.kind = ACT_KINDS[f'act{act}']
        shard = SHARD_OF[act]
        self.game.play.stash_pages = [('.' * 10,) * 10]
        self.game.play.stacks = {shard: shards}
        self.kills: list[str] = []
        self.shard: list[int] = []
        self.on_run = lambda area: None
        monkeypatch.setattr(terrorize, 'CLICKS', True)

        def used(run, key, act, terrorized):
            self.shard.append(act)
            if outcome != 'used':
                return None
            self.game.play.stacks[shard] -= 1
            return terrorize.Used(shard, act, shards, shards - 1, gone=True, listed=False)

        monkeypatch.setattr(actloop, 'terrorize', used)
        self.game.on_run = self._work

    def _work(self, area: int) -> None:
        progress = self.game.progress
        for _ in range(20):
            step = progress.step(area)
            if step is None or step.stage.kind not in WORK or step.stage.to:
                break
            stage = step.stage
            if stage.kind == FIGHT:
                self.game.killed.add(stage.boss)
                if stage.boss:
                    self.kills.append(stage.boss)
            elif stage.kind == USE:
                progress.facts = replace(progress.facts, finished=progress.facts.finished | {(area, stage.mark)})
            elif stage.kind == STAND:
                progress.stood(area, stage.mark)
            else:
                progress.looted(area)
        self.on_run(area)

    def way_on(self) -> None:
        """The runner's way on (running/legs.py `_way_on`): at a stage into a level (a door, a portal used: the
        Cairn Stones' into Tristram) through it, else the level run to it."""
        step = self.game.progress.step(self.game.area)
        if step is not None and step.stage.kind in (ENTER, USE) and step.stage.to:
            self.game.door()
        else:
            self.game.level_run()

    def play(self, legs: int = 300) -> Walk:
        """The game's legs until it is left (LEAVE), a leg stops it (`Walk.stopped`, `Walk.where`), or `legs` are
        made."""
        hands = replace(self.game.hands(), way_on=self.way_on)
        made: list[str] = []
        stopped = where = None
        for _ in range(legs):
            if not self.game.play.world.in_game:
                break
            try:
                made.append(self.game.loop.leg(self.game.play.run(), keys, self.game.progress, hands))
            except Abort as error:
                stopped, where = str(error), self.game.area
                break
            if made[-1] == LEAVE:
                break
        moves = [(call[0], call[1]) for call in self.game.calls if call[0] != 'prebuff']
        return Walk(made, moves, list(self.game.runs), list(self.kills), list(self.shard), stopped, where)
